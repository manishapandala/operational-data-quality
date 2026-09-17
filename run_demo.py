"""Run the public data-quality pipeline and save reproducible artifacts."""

from __future__ import annotations

import json
from pathlib import Path
import time

from data_quality import clean, generate_records, validate


def main() -> None:
    started = time.perf_counter()
    raw = generate_records()
    before = validate(raw)
    cleaned, audit = clean(raw)
    after = validate(cleaned)
    elapsed = time.perf_counter() - started

    cleaned.head(250).to_csv("cleaned_sample.csv", index=False)
    summary = {
        "scope": "deterministic generated-data validation",
        "input_rows": len(raw),
        "output_rows": len(cleaned),
        "quality_before": before["quality_score"],
        "quality_after": after["quality_score"],
        "quality_lift_points": round((after["quality_score"] - before["quality_score"]) * 100, 2),
        "issues_before": before["issue_counts"],
        "issues_after": after["issue_counts"],
        "audit": audit,
        "runtime_seconds": round(elapsed, 3),
    }
    Path("demo_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
