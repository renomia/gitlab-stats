import argparse
import csv
import sys
from collections import OrderedDict
from datetime import datetime

import gitlab
import inquirer
import yaml
from dateutil import parser


def log(msg):
	print(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + ' | ' + msg)


def is_within_period(str_test, str_from, str_to):
	dt_test = parser.parse(str_test)
	dt_from = parser.parse(str_from)
	dt_to = parser.parse(str_to)
	return dt_from <= dt_test <= dt_to


def list_instances(config):
	return list(config.keys())


def choose_instance(insts):
	if not sys.stdin.isatty():
		print("Non-interactive terminal detected. Please run the script with the instance argument.")
		print("Available instances:", ", ".join(insts))
		exit(1)

	questions = [
		inquirer.List('instance', message="Choose an instance", choices=insts + ["Quit"])
	]
	answers = inquirer.prompt(questions)
	if answers['instance'] == "Quit":
		print("Exiting...")
		exit(0)
	return answers['instance']


# parse command-line arguments
cmdparser = argparse.ArgumentParser(description='GitLab Stats Script')
cmdparser.add_argument('instance', nargs='?', help='Instance to fetch config for')
args = cmdparser.parse_args()

# load configuration
with open('config.yaml', 'r') as config_file:
	conf = yaml.safe_load(config_file)

# determine instance
if args.instance:
	instance = args.instance
else:
	instances = list_instances(conf)
	instance = choose_instance(instances)

# process config
url_root = conf[instance]["url_root"]
token = conf[instance]["token"]
include_path = conf[instance]["include_path"]
exclude_path = conf[instance]["exclude_path"]
commit_stats_exclude_groups = conf[instance]["commit_stats_exclude_groups"]
commit_stats_exclude_projects = conf[instance]["commit_stats_exclude_projects"]
if "stats_year" in conf[instance] and conf[instance]["stats_year"] > 0:
	stats_year = conf[instance]["stats_year"]
	stats_from = '{year}-01-01T00:00:00Z'.format(year=stats_year)
	stats_to = '{year}-12-31T23:59:59Z'.format(year=stats_year)
else:
	stats_year = 0
	stats_from = conf[instance]["stats_from"]
	stats_to = conf[instance]["stats_to"]
if "from_project_id" in conf[instance]:
	from_project_id = conf[instance]["from_project_id"]
else:
	from_project_id = 0

# let's go
log("Instance " + instance)
if stats_year > 0:
	log("Stats for year " + str(stats_year))
	filename = 'out/gitlab-stats-{instance}-{year}.csv'.format(instance=instance, year=stats_year)
else:
	log("Stats for period from " + stats_from + " to " + stats_to)
	filename = 'out/gitlab-stats-{instance}-from-{stats_from}-to-{stats_to}.csv'.format(instance=instance,
																						stats_from=stats_from,
																						stats_to=stats_to)
if from_project_id > 0:
	log("Appending to {filename}, starting from project id {id}".format(filename=filename, id=from_project_id))
	file_write_mode = 'at'
else:
	log("Overwriting file {filename}".format(filename=filename))
	file_write_mode = 'wt'

