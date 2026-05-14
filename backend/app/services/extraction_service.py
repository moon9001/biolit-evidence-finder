"""Rule-based extraction of scientific names, Chinese names, keywords, etc."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List, Tuple


# ---------------------------------------------------------------------------
# Regexes
# ---------------------------------------------------------------------------

# Genus species, with optional infraspecific epithets.
# We keep this conservative to avoid matching ordinary capitalised English.
_SCI_NAME_RE = re.compile(
    r"\b([A-Z][a-z]{2,})\s+([a-z]{3,}(?:-[a-z]{2,})?)"
    r"(?:\s+(?:var\.|subsp\.|ssp\.|f\.|fo\.|cv\.)\s+([a-zA-Z][a-zA-Z\-]+))?"
)

# Abbreviated genus, e.g. "R. chinensis"
_SCI_NAME_ABBREV_RE = re.compile(r"\b([A-Z])\.\s+([a-z]{3,}(?:-[a-z]{2,})?)\b")

# Avoid common false positives.
_SCI_NAME_BLOCKLIST = {
    "The", "This", "That", "These", "Those", "Their", "There", "Then",
    "When", "Where", "While", "With", "Would", "Could", "Should", "About",
    "After", "Before", "Below", "Above", "Under", "Between", "Through",
    "During", "Among", "Across", "Against", "Around", "Because", "Behind",
    "Beside", "Beyond", "Despite", "Except", "Inside", "Outside", "Through",
    "Toward", "Within", "Without", "Although", "However", "Therefore",
    "Meanwhile", "Moreover", "Furthermore", "Nevertheless", "Otherwise",
    "Similarly", "Specifically", "Subsequently", "Eventually", "Finally",
    "Generally", "Particularly", "Recently", "Additionally", "Initially",
    "Figure", "Table", "Plate", "Plates", "Figures", "Tables", "Page",
    "Pages", "Map", "Maps", "Volume", "Volumes", "Chapter", "Chapters",
    "Section", "Sections", "Appendix", "Reference", "References", "Index",
    "Abstract", "Introduction", "Conclusion", "Discussion", "Materials",
    "Methods", "Results", "Acknowledgement", "Acknowledgements",
    "Family", "Subfamily", "Genus", "Genera", "Species", "Subspecies",
    "Variety", "Varieties", "Form", "Forms", "Cultivar", "Cultivars",
    "Type", "Types", "Holotype", "Lectotype", "Neotype", "Syntype",
    "China", "Yunnan", "Sichuan", "Tibet", "Xinjiang", "Guizhou", "Qinghai",
    "Beijing", "Shanghai", "Guangdong", "Guangxi", "Hubei", "Hunan",
    "January", "February", "March", "April", "June", "July", "August",
    "September", "October", "November", "December",
    # English words that often appear as title-case + lowercase noun pairs
    "Voucher", "Specimen", "Locality", "Collection", "Collected", "Notes",
    "Material", "Examined", "Habitat", "Distribution", "Description",
    "Diagnosis", "Etymology", "Remarks", "Type", "Phenology", "Treatment",
    "Author", "Authors", "Editor", "Editors", "Volume", "Issue", "Number",
    "Note", "Key", "Keys", "Group", "Groups", "Class", "Order", "Phylum",
    "Kingdom", "Division", "Series", "Tribe", "Tribes", "Section",
    "Subsection", "Subgenus", "Sect", "Subg", "Plate", "Plates",
}

# When the species epithet matches one of these common English words, the
# pair is almost certainly NOT a Latin binomial.
_SPECIES_BLOCKLIST = {
    "specimen", "specimens", "examined", "studied", "collected", "selected",
    "section", "sections", "chapter", "chapters", "figure", "figures",
    "table", "tables", "page", "pages", "volume", "volumes", "number",
    "numbers", "series", "issue", "issues", "edition", "editions",
    "appendix", "abstract", "introduction", "discussion", "conclusion",
    "reference", "references", "acknowledgement", "acknowledgements",
    "method", "methods", "result", "results", "habitat", "distribution",
    "diagnosis", "etymology", "treatment", "key", "keys", "group", "groups",
    "country", "countries", "province", "provinces", "region", "regions",
    "family", "families", "genus", "genera", "species", "subspecies",
    "variety", "varieties", "form", "forms", "cultivar", "cultivars",
    "habitat", "type", "types", "holotype", "lectotype", "neotype",
    "syntype", "remarks", "notes",
}

# Chinese plant / taxonomy related keywords.
_CN_TAXONOMY_TERMS = [
    "属", "科", "亚科", "族", "亚族", "属", "种", "亚种", "变种", "变型",
    "品种", "栽培品种", "模式标本", "等模式", "全模式", "副模式",
    "图版", "图说", "形态", "分布", "生境", "海拔", "花期", "果期",
    "标本", "凭证标本", "凭证", "采集", "采集人", "采集地", "采集号",
    "中国", "云南", "四川", "西藏", "新疆", "贵州", "青海", "甘肃",
    "广东", "广西", "湖北", "湖南", "浙江", "江苏", "福建", "台湾",
]

# Chinese plant common names suffixes.
_CN_PLANT_SUFFIX_RE = re.compile(
    r"[\u4e00-\u9fa5]{1,8}(?:草|花|藤|树|木|蒲|蕨|莲|兰|苔|藓|菌|参|桂|"
    r"竹|柏|杉|松|枫|柳|桦|栎|槭|椴|椿|杨|榆|桑|榕|槟|椰|蓼|藻|"
    r"梅|荷|菊|莓|薇|芋|薯|葱|蒜|韭|麦|稻|粟|黍)"
)


@dataclass
class Extracted:
    term: str
    term_type: str
    start: int
    end: int
    context: str
    confidence: float = 1.0


def _context_window(text: str, start: int, end: int, radius: int = 80) -> str:
    s = max(0, start - radius)
    e = min(len(text), end + radius)
    snippet = text[s:e].replace("\n", " ").strip()
    return re.sub(r"\s+", " ", snippet)


def extract_scientific_names(text: str) -> List[Extracted]:
    out: List[Extracted] = []
    seen_spans: set[Tuple[int, int]] = set()

    for m in _SCI_NAME_RE.finditer(text):
        genus, species, infra = m.group(1), m.group(2), m.group(3)
        if genus in _SCI_NAME_BLOCKLIST:
            continue
        # Filter out lowercase epithet that is actually English connector.
        if species in {"and", "the", "for", "with", "from"}:
            continue
        if species.lower() in _SPECIES_BLOCKLIST:
            continue
        term = f"{genus} {species}"
        if infra:
            # Reconstruct full term with the infraspecific marker.
            mid = text[m.start():m.end()]
            term = re.sub(r"\s+", " ", mid).strip()
        span = (m.start(), m.end())
        if span in seen_spans:
            continue
        seen_spans.add(span)
        out.append(
            Extracted(
                term=term,
                term_type="scientific_name",
                start=m.start(),
                end=m.end(),
                context=_context_window(text, m.start(), m.end()),
                confidence=0.85,
            )
        )

    for m in _SCI_NAME_ABBREV_RE.finditer(text):
        term = f"{m.group(1)}. {m.group(2)}"
        span = (m.start(), m.end())
        # Skip if already covered by full name
        if any(s <= m.start() and m.end() <= e for s, e in seen_spans):
            continue
        out.append(
            Extracted(
                term=term,
                term_type="scientific_name_abbrev",
                start=m.start(),
                end=m.end(),
                context=_context_window(text, m.start(), m.end()),
                confidence=0.55,
            )
        )

    return out


def extract_chinese_terms(text: str) -> List[Extracted]:
    out: List[Extracted] = []

    # taxonomy / locations
    for term in _CN_TAXONOMY_TERMS:
        for m in re.finditer(re.escape(term), text):
            out.append(
                Extracted(
                    term=term,
                    term_type="taxonomy_term"
                    if term not in {"中国", "云南", "四川", "西藏", "新疆", "贵州", "青海",
                                    "甘肃", "广东", "广西", "湖北", "湖南", "浙江", "江苏",
                                    "福建", "台湾"}
                    else "location",
                    start=m.start(),
                    end=m.end(),
                    context=_context_window(text, m.start(), m.end()),
                    confidence=0.7,
                )
            )

    # Chinese plant common names by suffix
    for m in _CN_PLANT_SUFFIX_RE.finditer(text):
        out.append(
            Extracted(
                term=m.group(0),
                term_type="chinese_name",
                start=m.start(),
                end=m.end(),
                context=_context_window(text, m.start(), m.end()),
                confidence=0.5,
            )
        )

    return out


def dedupe(extracted: Iterable[Extracted]) -> List[Extracted]:
    """Deduplicate by (term, term_type, start)."""
    seen: set[tuple] = set()
    out: List[Extracted] = []
    for e in extracted:
        key = (e.term, e.term_type, e.start)
        if key in seen:
            continue
        seen.add(key)
        out.append(e)
    return out


def extract_all(text: str) -> List[Extracted]:
    items = list(extract_scientific_names(text)) + list(extract_chinese_terms(text))
    return dedupe(items)
