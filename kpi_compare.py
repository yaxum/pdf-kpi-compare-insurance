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
    value: Optional[float]
    raw: Optional[str]
    unit: Optional[str]
    evidence: Optional[Evidence]


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
    line = line.strip()
    # första "nummerblock" som kan innehålla mellanrum
    m = re.match(r"(\d[\d\s]*\d|\d)", line)
    return m.group(1).strip() if m else None

def find_first(pages, patterns, unit=None) -> KPI:
    for page, text in pages:
        for rx in patterns:
            m = rx.search(text)
            if m:
                raw = m.group(1).strip()
                try:
                    val = to_number(raw)
                except Exception:
                    val = None
                return KPI(
                    value=val,
                    raw=raw,
                    unit=unit,
                    evidence=Evidence(page, m.group(0).strip())
                )
    return KPI(None, None, unit, None)

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
                    evidence=Evidence(page, m.group(0).strip())
                )
    return KPI(None, None, None, None)

def find_company_address_block(pages: List[Tuple[int, str]]) -> KPI:
    """
    Försök plocka toppadressblock (bolag + gata + postnr/ort).
    Fungerar på era format:
    - Svedea: sida 1 överst: Bolag, Gata, Postnr Ort
    - PTL: ofta efter "Kundnr:" följt av bolag/adress eller i ett tidigt block.
    """
    # Vi tittar främst i första ~3 sidorna (snabbt och brukar räcka)
    for page, text in pages[:3]:
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        if len(lines) < 3:
            continue

        # 1) Direkt toppblock: leta tre på varandra följande rader där tredje har postnr
        # ex "602 32 Norrköping" eller "952 34 Kalix"
        for i in range(min(20, len(lines) - 2)):
            if re.search(r"\b\d{3}\s?\d{2}\b", lines[i + 2]):
                # Styr upp så att mittenraden ser ut som "gata 12" typ, men vi håller det lätt
                block = "\n".join([lines[i], lines[i + 1], lines[i + 2]])
                return KPI(None, block, None, Evidence(page, block))

        # 2) PTL-variant: block efter "Kundnr:"
        for i in range(len(lines) - 3):
            if lines[i].lower().startswith("kundnr"):
                block = "\n".join([lines[i + 1], lines[i + 2], lines[i + 3]])
                if re.search(r"\b\d{3}\s?\d{2}\b", lines[i + 3]):
                    return KPI(None, block, None, Evidence(page, block))

    return KPI(None, None, None, None)

def find_svedea_rooms(pages: List[Tuple[int, str]]) -> KPI:
    """
    Svedea: "Beh.rum 1-4/kök" (textvärde)
    """
    return find_first_line(
        pages,
        [
            re.compile(r"\bBeh\.rum\s+([^\n\r]+)", re.I),
        ]
    )

def find_svedea_ksek_turnover(pages: List[Tuple[int, str]]) -> KPI:
    """
    Svedea: "Årsomsättning i KSEK" och nästa rad innehåller flera tal.
    Vi tar första tal-token.
    """
    for page, text in pages:
        m = re.search(r"Årsomsättning\s+i\s*KSEK.*?\n\s*([0-9\s]+)", text, re.I)
        if m:
            raw_line = m.group(1).strip()
            first = first_number_token(raw_line)
            if first:
                try:
                    val = to_number(first)
                except Exception:
                    val = None
                return KPI(
                    value=val,
                    raw=first,
                    unit="KSEK",
                    evidence=Evidence(page, f"Årsomsättning i KSEK\n{raw_line}")
                )
    return KPI(None, None, "KSEK", None)


# -------------------- KPI extraction --------------------

