# Data Quality Automation for GCP (automation_jira_quality)

## Overview

This project automates data quality checks on BigQuery tables using Google Cloud Dataplex, and integrates with Jira and Microsoft Teams for alerting and incident management. It is designed to be run as a job (e.g., via Cloud Run or Docker) and is configurable via YAML files stored in Google Cloud Storage (GCS).

## Project Structure

```
automation_jira_quality/
├── main.py                # Main entry point for running the data quality job
├── utils/
│   └── utils.py           # Core logic: GCP, Dataplex, Teams, Jira integration, config parsing
├── requirements.txt       # Python dependencies
├── Dockerfile             # Containerization setup
├── docker-compose.yaml    # (Optional) Local container orchestration
├── .gitlab-ci.yml         # CI/CD pipeline configuration
├── changelog.md           # Project changelog
├── Procfile               # Process type declaration (for some PaaS)
└── README.md              # Project documentation
```

## Main Features

- **Automated Data Quality Scans**: Launches and manages Dataplex DataScan jobs on BigQuery tables, using YAML-based configuration files from GCS.
- **Configurable via GCS**: Reads job and scan configuration from YAML files stored in a GCS bucket.
- **Notification System**: Sends alerts to Microsoft Teams channels when data quality checks fail, including summary and direct links.
- **Jira Integration**: Automatically creates or updates Jira issues (cards) for failed data quality checks, grouping repeated failures and managing issue status transitions.
- **Secret Management**: Securely retrieves credentials and webhook URLs from Google Secret Manager.
- **Extensible and Modular**: All core logic is in `utils/utils.py`, making it easy to extend for new notification or ticketing systems.

## How It Works

1. **Startup**: The job is started (e.g., via Docker, Cloud Run, or directly with Python). The main entry point is `main.py`.
2. **Argument Parsing**: Command-line arguments specify the GCS bucket and blob for the config, and project metadata (labels, etc).
3. **Config Loading**: The config YAML is loaded from GCS, and merged with runtime arguments.
4. **Data Quality Scan**: The job launches a Dataplex DataScan on the specified BigQuery table, using the rules and settings from the config.
5. **Result Handling**: If the scan fails, a notification is sent to MS Teams and a Jira card is created or updated. The system tracks repeated failures and manages Jira card status transitions.
6. **Secrets**: All sensitive information (API tokens, webhook URLs) is retrieved securely from Google Secret Manager.

## Example Usage

```bash
python main.py <configbucket> <configblob> <projectid> [--labelapplication ...] [--labelcostcenter ...] [--labelenvironment ...]
```

- `configbucket`: Name of the GCS bucket containing the config files
- `configblob`: Path to the YAML config file in the bucket
- `projectid`: GCP project ID
- Optional labels for application, cost center, and environment

## Dependencies
- Python 3.9+
- Google Cloud Dataplex, Storage, Secret Manager
- Jira Python client
- pymsteams
- PyYAML

See `requirements.txt` for the full list.

## Extending
- To add new notification channels or ticketing systems, extend the logic in `utils/utils.py`.
- To add new data quality rules, update the YAML config schema and Dataplex scan logic.

## Authors and Acknowledgments
- See `changelog.md` for contributors and version history.

## License
None

## Project Status
Active development. Contributions welcome!
