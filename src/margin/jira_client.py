import logging
from typing import Optional

import requests

from margin.config import JiraConfig
from margin.models import Advisor, MarginItem

logger = logging.getLogger(__name__)


class JiraClient:
    def __init__(self, config: JiraConfig):
        self.config = config
        self.session = requests.Session()
        self.session.auth = (config.user_email, config.api_token)
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
        })
        self.base_url = config.base_url.rstrip("/")

    def create_ticket(self, item: MarginItem, advisor: Optional[Advisor] = None) -> str:
        """Create a Jira ticket for a margin call item. Returns the ticket key."""
        summary = f"Margin Call - {item.account_number} - {item.error_type}"

        description_lines = [
            f"Account Number: {item.account_number}",
            f"Error Type: {item.error_type}",
            f"Date: {item.date}",
            f"Amount: ${item.dollar_amount:,.2f}",
        ]
        if advisor:
            description_lines.append(f"Firm: {advisor.firm_name}")
            description_lines.append(f"Advisor Email: {advisor.email}")

        # Jira Cloud API v3 uses Atlassian Document Format
        description_content = []
        for line in description_lines:
            description_content.append({
                "type": "paragraph",
                "content": [{"type": "text", "text": line}],
            })

        payload = {
            "fields": {
                "project": {"key": self.config.project_key},
                "issuetype": {"name": self.config.issue_type},
                "summary": summary,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": description_content,
                },
                "labels": ["margin-call", item.error_type.lower().replace(" ", "-")],
            }
        }

        url = f"{self.base_url}/rest/api/3/issue"
        resp = self.session.post(url, json=payload)
        resp.raise_for_status()
        ticket_key = resp.json()["key"]
        logger.info(f"Created Jira ticket {ticket_key} for account {item.account_number}")
        return ticket_key
