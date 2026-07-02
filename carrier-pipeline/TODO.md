# carrier-pipeline — open items

## need to do
- [ ] carrier E onboarding (they confirmed API access ready, need to write normalizer)
- [ ] backfill gap from june 2-8 when cron died silently (data exists in S3, just never loaded)
- [ ] move cred refresh from cron to EventBridge scheduled rule (single point of failure rn)

## want to do but not blocking
- [ ] consolidator: add a --dry-run that prints what WOULD be inserted without touching the db
- [ ] health check should post to slack not just log to file. nobody reads logs until its too late
- [ ] look into whether the 15-64 blank/day for carrier A is reducible with an external FC mapping table
  - probably not worth it. those are DART_CON / PCNA style intermediate facilities that dont map to our FC codes
  - nici confirmed these are fine as-is

## won't fix
- carrier B sometimes sends duplicate rows same day — dedup handles it, but their side should fix it
- the enrichment query takes 49s which feels slow but its 4 statements with a full datashare scan, not much to optimize without materialized views (which we dont own)

## random notes
- if carrier A stops sending for >2 days, check their billing — they pause the feed when invoices are overdue (learned this the hard way in march)
- the known_issues.json framework saved us 3 times in the first month. worth the overhead.
