# Export Readiness Checker (Free)

A free basic version of the Export Description and Classification Compliance product.

## What this version does
- Checks whether a product record is missing critical shipment data
- Suggests a basic HS code direction for selected product types
- Validates a user-provided HS code against simple product rules
- Improves weak product descriptions into more customs-ready wording
- Flags product records as low, medium, or high risk
- Supports small CSV bulk uploads
- Lets users download result files during the session

## Free version limits
- 20 checks per day per session
- 50 rows maximum per bulk upload
- Session-only history
- No saved accounts, API, integrations, or persistent audit storage

## Bulk upload columns
Required:
- description
- material
- construction
- origin
- category
- value

Optional:
- provided_hs_code

## Files
- `app.py` — Streamlit app
- `requirements.txt` — Python dependencies
- `sample_products.csv` — test data

## Local run
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Important disclaimer
This tool provides preliminary guidance only. Final HS classification and customs compliance remain the responsibility of the exporter and customs broker.
