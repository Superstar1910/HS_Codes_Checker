
import streamlit as st
import pandas as pd
from datetime import date, datetime

st.set_page_config(page_title="Export Readiness Checker (Free)", layout="wide")

LIMIT_DAILY_CHECKS = 20
MAX_BULK_ROWS = 50

if "usage_count" not in st.session_state:
    st.session_state.usage_count = 0
if "last_reset" not in st.session_state:
    st.session_state.last_reset = date.today()
if "history" not in st.session_state:
    st.session_state.history = []

if st.session_state.last_reset != date.today():
    st.session_state.usage_count = 0
    st.session_state.last_reset = date.today()
    st.session_state.history = []

def reset_usage():
    st.session_state.usage_count = 0
    st.session_state.last_reset = date.today()
    st.session_state.history = []

def missing_fields_for_category(category: str, description: str, material: str, origin: str, construction: str) -> list[str]:
    missing = []

    if not description.strip():
        missing.append("product description")
    if not material.strip():
        missing.append("material composition")
    if not origin.strip():
        missing.append("country of origin")

    desc = description.lower()
    category = category.lower()

    if category in {"fashion_accessories", "bags"} and not construction.strip():
        missing.append("product construction or type")

    if "scarf" in desc and not construction.strip():
        missing.append("construction type (for example woven or knitted)")

    if category == "beauty":
        if "ml" not in desc and "spray" not in desc and "bottle" not in desc:
            missing.append("packaging format or volume")

    return missing

def classify_product(description: str, material: str, origin: str, category: str, value: float) -> dict:
    desc = (description or "").lower()
    material_l = (material or "").lower()

    if "scarf" in desc and "silk" in material_l:
        return {
            "hs6": "621410",
            "uk_code": "6214100090",
            "confidence": 0.94,
            "risk": "GREEN",
            "duty": "8%",
            "vat": "20%",
            "explanation": "Matched to silk scarves based on product type and material composition."
        }
    elif "bag" in desc and any(x in material_l for x in ["leather", "suede", "hide"]):
        return {
            "hs6": "420221",
            "uk_code": "4202210000",
            "confidence": 0.88,
            "risk": "AMBER",
            "duty": "16%",
            "vat": "20%",
            "explanation": "Matched to handbags or similar carrying articles with an outer surface of leather."
        }
    elif "perfume" in desc or "parfum" in desc or category == "beauty":
        return {
            "hs6": "330300",
            "uk_code": "3303001000",
            "confidence": 0.81,
            "risk": "RED",
            "duty": "6.5%",
            "vat": "20%",
            "explanation": "Matched to perfumes and toilet waters. Higher risk because beauty products often require more complete declaration detail."
        }
    elif "dress" in desc and "cotton" in material_l:
        return {
            "hs6": "620442",
            "uk_code": "6204420000",
            "confidence": 0.79,
            "risk": "AMBER",
            "duty": "12%",
            "vat": "20%",
            "explanation": "Likely matched to women's cotton dresses, but construction and use detail should still be reviewed."
        }
    else:
        return {
            "hs6": "UNKNOWN",
            "uk_code": "UNKNOWN",
            "confidence": 0.52,
            "risk": "AMBER",
            "duty": "TBD",
            "vat": "20%",
            "explanation": "Insufficient product specificity to provide a strong classification suggestion."
        }

def improve_description(description: str, material: str, origin: str, category: str, construction: str) -> str:
    desc = (description or "").strip()
    material = (material or "").strip()
    origin = (origin or "").strip()
    construction = (construction or "").strip()

    parts = []
    if construction:
        parts.append(construction)
    if desc:
        parts.append(desc)
    if material:
        parts.append(material)
    if origin:
        parts.append(f"made in {origin}")

    cleaned = ", ".join([p for p in parts if p])

    if not cleaned:
        return "No description available."

    return cleaned

def why_flagged_text(risk: str, missing_fields: list[str]) -> str:
    if missing_fields:
        return "Missing required shipment data increases customs risk and makes the description less usable for carriers or brokers."
    if risk == "RED":
        return "This item is high risk for shipment because the category or description quality may require closer review before export."
    if risk == "AMBER":
        return "This item likely needs more detail or manual review before shipment."
    return "The product information provided appears sufficiently detailed for a basic pre-check."

