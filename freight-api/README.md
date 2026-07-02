# freight-api

FastAPI service that polls carrier REST APIs on a schedule, normalizes responses into a canonical shipment model, and upserts to PostgreSQL. Built to replace an email-dependent ingestion layer where "carrier forgot to send the file" meant no data for 24 hours.

## why I built this

The pipeline I was running (carrier-pipeline) works. But the ingestion layer depends on carriers sending Excel files via email. If they forget, I don't get data. If they change a column, my parser breaks silently. The whole thing requires Midway auth on my EC2 — if I'm out, it doesn't run.

This API-first approach fixes all three problems: poll on a schedule, validate response shape before processing, retry on failure. No human in the loop.

## security posture

I drew a hard line on this one. It handles carrier shipment IDs, container numbers, routing, ETAs — but zero PII. No associate names, no customer data. If downstream needs PII, they join on shipment_id on their side.

- Secrets Manager for all credentials (no config files with creds on my machine)
- TLS everywhere, sslmode=require on DB
- Non-root Docker image, multi-stage build
- CI runs Bandit + TruffleHog + pip-audit + Trivy before tests
- Audit logging on every request (src IP, path, status)
- CloudWatch heartbeat alarm if scheduler stops emitting

## adding a new carrier

1. Write a client class in `carriers/`
2. Add normalizer to dispatch table
3. Add mock payload to `tests/mock_payloads/`
4. Add test
5. Done — scheduler picks it up automatically

## status

Code is complete and tested. Waiting on production API credentials from carriers (they've confirmed ready). The architecture decision to use Secrets Manager over config files came directly from my L6 flagging the bus-factor risk of the current setup.
