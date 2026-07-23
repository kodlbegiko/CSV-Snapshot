# Limitations

- Only UTF-8 and UTF-8 BOM text CSVs with a header are supported.
- Delimiters must be a single character.
- Duplicate headers and irregular row lengths are errors.
- Date inference is limited to ISO dates and ISO 8601 datetimes containing `T`.
- Mixed columns receive string-length metrics, not per-subtype distribution metrics.
- Exact distinct counting can require substantial temporary disk for very high-cardinality data.
- Numeric standard deviation is population standard deviation.
- No XLSX, Parquet, JSONL, compressed archive, remote URL, bucket, automatic cleaning, category-value output, random sampling, or ML drift metric is provided.
- A snapshot reflects statistical properties, not business meaning or full data-governance policy.
- v0.1.0 is not published to PyPI.
