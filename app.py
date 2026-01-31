# app.py (din Streamlit-fil) - endast de ändringar som behövs
# ------------------------------------------------------------
# Byt ut safe_raw/safe_page + justera keys-listan och använd k.display()
# ------------------------------------------------------------

import streamlit as st
import tempfile
from kpi_compare import extract_kpis

# Inject custom CSS for premium styling
with open(".streamlit/theme.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

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

st.session_state.setdefault("rooms_auto", "—")
st.session_state.setdefault("location_auto", "—")

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
    auto = (st.session_state.get("rooms_auto") or "").strip()
    if auto and auto != "—":
        return auto
    return "—"

def effective_location() -> str:
    auto = (st.session_state.get("location_auto") or "").strip()
    if auto and auto != "—":
        return auto
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

        # Build sjukavbrott row - use extracted data from scraper
        sjukavbrott_row = ""
        if sjukavbrott_details_new and sjukavbrott_details_new != "Nej":
            sjukavbrott_row = f"Sjukavbrott: {sjukavbrott_details_new}\n"
        
        # Build protetik row - use extracted data from scraper
        protetik_row = ""

        # Build comparison rows - only include if values differ
        prot_comparison = ""
        if prot_years_new != prot_years_current:
            prot_comparison += f"- Garantitid (år): {new_company} {prot_years_new}, {current_company} {prot_years_current}\n"
        if prot_dent_new != prot_dent_current:
            prot_comparison += f"- Antal tandläkare som omfattas: {new_company} {prot_dent_new}, {current_company} {prot_dent_current}\n"

        # Build main comparison section - only include different values
        comparison_lines = []
        if oms_new != oms_current:
            comparison_lines.append(f"Angiven omsättning: {new_company} {oms_new}, {current_company} {oms_current}.")
        if hygienists_new != hygienists_current:
            comparison_lines.append(f"Antal tandhygienister: {new_company} {hygienists_new}, {current_company} {hygienists_current}.")
        if sjukavbrott_details_new != sjukavbrott_details_current:
            comparison_lines.append(f"Sjukavbrott: {new_company} {sjukavbrott_details_new}, {current_company} {sjukavbrott_details_current}.")
        
        comparison_section = ""
        if comparison_lines:
            comparison_section = f"Jämförelse mellan {new_company} och {current_company}.\n" + "\n".join(comparison_lines)

        letter = f"""Hej {customer_name},

    Enligt önskemål bifogas här en offert från {new_company} i samarbete med {partner}.


    PRISER
    ----------------------------------------
    | Bolag   | Årspris                      |
    |---------|------------------------------|
    | {new_company:<7} | {new_price:<28}|
    | {current_company:<7} | {current_price:<28}|


    PREMIEGRUND
    ----------------------------------------
    Omsättning:              {oms_new}
    Behandlingsrum:          {effective_rooms()}
    Avbrott:                 {avbrott_new}
    Tandläkare:              {dentists_new}
    Tandhygienister:         {hygienists_new}
    Försäkringsställe:       {effective_location()}
    {protetik_row}{sjukavbrott_row}

    PROTETIK
    ----------------------------------------
    {prot_comparison if prot_comparison else "Villkoren är identiska mellan bolagen."}

    {injections_note}

    ÖVRIGA SKILLNADER
    ----------------------------------------
    {comparison_section if comparison_section else "Övriga villkor är identiska."}

    FÖRSÄKRINGSBELOPP – RÄTTSSKYDD
    ----------------------------------------
    Max ersättning per skada via {current_company}: 1 basbelopp
    Max ersättning per skada via {new_company}: 2 basbelopp
    (1 basbelopp 2026 = 59 200 kr)


    VID ACCEPT
    ----------------------------------------
    Bifogar här även villkoren hos {new_company} för patientförsäkring, garantiförsäkring för protetik samt informationsblad.

    Vid accept behöver vi namn, efternamn och personnummer på de tandläkare som ska omfattas av garantiförsäkringen för protetik. Vi skickar även en fullmakt som behöver undertecknas.

    Ni är välkomna att höra av er med frågor eller om ni önskar ett möte för att diskutera offerten.

    {greeting}
    """

        st.subheader("Kundtext (redo att kopiera)")
        st.text_area("", letter, height=720)
