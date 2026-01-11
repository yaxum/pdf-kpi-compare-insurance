import streamlit as st
import tempfile
from kpi_compare import extract_kpis

st.set_page_config(page_title="PDF KPI-jämförelse", layout="wide")
st.title("PDF KPI-jämförelse")

# -------- Inputs --------
colA, colB = st.columns(2)

with colA:
    pdf_current = st.file_uploader("Ladda upp PDF – Nuvarande försäkring", type="pdf")
    current_company = st.selectbox("Nuvarande bolag", ["PTL", "Svedea"], index=0)

with colB:
    pdf_new = st.file_uploader("Ladda upp PDF – Ny offert", type="pdf")
    new_company = st.selectbox("Nytt bolag", ["Svedea", "PTL"], index=0)

st.divider()

meta1, meta2, meta3, meta4 = st.columns(4)
with meta1:
    customer_name = st.text_input("Kundnamn", "Lisa")
with meta2:
    partner = st.text_input("Samarbete/Partner", "DentFriends")
with meta3:
    greeting = st.text_input("Hälsningsfras", "Trevlig helg!")
with meta4:
    include_injections_note = st.checkbox(
        "Inkludera notis om estetiska injektioner (botox/filler)",
        value=True
    )

# Manuella fält (för sådant som ofta saknas i PDF)
st.subheader("Manuella uppgifter (om de inte finns i PDF:erna)")
m1, m2, m3 = st.columns(3)
with m1:
    rooms = st.text_input("Antal behandlingsrum", "—")
    location = st.text_input("Försäkringsställe (adress)", "—")
with m2:
    sjukavbrott_text = st.text_input("Sjukavbrott (ex: Lisa Taavo 1,9 MSEK)", "—")
    cyber_text = st.text_input("Cyberförsäkring (fri text)", "—")
with m3:
    rattsskydd_text = st.text_area(
        "Rättsskydd (fri text)",
        "Tvister och kostnader som ersätts ur Rättsskyddsförsäkringen ökar varje år till antal och till kostnad per ärende.\n"
        "Maximal ersättning per skada via PTL är __ Basbelopp\n"
        "Maximal ersättning per skada via Svedea är __ Basbelopp\n"
        "(1 basbelopp år 2025 är 58 800 kr)",
        height=140
    )

krav_text = st.text_area(
    "Krav vid sjukavbrottsförsäkring (fri text)",
    "Om man tecknar en sjukavbrottsförsäkring så har PTL krav på att man samtidigt måste ha en sjukvårdsförsäkring.\n"
    "Detta krav har inte Svedea.",
    height=90
)

ovrigt_text = st.text_area(
    "Övrigt (fri text)",
    "En stor fördel med Svedea är deras skadeavdelning. Det är korta vänt- och ledtider. Personligt bemötande och mycket kunnig personal. "
    "Det finns flera specialister på just tand- och protetikskador.\n"
    "Svedeas skadeavdelning kommer oftast i topp när kunder, försäkringsförmedlare och branschorganisationer får sätta betyg.",
    height=110
)

protetik_accept_text = st.text_area(
    "Text vid accept (fri text)",
    "Vid eventuell accept av offerten om ni önskar teckna garantiförsäkring för protetik behöver vi namn, efternamn och personnummer på de "
    "tandläkare som ska omfattas av protetiken då Svedea skriver in det i försäkringsbrevet.\n\n"
    "Om ni accepterar offerten återkommer vi med en fullmakt också. Det är något vi formellt behöver få på plats för att få hjälpa er gentemot "
    "försäkringsbolagen framöver.\n\n"
    "Ni är välkomna att höra av er om ni har några frågor och vi bokar gärna in ett möte om ni önskar det.",
    height=160
)

st.divider()

# -------- Run extraction --------
def safe_raw(kpis, key):
    try:
        v = kpis[key]
        return v.raw if v and v.raw else "—"
    except Exception:
        return "—"

def safe_page(kpis, key):
    try:
        v = kpis[key]
        return str(v.evidence.page) if v and v.evidence else "—"
    except Exception:
        return "—"

btn = st.button("Analysera & skapa kundtext")

if btn:
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

    tab_compare, tab_letter = st.tabs(["📊 Jämförelse", "✉️ Kundtext (mall)"])

    # -------- TAB 1: Comparison --------
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
        ]

        for key in keys:
            c = safe_raw(k_current, key)
            n = safe_raw(k_new, key)
            st.markdown(f"### {key}")
            st.write(f"**{current_company}:** {c}  (sida {safe_page(k_current, key)})")
            st.write(f"**{new_company}:** {n}  (sida {safe_page(k_new, key)})")

    # -------- TAB 2: Customer letter (your template) --------
    with tab_letter:
        # Values for letter
        new_price = safe_raw(k_new, "Premie / Pris")
        current_price = safe_raw(k_current, "Premie / Pris")

        # “Premiegrund”-uppgifter (primärt från NY offert, men du kan ändra i texten efteråt)
        oms_new = safe_raw(k_new, "Omsättning")
        avbrott_new = safe_raw(k_new, "Avbrottstid")
        dentists_new = safe_raw(k_new, "Antal tandläkare")
        hygienists_new = safe_raw(k_new, "Antal tandhygienister")

        # protetik i din mall är ofta “antal som omfattas” – vi har “år” idag.
        # Vi stoppar in extraherat värde ändå, men du kan skriva över i texten.
        protetik_new = safe_raw(k_new, "Protetik (år)")

        # Jämförelse-del (ny vs nuvarande)
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
Antal behandlingsrum: {rooms}
Avbrott: {avbrott_new} månader
Antal tandläkare: {dentists_new}
Antal tandhygienist: {hygienists_new}
Garantiförsäkring protetik: {protetik_new}
Sjukavbrott: {sjukavbrott_text}
Försäkringsställe: {location}
{injections_note}
Jämförelse mellan {new_company} och {current_company}.
Angiven omsättning: {new_company} {oms_new}, {current_company} {oms_current}.
Antal tandhygienister: {new_company} {hygienists_new}, {current_company} {hygienists_current}.
Cyberförsäkring: {cyber_text}

Försäkringsbelopp Rättsskydd
{rattsskydd_text}

Krav vid sjukavbrottsförsäkring
{krav_text}

Övrigt
{ovrigt_text}

{protetik_accept_text}

{greeting}
"""

        st.subheader("Kundtext (redo att kopiera)")
        st.text_area("", letter, height=650)
