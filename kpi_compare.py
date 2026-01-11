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
    s = s.replace("\u00A0", " ").replace(" ", "").replace(",", ".")
    return float(s)

def read_pages(path: str) -> List[Tuple[int, str]]:
    with pdfplumber.open(path) as pdf:
        return [(i + 1, p.extract_text() or "") for i, p in enumerate(pdf.pages)]

def find_first(pages, patterns, unit=None):
    for page, text in pages:
        for rx in patterns:
            m = rx.search(text)
            if m:
                raw = m.group(1)
                try:
                    val = to_number(raw)
                except:
                    val = None
                return KPI(
                    value=val,
                    raw=raw,
                    unit=unit,
                    evidence=Evidence(page, m.group(0).strip())
                )
    return KPI(None, None, unit, None)

def find_first_text_line(pages, line_patterns: List[re.Pattern], fallback_address: bool = True) -> KPI:
    """
    För textvärden (t.ex. adress/försäkringsställe).
    1) Försöker först hitta rader som matchar 'Försäkringsställe(n) ...'
    2) Om fallback_address=True: försöker hitta en tydlig adressrad av typen 'Stad, Gatan 12'
    """
    for page, text in pages:
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        if not lines:
            continue

        # 1) Label-baserade träffar (PTL/Säkra brukar ha detta)
        for ln in lines:
            for rx in line_patterns:
                m = rx.search(ln)
                if m:
                    addr_1 = m.group(1).strip()

                    # Ta med postnr/stad om det råkar ligga på nästa rad i vissa PDFs
                    # (vi kan inte alltid få "nästa rad" här eftersom vi itererar per rad,
                    #  men ofta står allt på samma rad i era exempel)
                    return KPI(
                        value=None,
                        raw=addr_1,
                        unit=None,
                        evidence=Evidence(page, ln)
                    )

        # 2) Fallback: Svedea-offerten kan ibland ha adress utan label
        if fallback_address:
            addr_like = re.compile(
                r"^[A-ZÅÄÖ][A-Za-zÅÄÖåäö\- ]{2,30},\s*.+\b(gatan|vägen|gränd|torget|allén|allen|stigen|plan|g|v)\b.*$",
                re.IGNORECASE
            )
            for ln in lines:
                # filtrera bort uppenbara “inte adresser”
                if len(ln) > 80:
                    continue
                if addr_like.search(ln):
                    return KPI(
                        value=None,
                        raw=ln,
                        unit=None,
                        evidence=Evidence(page, ln)
                    )

    return KPI(None, None, None, None)

# -------------------- KPI extraction --------------------

def extract_kpis(pdf_path: str) -> Dict[str, KPI]:
    pages = read_pages(pdf_path)
    kpis: Dict[str, KPI] = {}

    kpis["Antal tandläkare"] = find_first(
        pages,
        [re.compile(r"Antal\s+Tandläkare\s+(\d+)", re.I)],
        "st"
    )

    kpis["Antal tandhygienister"] = find_first(
        pages,
        [re.compile(r"Antal\s+Tandhygienister\s+(\d+)", re.I)],
        "st"
    )

    kpis["Antal tandkirurgi/käkkirurger"] = find_first(
        pages,
        [
            re.compile(r"Antal\s+Käkkirurger\s+(\d+)", re.I),
            re.compile(r"Antal\s+Tandkirurger\s+(\d+)", re.I),
        ],
        "st"
    )

    kpis["Omsättning"] = find_first(
        pages,
        [
            re.compile(r"Årsomsättning\s+([\d\s]+)\s*kr", re.I),
            re.compile(r"Årsomsättning\s+i\s*KSEK.*?([\d\s]+)", re.I | re.S),
        ],
        "kr / KSEK"
    )

    # ✅ Avbrottstid: gör specifik, inte "första bästa X månader"
    kpis["Avbrottstid"] = find_first(
        pages,
        [
            # PTL/Säkra-varianten
            re.compile(r"Avbrottsförsäkring\s+(\d+)\s*månader", re.I),
            # Svedea-varianten (brukar stå "Ansvarstid 18 månader")
            re.compile(r"Ansvarstid\s+(\d+)\s*månader", re.I),
        ],
        "månader"
    )

    kpis["Protetik (år)"] = find_first(
        pages,
        [re.compile(r"Grund\s+(\d+)\s*år", re.I)],
        "år"
    )

    kpis["Premie / Pris"] = find_first(
        pages,
        [
            re.compile(r"Total\s+årspremie\s+([\d\s]+)\s*kr", re.I),
            re.compile(r"Årspremie\s+([\d\s]+)\s*kr", re.I),
        ],
        "kr"
    )

    # ✅ Ny: Försäkringsställe (PTL har label, Svedea kan ibland sakna label)
    kpis["Försäkringsställe"] = find_first_text_line(
        pages,
        line_patterns=[
            re.compile(r"Försäkringsställen?\s+(.+)$", re.I),
            re.compile(r"Försäkringsställe\s*[:\-]\s*(.+)$", re.I),
        ],
        fallback_address=True
    )

    return kpis

# -------------------- Comparison --------------------

def fmt(k: KPI) -> str:
    if k.value is None:
        return "—"
    if float(k.value).is_integer():
        return f"{int(k.value)} {k.unit}"
    return f"{k.value:.2f} {k.unit}"

def compare(pdf1, pdf2):
    k1 = extract_kpis(pdf1)
    k2 = extract_kpis(pdf2)

    print("| KPI | PDF 1 | PDF 2 | Skillnad | Källa PDF1 | Källa PDF2 |")
    print("|-----|-------|-------|----------|------------|------------|")

    for key in k1:
        a, b = k1[key], k2[key]
        diff = "—"
        if a.value is not None and b.value is not None:
            diff = b.value - a.value

        def src(k):
            return f"s.{k.evidence.page}: {k.evidence.text[:60]}" if k.evidence else "—"

        print(
            f"| {key} | {fmt(a)} | {fmt(b)} | {diff} | {src(a)} | {src(b)} |"
        )

if __name__ == "__main__":
    compare(
        "Försäkrngsbrev SÄKRA PTL.pdf",
        "Offert - yaxum version.pdf"
    )
