import streamlit as st
import tempfile
from kpi_compare import extract_kpis

st.set_page_config(page_title="PDF KPI-jämförelse", layout="centered")
st.title("PDF KPI-jämförelse")

pdf1 = st.file_uploader("Ladda upp PDF 1", type="pdf")
pdf2 = st.file_uploader("Ladda upp PDF 2", type="pdf")

if pdf1 and pdf2 and st.button("Analysera"):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f1, \
         tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f2:
        f1.write(pdf1.read())
        f2.write(pdf2.read())

        k1 = extract_kpis(f1.name)
        k2 = extract_kpis(f2.name)

    st.subheader("Resultat")

    for key in k1:
        a, b = k1[key], k2[key]
        st.markdown(f"### {key}")

        st.write("**PDF 1:**", a.raw or "—")
        if a.evidence:
            st.caption(f"Källa: sida {a.evidence.page}")

        st.write("**PDF 2:**", b.raw or "—")
        if b.evidence:
            st.caption(f"Källa: sida {b.evidence.page}")
