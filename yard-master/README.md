# yard-master

Consolidated 12 fragmented jobs into one pipeline. 3 teams maintaining separate ETLs → 1 owner, 1 codebase, 1 hourly refresh. Validated at 93.5% key overlap with the legacy system across 13 weeks before I cut over.

## what it does

Joins 5 upstream sources (yard positions, gate events, appointments, load summaries, capacity data) into a single hourly snapshot: 107 columns, ~100K active trailers across 200+ facilities. Daily job appends to a history table and produces a processed-trailer grain for WBR reporting.

## why the patterns exist

The safe-cast approach (VARCHAR first, regex validate, then convert) exists because upstream owners changed column types without telling anyone — twice. Silent DECIMAL evaluation failures at 2am that took hours to diagnose. Never again.

The equipment fallback JOIN exists because primary appointment matching only covers ~85%. The other 15% need a recency-ranked trailer_id fallback or dwell numbers are understated.

The staging→production swap exists because production tables are never dropped. CTAS builds staging, validation checks row counts and key uniqueness, then truncate+insert. Consumers always have data.

## consumers

- Executive weekly business review (WBR bridge table)
- QuickSight dashboards
- Operations flash reports (IB Dwell Flash)
- Downstream pipelines (DnD scorecard, warehouse transfer, NACF/IB Trans teams)
