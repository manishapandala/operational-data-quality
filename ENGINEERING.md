# Engineering Review

This file preserves architecture and verification decisions outside conversational context. It should change whenever a validation rule, repair policy, or public metric changes.

## Architecture

| Layer | Responsibility | File |
|---|---|---|
| Contract | Required fields, accepted statuses, email structure | `data_quality.py` constants |
| Detection | Return row-level issues without mutating input | `data_quality.py::validate` |
| Repair | Apply explicit fixes and produce an audit log | `data_quality.py::clean` |
| Fixture | Generate deterministic records with known defects | `data_quality.py::generate_records` |
| Reproduction | Write summary and cleaned sample | `run_demo.py` |
| Presentation | Explain checks and before/after evidence | `index.html` |

Detection and repair are intentionally separate so callers can profile data without silently changing it.

## Verification contract

```bash
python -m ruff check .
python -m compileall -q .
python -m unittest discover -s tests -v
python run_demo.py
```

The tests cover schema enforcement, known issue detection, deterministic generation, repair audit counts, idempotence, and a clean post-repair validation result.

## Change-safety checklist

- Review the diff for removed validation rules or changed defaults.
- Require a test for each new issue code and each repair policy.
- Keep `validate` non-mutating and `clean` auditable.
- Never publish real customer data or inferred personal details.
- Re-run the demo after rule changes and update all displayed metrics together.
- Treat imputation choices as domain decisions, not universal defaults.
- Use small commits so a harmful automated refactor can be reverted.

## Known boundaries

The generated defects prove pipeline behavior, not production data quality. Median imputation, placeholder emails, and the fallback date are explicit demonstration policies that require stakeholder approval before real use.
