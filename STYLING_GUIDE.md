# Styling Integration Guide

## Vad är gjort (utan kodändring):

1. **`.streamlit/config.toml`** - Streamlit tema konfiguration
   - Primärfärg: #E85B4F
   - Bakgrund: #FFFFFF
   - Sekundär bakgrund: #FAFAFA
   - Text: #111111
   - Font: sans serif (system-ui)

## För FULL styling (Cards, rounded buttons, input styling, spacing):

CSS-filen **`.streamlit/theme.css`** är redan skapad med all styling. 

För att aktivera den behövs en **mycket liten kodändring** i `app.py` (bara 2 rader):

### Lägg till detta längst upp i app.py, efter `import streamlit as st`:

```python
import streamlit as st

# Inject custom CSS
with open(".streamlit/theme.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.set_page_config(page_title="PDF KPI-jämförelse", layout="wide")
```

### Det är allt! Efter det får du:

✅ Premium cards & borders
✅ Rounded pill-buttons med hover-effekter
✅ Tydliga input-fält med fokus-styling
✅ Professionell table med zebra-rader
✅ Rätt spacing, typografi, färger
✅ Subtila skuggor
✅ Responsive design för mobile

---

## Vad CSS-filen innehåller:

- **Färger**: Alla accent-, text-, border-färger från specifikationen
- **Typografi**: Inter font, rätt storlekar för H1, H2, body, labels
- **Komponenter**:
  - Buttons: pill-form, hover-effekter, fokus-outline
  - Inputs: border, radius, fokus-state med färg
  - Cards/sections: border, radius, shadow
  - Tables: sticky header, zebra-rader, hover
  - Dividers, tabs, alerts med rätt färger
- **Layout**: Max-width 1200px, 24px gutter, god spacing
- **Responsive**: Mobile-optimerad

---

## Nästa steg:

1. Kopiera dessa 2 rader in i `app.py` (efter `import streamlit as st`)
2. Kör `streamlit run app.py`
3. Se resultatet! 🎨

Om du vill justera något i styling senare, redigera bara `.streamlit/theme.css` direkt.
