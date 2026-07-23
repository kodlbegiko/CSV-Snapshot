# Type inference

Inference is deterministic and operates on non-null, non-empty values.

1. Case-insensitive `true` and `false` are boolean.
2. Signed base-10 whole numbers are integer, except non-zero leading-zero strings such as `00123`.
3. Decimal and scientific notation are float when finite.
4. ISO `YYYY-MM-DD` is date.
5. ISO 8601 values containing `T` are datetime. Offset-aware values are normalized to UTC before metrics.
6. Remaining values are string.

A column containing only configured null tokens is `null`. Integer plus float becomes float. Incompatible categories become `mixed`. Empty strings do not become null; they are counted separately and do not force a numeric column to string.

No locale-specific dates, thousands separators, decimal commas, system timezone, or current date are consulted.