def extract_kpis(pdf_path: str) -> Dict[str, KPI]:
    pages = read_pages(pdf_path)
    kpis: Dict[str, KPI] = {}

    # Antal tandläkare (PTL + Svedea)
    kpis["Antal tandläkare"] = find_first(
        pages,
        [
            re.compile(r"Antal\s+Tandläkare\s+(\d+)", re.I),  # PTL
            re.compile(r"Tandläkare\s*-\s*övrigt\s*([\d\s]+,\d+|\d+)\s*st", re.I),  # Svedea
        ],
        "st"
    )

    # Antal tandhygienister (PTL)
    kpis["Antal tandhygienister"] = find_first(
        pages,
        [
            re.compile(r"Antal\s+Tandhygienister\s+(\d+)", re.I),
        ],
        "st"
    )

    # Antal tandkirurgi/käkkirurger (PTL, ev Svedea om ni får in det senare)
    kpis["Antal tandkirurgi/käkkirurger"] = find_first(
        pages,
        [
            re.compile(r"Antal\s+Käkkirurger\s+(\d+)", re.I),
            re.compile(r"Antal\s+Tandkirurger\s+(\d+)", re.I),
            re.compile(r"Käkkirurger\s*-\s*övrigt\s*([\d\s]+,\d+|\d+)\s*st", re.I),
            re.compile(r"Tandkirurger\s*-\s*övrigt\s*([\d\s]+,\d+|\d+)\s*st", re.I),
        ],
        "st"
    )

    # Omsättning
    # PTL: "Årsomsättning 8 232 000 kr"
    oms_ptl = find_first(
        pages,
        [
            re.compile(r"Årsomsättning\s+([\d\s]+)\s*kr", re.I),
        ],
        "kr"
    )
    if oms_ptl.raw:
        kpis["Omsättning"] = oms_ptl
    else:
        kpis["Omsättning"] = find_svedea_ksek_turnover(pages)

    # Avbrottstid
    kpis["Avbrottstid"] = find_first(
        pages,
        [
            re.compile(r"Avbrottsförsäkring\s+(\d+)\s*månader", re.I),  # PTL
            re.compile(r"Ansvarstid\s+(\d+)\s*månader", re.I),          # Svedea
        ],
        "månader"
    )

    # Protetik (år) - PTL "Grund 3 år"
    kpis["Protetik (år)"] = find_first(
        pages,
        [
            re.compile(r"Grund\s+(\d+)\s*år", re.I),
        ],
        "år"
    )

    # Premie / Pris
    kpis["Premie / Pris"] = find_first(
        pages,
        [
            re.compile(r"Total\s+årspremie\s+([\d\s]+)\s*kr", re.I),  # PTL
            re.compile(r"Årspremie\s+([\d\s]+)\s*kr", re.I),          # Svedea
        ],
        "kr"
    )

    # Antal behandlingsrum (rooms) - Svedea
    kpis["Antal behandlingsrum"] = find_svedea_rooms(pages)

    # Försäkringsställe / Adress (robust)
    # Prioritet: toppblock > labelrad
    addr_block = find_company_address_block(pages)

    # PTL har ofta: "Försäkringsställen Hantverkargatan 1 a, 95234"
    addr_label = find_first_line(
        pages,
        [
            re.compile(r"Försäkringsställen?\s+(.+)$", re.I | re.M),
            re.compile(r"Försäkringsställe\s*[:\-]\s*(.+)$", re.I | re.M),
        ]
    )

    if addr_block.raw:
        kpis["Försäkringsställe"] = addr_block
    else:
        kpis["Försäkringsställe"] = addr_label

    return kpis


# -------------------- CLI compare (optional) --------------------

def fmt(k: KPI) -> str:
    if k.value is None:
        return k.raw if k.raw else "—"
    if float(k.value).is_integer():
        return f"{int(k.value)} {k.unit}".strip()
    return f"{k.value:.2f} {k.unit}".strip()

def compare(pdf1, pdf2):
    k1 = extract_kpis(pdf1)
    k2 = extract_kpis(pdf2)

    print("| KPI | PDF 1 | PDF 2 | Källa PDF1 | Källa PDF2 |")
    print("|-----|-------|-------|------------|------------|")

    for key in sorted(set(k1.keys()) | set(k2.keys())):
        a, b = k1.get(key), k2.get(key)

        def src(k):
            return f"s.{k.evidence.page}: {k.evidence.text[:80]}" if k and k.evidence else "—"

        print(
            f"| {key} | {fmt(a) if a else '—'} | {fmt(b) if b else '—'} | {src(a)} | {src(b)} |"
        )

if __name__ == "__main__":
    compare(
        "Försäkrngsbrev SÄKRA PTL.pdf",
        "Offert - yaxum version.pdf"
    )
