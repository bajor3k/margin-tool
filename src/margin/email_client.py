import base64
import logging
from pathlib import Path
from typing import List, Optional

import msal
import requests

from margin.config import OutlookConfig
from margin.models import Advisor, MarginItem

logger = logging.getLogger(__name__)


class OutlookClient:
    def __init__(self, config: OutlookConfig):
        self.config = config
        self.app = msal.ConfidentialClientApplication(
            config.client_id,
            authority=f"https://login.microsoftonline.com/{config.tenant_id}",
            client_credential=config.client_secret,
        )
        self.sender = config.sender

    def _get_token(self) -> str:
        result = self.app.acquire_token_for_client(
            scopes=["https://graph.microsoft.com/.default"]
        )
        if "access_token" not in result:
            error = result.get("error_description", result.get("error", "Unknown error"))
            raise RuntimeError(f"Failed to acquire Graph API token: {error}")
        return result["access_token"]

    def _render_template(
        self,
        template_path: str,
        advisor: Advisor,
        item: MarginItem,
        jira_key: Optional[str] = None,
    ) -> str:
        """Render the email HTML template with item details."""
        template = Path(template_path).read_text()
        replacements = {
            "{{firm_name}}": advisor.firm_name,
            "{{account_number}}": item.account_number,
            "{{error_type}}": item.error_type,
            "{{date}}": str(item.date),
            "{{dollar_amount}}": f"${item.dollar_amount:,.2f}",
            "{{jira_ticket}}": jira_key or "N/A",
        }
        for placeholder, value in replacements.items():
            template = template.replace(placeholder, value)
        return template

    def _build_attachments(self, attachment_paths: List[str]) -> list:
        """Read and base64-encode file attachments for the Graph API."""
        attachments = []
        for path_str in attachment_paths:
            path = Path(path_str)
            if not path.exists():
                logger.warning(f"Attachment not found, skipping: {path_str}")
                continue
            content = base64.b64encode(path.read_bytes()).decode("utf-8")
            attachments.append({
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": path.name,
                "contentBytes": content,
            })
        return attachments

    def send_email(
        self,
        advisor: Advisor,
        item: MarginItem,
        template_path: str,
        attachment_paths: List[str],
        jira_key: Optional[str] = None,
    ) -> None:
        """Send the margin call notification email to an advisor."""
        html_body = self._render_template(template_path, advisor, item, jira_key)
        attachments = self._build_attachments(attachment_paths)

        payload = {
            "message": {
                "subject": f"Action Required: Margin Call - Account {item.account_number}",
                "body": {"contentType": "HTML", "content": html_body},
                "toRecipients": [
                    {"emailAddress": {"address": advisor.email}}
                ],
                "attachments": attachments,
            }
        }

        token = self._get_token()
        resp = requests.post(
            f"https://graph.microsoft.com/v1.0/users/{self.sender}/sendMail",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
        logger.info(f"Sent email to {advisor.email} for account {item.account_number}")
