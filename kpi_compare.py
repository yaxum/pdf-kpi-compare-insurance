# kpi_compare.py
# ------------------------------------------------------------
# Robust KPI-extraktion för PTL + Svedea med:
# - Omsättning: normaliserar KSEK -> SEK
# - Årspremie: bolagsspecifik prioritet + säkrare träff
# - Protetik: 2 KPI:er (garantitid + antal tandläkare)
# - Försäkringsställe: label/sektion först, toppblock sist
# - Sjukavbrott: finns/ej + (ev) radbevis
# ------------------------------------------------------------

import re
import pdfplumber
from dataclasses import dataclass
from typing import Optional, Dict, List, Tuple


# -------------------- Data models --------------------

@dataclass
class Evidence:
    page: int
    text: str

@dataclass
class KPI:
    # Normaliserat numeriskt värde (t.ex. SEK)
    value: Optional[float]
    # Det som stod i PDF (t.ex. "10 000")
    raw: Optional[str]
    # Enhet för raw (t.ex. "KSEK" eller "kr")
    unit: Optional[str]
    # Om raw-unit behöver skalas för att bli value (t.ex. 1000 för KSEK->SEK)
    multiplier: float = 1.0
    evidence: Optional[Evidence] = None

def display(self) -> str:
    """
    Human friendly display med svensk talformatering.
    - Om value saknas: visa raw + unit
    - Om unit=KSEK: visa "10 000 KSEK (= 10 000 000 kr)"
    - Annars: visa "8 232 000 kr" etc.
    """

    def fmt_number_sv(x: float) -> str:
        # Om heltal: 8 232 000
        if float(x).is_integer():
            return f"{int(x):,}".replace(",", " ")
        # Annars: 3,50 (svensk decimal)
        s = f"{x:,.2f}"          # "1,234.56"
        s = s.replace(",", " ")  # "1 234.56"
        s = s.replace(".", ",")  # "1 234,56"
        return s

    if self.value is None:
        if self.raw:
            return f"{self.raw} {self.unit or ''}".strip()
        return "—"

    v = self.value

    # Om originalet var KSEK: visa både raw KSEK och normaliserad SEK (kr)
    if (self.unit or "").upper() == "KSEK":
        raw_part = f"{self.raw} KSEK" if self.raw else "KSEK"
        return f"{raw_part} (= {fmt_number_sv(v)} kr)".strip()

    # Default: value + unit
    u = self.unit or ""
    return f"{fmt_number_sv(v)} {u}".strip()



# -------------------- Helpers --------------------

def to_number(s: str) -> float:
    """
    Klarar "3,00" och "10 000" etc.
    """
    s = s.replace("\u00A0", " ").strip()
    s = s.replace(" ", "").replace(",", ".")
    return float(s)

def read_pages(path: str) -> List[Tuple[int, str]]:
    with pdfplumber.open(path) as pdf:
        return [(i + 1, (p.extract_text() or "")) for i, p in enumerate(pdf.pages)]

def first_number_token(line: str) -> Optional[str]:
    """
    Plockar första tal-token ur en rad med flera tal.
    Ex: "10 000 10 000 0 0 0" -> "10 000"
    """
    line = line.replace("\u00A0", " ").strip()

    # Hitta alla siffergrupper som kan ha tusentalsmellanslag och ev decimal (3,00)
    nums = re.findall(r"\d+(?:\s\d{3})*(?:,\d+)?", line)
    return nums[0].strip() if nums else None


def detect_company(pages: List[Tuple[int, str]]) -> str:
    """
    Enkel bolagsdetektion baserat på typiska ord.
    """
    head = "\n".join([t for _, t in pages[:2]]).lower()
    if "svedea" in head:
        return "Svedea"
    # PTL-dokument brukar ha "Försäkringsbesked" och/eller "kundnr"
    if "försäkringsbesked" in head or "kundnr" in head or "ptl" in head:
        return "PTL"
    return "Unknown"

def kpi_none() -> KPI:
    return KPI(None, None, None, 1.0, None)

def find_first(pages, patterns, unit=None, multiplier: float = 1.0) -> KPI:
    for page, text in pages:
        for rx in patterns:
            m = rx.search(text)
            if m:
                raw = m.group(1).strip()
                try:
                    val = to_number(raw) * multiplier
                except Exception:
                    val = None
                return KPI(
                    value=val,
                    raw=raw,
                    unit=unit,
                    multiplier=multiplier,
                    evidence=Evidence(page, m.group(0).strip())
                )
    return KPI(None, None, unit, multiplier, None)

