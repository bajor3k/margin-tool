import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import yaml
from dotenv import load_dotenv


@dataclass
class JiraConfig:
    base_url: str = ""
    project_key: str = ""
    issue_type: str = "Task"
    api_token: str = ""
    user_email: str = ""


@dataclass
class OutlookConfig:
    tenant_id: str = ""
    client_id: str = ""
    client_secret: str = ""
    sender: str = ""


@dataclass
class Config:
    margin_file: str = ""
    advisor_file: str = ""
    error_types: List[str] = field(default_factory=list)
    tracker_db: str = "./processed.db"
    email_template: str = "./templates/margin_email.html"
    attachments: List[str] = field(default_factory=list)
    margin_file_header_row: int = 0
    jira: JiraConfig = field(default_factory=JiraConfig)
    outlook: OutlookConfig = field(default_factory=OutlookConfig)


def load_config(config_path: str) -> Config:
    """Load configuration from YAML file and overlay environment variables."""
    load_dotenv()

    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(
            f"Config file not found: {config_path}\n"
            f"Copy config.yaml.example to config.yaml and update the values."
        )

    with open(config_file) as f:
        raw = yaml.safe_load(f) or {}

    jira_raw = raw.get("jira", {})
    outlook_raw = raw.get("outlook", {})

    jira = JiraConfig(
        base_url=jira_raw.get("base_url", ""),
        project_key=jira_raw.get("project_key", ""),
        issue_type=jira_raw.get("issue_type", "Task"),
        api_token=os.environ.get("JIRA_API_TOKEN", ""),
        user_email=os.environ.get("JIRA_USER_EMAIL", ""),
    )

    outlook = OutlookConfig(
        tenant_id=os.environ.get("GRAPH_TENANT_ID", outlook_raw.get("tenant_id", "")),
        client_id=os.environ.get("GRAPH_CLIENT_ID", ""),
        client_secret=os.environ.get("GRAPH_CLIENT_SECRET", ""),
        sender=outlook_raw.get("sender", ""),
    )

    return Config(
        margin_file=raw.get("margin_file", ""),
        advisor_file=raw.get("advisor_file", ""),
        error_types=[e.upper() for e in raw.get("error_types", [])],
        tracker_db=raw.get("tracker_db", "./processed.db"),
        email_template=raw.get("email_template", "./templates/margin_email.html"),
        attachments=raw.get("attachments", []),
        margin_file_header_row=raw.get("margin_file_header_row", 0),
        jira=jira,
        outlook=outlook,
    )
