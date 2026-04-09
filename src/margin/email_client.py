import logging
from pathlib import Path
from typing import List, Optional

from margin.config import OutlookConfig
from margin.models import Advisor, MarginItem

logger = logging.getLogger(__name__)


class OutlookClient:
    def __init__(self, config: OutlookConfig, manual_send: bool = True):
        """Initialize Outlook client.

        Args:
            config: OutlookConfig with sender email
            manual_send: If True, open draft for manual review. If False, auto-send.
        """
        self.config = config
        self.sender = config.sender
        self.manual_send = manual_send
        try:
            import win32com.client
            self.outlook = win32com.client.Dispatch("Outlook.Application")
        except ImportError:
            raise ImportError(
                "pywin32 is required for Outlook integration. "
                "Install it with: pip install pywin32"
            )

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

    def send_email(
        self,
        advisor: Advisor,
        item: MarginItem,
        template_path: str,
        attachment_paths: List[str],
        jira_key: Optional[str] = None,
    ) -> None:
        """Create and send (or display) the margin call notification email to an advisor."""
        html_body = self._render_template(template_path, advisor, item, jira_key)
        subject = f"Action Required: Margin Call - Account {item.account_number}"

        # Create mail item
        mail = self.outlook.CreateItem(0)  # 0 = olMailItem
        mail.Subject = subject
        mail.To = advisor.email
        mail.HTMLBody = html_body
        mail.SentOnBehalfOfName = self.sender

        # Attach files
        for attachment_path in attachment_paths:
            path = Path(attachment_path)
            if path.exists():
                mail.Attachments.Add(str(path.absolute()))
            else:
                logger.warning(f"Attachment not found, skipping: {attachment_path}")

        # Send or display for manual review
        if self.manual_send:
            mail.Display(False)  # Display in non-modal window
            logger.info(
                f"Email draft opened in Outlook for {advisor.email} "
                f"(account {item.account_number}). Please review and send manually."
            )
        else:
            mail.Send()
            logger.info(f"Sent email to {advisor.email} for account {item.account_number}")
