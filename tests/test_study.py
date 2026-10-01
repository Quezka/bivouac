import json
from datetime import date, timedelta

import pytest

from bivouac.application.errors import FileFormatError, InvalidInput, NotFound
from bivouac.application.inputs import BrandingInput, CardInput, PackInput
from bivouac.application.types import SCOPE_ALL, SCOPE_GLOSSARY, Grade


def test_import_json_pack_becomes_active(services, pack):
    assert pack.title == "Demo CTF" and pack.chapter_count == 2
    assert pack.card_count == 5 + 1 + 2  # concepts + self-check + glossary
    assert services.library.active().id == "demo-ctf"


def test_import_rejects_other_files(services, tmp_path):
    other = tmp_path / "notes.txt"
    other.write_text("hi")
    with pytest.raises(FileFormatError):
        services.library.import_file(str(other))
    bad = tmp_path / "bad.json"
    bad.write_text("{nope")
    with pytest.raises(FileFormatError):
        services.library.import_file(str(bad))


def test_reimport_keeps_own_cards_date_and_progress(services, pack, pack_file):
    services.library.add_card(pack.id, CardInput("What's a flag?", "A secret string", "1"))
    services.library.update(pack.id, PackInput("Demo CTF", "Finals", date(2026, 11, 5)))
    services.study.grade(pack.id, "k:1:xor", Grade.GOOD)
    again = services.library.import_file(str(pack_file))
    assert again.id == pack.id and again.custom_cards == 1
    assert again.event_date == date(2026, 11, 5)
    assert services.study.overview(pack.id).seen == 1


def test_pdf_import_keeps_a_copy_of_the_manual(services, tmp_path):
    pdf = tmp_path / "manual.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    record = services.library.import_file(str(pdf))
    assert record.has_source
    assert open(services.library.source_path(record.id), "rb").read() == b"%PDF-1.4 fake"


def test_queue_is_due_cards_then_limited_new_ones(services, pack, clock):
    services.study.set_new_per_day(3)
    first = services.study.queue(pack.id)
    assert len(first) == 3 and all(c.new for c in first)
    for c in first:
        services.study.grade(pack.id, c.id, Grade.GOOD)
    assert services.study.queue(pack.id) == []  # today's new cards are used up
    clock.day += timedelta(days=1)
    tomorrow = services.study.queue(pack.id)
    assert [c.id for c in tomorrow[:3]] == [c.id for c in first]  # due first
    assert len(tomorrow) == 6


def test_cram_returns_the_whole_scope(services, pack):
    assert len(services.study.queue(pack.id, SCOPE_GLOSSARY, cram=True)) == 2
    assert len(services.study.queue(pack.id, "ch:1", cram=True)) == 4
    with pytest.raises(NotFound):
        services.study.queue(pack.id, "ch:9")


def test_overview_counts_streak_and_countdown(services, pack, clock):
    services.library.update(pack.id, PackInput("Demo CTF", "Finals", clock.day + timedelta(days=12)))
    services.study.grade(pack.id, "g:ctf", Grade.GOOD)
    clock.day += timedelta(days=1)
    services.study.grade(pack.id, "g:ctf", Grade.GOOD)
    o = services.study.overview(pack.id)
    assert o.days_left == 11
    assert o.streak == 2 and o.reviewed_today == 1 and o.seen == 1
    assert o.history[-1] == (clock.day, 1)
    assert len(o.chapters) == 2


def test_multiple_choice_wrong_answer_resets_the_card(services, pack):
    q = services.study.choice(pack.id, "ch:1")
    assert q.options[q.answer] in {"XOR", "Base64", "ROT13"}
    services.study.answer_choice(pack.id, q.card_id, False)
    card = next(c for c in services.study.queue(pack.id, "ch:1", cram=True) if c.id == q.card_id)
    assert card.interval == 0 and not card.new
    before = services.study.overview(pack.id).seen
    q2 = services.study.choice(pack.id)
    services.study.answer_choice(pack.id, q2.card_id, True)
    assert services.study.overview(pack.id).seen == before  # recognising isn't learning


def test_chapters_read_flag(services, pack):
    services.study.set_read(pack.id, "1", True)
    chapters = services.study.chapters(pack.id)
    assert [c.read for c in chapters] == [True, False]
    assert chapters[0].concepts[1].example == "aGk="
    assert services.study.overview(pack.id).chapters_read == 1


def test_reference_search(services, pack):
    assert [t.term for t in services.study.glossary(pack.id, "secret")] == ["Flag"]
    assert len(services.study.cheatsheet(pack.id, "nmap")) == 1
    assert services.study.cheatsheet(pack.id, "hashcat") == []


def test_own_pack_and_cards(services):
    with pytest.raises(InvalidInput):
        services.library.create(PackInput("  "))
    mine = services.library.create(PackInput("OliCyber 2027", "OliCyber", date(2027, 3, 1)))
    assert services.library.active().id == mine.id == "olicyber-2027"
    services.library.add_card(mine.id, CardInput("nc -lvnp 4444?", "Listen for a shell"))
    assert services.study.queue(mine.id)[0].front == "nc -lvnp 4444?"
    card_id = services.study.queue(mine.id)[0].id
    assert services.library.delete_card(mine.id, card_id).card_count == 0
    with pytest.raises(InvalidInput):
        services.library.add_card(mine.id, CardInput("front only", ""))


def test_export_and_delete(services, pack, tmp_path):
    out = tmp_path / "out.json"
    services.library.export(pack.id, str(out))
    assert json.loads(out.read_text())["title"] == "Demo CTF"
    services.study.grade(pack.id, "g:ctf", Grade.GOOD)
    services.library.delete(pack.id)
    assert services.library.packs() == [] and services.library.active() is None
    again = services.library.import_file(str(out))
    assert services.study.overview(again.id).seen == 0  # progress went with the pack


def test_branding_defaults_to_the_school(services):
    brand = services.library.branding()
    assert brand.school == 'I.T.S. "E. Alessandrini"' and brand.logo is None
    services.library.set_branding(BrandingInput("Liceo X", "Pescara", "/tmp/x.png"))
    assert services.library.branding().place == "Pescara"
    services.library.set_branding(BrandingInput("", "", None))
    assert services.library.branding().school == 'I.T.S. "E. Alessandrini"'


def test_scopes(services, pack):
    keys = [s.key for s in services.study.scopes(pack.id)]
    assert keys == [SCOPE_ALL, SCOPE_GLOSSARY, "ch:1", "ch:2"]


def test_digest_lists_every_chapter(services, pack):
    digest = services.study.digest(pack.id)
    assert [c.id for c in digest.chapters] == ["1", "2"]
    assert digest.total_chapters == 2 and digest.total_concepts == 5
    assert digest.chapters[0].takeaways == ("XOR is its own inverse.",)


def test_digest_search_keeps_matching_bits(services, pack):
    only_xss = services.study.digest(pack.id, "script injected").chapters
    assert [(c.id, [k.term for k in c.concepts]) for c in only_xss] == [("2", ["XSS"])]
    by_takeaway = services.study.digest(pack.id, "inverse").chapters
    assert [c.id for c in by_takeaway] == ["1"] and by_takeaway[0].concepts == ()
    whole = services.study.digest(pack.id, "crypto").chapters
    assert len(whole[0].concepts) == 3  # the title matches: the chapter stays whole
    assert services.study.digest(pack.id, "nothing like this").chapters == ()


def test_digest_shows_what_is_read(services, pack):
    services.study.set_read(pack.id, "2", True)
    assert [c.read for c in services.study.digest(pack.id).chapters] == [False, True]
