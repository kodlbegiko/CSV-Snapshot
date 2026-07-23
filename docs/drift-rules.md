# Drift rules

Findings have a stable rule ID, severity, optional column, baseline, current value, difference, threshold, message, and suggestion.

## Schema

- `schema.column_added`
- `schema.column_removed`
- `schema.column_order_changed`
- `schema.type_changed`
- `schema.nullable_changed`

A rename is deliberately represented as one removal and one addition; semantic rename guessing is unsafe.

## Volume and missingness

- `volume.row_count_changed`
- `volume.empty_file`
- `volume.header_only`
- `missingness.null_rate_increased`

Relative change from zero is represented as `from-zero`, never Infinity or NaN.

## Numeric, string, and temporal

Numeric findings cover min, max, material mean change, and newly appearing negative values. String findings cover min/max length and material distinct-count change. Date/datetime findings report earliest/latest changes as informational.

## Column contracts

Configured rules validate expected type, non-nullability, maximum null rate, and numeric min/max. Errors block by default. Warnings block only with `--warnings-as-errors`.
