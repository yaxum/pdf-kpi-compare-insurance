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

    with tab_letter:
        new_price = safe_display(k_new, "Premie / Pris")
        current_price = safe_display(k_current, "Premie / Pris")

        oms_new = safe_display(k_new, "Omsättning")
        avbrott_new = safe_display(k_new, "Avbrottstid")
        dentists_new = safe_display(k_new, "Antal tandläkare")
        hygienists_new = safe_display(k_new, "Antal tandhygienister")

        oms_current = safe_display(k_current, "Omsättning")
        hygienists_current = safe_display(k_current, "Antal tandhygienister")

        sjukavbrott_exists_new = safe_display(k_new, "Sjukavbrott (finns)")
        sjukavbrott_exists_current = safe_display(k_current, "Sjukavbrott (finns)")
        sjukavbrott_details_new = safe_display(k_new, "Sjukavbrott (detaljer)")
        sjukavbrott_details_current = safe_display(k_current, "Sjukavbrott (detaljer)")

        prot_years_new = safe_display(k_new, "Protetik - garantitid (år)")
        prot_years_current = safe_display(k_current, "Protetik - garantitid (år)")
        prot_dent_new = safe_display(k_new, "Protetik - antal tandläkare")
        prot_dent_current = safe_display(k_current, "Protetik - antal tandläkare")

        injections_note = ""
        if include_injections_note:
            injections_note = (
                "\nNotera att offerten inte inkluderar estetiska injektionsbehandlingar (botox/filler). "
                "Återkom om det finns ett behov av att utöka omfattningen till att även omfatta den typen av behandlingar.\n"
            )

        letter = f"""Hej {customer_name},

Enligt önskemål bifogas här en offert från {new_company} i samarbete med {partner}. 

Årspris {new_company}, inklusive arvode: {new_price} 
Årspris nuvarande {current_company}: {current_price}

Bifogar här även villkoren hos {new_company} för patientförsäkring, garantiförsäkring för protetik samt informationsblad hur garantiförsäkring fungerar hos {new_company}.

{new_company} har använt sig av nedan angiva uppgifter som premiegrund i sin offert.
Omsättning: {oms_new}
Antal behandlingsrum: {effective_rooms()}
Avbrott: {avbrott_new}
Antal tandläkare: {dentists_new}
Antal tandhygienist: {hygienists_new}
Garantiförsäkring protetik (manuell): {protetik_manual}
Sjukavbrott (manuell): {sjukavbrott_text}
Sjukavbrott (detekterat i PDF): {sjukavbrott_exists_new}
Sjukavbrott (detaljer): {sjukavbrott_details_new}
Försäkringsställe: {effective_location()}

Protetik (jämförelse):
- Garantitid (år): {new_company} {prot_years_new}, {current_company} {prot_years_current}
- Antal tandläkare som omfattas: {new_company} {prot_dent_new}, {current_company} {prot_dent_current}

{injections_note}
Jämförelse mellan {new_company} och {current_company}.
Angiven omsättning: {new_company} {oms_new}, {current_company} {oms_current}.
Antal tandhygienister: {new_company} {hygienists_new}, {current_company} {hygienists_current}.
Sjukavbrott (PDF-detektion): {new_company} {sjukavbrott_exists_new}, {current_company} {sjukavbrott_exists_current}.
Sjukavbrott (detaljer): {new_company} {sjukavbrott_details_new}, {current_company} {sjukavbrott_details_current}.

Försäkringsbelopp Rättsskydd
Tvister och kostnader som ersätts ur Rättsskyddsförsäkringen ökar varje år till antal och till kostnad per ärende.
Maximal ersättning per skada via {current_company} är {basbelopp_ptl} Basbelopp
Maximal ersättning per skada via {new_company} är {basbelopp_svedea} Basbelopp
(1 basbelopp år 2026 är 59 200 kr)

Övrigt
En stor fördel med Svedea är deras skadeavdelning. Det är korta vänt- och ledtider. Personligt bemötande och mycket kunnig personal. Det finns flera specialister på just tand- och protetikskador.
Svedeas skadeavdelning kommer oftast i topp när kunder, försäkringsförmedlare och branschorganisationer får sätta betyg.

Vid eventuell accept av offerten om ni önskar teckna garantiförsäkring för protetik behöver vi namn, efternamn och personnummer på de tandläkare som ska omfattas av protetiken då Svedea skriver in det i försäkringsbrevet.

Om ni accepterar offerten återkommer vi med en fullmakt också. Det är något vi formellt behöver få på plats för att få hjälpa er gentemot försäkringsbolagen framöver.

Ni är välkomna att höra av er om ni har några frågor och vi bokar gärna in ett möte om ni önskar det.

{greeting}
"""

        st.subheader("Kundtext (redo att kopiera)")
        st.text_area("", letter, height=720)
