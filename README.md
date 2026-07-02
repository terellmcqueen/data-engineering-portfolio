# terell mcqueen — data engineering

I build pipelines that replace manual processes, consolidate fragmented systems, and produce numbers people trust without babysitting. Most of my work lives at the intersection of Python, SQL, and AWS — taking messy multi-source data and turning it into something reliable enough to run business decisions off of.

## what's here

Each folder is a standalone project. Click into whichever matches what you're hiring for.

**[yard-master](./yard-master/)** — Replaced 12 fragmented ETL jobs with one pipeline. 5 data sources → 107-column hourly warehouse table. 93.5% validated accuracy.

**[carrier-pipeline](./carrier-pipeline/)** — Refactored a 20-script EC2 monolith into modular Lambda + S3 event-driven architecture. Blank rate: 1000+/day → 15-64/day.

**[freight-api](./freight-api/)** — FastAPI service polling carrier REST APIs on a schedule. Docker, pytest, AWS Secrets Manager, cross-account IAM. Replaces an email-dependent ingestion layer.

**[disruptions-tracker](./disruptions-tracker/)** — Daily CLI that queries Redshift, validates its own math, and appends to an Excel tracker. Replaced a 45-min manual process.

**[metric-builder](./metric-builder/)** — Config-driven tool that generates formula-wired Excel dashboards from SQL output + YAML. No manual SUMIFS/INDEX-MATCH on refresh.

**[platform-tools](./platform-tools/)** — Internal developer tools: SQL validator, Excel diff engine, drift detector, governance CLI. Built to catch my own mistakes before they hit production.

**[redshift-lambda](./redshift-lambda/)** — Lambda function with cross-account STS role assumption → Redshift Data API. Deploy script included.

**[ops-dashboard](./ops-dashboard/)** — Flask app with LLM-powered chat over live operational data. Per-dashboard context builders, stateless, pluggable backend.

## how I work

- Python for pipelines, not notebooks
- SQL in Redshift (Postgres dialect) — window functions, CTEs, temp table chains, safe-cast patterns
- AWS: Lambda, S3, EventBridge, Redshift Data API, DynamoDB, Secrets Manager, STS cross-account
- Everything idempotent. If it can't be re-run safely, it doesn't ship.
- Every bug fix ships with a regression test
- Config-driven: adding a new data source shouldn't require rewriting the orchestrator

## contact

Upwork: [terellmcqueen](https://www.upwork.com/freelancers/terellmcqueen)
