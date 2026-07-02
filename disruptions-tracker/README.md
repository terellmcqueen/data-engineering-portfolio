# disruptions-tracker

Replaced a 45-minute manual process with one CLI command. Queries Redshift, validates its own math, appends to an Excel tracker. SUMIFS in the tracker auto-compute day-over-day and week-over-week trends.

If the balance doesn't check out (SOS + New - Resolved ≠ EOS), nothing writes. No partial state, no "oops I fat-fingered the paste."

## how it works

1. Store today's morning snapshot (idempotent — INSERT WHERE NOT EXISTS)
2. Run shift query: point-in-time case counts at 06:00 and 18:00, yard metrics
3. Validate balance equation
4. Append to Excel (openpyxl)
5. Tracker tab auto-populates via SUMIFS

The shift query uses point-in-time snapshots, not date-range aggregates. "How many cases were open at 06:00" is a different question than "how many cases existed on this date" — the first one handles reopens correctly.
