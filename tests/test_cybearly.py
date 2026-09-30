from bivouac.infrastructure.cybearly import clean_lines, parse_manual

from .fakes import MANUAL


def test_page_furniture_and_watermarks_are_dropped_but_columns_kept():
    lines, pages = clean_lines(MANUAL)
    text = "\n".join(lines)
    for junk in ("CYBEARLY|", "YLRAEBYC", "S.r.l.", "Partita IVA", "bearit"):
        assert junk not in text
    kept = next(l for l in lines if "Altro testo." in l)
    assert kept.index("Altro testo.") == len("onavlisetnoM|3333-2222-1111|YLRAEBYC   ")
    assert len(lines) == len(pages) and pages[-1] == 4


def test_chapters_with_recap_concepts_quiz_and_pages():
    pack = parse_manual(MANUAL, "demo")
    assert [c["id"] for c in pack["chapters"]] == ["0.1", "R1"]
    first, red = pack["chapters"]
    assert first["title"] == "Primo capitolo di prova"
    assert first["part"] == "Fondamenta" and red["part"] == "Red Track"
    assert first["page"] == 1 and red["page"] == 3
    assert first["summary"] == ["Il primo punto, che va a capo su due righe.", "Il secondo punto."]
    assert first["concept_headers"] == ["Termine", "Significato"]
    assert first["concepts"] == [
        {"term": "CIA triad", "meaning": "Riservatezza, integrità, disponibilità"},
        {"term": "SOC", "meaning": "Centro operativo"}]  # shifted a character left
    assert first["resources"] == ["esempio.org"]
    assert first["quiz"] == [{"question": "Una domanda su due righe?",
                              "answer": "La risposta."}]
    assert first["sections"][0] == {"title": "0.1.1 La prima sezione", "page": 1}
    assert first["sections"][-1] == {"title": "Recap", "page": 2}
    assert red["summary"] == ["Recon prima di tutto."]
    assert red["quiz"][0]["answer"] == "Rileva le versioni."


def test_glossary_and_cheatsheet():
    pack = parse_manual(MANUAL, "demo")
    assert pack["glossary"] == [
        {"term": "AD (Active Directory)", "definition": "Gestione identità. Molto usato."},
        {"term": "ATT&CK", "definition": "Vedi MITRE ATT&CK."}]
    assert pack["cheatsheet"] == [{"section": "Recon (Cap R1)", "title": "Port scanning",
                                   "lines": ["nmap -sV target", "nmap -p- target"]}]