def find_first_line(pages, patterns: List[re.Pattern]) -> KPI:
    """
    För textvärden där vi vill plocka en rad/bit text.
    """
    for page, text in pages:
        for rx in patterns:
            m = rx.search(text)
            if m:
                raw = m.group(1).strip()
                return KPI(
                    value=None,
                    raw=raw,
                    unit=None,
                    multiplier=1.0,
                    evidence=Evidence(page, m.group(0).strip())
                )
    return kpi_none()

def find_svedea_rooms(pages: List[Tuple[int, str]]) -> KPI:
    """
    Svedea: "Beh.rum 1-4/kök" (textvärde)
    """
    return find_first_line(
        pages,
        [re.compile(r"\bBeh\.rum\s+([^\n\r]+)", re.I)]
    )

def find_svedea_ksek_turnover(pages: List[Tuple[int, str]]) -> KPI:
    """
    Svedea: "Årsomsättning i KSEK" och nästa rad innehåller flera tal.
    Vi tar första tal-token och normaliserar till SEK (multiplicerar med 1000).
    """
    for page, text in pages:
        m = re.search(r"Årsomsättning\s+i\s*KSEK.*?\n\s*([0-9\s]+)", text, re.I)
        if m:
            raw_line = m.group(1).strip()
            first = first_number_token(raw_line)
            if first:
                try:
                    val_sek = to_number(first) * 1000
                except Exception:
                    val_sek = None
                return KPI(
                    value=val_sek,
                    raw=first,
                    unit="KSEK",
                    multiplier=1000.0,
                    evidence=Evidence(page, f"Årsomsättning i KSEK\n{raw_line}")
                )
    return KPI(None, None, "KSEK", 1000.0, None)

def find_ptl_turnover_sek(pages: List[Tuple[int, str]]) -> KPI:
    # PTL: "Årsomsättning 8 232 000 kr"
    return find_first(
        pages,
        [re.compile(r"Årsomsättning\s+([\d\s]+)\s*kr", re.I)],
        unit="kr",
        multiplier=1.0,
    )

def find_premium_ptl(pages: List[Tuple[int, str]]) -> KPI:
    """
    PTL: prioritera "Total årspremie ..." (ofta i försäkringsbesked-delen).
    Vi försöker först hitta inom sidor där 'Försäkringsbesked' förekommer,
    annars global fallback.
    """
    rx = re.compile(r"Total\s+årspremie\s+([\d\s]+)\s*kr", re.I)

    # 1) Försök hitta sidor med "Försäkringsbesked"
    priority_pages: List[Tuple[int, str]] = []
    for page, text in pages:
        if re.search(r"Försäkringsbesked", text, re.I):
            priority_pages.append((page, text))
    if priority_pages:
        k = find_first(priority_pages, [rx], unit="kr")
        if k.raw:
            return k

    # 2) Fallback: hela dokumentet
    return find_first(pages, [rx], unit="kr")

def find_premium_svedea(pages: List[Tuple[int, str]]) -> KPI:
    # Svedea: "Årspremie 37 240 kr"
    return find_first(
        pages,
        [re.compile(r"Årspremie\s+([\d\s]+)\s*kr", re.I)],
        unit="kr",
        multiplier=1.0,
    )

def find_protetik_years_ptl(pages: List[Tuple[int, str]]) -> KPI:
    # PTL: "Grund 3 år"
    return find_first(
        pages,
        [re.compile(r"\bGrund\s+(\d+)\s*år\b", re.I)],
        unit="år",
    )

def find_protetik_dentist_count_svedea(pages: List[Tuple[int, str]]) -> KPI:
    # Svedea: "- Antal tandläkare 3,00"
    return find_first(
        pages,
        [re.compile(r"-\s*Antal\s+tandläkare\s+([\d\s]+,\d+|\d+)", re.I)],
        unit="st",
        multiplier=1.0
    )

