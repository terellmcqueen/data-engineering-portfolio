# platform-tools

Internal developer tools I built to catch my own mistakes before they hit production. Each one exists because something went wrong once and I never wanted it to happen again.

## sql-validator

Validates SQL against a registry of known table schemas and correction patterns before execution. Catches:
- Aggregation on snapshot tables without dedup (learned this the hard way — CM-001)
- Bare ::numeric casts in Redshift (need explicit precision — CM-003)
- AVG(dwell) without GREATEST(0, ...) floor (negative dwell = within free time, not a bug — CM-007)
- Joins on wrong key (final_vrid vs active_vrid for multi-stop loads)
- Entry timestamps without 1-year guard (stale data from years ago inflates counts)

## xlsx-diff

Cell-level comparison of two Excel workbooks. Built because weekly dashboard updates need verification — "did the formulas produce the same results as last week, or did something shift?" Handles:
- Modified, added, removed cells
- Numeric tolerance for floating-point comparison
- Merged cell handling
- Summary stats (sheets affected, change counts)

## drift-detector

Runs against the table registry and checks:
- Do all registered tables still exist?
- Is data fresh (daily table should have data from today or yesterday)?
- Are any tables empty that shouldn't be?

## governance CLI

Pre-check and post-check gates for pipeline modifications. Scores confidence across 4 dimensions (schema match, SQL safety, retrieval completeness, grain integrity). Outputs PROCEED / REVIEW_REQUIRED / BLOCKED.

Built this after an incident where a "simple" query change broke a downstream consumer nobody knew about. Now every modification traces blast radius through the lineage graph first.
