# GitLab Dev Stats

## Description

This script fetches and processes statistics from GitLab projects, including number of commits, lines of code added and deleted, number of merged MRs, number of pipelines and their duration, number of tags created and number of releases.

## Features

- Fetches project details from GitLab
- Filters projects based on include and exclude paths
- Collects statistics on commits, merge requests, pipelines, tags, and releases
- Outputs results to a CSV file

## Usage

1. Clone the repository:
   ```shell
   git clone https://github.com/yourusername/gitlab-stats.git
   cd gitlab-stats
   ```
2. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
3. Update config.yaml with your configuration values. See Configuration section for details.
4. Run the script:
   ```sh
   # with configured instance to process as commandline argument
   python gitlab-stats.py my_gitlab_instance
   # or in interactive python mode without specifying an instance - you will be prompted to select one
   python gitlab-stats.py
   ```

## Requirements

- Python 3.x
- Python packages: see requirements.txt
- GitLab API access (personal access token with read access)

## Configuration

Configuration values are stored in `config.yaml`. Update this file with your GitLab instance details and other settings. You can configure several gitlab instances for your convenience and reference the particular instance  when the script is run.

### Some notable configuration values

- `url_root`: The root URL of your GitLab instance.
- `token`: Your GitLab personal access token.
- `stats_from`: The start date for the statistics. Format: `YYYY-MM-DDTHH:MM:SSZ`
- `stats_to`: The end date for the statistics. Format: `YYYY-MM-DDTHH:MM:SSZ`
- `stats_year`: The year for the statistics. If this is specified, stats from and to are ignored. Format: `YYYY`
- `from_project_id`: The project ID to start fetching statistics from. This serves well if your GitLab instance times out during lengthy fetch and you want to continue where you last left off. Set to 0 to fetch all projects.
- `include_path`: Only include projects within this path. If left empty, all groups and projects in the instance are processed.
- `exclude_path`: Exclude projects and groups within this path.
- `commit_stats_exclude_groups`: Exclude groups from commit statistics. This is useful if you have groups that you don't want to include in the commit statistics as they would distort your stats. Probably very rarely used (I had to once).
- `commit_stats_exclude_projects`: Same as above but projects. This is more likely to be used. For example, you might have a project that is a fork of another project and you don't want to include it in the stats.

### Example config.yaml

Provided in this project as `config-demo.yaml` for your convenience.

```yaml
my_gitlab_instance_1:
  url_root: "https://gitlab.com/"
  token: "glpat-xxx"
  stats_from: "2024-01-01T00:00:00Z"
  stats_to: "2024-01-31T23:59:59Z"
  from_project_id: 0
  include_path: ""
  exclude_path: ""
  commit_stats_exclude_groups: []
  commit_stats_exclude_projects: []

my_gitlab_instance_2:
  url_root: "https://gitlab.yourcompany.com/"
  token: "glpat-xxx"
  stats_year: "2024"
  include_path: "core/backend"
  exclude_path: ""
  commit_stats_exclude_groups:
    - "core/backend/obsolete"
  commit_stats_exclude_projects:
    - "core/backend/p1"
    - "core/backend/p2"
```

- `my_gitlab_instance_1` is an example of a configuration for a SaaS GitLab instance. It fetches statistics for the entire instance the user (represented by token) has access to from January 1, 2024 to January 31, 2024.
- `my_gitlab_instance_2` is an example of a configuration for a self-hosted GitLab instance hosted on gitlab.yourcompany.com. It fetches statistics for the year 2024 for projects under the path core/backend, excluding projects in the group core/backend/obsolete and projects core/backend/p1 and core/backend/p2. 

## License

This project is licensed under the MIT License.