# Security

## Supported versions

| Version | Supported |
| --- | --- |
| 0.1.x | Yes |

## Reporting

Please use [GitHub Security Advisories](https://github.com/ryaneditraj/cbse-physics-predictor/security/advisories/new). Do not open a public issue for a vulnerability, and do not include a live secret in the report.

## Secrets

There is nothing in this repository to rotate. The history before the open-source pass was a one-line README title. No API key, token, or password has been committed. History was not rewritten.

The app does not ship credentials. `.env` is gitignored. `.env.example` only names two optional OCR settings, and the program does not load that file for you. Export `CBSE_PHYSICS_OCR` and `CBSE_PHYSICS_TESSERACT_CMD` yourself. The tesseract path is checked as a plain path and is never passed through a shell.

## What the tool is careful about

- **HTML reports.** Concept names, filenames, and warnings are escaped. The report has no scripts and sends `noindex`. A content security policy blocks everything except inline styles.
- **Paths.** A directory ingest skips symlinks that resolve outside the folder you named. Stored source labels are basenames, so a home-directory path does not land in the corpus.
- **PDFs.** Size, page count, and extracted length are capped. Encrypted files are refused. Question text is tagged in memory and not written to the JSONL corpus.
- **Models.** Rankers are fit in memory. Nothing is loaded with `pickle` or `joblib`.
- **Walk-forward.** Features for a year are built only from earlier years.
- **Dependencies.** CI runs `pip-audit` on the installed environment.

## Residual risk

A malicious PDF can still stress a PDF parser. Ingest papers you trust. OCR runs local binaries you installed. Point `CBSE_PHYSICS_TESSERACT_CMD` only at the real tesseract binary.

The HTML report is a local file. Do not host a report built from someone else's corpus on a site you do not control. The sample report in `docs/` is the fixture, and it is marked `noindex`.

## Audit notes for this release

Reviewed in the open-source pass: secret scan of the tree, HTML escaping (including a `<script>` and an attribute payload), symlink escape on directory ingest, OCR command metacharacters, corpus path stripping, and dependency audit via `pip-audit`. No committed secret was found.
