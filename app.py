import streamlit as st
import tempfile
from kpi_compare import extract_kpis

st.set_page_config(page_title="PDF KPI-jämförelse", layout="wide")
st.title("PDF KPI-jämförelse")

# ---------------- Upload + bolag ----------------
col1, col2 = st.columns(2)

with col1:
    pdf_current = st.file_uploader("Ladda upp PDF – Nuvarande försäkring", type="pdf")
    current_company = st.selectbox("Nuvarande bolag", ["PTL", "Svedea"], index=0)

with col2:
    pdf_new = st.file_uploader("Ladda upp PDF – Ny offert", type="pdf")
    new_company = st.selectbox("Nytt bolag", ["Svedea", "PTL"], index=0)

# ---------------- Kunduppgifter ----------------
st.divider()
name_col, _ = st.columns([1, 3])
with name_col:
    customer_name = st.text_input("Kundnamn", "")

partner = "DentFriends"
greeting = "Trevlig helg!"

# ---------------- State-init ----------------
# Vi använder separata nycklar för "auto"-värden så vi aldrig krockar med widget-keys.
st.session_state.setdefault("rooms_manual", "—")
st.session_state.setdefault("rooms_auto", "—")
st.session_state.setdefault("location_manual", "—")
st.session_state.setdefault("location_auto", "—")

# ---------------- Manuella fält ----------------
st.subheader("Manuella uppgifter (om de inte finns i PDF)")
m1, m2, m3 = st.columns(3)

with m1:
    # Manual input (egen key)
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

# ---------------- Helpers ----------------
def safe_raw(kpis, key):
    try:
        v = kpis.get(key)
        return v.raw if v and v.raw else "—"
    except Exception:
        return "—"

def safe_page(kpis, key):
    try:
        v = kpis.get(key)
        return str(v.evidence.page) if v and v.evidence else "—"
    except Exception:
        return "—"

def effective_rooms() -> str:
    """
    Prioritet:
    1) Om användaren har skrivit manuellt (inte '—' och inte tomt) -> använd det
    2) annars använd auto från PDF
    3) annars '—'
    """
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

# ---------------- Run ----------------
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

    # -------- Auto-fyll (men i separata keys som INTE är widget-keys) --------
    st.session_state["rooms_auto"] = safe_raw(k_new, "Antal behandlingsrum")

    # Försäkringsställe från NUVARANDE PDF (enligt ert upplägg)
    st.session_state["location_auto"] = safe_raw(k_current, "Försäkringsställe")

    # -------- Render output --------
    tab_compare, tab_letter = st.tabs(["📊 Jämförelse", "✉️ Kundtext"])

    # ---------- TAB 1: Jämförelse ----------
    with tab_compare:
        st.subheader("Utdrag (med källor)")
        keys = [
            "Antal tandläkare",
            "Antal tandhygienister",
            "Antal tandkirurgi/käkkirurger",
            "Omsättning",
            "Avbrottstid",
            "Protetik (år)",
            "Premie / Pris",
            "Försäkringsställe",
            "Antal behandlingsrum",
        ]

        for key in keys:
            c = safe_raw(k_current, key)
            n = safe_raw(k_new, key)
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

    # ---------- TAB 2: Kundtext ----------
    with tab_letter:
        new_price = safe_raw(k_new, "Premie / Pris")
        current_price = safe_raw(k_current, "Premie / Pris")

        oms_new = safe_raw(k_new, "Omsättning")
        avbrott_new = safe_raw(k_new, "Avbrottstid")
        dentists_new = safe_raw(k_new, "Antal tandläkare")
        hygienists_new = safe_raw(k_new, "Antal tandhygienister")

        oms_current = safe_raw(k_current, "Omsättning")
        hygienists_current = safe_raw(k_current, "Antal tandhygienister")

        injections_note = ""
        if include_injections_note:
            injections_note = (
                "\nNotera att offerten inte inkluderar estetiska injektionsbehandlingar (botox/filler). "
                "Återkom om det finns ett behov av att utöka omfattningen till att även omfatta den typen av behandlingar.\n"
            )

        letter = f"""Hej {customer_name},

Enligt önskemål bifogas här en offert från {new_company} i samarbete med {partner}. 

Årspris {new_company}, inklusive arvode: {new_price} kr 
Årspris nuvarande {current_company}: {current_price} kr

Bifogar här även villkoren hos {new_company} för patientförsäkring, garantiförsäkring för protetik samt informationsblad hur garantiförsäkring fungerar hos {new_company}.

{new_company} har använt sig av nedan angiva uppgifter som premiegrund i sin offert.
Omsättning: {oms_new}
Antal behandlingsrum: {effective_rooms()}
Avbrott: {avbrott_new} månader
Antal tandläkare: {dentists_new}
Antal tandhygienist: {hygienists_new}
Garantiförsäkring protetik: {protetik_manual}
Sjukavbrott: {sjukavbrott_text}
Försäkringsställe: {effective_location()}
{injections_note}
Jämförelse mellan {new_company} och {current_company}.
Angiven omsättning: {new_company} {oms_new}, {current_company} {oms_current}.
Antal tandhygienister: {new_company} {hygienists_new}, {current_company} {hygienists_current}.


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
