
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

def normalize_text(value: str) -> str:
    return (value or "").strip()

def infer_expected_hs(description: str, material: str, category: str) -> dict:
    desc = (description or "").lower()
    material_l = (material or "").lower()
    category_l = (category or "").lower()

    if "scarf" in desc and "silk" in material_l:
        return {
            "hs6": "621410",
            "uk_code": "6214100090",
            "label": "Silk scarves and similar textile accessories",
            "confidence": 0.94,
            "explanation": "Description and material align with silk scarves."
        }
    elif "bag" in desc and any(x in material_l for x in ["leather", "suede", "hide"]):
        return {
            "hs6": "420221",
            "uk_code": "4202210000",
            "label": "Handbags with outer surface of leather",
            "confidence": 0.88,
            "explanation": "Description and material align with leather handbags or similar carrying articles."
        }
    elif "perfume" in desc or "parfum" in desc or category_l == "beauty":
        return {
            "hs6": "330300",
            "uk_code": "3303001000",
            "label": "Perfumes and toilet waters",
            "confidence": 0.81,
            "explanation": "Description and category align with perfume and fragrance products."
        }
    elif "dress" in desc and "cotton" in material_l:
        return {
            "hs6": "620442",
            "uk_code": "6204420000",
            "label": "Women's or girls' cotton dresses",
            "confidence": 0.79,
            "explanation": "Description and material align with cotton dresses."
        }
    else:
        return {
            "hs6": "UNKNOWN",
            "uk_code": "UNKNOWN",
            "label": "No strong pattern match",
            "confidence": 0.52,
            "explanation": "The current description and material do not provide a strong rule-based match."
        }

def missing_fields_for_category(category: str, description: str, material: str, origin: str, construction: str, has_hs_code: bool, supplied_hs_code: str) -> list[str]:
    missing = []

    if not normalize_text(description):
        missing.append("product description")
    if not normalize_text(material):
        missing.append("material composition")
    if not normalize_text(origin):
        missing.append("country of origin")

    desc = description.lower()
    category = category.lower()

    if category in {"fashion_accessories", "bags"} and not normalize_text(construction):
        missing.append("product construction or type")

    if "scarf" in desc and not normalize_text(construction):
        missing.append("construction type (for example woven or knitted)")

    if category == "beauty":
        if "ml" not in desc and "spray" not in desc and "bottle" not in desc:
            missing.append("packaging format or volume")

    if has_hs_code and not normalize_text(supplied_hs_code):
        missing.append("provided HS code")

    return missing

def improve_description(description: str, material: str, origin: str, category: str, construction: str) -> str:
    desc = normalize_text(description)
    material = normalize_text(material)
    origin = normalize_text(origin)
    construction = normalize_text(construction)

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
    return cleaned if cleaned else "No description available."

def assess_hs_code_input(provided_hs_code: str, expected: dict) -> dict:
    provided = normalize_text(provided_hs_code)
    expected_hs = expected.get("hs6", "UNKNOWN")

    if not provided:
        return {
            "mode": "NO_CODE_PROVIDED",
            "status": "NO_INPUT",
            "message": "No HS code was provided, so the tool generated a basic suggestion from the product information."
        }

    if expected_hs == "UNKNOWN":
        return {
            "mode": "CODE_PROVIDED",
            "status": "UNVERIFIED",
            "message": "An HS code was provided, but the product information is not specific enough for this free version to validate it confidently."
        }

    if provided == expected_hs:
        return {
            "mode": "CODE_PROVIDED",
            "status": "MATCH",
            "message": f"The provided HS code matches the tool's basic suggestion ({expected_hs})."
        }

    return {
        "mode": "CODE_PROVIDED",
        "status": "MISMATCH",
        "message": f"The provided HS code ({provided}) may not match the product details entered. The tool's basic suggestion is {expected_hs}."
    }

