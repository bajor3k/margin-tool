import logging
from pathlib import Path
from typing import Dict, Optional

import pandas as pd

from margin.models import Advisor

logger = logging.getLogger(__name__)


def load_advisors(file_path: str) -> Dict[str, Advisor]:
    """Load advisor lookup file into a dict keyed by account number."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Advisor file not found: {file_path}")

    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
    else:
        df = pd.read_excel(path, engine="openpyxl")

    # Normalize column names
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]

    # Try to find the right columns
    acct_col = _find_col(df, ["account_number", "account_no", "account", "acct", "acct_number", "acct_no"])
    firm_col = _find_col(df, ["firm_name", "firm", "company", "company_name", "advisor_firm", "advisor"])
    email_col = _find_col(df, ["email", "email_address", "advisor_email", "contact_email"])

    advisors = {}
    for _, row in df.iterrows():
        acct = str(row[acct_col]).strip()
        if not acct or acct.lower() == "nan":
            continue

        advisors[acct] = Advisor(
            account_number=acct,
            firm_name=str(row[firm_col]).strip(),
            email=str(row[email_col]).strip(),
        )

    logger.info(f"Loaded {len(advisors)} advisors from {file_path}")
    return advisors


def _find_col(df: pd.DataFrame, candidates: list) -> str:
    for c in candidates:
        if c in df.columns:
            return c
    raise KeyError(
        f"Could not find column. Expected one of: {candidates}. "
        f"Found: {list(df.columns)}"
    )


def get_advisor(advisors: Dict[str, Advisor], account_number: str) -> Optional[Advisor]:
    """Look up an advisor by account number. Returns None if not found."""
    advisor = advisors.get(account_number)
    if advisor is None:
        logger.warning(f"No advisor found for account {account_number}")
    return advisor
