# Export Readiness Checker (Free)

A free basic version of the Export Description and Classification Compliance product.

## What this version does
- Checks whether a product record is missing critical shipment data
- Suggests a basic HS code direction for selected product types
- Improves weak product descriptions into more customs-ready wording
- Flags product records as low, medium, or high risk
- Supports small CSV bulk uploads
- Lets users download result files during the session

## Free version limits
- 20 checks per day per session
- 50 rows maximum per bulk upload
- Session-only history
- No saved accounts, API, integrations, or persistent audit storage

## Files
- `app.py` — Streamlit app
- `requirements.txt` — Python dependencies
- `sample_products.csv` — test data

## Local run
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy
This app is suitable for Streamlit Community Cloud deployment.

## Important disclaimer
This tool provides preliminary guidance only. Final HS classification and customs compliance remain the responsibility of the exporter and customs broker.
