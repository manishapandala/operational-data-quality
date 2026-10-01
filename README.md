# Operational Data Quality Pipeline

A reproducible validation and cleaning pipeline for operational records. It profiles a generated 10,000-row dataset, identifies row-level quality issues, applies explicit repairs, and writes an audit summary plus a cleaned sample.

## Checks

- missing record identifiers and customer names;
- duplicate record identifiers;
- malformed email addresses;
- missing or negative amounts;
- uncontrolled status values;
- invalid event dates.

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run_demo.py
python -m unittest discover -s tests -v
```

Outputs:

- `demo_summary.json` — before/after metrics and repair audit;
- `cleaned_sample.csv` — 250 publishable generated records.

The public metrics use deterministic generated data and validate pipeline behavior. They do not disclose employer data or claim production performance.

## Engineering quality

- validation is separate from mutation, and every repair is counted;
- deterministic fixtures exercise both clean and defective records;
- Ruff, bytecode compilation, and nine unit tests run in GitHub Actions;
- the README and demo distinguish generated evidence from production claims.

See [ENGINEERING.md](ENGINEERING.md) for architecture, verification, safe-change rules, and limitations.