def build_result(description: str, material: str, origin: str, category: str, construction: str, value: float, has_hs_code: bool, supplied_hs_code: str) -> dict:
    missing = missing_fields_for_category(category, description, material, origin, construction, has_hs_code, supplied_hs_code)
    improved_desc = improve_description(description, material, origin, category, construction)
    expected = infer_expected_hs(description, material, category)

    if missing:
        return {
            "status": "BLOCKED",
            "hs6": "N/A",
            "uk_code": "N/A",
            "confidence": 0.0,
            "risk": "RED",
            "duty": "N/A",
            "vat": "N/A",
            "explanation": "The record does not contain enough information for a reliable pre-check.",
            "improved_description": improved_desc,
            "missing_fields": missing,
            "why_flagged": "Missing required shipment data increases customs risk and makes the description less usable for carriers or brokers.",
            "hs_validation": {
                "status": "NOT_ASSESSED",
                "message": "The provided information is incomplete, so HS code validation was not completed."
            },
            "provided_hs_code": normalize_text(supplied_hs_code) if has_hs_code else "",
            "suggested_hs_code": expected.get("hs6", "N/A"),
            "suggested_label": expected.get("label", "")
        }

    hs_validation = assess_hs_code_input(supplied_hs_code if has_hs_code else "", expected)

    final_hs = expected["hs6"]
    final_uk_code = expected["uk_code"]
    explanation = expected["explanation"]
    risk = "GREEN" if expected["confidence"] >= 0.9 else "AMBER"

    if has_hs_code and hs_validation["status"] == "MISMATCH":
        risk = "RED"
        explanation = explanation + " The supplied HS code does not appear to align with the product information entered."

    if has_hs_code and hs_validation["status"] == "UNVERIFIED":
        risk = "AMBER"

    if final_hs == "UNKNOWN":
        risk = "AMBER"

    why_flagged = {
        "GREEN": "The product information provided appears sufficiently detailed for a basic pre-check.",
        "AMBER": "This item likely needs more detail or manual review before shipment.",
        "RED": "This item is high risk for shipment because the category, description quality, or supplied HS code may require closer review before export."
    }[risk]

    return {
        "status": "APPROVED" if risk == "GREEN" else "REVIEW",
        "hs6": final_hs,
        "uk_code": final_uk_code,
        "confidence": expected["confidence"],
        "risk": risk,
        "duty": "TBD" if final_hs == "UNKNOWN" else ("8%" if final_hs == "621410" else "16%" if final_hs == "420221" else "6.5%" if final_hs == "330300" else "12%"),
        "vat": "20%",
        "explanation": explanation,
        "improved_description": improved_desc,
        "missing_fields": [],
        "why_flagged": why_flagged,
        "hs_validation": hs_validation,
        "provided_hs_code": normalize_text(supplied_hs_code) if has_hs_code else "",
        "suggested_hs_code": expected.get("hs6", "N/A"),
        "suggested_label": expected.get("label", "")
    }

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
    a.metric("Suggested HS Code", result.get("suggested_hs_code", "N/A"))
    b.metric("UK Commodity Code", result.get("uk_code", "N/A"))
    c.metric("Confidence", f"{int(result.get('confidence', 0) * 100)}%")

    if result.get("provided_hs_code"):
        st.markdown("### Provided HS Code Check")
        hs_check = result["hs_validation"]
        if hs_check["status"] == "MATCH":
            st.success(hs_check["message"])
        elif hs_check["status"] == "MISMATCH":
            st.error(hs_check["message"])
        else:
            st.warning(hs_check["message"])
        st.markdown(f"**Provided HS Code:** `{result.get('provided_hs_code')}`")

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

    if result.get("suggested_label"):
        st.markdown(f"**Suggested classification meaning:** {result['suggested_label']}")

st.sidebar.title("Export Readiness Checker (Free)")
page = st.sidebar.radio("Navigate", ["Dashboard", "Classify", "Bulk Upload", "Issues Queue", "Session History"])

st.title("Export Readiness Checker (Free)")
st.caption("Check if your product description is customs-ready before shipment. Detect missing data, improve descriptions, validate a provided HS code, and reduce shipment rejection risk.")

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
    st.write("- Provided HS code validation against simple product rules")
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
            has_hs_code = st.checkbox("I already have an HS code")
            supplied_hs_code = ""
            if has_hs_code:
                supplied_hs_code = st.text_input("Provided HS Code", "621410")

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
            st.info("This free version gives a preliminary pre-shipment check. It helps identify weak descriptions, missing data, and possible mismatch between a provided HS code and the product details entered.")

        if improve_clicked:
            st.markdown("### Suggested Improved Description")
            st.code(improve_description(description, material, origin, category, construction))

        if run_clicked:
            st.session_state.usage_count += 1
            result = build_result(description, material, origin, category, construction, value, has_hs_code, supplied_hs_code)
            render_result(result)
            record_history({
                "product_description": description,
                "category": category,
                "provided_hs_code": supplied_hs_code if has_hs_code else "",
                "suggested_hs_code": result["suggested_hs_code"],
                "hs_validation_status": result["hs_validation"]["status"],
                "risk": result["risk"],
                "status": result["status"],
                "improved_description": result["improved_description"]
            })

elif page == "Bulk Upload":
    st.markdown("### Bulk Upload")
    st.caption(f"Free version supports up to {MAX_BULK_ROWS} rows per upload.")
    st.caption("Optional column supported: provided_hs_code")

    uploaded = st.file_uploader(
        "Upload CSV with columns: description, material, construction, origin, category, value, provided_hs_code(optional)",
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
                provided_hs_code = str(row["provided_hs_code"]) if "provided_hs_code" in df.columns and pd.notna(row["provided_hs_code"]) else ""
                result = build_result(
                    str(row["description"]),
                    str(row["material"]),
                    str(row["origin"]),
                    str(row["category"]),
                    str(row["construction"]),
                    float(row["value"]),
                    bool(provided_hs_code),
                    provided_hs_code
                )
                results.append({
                    "description": row["description"],
                    "provided_hs_code": provided_hs_code,
                    "suggested_hs_code": result["suggested_hs_code"],
                    "hs_validation_status": result["hs_validation"]["status"],
                    "uk_code": result["uk_code"],
                    "risk": result["risk"],
                    "status": result["status"],
                    "improved_description": result["improved_description"],
                    "missing_fields": ", ".join(result["missing_fields"]) if result["missing_fields"] else ""
                })
                record_history({
                    "product_description": row["description"],
                    "category": row["category"],
                    "provided_hs_code": provided_hs_code,
                    "suggested_hs_code": result["suggested_hs_code"],
                    "hs_validation_status": result["hs_validation"]["status"],
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
        issues_df = hist_df[(hist_df["risk"] != "GREEN") | (hist_df["hs_validation_status"].isin(["MISMATCH", "UNVERIFIED"]))]
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