with open(filename, mode=file_write_mode, encoding='utf-8') as out_file:
	cert_list_fieldnames = ["stats_from", "stats_to", "gl_instance", "project_id", "project_name", "project_path",
							"commits", "commits_additions", "commits_deletions", "mrs", "releases", "tags", "pipelines",
							"pipelines_duration"]
	writer = csv.DictWriter(
		out_file,
		fieldnames=cert_list_fieldnames,
		lineterminator='\n')
	if from_project_id == 0:
		writer.writeheader()

	gl = gitlab.Gitlab(url_root, private_token=token)
	groups = gl.groups.list(all=True)
	log("Got {group_count} groups".format(group_count=len(groups)))
	projects = {}  # buffer dictionary of projects, to ba able to sort them by ids outside groups
	for group in groups:

		# check include_path rule
		if include_path != '':
			if include_path not in group.full_path:
				log("Skipping group {fp} because include_path {ip} excludes it".format(fp=group.full_path,
																					   ip=include_path))
				continue

		# check exclude_path rule
		if exclude_path != '':
			if exclude_path in group.full_path:
				log("Skipping group {fp} because exclude_path {ep} requires it".format(fp=group.full_path,
																					   ep=exclude_path))
				continue

		group_projects = group.projects.list(all=True, lazy=True)
		for group_project in group_projects:
			log("Adding project {project_path} to the buffer".format(
				project_path=group_project.attributes['path_with_namespace']))
			# add project to the buffer dictionary of projects with id as key and name and path_with_namespace as keys
			projects[group_project.attributes['id']] = {
				"name": group_project.attributes['name'],
				"path_with_namespace": group_project.attributes['path_with_namespace']
			}

	# sort projects dictionary by keys
	project_ids = list(projects.keys())
	project_ids.sort()

	log("Got {project_count} projects to fetch details for".format(project_count=len(project_ids)))

	for project_id in project_ids:

		if from_project_id > 0 and project_id < from_project_id:
			log("Skipping project {project_path} id {id} because threshold is set to {from_project_id}".format(
				project_path=projects[project_id].get('path_with_namespace'), id=project_id,
				from_project_id=from_project_id))
			continue

		log("Getting details of project {project_path} (id {id})".format(
			project_path=projects[project_id].get('path_with_namespace'), id=project_id))

		# get project detail
		project_detail = gl.projects.get(project_id)

		# skip projects with repository_access_level = 'disabled'
		if project_detail.repository_access_level == 'disabled':
			log("Repository_access_level is 'disabled', skipping to next iteration")
			continue

		# get commits
		c = 0  # init counter
		c_add = 0  # init counter
		c_del = 0  # init counter
		commits = project_detail.commits.list(since=stats_from, get_all=True)
		for commit in commits:
			if is_within_period(commit.created_at, stats_from, stats_to):
				c = c + 1
				# skip extracting commit stats if this GROUP is on abuse blacklist
				if group.full_path in commit_stats_exclude_groups:
					log("Skipping commit stats extraction for project {pp} because group {gp} is on group abusers blackist".format(
						pp=projects[project_id].get('path_with_namespace'), gp=group.full_path
					))
					continue
				# skip extracting commit stats if this PROJECT is on abuse blacklist
				if projects[project_id].get('path_with_namespace') in commit_stats_exclude_projects:
					log("Skipping commit stats extraction for project {pp} because it is on project abusers blackist".format(
						pp=projects[project_id].get('path_with_namespace')
					))
					continue
				commit_detail = project_detail.commits.get(commit.short_id)
				c_add = c_add + commit_detail.stats["additions"]
				c_del = c_del + commit_detail.stats["deletions"]

		# get accepted merge requests
		m = 0  # init counter
		mrs = project_detail.mergerequests.list(state='merged', order_by='updated_at', get_all=True)
		for mr in mrs:
			if is_within_period(mr.created_at, stats_from, stats_to):
				m = m + 1

		# pipelines
		p = 0  # init counter
		p_dur = 0  # init counter
		pipelines = project_detail.pipelines.list(all=True, lazy=True)
		for pipeline in pipelines:
			if is_within_period(pipeline.created_at, stats_from, stats_to):
				p = p + 1
				pipeline_detail = project_detail.pipelines.get(pipeline.id)
				p_dur = p_dur + int(pipeline_detail.duration or 0)

		# tags
		t = 0  # init counter
		tags = project_detail.tags.list(all=True, lazy=True)
		for tag in tags:
			if is_within_period(tag.commit["created_at"], stats_from, stats_to):
				t = t + 1

		# releases
		r = 0  # init counter
		releases = project_detail.releases.list(all=True, lazy=True)
		for release in releases:
			if is_within_period(release.created_at, stats_from, stats_to):
				r = r + 1

		row_out = OrderedDict()
		row_out["stats_from"] = parser.parse(stats_from).strftime("%Y-%m-%d")
		row_out["stats_to"] = parser.parse(stats_to).strftime("%Y-%m-%d")
		row_out["gl_instance"] = instance
		row_out["project_id"] = project_id
		row_out["project_name"] = projects[project_id].get('name')
		row_out["project_path"] = projects[project_id].get('path_with_namespace')
		row_out["commits"] = c
		row_out["commits_additions"] = c_add
		row_out["commits_deletions"] = c_del
		row_out["mrs"] = m
		row_out["pipelines"] = p
		row_out["pipelines_duration"] = p_dur
		row_out["tags"] = t
		row_out["releases"] = r

		writer.writerow(row_out)
