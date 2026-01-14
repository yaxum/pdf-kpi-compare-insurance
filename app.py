# app.py (din Streamlit-fil) - endast de ändringar som behövs
# ------------------------------------------------------------
# Byt ut safe_raw/safe_page + justera keys-listan och använd k.display()
# ------------------------------------------------------------

import streamlit as st
import tempfile
from kpi_compare import extract_kpis

st.set_page_config(page_title="PDF KPI-jämförelse", layout="wide")
st.title("PDF KPI-jämförelse")

col1, col2 = st.columns(2)

with col1:
    pdf_current = st.file_uploader("Ladda upp PDF – Nuvarande försäkring", type="pdf")
    current_company = st.selectbox("Nuvarande bolag", ["PTL", "Svedea"], index=0)

with col2:
    pdf_new = st.file_uploader("Ladda upp PDF – Ny offert", type="pdf")
    new_company = st.selectbox("Nytt bolag", ["Svedea", "PTL"], index=0)

st.divider()
name_col, _ = st.columns([1, 3])
with name_col:
    customer_name = st.text_input("Kundnamn", "")

partner = "DentFriends"
greeting = "Trevlig helg!"

st.session_state.setdefault("rooms_manual", "—")
st.session_state.setdefault("rooms_auto", "—")
st.session_state.setdefault("location_manual", "—")
st.session_state.setdefault("location_auto", "—")

st.subheader("Manuella uppgifter (om de inte finns i PDF)")
m1, m2, m3 = st.columns(3)

with m1:
    rooms_manual = st.text_input("Antal behandlingsrum (manuellt)", key="rooms_manual")
    location_manual = st.text_input("Försäkringsställe (manuellt fallback)", key="location_manual")

with m2:
    protetik_manual = st.text_input("Garantiförsäkring protetik", "—")
    sjukavbrott_text = st.text_input("Sjukavbrott", "—")

with m3:
    basbelopp_ptl = st.text_input("Max ersättning PTL (basbelopp)", "__")
    basbelopp_svedea = st.text_input("Max ersättning Svedea (basbelopp)", "__")

include_injections_note = st.checkbox(
    "Inkludera notis om estetiska injektioner (botox/filler)",
    value=True
)

st.divider()

def safe_display(kpis, key) -> str:
    try:
        k = kpis.get(key)
        if not k:
            return "—"
        return k.display()
    except Exception:
        return "—"

def safe_raw(kpis, key) -> str:
    # om du vill ha exakt raw-strängen ibland (t.ex. rooms)
    try:
        k = kpis.get(key)
        return (k.raw or "—") if k else "—"
    except Exception:
        return "—"

def safe_page(kpis, key):
    try:
        v = kpis.get(key)
        return str(v.evidence.page) if v and v.evidence else "—"
    except Exception:
        return "—"

def effective_rooms() -> str:
    manual = (st.session_state.get("rooms_manual") or "").strip()
    auto = (st.session_state.get("rooms_auto") or "").strip()
    if manual and manual != "—":
        return manual
    if auto and auto != "—":
        return auto
    return "—"

def effective_location() -> str:
    manual = (st.session_state.get("location_manual") or "").strip()
    auto = (st.session_state.get("location_auto") or "").strip()
    if auto and auto != "—":
        return auto
    if manual and manual != "—":
        return manual
    return "—"

if st.button("Analysera & visa jämförelse + kundtext"):
    if not pdf_current or not pdf_new:
        st.error("Ladda upp båda PDF:erna först.")
        st.stop()

    with st.spinner("Läser PDF:er..."):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f1, \
             tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f2:
            f1.write(pdf_current.read())
            f2.write(pdf_new.read())

            k_current = extract_kpis(f1.name)
            k_new = extract_kpis(f2.name)

    st.session_state["rooms_auto"] = safe_raw(k_new, "Antal behandlingsrum")
    st.session_state["location_auto"] = safe_display(k_current, "Försäkringsställe")

    tab_compare, tab_letter = st.tabs(["📊 Jämförelse", "✉️ Kundtext"])

    with tab_compare:
        st.subheader("Utdrag (med källor)")

        keys = [
            "Antal tandläkare",
            "Antal tandhygienister",
            "Antal tandkirurgi/käkkirurger",
            "Omsättning",
            "Avbrottstid",
            "Protetik - garantitid (år)",
            "Protetik - antal tandläkare",
            "Premie / Pris",
            "Försäkringsställe",
            "Antal behandlingsrum",
            "Sjukavbrott (finns)",
        ]

        for key in keys:
            c = safe_display(k_current, key)
            n = safe_display(k_new, key)
            st.markdown(f"### {key}")
            st.write(f"**{current_company}:** {c}  (sida {safe_page(k_current, key)})")
            st.write(f"**{new_company}:** {n}  (sida {safe_page(k_new, key)})")

        st.divider()
        st.subheader("Auto vs manuellt (kontroll)")
        st.write(f"**Rooms (auto):** {st.session_state['rooms_auto']}")
        st.write(f"**Rooms (manuellt):** {st.session_state['rooms_manual']}")
        st.write(f"**Rooms (används i texten):** {effective_rooms()}")
        st.write(f"**Försäkringsställe (auto):** {st.session_state['location_auto']}")
        st.write(f"**Försäkringsställe (manuellt):** {st.session_state['location_manual']}")
        st.write(f"**Försäkringsställe (används i texten):** {effective_location()}")

    with tab_letter:
        new_price = safe_display(k_new, "Premie / Pris")
        current_price = safe_display(k_current, "Premie / Pris")

        oms_new = safe_display(k_new, "Omsättning")
        avb