def record_history(row: dict):
    st.session_state.history.append({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        **row
    })

def render_result(result: dict):
    st.markdown("### Check Result")

    risk = result["risk"]
    if risk == "GREEN":
        st.success("Low Risk — Ready for shipment pre-check")
    elif risk == "AMBER":
        st.warning("Medium Risk — Review recommended before shipment")
    else:
        st.error("High Risk — Do not rely on this record without further review")

    a, b, c = st.columns(3)
    a.metric("Suggested HS Code", result.get("hs6", "N/A"))
    b.metric("UK Commodity Code", result.get("uk_code", "N/A"))
    c.metric("Confidence", f"{int(result.get('confidence', 0) * 100)}%")

    d, e = st.columns(2)
    d.metric("Risk Level", result.get("risk", "N/A"))
    e.metric("Declared VAT", result.get("vat", "N/A"))

    st.markdown("**Improved Customs Description**")
    st.code(result.get("improved_description", "N/A"))

    if result.get("missing_fields"):
        st.markdown("### Missing Information")
        for f in result["missing_fields"]:
            st.write(f"- {f}")

    st.markdown("### Why this was flagged")
    st.info(result.get("why_flagged", ""))

    st.markdown("### Classification Explanation")
    st.write(result.get("explanation", ""))

def process_single(description: str, material: str, origin: str, category: str, construction: str, value: float):
    missing = missing_fields_for_category(category, description, material, origin, construction)

    if missing:
        result = {
            "status": "BLOCKED",
            "hs6": "N/A",
            "uk_code": "N/A",
            "confidence": 0.0,
            "risk": "RED",
            "duty": "N/A",
            "vat": "N/A",
            "explanation": "The record does not contain enough information for a reliable pre-check.",
            "improved_description": improve_description(description, material, origin, category, construction),
            "missing_fields": missing,
            "why_flagged": why_flagged_text("RED", missing)
        }
    else:
        result = classify_product(description, material, origin, category, value)
        result["status"] = "APPROVED" if result["risk"] == "GREEN" else "REVIEW"
        result["improved_description"] = improve_description(description, material, origin, category, construction)
        result["missing_fields"] = []
        result["why_flagged"] = why_flagged_text(result["risk"], [])

    return result

st.sidebar.title("Export Readiness Checker (Free)")
page = st.sidebar.radio("Navigate", ["Dashboard", "Classify", "Bulk Upload", "Issues Queue", "Session History"])

st.title("Export Readiness Checker (Free)")
st.caption("Check if your product description is customs-ready before shipment. Detect missing data, improve descriptions, and reduce shipment rejection risk.")

remaining = max(LIMIT_DAILY_CHECKS - st.session_state.usage_count, 0)
st.sidebar.markdown(f"**Checks used today:** {st.session_state.usage_count}/{LIMIT_DAILY_CHECKS}")
st.sidebar.markdown(f"**Checks remaining:** {remaining}")
if st.sidebar.button("Reset session data"):
    reset_usage()
    st.sidebar.success("Session data reset.")

if page == "Dashboard":
    c1, c2, c3 = st.columns(3)
    c1.metric("Checks Today", st.session_state.usage_count)
    c2.metric("Remaining Today", remaining)
    c3.metric("Session History Items", len(st.session_state.history))

    st.markdown("### Free Version Includes")
    st.write("- Single product checks")
    st.write("- Basic customs-ready description improvement")
    st.write("- Missing data detection")
    st.write("- Basic HS code suggestion")
    st.write("- Small bulk upload")

    if st.session_state.history:
        hist_df = pd.DataFrame(st.session_state.history)
        issue_counts = hist_df["risk"].value_counts().rename_axis("Risk").reset_index(name="Count")
        st.markdown("### Session Risk Distribution")
        st.bar_chart(issue_counts.set_index("Risk"))

