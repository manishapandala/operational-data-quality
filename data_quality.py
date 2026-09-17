"""Rule-based validation and cleaning for operational records."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = ("record_id", "customer", "email", "amount", "status", "event_date")
VALID_STATUSES = {"pending", "completed", "cancelled"}
STATUS_ALIASES = {"complete": "completed", "canceled": "cancelled", "in progress": "pending"}
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


@dataclass(frozen=True)
class Issue:
    row: int
    field: str
    code: str

    def to_dict(self) -> dict:
        return asdict(self)


def _require_schema(frame: pd.DataFrame) -> None:
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing columns: {', '.join(missing)}")


def validate(frame: pd.DataFrame) -> dict:
    """Return row-level issues and a strict fully-valid-row score."""
    _require_schema(frame)
    issues: list[Issue] = []
    duplicated = frame["record_id"].astype(str).duplicated(keep=False)
    parsed_amount = pd.to_numeric(frame["amount"], errors="coerce")
    parsed_date = pd.to_datetime(frame["event_date"], format="%Y-%m-%d", errors="coerce")

    for position, (_, row) in enumerate(frame.iterrows()):
        if not str(row["record_id"]).strip() or str(row["record_id"]).lower() == "nan":
            issues.append(Issue(position, "record_id", "missing"))
        if duplicated.iloc[position]:
            issues.append(Issue(position, "record_id", "duplicate"))
        if not str(row["customer"]).strip() or str(row["customer"]).lower() == "nan":
            issues.append(Issue(position, "customer", "missing"))
        if not EMAIL_PATTERN.match(str(row["email"]).strip().lower()):
            issues.append(Issue(position, "email", "invalid_format"))
        if pd.isna(parsed_amount.iloc[position]) or parsed_amount.iloc[position] < 0:
            issues.append(Issue(position, "amount", "invalid_value"))
        if str(row["status"]).strip().lower() not in VALID_STATUSES:
            issues.append(Issue(position, "status", "invalid_category"))
        if pd.isna(parsed_date.iloc[position]):
            issues.append(Issue(position, "event_date", "invalid_date"))

    invalid_rows = {issue.row for issue in issues}
    valid_rows = len(frame) - len(invalid_rows)
    score = valid_rows / len(frame) if len(frame) else 1.0
    counts: dict[str, int] = {}
    for issue in issues:
        key = f"{issue.field}:{issue.code}"
        counts[key] = counts.get(key, 0) + 1
    return {
        "rows": len(frame),
        "valid_rows": valid_rows,
        "invalid_rows": len(invalid_rows),
        "quality_score": round(score, 4),
        "issue_counts": dict(sorted(counts.items())),
        "issues": [issue.to_dict() for issue in issues],
    }


def clean(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Apply explicit repairs and return the cleaned frame plus an audit log."""
    _require_schema(frame)
    cleaned = frame.copy()
    audit = {"input_rows": len(cleaned), "duplicates_removed": 0, "repairs": {}}

    cleaned["record_id"] = cleaned["record_id"].astype(str).str.strip()
    missing_ids = cleaned["record_id"].isin({"", "nan", "None"})
    for sequence, index in enumerate(cleaned.index[missing_ids], start=1):
        cleaned.at[index, "record_id"] = f"RECOVERED-{sequence:05d}"
    audit["repairs"]["record_id"] = int(missing_ids.sum())

    duplicate_mask = cleaned["record_id"].duplicated(keep="first")
    audit["duplicates_removed"] = int(duplicate_mask.sum())
    cleaned = cleaned.loc[~duplicate_mask].copy()

    cleaned["customer"] = cleaned["customer"].fillna("").astype(str).str.strip()
    missing_customer = cleaned["customer"].isin({"", "nan", "None"})
    cleaned.loc[missing_customer, "customer"] = "Unknown customer"
    audit["repairs"]["customer"] = int(missing_customer.sum())

    cleaned["email"] = cleaned["email"].fillna("").astype(str).str.strip().str.lower()
    invalid_email = ~cleaned["email"].map(lambda value: bool(EMAIL_PATTERN.match(value)))
    cleaned.loc[invalid_email, "email"] = cleaned.loc[invalid_email, "record_id"].map(
        lambda value: f"{value.lower()}@unknown.invalid"
    )
    audit["repairs"]["email"] = int(invalid_email.sum())

    cleaned["amount"] = pd.to_numeric(cleaned["amount"], errors="coerce")
    invalid_amount = cleaned["amount"].isna() | (cleaned["amount"] < 0)
    valid_median = float(cleaned.loc[~invalid_amount, "amount"].median()) if (~invalid_amount).any() else 0.0
    cleaned.loc[invalid_amount, "amount"] = valid_median
    cleaned["amount"] = cleaned["amount"].round(2)
    audit["repairs"]["amount"] = int(invalid_amount.sum())

    original_status = cleaned["status"].fillna("").astype(str).str.strip().str.lower()
    cleaned["status"] = original_status.replace(STATUS_ALIASES)
    invalid_status = ~cleaned["status"].isin(VALID_STATUSES)
    cleaned.loc[invalid_status, "status"] = "pending"
    audit["repairs"]["status"] = int((original_status != cleaned["status"]).sum())

    parsed_date = pd.to_datetime(cleaned["event_date"], format="%Y-%m-%d", errors="coerce")
    invalid_date = parsed_date.isna()
    parsed_date.loc[invalid_date] = pd.Timestamp("2025-01-01")
    cleaned["event_date"] = parsed_date.dt.strftime("%Y-%m-%d")
    audit["repairs"]["event_date"] = int(invalid_date.sum())
    audit["output_rows"] = len(cleaned)
    return cleaned.reset_index(drop=True), audit


def generate_records(size: int = 10_000, seed: int = 23) -> pd.DataFrame:
    """Create deterministic operational data with intentional quality defects."""
    if size < 1:
        raise ValueError("size must be positive")
    rng = np.random.default_rng(seed)
    rows = []
    statuses = ("pending", "completed", "cancelled")
    for index in range(size):
        record_id = f"ORD-{index:06d}"
        customer = f"Customer {index % 700}"
        email = f"customer{index % 700}@example.com"
        amount = round(float(rng.uniform(10, 1800)), 2)
        status = statuses[index % len(statuses)]
        event_date = (pd.Timestamp("2025-01-01") + pd.Timedelta(days=index % 365)).strftime("%Y-%m-%d")
        if index % 17 == 0:
            email = "invalid-email"
        if index % 19 == 0:
            amount = -amount
        if index % 23 == 0:
            status = "complete"
        if index % 29 == 0:
            event_date = "not-a-date"
        if index % 31 == 0:
            customer = ""
        if index > 0 and index % 37 == 0:
            record_id = f"ORD-{index - 1:06d}"
        rows.append((record_id, customer, email, amount, status, event_date))
    return pd.DataFrame(rows, columns=REQUIRED_COLUMNS)
