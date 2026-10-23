# Contributing

Thanks for wanting to make the study plan more honest. This project is a local Class 12 Physics tool. It is not affiliated with CBSE or NCERT.

## Setup

```bash
git clone https://github.com/ryaneditraj/cbse-physics-predictor.git
cd cbse-physics-predictor
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
cbse-physics demo
```

Python 3.11 or newer. The demo needs no API key and no network.

## What helps

- A keyword that stops a false tag, with a sentence you wrote yourself and a test in `tests/`.
- A walk-forward metric, a leakage test, or a clearer disclaimer.
- Docs that match the command that actually runs.

## What to leave out

- Question-paper text, textbook passages, or a scanned paper. Tag ids are fine. The wording of the paper is not.
- Secrets, `.env` files, and corpora built from papers you cannot redistribute. `papers/` and `out/` are gitignored on purpose.
- A README number you typed by hand. Quote `cbse-physics backtest` or `cbse-physics demo --json`.

## Tests

`pytest` is the check that matters. CI runs it on Python 3.11 and 3.12 and then runs `pip-audit`.

If you change the demo copy or the ranker, regenerate the sample and look at it:

```bash
cbse-physics demo --out docs/sample-report.html --svg docs/screenshots/demo.svg
```

Screenshots in `docs/screenshots/` are taken from that report and from the SVG in a browser. Do not draw a mock.

## Pull requests

Use the template. Keep the change focused. The walk-forward test year must stay out of that year's features.

## Conduct and security

The [Code of Conduct](CODE_OF_CONDUCT.md) applies to issues, pull requests, and discussions. Vulnerability reports go through [Security Advisories](https://github.com/ryaneditraj/cbse-physics-predictor/security/advisories/new), not a public issue. See [SECURITY.md](SECURITY.md).
