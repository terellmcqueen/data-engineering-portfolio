# carrier-pipeline

Refactored a 20-script EC2 monolith into 12 clean modules. Blank-destination rate went from 1000+/day to 15-64/day. Warehouse transfer query dropped from 341s to 49s after I rewrote it with shared CTEs.

## the migration

v1 was over-engineered: ECS cluster, Fargate tasks, RDS Postgres, ALB. For what amounted to "read CSV, write to warehouse." I killed it. Lambda + S3 event triggers does the same job at 1/10th the operational surface area.

v2 architecture:
- Email fetch via MCP JSON-RPC (0.6s/call, replaced 15s+ sleep-based polling)
- S3 staging with dedup by filename
- EventBridge → Lambda for normalization + load
- 4-statement SQL enrichment (destination lookup, appointment match, dwell calc, risk tiering)
- Cron 2x daily for enrichment pass
- Per-carrier regression tests

## why it's config-driven

4+ carriers, each with a different CSV format (pipe-delimited, tab-delimited, different date formats, merged header rows). Adding carrier #5 is a YAML block + one normalizer function. Zero orchestrator changes.

Blank-rate thresholds are per-carrier because some blanks are *structural* (mid-leg loads have no destination by definition). The pipeline distinguishes expected gaps from bugs. Alert only on anomalies.

## lessons from production

Every bug fix is recorded in `known_issues.json` with a regression test. Anyone touching this code reads that file first. That pattern caught 3 near-misses in the first month.