def find_protetik_dentist_count_ptl(pages: List[Tuple[int, str]]) -> KPI:
    """
    PTL: de listar namn i protetikavsnittet.
    Vi räknar unika namn som står efter 'Tandläkare' inom samma block.
    Heuristik:
      - hitta ett textutdrag runt 'Tandläkare som' eller 'Garantiförsäkring protetik'
      - plocka rader som matchar 'Tandläkare <Förnamn> <Efternamn>'
    """
    # Leta protetik-nära sidor först
    candidates: List[Tuple[int, str]] = []
    for page, text in pages:
        if re.search(r"(Garantiförsäkring\s+protetik|protetik|Tandläkare\s+som)", text, re.I):
            candidates.append((page, text))

    # regex för tandläkarnamn (2+ ord, tillåter bindestreck)
    name_rx = re.compile(r"\bTandläkare\s+([A-Za-zÅÄÖåäö\-]+(?:\s+[A-Za-zÅÄÖåäö\-]+)+)\b")

    for page, text in candidates or pages:
        names = set(m.group(1).strip() for m in name_rx.finditer(text))
        # filtrera bort uppenbart skräp (t.ex. om någon rubrik råkar matcha)
        names = {n for n in names if len(n) >= 5 and not re.search(r"(protetik|försäkring|ansvar|premie)", n, re.I)}
        if names:
            return KPI(
                value=float(len(names)),
                raw=str(len(names)),
                unit="st",
                multiplier=1.0,
                evidence=Evidence(page, "PTL protetik tandläkare:\n" + "\n".join(sorted(names)))
            )

    return kpi_none()

def find_location_ptl(pages: List[Tuple[int, str]]) -> KPI:
    # PTL: "Försäkringsställen Hantverkargatan 1 a, 95234"
    return find_first_line(
        pages,
        [
            re.compile(r"Försäkringsställen?\s+(.+)$", re.I | re.M),
            re.compile(r"Försäkringsställe\s*[:\-]\s*(.+)$", re.I | re.M),
        ]
    )

def find_location_svedea(pages: List[Tuple[int, str]]) -> KPI:
    """
    Svedea: ofta finns en rad som ser ut som "Norrköping, Drottninggatan 64"
    i egendomsdelen. Vi försöker hitta den nära rubriken, annars fallback.
    """
    # 1) sektionstyrd: hitta block runt 'EGENDOMSFÖRSÄKRING' och 'SJÄLVRISK'
    for page, text in pages[:3]:
        if re.search(r"EGENDOMSFÖRSÄKRING", text, re.I) and re.search(r"SJÄLVRISK", text, re.I):
            # hitta rad med "Ort, Gata" (komma är en bra signal)
            for ln in [l.strip() for l in text.splitlines() if l.strip()]:
                if re.search(r"^[A-Za-zÅÄÖåäö\- ]+,\s*.+\d", ln):
                    return KPI(None, ln, None, 1.0, Evidence(page, ln))

    # 2) fallback: första rad som ser ut som "Ort, Gata ..."
    for page, text in pages[:3]:
        for ln in [l.strip() for l in text.splitlines() if l.strip()]:
            if re.search(r"^[A-Za-zÅÄÖåäö\- ]+,\s*.+\d", ln):
                return KPI(None, ln, None, 1.0, Evidence(page, ln))

    return kpi_none()

def find_company_address_block(pages: List[Tuple[int, str]]) -> KPI:
    """
    SISTA FALLBACK: toppadressblock (bolag + gata + postnr/ort).
    OBS: kan vara förmedlar-/boxadress i vissa PDF:er.
    """
    for page, text in pages[:3]:
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        if len(lines) < 3:
            continue

        for i in range(min(25, len(lines) - 2)):
            if re.search(r"\b\d{3}\s?\d{2}\b", lines[i + 2]):
                block = "\n".join([lines[i], lines[i + 1], lines[i + 2]])
                return KPI(None, block, None, 1.0, Evidence(page, block))

        for i in range(len(lines) - 3):
            if lines[i].lower().startswith("kundnr"):
                block = "\n".join([lines[i + 1], lines[i + 2], lines[i + 3]])
                if re.search(r"\b\d{3}\s?\d{2}\b", lines[i + 3]):
                    return KPI(None, block, None, 1.0, Evidence(page, block))

    return kpi_none()

def find_sjukavbrott_exists(pages: List[Tuple[int, str]]) -> KPI:
    """
    Returnerar Ja/Nej som text (raw), och value=1/0.
    """
    for page, text in pages:
        if re.search(r"\bSjukavbrott\b", text, re.I):
            # ta en kort evidensrad om möjligt
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
            evidence_line = next((ln for ln in lines if re.search(r"\bSjukavbrott\b", ln, re.I)), "Sjukavbrott (träff)")
            return KPI(
                value=1.0,
                raw="Ja",
                unit=None,
                multiplier=1.0,
                evidence=Evidence(page, evidence_line)
            )
    return KPI(value=0.0, raw="Nej", unit=None, multiplier=1.0, evidence=None)


# -------------------- KPI extraction --------------------

