# AE Report on S3: SAS + Python + AWS

A small end-to-end project: **clinical adverse-event summary** built from synthetic trial data, written in **SAS** and re-implemented in **Python** (unit-tested against the SAS expected output), then published as a **static website on Amazon S3**.

> All data is synthetic. No real patients.

## What it shows

| Skill | Where |
|---|---|
| Clinical programming logic: safety population, treatment-emergent flag, subject-level counting, n (%) tables | `sas/ae_summary_export.sas`, `python/build_report.py` |
| Verifying one implementation against another | `tests/test_build_report.py` |
| Cloud hosting: S3 static website, bucket policy | `deploy/DEPLOY.md`, `deploy/bucket-policy.json` |
| CI with GitHub Actions: test, build, keep the site as an artifact | `.github/workflows/ci.yml` |

## Result

7 preferred terms, 11 subjects per arm (2 screen failures excluded). For example nausea: 0 (0.0%) on placebo vs 5 (45.5%) on drug 10 mg.

## Run it

```
python -m unittest discover -s tests -v     # 4 tests
python python/build_report.py               # writes site/index.html and site/ae_summary.csv
```

Open `site/index.html` in a browser. Python 3.9+ only, nothing to install.

## The SAS version

`sas/ae_summary_export.sas` follows the same rules and writes `output/ae_summary.csv`. Edit the `root` path at the top, run it, and compare its CSV with `site/ae_summary.csv`. The two should match.

**Honest status:** the Python version is tested. The SAS program was written carefully to match but has **not been run in SAS yet**. Treat any difference as something to debug and write up.

## Publish to S3

See [`deploy/DEPLOY.md`](deploy/DEPLOY.md). Public hosting is only for synthetic data.

## Rules used (simplified for practice)

- Safety population: first dose date present.
- Treatment-emergent: AE start date on or after first dose date.
- A subject is counted once per preferred term.
- Percent = subjects with the event / safety subjects in that arm, shown to one decimal.

## Ideas to extend

- Add severity and serious-AE tables.
- Deploy from GitHub Actions to S3 using OIDC (no stored keys).
- Put CloudFront in front of the bucket for https.
- Add a Route 53 record for a custom domain.
