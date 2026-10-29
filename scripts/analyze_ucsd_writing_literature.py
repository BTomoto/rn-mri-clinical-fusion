"""Measure prose lengths and heading structure in public JATS full texts.

Full texts stay in an external cache; only metadata and derived counts are saved.
These are reproducible approximate English token counts, not publisher word counts.
"""
import argparse
import copy
import hashlib
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPERS = {
    "PMC9873493": {"key": "L1", "author": "McKenney et al.", "year": "2023 (online 2022)",
        "map": {"Introduction": "Introduction", "Methods and Materials": "Methods", "Results": "Results", "Discussion": "Discussion", "Conclusion": "Conclusion"}},
    "PMC10034916": {"key": "L2", "author": "Leone et al.", "year": "2023", "direct_intro": True,
        "map": {"Material and Methods": "Methods", "Results": "Results", "Discussion": "Discussion"}},
    "PMC7860032": {"key": "L3", "author": "Sun et al.", "year": "2021",
        "map": {"Background": "Introduction", "Methods": "Methods", "Radiomics Strategy": "Methods", "Results": "Results", "Discussion": "Discussion", "Conclusion": "Conclusion"}},
    "PMC10142504": {"key": "L4", "author": "de Godoy et al.", "year": "2023",
        "map": {"Background": "Introduction", "Materials and methods": "Methods", "Results": "Results", "Discussion": "Discussion"}},
}
DROP = {"fig", "table-wrap", "table-wrap-group", "supplementary-material", "ref-list", "fn-group", "disp-formula", "inline-formula", "xref"}


def plain(node):
    return " ".join("".join(node.itertext()).split()) if node is not None else ""


def clean(node):
    node = copy.deepcopy(node)
    for parent in list(node.iter()):
        for child in list(parent):
            if child.tag in DROP or child.get('sec-type') == 'kwd-group':
                tail = child.tail or ""
                index = list(parent).index(child)
                if index:
                    previous = list(parent)[index - 1]
                    previous.tail = (previous.tail or "") + " " + tail
                else:
                    parent.text = (parent.text or "") + " " + tail
                parent.remove(child)
    return node


def prose(node):
    node = clean(node)
    return [plain(p) for p in node.iter("p") if plain(p)]


def wc(paragraphs):
    text = " ".join(paragraphs).replace("\u2010", "-").replace("\u2011", "-").replace("\u2013", "-")
    return len(re.findall(r"[A-Za-z0-9]+(?:['’/-][A-Za-z0-9]+)*", text))


def main(cache):
    cache.mkdir(parents=True, exist_ok=True)
    records = []
    for pmcid, spec in PAPERS.items():
        url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"
        path = cache / f"{pmcid}.xml"
        if not path.exists():
            path.write_bytes(urllib.request.urlopen(url, timeout=45).read())
        data = path.read_bytes()
        root = ET.fromstring(data)
        meta = root.find("./front/article-meta")
        doi = next(n.text for n in meta.findall("article-id") if n.get("pub-id-type") == "doi")
        counts = {k: 0 for k in ["Introduction", "Methods", "Results", "Discussion", "Conclusion"]}
        paragraphs = dict.fromkeys(counts, 0)
        sections = []
        if spec.get("direct_intro"):
            ps = [plain(clean(p)) for p in root.findall("./body/p")]
            counts["Introduction"] = wc(ps)
            paragraphs["Introduction"] = len(ps)
        for sec in root.findall("./body/sec"):
            title = plain(sec.find("title"))
            if title not in spec["map"]:
                continue
            key = spec["map"][title]
            ps = prose(sec)
            counts[key] += wc(ps)
            paragraphs[key] += len(ps)
            sections.append({"heading": title, "group": key, "words": wc(ps),
                "subheadings": [plain(t) for t in sec.findall(".//sec/title")]})
        abstracts = [a for a in meta.findall("abstract") if a.get("abstract-type") not in ["graphical", "toc"]]
        abstract_words = sum(wc(prose(a)) for a in abstracts)
        records.append({"key": spec["key"], "pmcid": pmcid, "author": spec["author"], "year": spec["year"],
            "title": plain(meta.find("title-group/article-title")), "doi": doi,
            "journal": root.findtext("./front/journal-meta/journal-title-group/journal-title"),
            "url": f"https://doi.org/{doi}", "fulltext_url": url, "retrieved_date": "2026-10-29",
            "source_bytes": len(data), "source_sha256": hashlib.sha256(data).hexdigest(),
            "abstract_words": abstract_words, "section_words": counts, "section_paragraphs": paragraphs,
            "main_prose_words": sum(counts.values()), "abstract_plus_main_words": abstract_words + sum(counts.values()),
            "sections": sections})
    result = {"study_type": "focused narrative literature preparation; not a systematic review",
        "count_definition": "ASCII letters/numerals with internal apostrophe, slash or hyphen as a token; prose p nodes only; remove headings, numeric/cross-reference xrefs, captions, table cells, formulae, supplementary/back matter, references. Sun: Methods plus Radiomics Strategy. Leone: four unheaded body paragraphs are Introduction. Embedded conclusions remain in Discussion. Abstract labels/keywords excluded. No publisher word-count claim.",
        "papers": records}
    out = ROOT / "reports/ucsd_writing_preparation/literature_structure_counts.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps([{k: p[k] for k in ["key", "abstract_words", "section_words", "main_prose_words"]} for p in records], indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, required=True)
    main(parser.parse_args().cache)
