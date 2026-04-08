from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Optional


@dataclass
class MarginItem:
    account_number: str
    error_type: str
    date: date
    dollar_amount: Decimal
    row_index: int  # original spreadsheet row for error reporting


@dataclass
class Advisor:
    account_number: str
    firm_name: str
    email: str


@dataclass
class ProcessedRecord:
    id: int
    account_number: str
    error_type: str
    margin_date: str
    dollar_amount: str
    jira_ticket_key: Optional[str]
    email_sent: bool
    processed_at: str
    run_id: str
    flagged_duplicate: bool