elif page == "Classify":
    if st.session_state.usage_count >= LIMIT_DAILY_CHECKS:
        st.error(f"Free limit reached ({LIMIT_DAILY_CHECKS} checks/day).")
    else:
        left, right = st.columns([2, 1])

        with left:
            description = st.text_input("Product Description", "Luxury silk scarf with hand-rolled edges")
            material = st.text_input("Material Composition", "100% silk")
            construction = st.text_input("Construction / Product Type", "woven")
            origin = st.text_input("Country of Origin", "IT")
            category = st.selectbox("Category", ["fashion_accessories", "bags", "beauty", "food", "other"])
            value = st.number_input("Declared Value (£)", min_value=0.0, value=250.0, step=10.0)

            col_run, col_fix = st.columns(2)
            run_clicked = col_run.button("Run Check")
            improve_clicked = col_fix.button("Improve Description Only")

        with right:
            st.info("This free version gives a preliminary pre-shipment check. It helps identify weak descriptions and missing data before customs, carriers, or brokers flag them.")

        if improve_clicked:
            st.markdown("### Suggested Improved Description")
            st.code(improve_description(description, material, origin, category, construction))

        if run_clicked:
            st.session_state.usage_count += 1
            result = process_single(description, material, origin, category, construction, value)
            render_result(result)
            record_history({
                "product_description": description,
                "category": category,
                "hs6": result["hs6"],
                "risk": result["risk"],
                "status": result["status"],
                "improved_description": result["improved_description"]
            })

elif page == "Bulk Upload":
    st.markdown("### Bulk Upload")
    st.caption(f"Free version supports up to {MAX_BULK_ROWS} rows per upload.")

    uploaded = st.file_uploader(
        "Upload CSV with columns: description, material, construction, origin, category, value",
        type=["csv"]
    )

    if uploaded:
        df = pd.read_csv(uploaded)
        required = {"description", "material", "construction", "origin", "category", "value"}
        missing_cols = required - set(df.columns)

        if missing_cols:
            st.error(f"Missing required columns: {', '.join(sorted(missing_cols))}")
        elif len(df) > MAX_BULK_ROWS:
            st.error(f"Free version supports a maximum of {MAX_BULK_ROWS} rows per upload.")
        else:
            results = []
            for _, row in df.iterrows():
                if st.session_state.usage_count >= LIMIT_DAILY_CHECKS:
                    break
                st.session_state.usage_count += 1
                result = process_single(
                    str(row["description"]),
                    str(row["material"]),
                    str(row["origin"]),
                    str(row["category"]),
                    str(row["construction"]),
                    float(row["value"])
                )
                results.append({
                    "description": row["description"],
                    "category": row["category"],
                    "hs6": result["hs6"],
                    "uk_code": result["uk_code"],
                    "risk": result["risk"],
                    "status": result["status"],
                    "improved_description": result["improved_description"],
                    "missing_fields": ", ".join(result["missing_fields"]) if result["missing_fields"] else ""
                })
                record_history({
                    "product_description": row["description"],
                    "category": row["category"],
                    "hs6": result["hs6"],
                    "risk": result["risk"],
                    "status": result["status"],
                    "improved_description": result["improved_description"]
                })

            result_df = pd.DataFrame(results)
            st.success(f"Processed {len(result_df)} rows")
            st.dataframe(result_df, use_container_width=True)

            st.download_button(
                "Download Results (CSV)",
                data=result_df.to_csv(index=False).encode("utf-8"),
                file_name="export_check_results.csv",
                mime="text/csv"
            )

elif page == "Issues Queue":
    st.markdown("### Issues Queue")
    st.caption("Products that may fail customs checks and need more detail before shipment.")

    if st.session_state.history:
        hist_df = pd.DataFrame(st.session_state.history)
        issues_df = hist_df[hist_df["risk"] != "GREEN"]
        if len(issues_df) == 0:
            st.success("No issues in the current session.")
        else:
            st.dataframe(issues_df, use_container_width=True)
    else:
        st.info("No products checked yet in this session.")

elif page == "Session History":
    st.markdown("### Session History")
    st.caption("History is stored for the current session only in the free version.")

    if st.session_state.history:
        hist_df = pd.DataFrame(st.session_state.history)
        st.dataframe(hist_df, use_container_width=True)
        st.download_button(
            "Download Session History",
            data=hist_df.to_csv(index=False).encode("utf-8"),
            file_name="session_history.csv",
            mime="text/csv"
        )
    else:
        st.info("No session history available yet.")

st.markdown("---")
st.caption(
    "Disclaimer: This tool provides preliminary guidance only. Final HS classification and customs compliance remain the responsibility of the exporter and customs broker."
)
