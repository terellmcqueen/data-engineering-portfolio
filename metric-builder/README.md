# metric-builder

Eliminated 2+ hours/week of manual Excel formula wiring per dashboard. Takes SQL output + YAML config → produces a fully formula-wired .xlsx. SUMIFS rollups, INDEX/MATCH Top-N ranked blocks, dynamic period headers. Onboarding a new dashboard is a config file, not a code change.

## the problem

Ops teams paste SQL output into Excel, then spend an hour wiring SUMIFS and INDEX/MATCH formulas by hand. When the data shape changes, formulas break silently — IFERROR masks the failure, you see blanks, nobody notices until someone asks "why is this empty?"

## how it works

```
metric-builder build --data output.csv --config dashboard.yaml --output report.xlsx
```

The engine reads the config, validates the CSV schema matches, injects data into the Raw tab, then generates formulas referencing hidden key columns. Display labels and lookup keys are always separate — formulas never parse formatted text.

## design decisions

- Domain-agnostic: engine never references any business domain. All context lives in YAML.
- Hidden key columns for Top-N: raw node value in col Z, display label in col B. Formulas reference $Z16, never parse "FAC01 | Type A" with LEFT/FIND.
- Tier 1 functions only: SUMIFS, INDEX, MATCH, IFERROR. No XLOOKUP. Works in Excel 2007+.
- No pandas. openpyxl + csv module. Fast, small dependency footprint.
- Semantic completeness validation: after generation, checks that sections with matching source data actually produced non-blank values.