def extract_kpis(pdf_path: str) -> Dict[str, KPI]:
    pages = read_pages(pdf_path)
    company = detect_company(pages)

    kpis: Dict[str, KPI] = {}

    # Antal tandläkare
    kpis["Antal tandläkare"] = find_first(
        pages,
        [
            re.compile(r"Antal\s+Tandläkare\s+(\d+)", re.I),  # PTL
            re.compile(r"Tandläkare\s*-\s*övrigt\s*([\d\s]+,\d+|\d+)\s*st", re.I),  # Svedea
        ],
        unit="st"
    )

    # Antal tandhygienister
    kpis["Antal tandhygienister"] = find_first(
        pages,
        [
            re.compile(r"Antal\s+Tandhygienister\s+(\d+)", re.I),  # PTL
            # ev svedea-format kan läggas till senare
        ],
        unit="st"
    )

    # Antal tandkirurgi/käkkirurger
    kpis["Antal tandkirurgi/käkkirurger"] = find_first(
        pages,
        [
            re.compile(r"Antal\s+Käkkirurger\s+(\d+)", re.I),
            re.compile(r"Antal\s+Tandkirurger\s+(\d+)", re.I),
            re.compile(r"Käkkirurger\s*-\s*övrigt\s*([\d\s]+,\d+|\d+)\s*st", re.I),
            re.compile(r"Tandkirurger\s*-\s*övrigt\s*([\d\s]+,\d+|\d+)\s*st", re.I),
        ],
        unit="st"
    )

    # Omsättning (normaliserad)
    if company == "Svedea":
        kpis["Omsättning"] = find_svedea_ksek_turnover(pages)  # value = SEK, raw = KSEK
        if not kpis["Omsättning"].raw:
            # fallback om layout avviker
            kpis["Omsättning"] = find_ptl_turnover_sek(pages)
    else:
        # PTL först
        k = find_ptl_turnover_sek(pages)
        kpis["Omsättning"] = k if k.raw else find_svedea_ksek_turnover(pages)

    # Avbrottstid
    kpis["Avbrottstid"] = find_first(
        pages,
        [
            re.compile(r"Avbrottsförsäkring\s+(\d+)\s*månader", re.I),  # PTL
            re.compile(r"Ansvarstid\s+(\d+)\s*månader", re.I),          # Svedea
        ],
        unit="månader"
    )

    # Protetik - garantitid (år)
    # PTL: Grund 3 år; Svedea varierar -> lämna tom om ej hittas
    kpis["Protetik - garantitid (år)"] = find_protetik_years_ptl(pages)

    # Protetik - antal tandläkare
    if company == "Svedea":
        kpis["Protetik - antal tandläkare"] = find_protetik_dentist_count_svedea(pages)
    else:
        kpis["Protetik - antal tandläkare"] = find_protetik_dentist_count_ptl(pages)

    # Premie / Pris (bolagsspecifik)
    if company == "Svedea":
        kpis["Premie / Pris"] = find_premium_svedea(pages)
    else:
        kpis["Premie / Pris"] = find_premium_ptl(pages)

    # Antal behandlingsrum (Svedea)
    kpis["Antal behandlingsrum"] = find_svedea_rooms(pages)

    # Försäkringsställe (bolagsspecifik, label/sektion först)
    if company == "Svedea":
        loc = find_location_svedea(pages)
        if loc.raw:
            kpis["Försäkringsställe"] = loc
        else:
            # fallback: toppblock allra sist
            kpis["Försäkringsställe"] = find_company_address_block(pages)
    else:
        loc = find_location_ptl(pages)
        if loc.raw:
            kpis["Försäkringsställe"] = loc
        else:
            kpis["Försäkringsställe"] = find_company_address_block(pages)

    # Sjukavbrott (finns)
    kpis["Sjukavbrott (finns)"] = find_sjukavbrott_exists(pages)

    return kpis


# -------------------- CLI compare (optional) --------------------

def fmt(k: KPI) -> str:
    if not k:
        return "—"
    return k.display()

def compare(pdf1, pdf2):
    k1 = extract_kpis(pdf1)
    k2 = extract_kpis(pdf2)

    print("| KPI | PDF 1 | PDF 2 | Källa PDF1 | Källa PDF2 |")
    print("|-----|-------|-------|------------|------------|")

    for key in sorted(set(k1.keys()) | set(k2.keys())):
        a, b = k1.get(key), k2.get(key)

        def src(k):
            return f"s.{k.evidence.page}: {k.evidence.text[:120]}" if k and k.evidence else "—"

        print(f"| {key} | {fmt(a)} | {fmt(b)} | {src(a)} | {src(b)} |")

if __name__ == "__main__":
    compare(
        "Försäkrngsbrev SÄKRA PTL.pdf",
        "Offert - yaxum version.pdf"
    )
