import logging
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import List

import pandas as pd

from margin.models import MarginItem

logger = logging.getLogger(__name__)


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names: strip whitespace, lowercase."""
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    return df


# Common column name variations we'll try to map
_COLUMN_MAP = {
    "account_number": ["account_number", "account_no", "account", "acct", "acct_number", "acct_no", "account_#"],
    "error_type": ["error_type", "error", "type", "margin_error", "margin_type", "call_type", "open_item_type"],
    "date": ["date", "margin_date", "call_date", "error_date", "open_item_date"],
    "dollar_amount": ["dollar_amount", "amount", "dollar_amt", "$_amount", "margin_amount", "usde"],
}


def _find_column(df: pd.DataFrame, field: str) -> str:
    """Find the actual column name in the dataframe for a given field."""
    candidates = _COLUMN_MAP.get(field, [field])
    for candidate in candidates:
        if candidate in df.columns:
            return candidate
    raise KeyError(
        f"Could not find column for '{field}'. "
        f"Expected one of: {candidates}. "
        f"Found columns: {list(df.columns)}"
    )


def read_margin_file(file_path: str, error_types: List[str], header_row: int = 0) -> List[MarginItem]:
    """Read the margin spreadsheet, filter by error types, return MarginItems."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Margin file not found: {file_path}")

    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
    else:
        df = pd.read_excel(path, engine="openpyxl", header=header_row)

    df = _normalize_columns(df)

    acct_col = _find_column(df, "account_number")
    error_col = _find_column(df, "error_type")
    date_col = _find_column(df, "date")
    amount_col = _find_column(df, "dollar_amount")

    # Filter to configured error types (case-insensitive)
    error_types_upper = [e.upper() for e in error_types]
    mask = df[error_col].astype(str).str.strip().str.upper().isin(error_types_upper)
    filtered = df[mask]

    items = []
    for idx, row in filtered.iterrows():
        acct = str(row[acct_col]).strip()
        if not acct or acct.lower() == "nan":
            logger.warning(f"Row {idx + 2}: skipping — empty account number")
            continue

        error = str(row[error_col]).strip()

        # Parse date
        raw_date = row[date_col]
        if isinstance(raw_date, date):
            item_date = raw_date
        else:
            try:
                item_date = pd.to_datetime(raw_date).date()
            except Exception:
                logger.warning(f"Row {idx + 2}: skipping — invalid date '{raw_date}'")
                continue

        # Parse dollar amount
        raw_amount = str(row[amount_col]).replace("$", "").replace(",", "").strip()
        try:
            amount = Decimal(raw_amount)
        except InvalidOperation:
            logger.warning(f"Row {idx + 2}: skipping — invalid amount '{row[amount_col]}'")
            continue

        items.append(MarginItem(
            account_number=acct,
            error_type=error,
            date=item_date,
            dollar_amount=amount,
            row_index=idx + 2,  # +2 for 1-based + header row
        ))

    logger.info(f"Read {len(df)} rows, filtered to {len(filtered)} matching error types, parsed {len(items)} valid items")
    return items
