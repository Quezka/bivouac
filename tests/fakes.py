"""Made-up study material for the tests (never real competition content)."""
from __future__ import annotations

from bivouac.application.errors import FileFormatError
from bivouac.infrastructure.packs import pack_from_dict


def sample_pack_dict() -> dict:
    return {
        "format": 1, "id": "demo-ctf", "title": "Demo CTF", "event": "Demo CTF finals",
        "chapters": [
            {"id": "1", "title": "Crypto", "part": "Warm-up", "page": 2,
             "summary": ["XOR is its own inverse."],
             "concept_headers": ["Term", "Meaning"],
             "concepts": [{"term": "XOR", "meaning": "Bitwise exclusive or"},
                          {"term": "Base64", "meaning": "Binary-to-text encoding", "example": "aGk="},
                          {"term": "ROT13", "meaning": "Caesar shift by 13"}],
             "quiz": [{"question": "Is Base64 encryption?", "answer": "No, it's an encoding."}],
             "sections": [{"title": "1.1 Encodings", "page": 3}]},
            {"id": "2", "title": "Web", "part": "Red",
             "concepts": [{"term": "XSS", "meaning": "Script injected into a page"},
                          {"term": "SQLi", "meaning": "Query injection"}]},
        ],
        "glossary": [{"term": "CTF", "definition": "Capture the flag"},
                     {"term": "Flag", "definition": "The secret string you submit"}],
        "cheatsheet": [{"section": "Recon", "title": "Nmap", "lines": ["nmap -sV target"]}],
    }


class FakeManuals:
    def __init__(self):
        self.data = sample_pack_dict()

    def read(self, pdf_path: str):
        if "broken" in pdf_path:
            raise FileFormatError("no chapters")
        return pack_from_dict(self.data)


# A few pages of a Cybearly-style manual, as `pdftotext -layout` prints them.
MANUAL = """\
                                 Indice
                                 PARTE 0: FONDAMENTA ........................................ 3
                                 Capitolo 0.1: Primo capitolo di prova ........................ 4
                                 Capitolo R1: Recon di prova .................................. 6
                                 Appendice A: Cheatsheet consolidato .......................... 8
\f                                 PARTE 0: FONDAMENTA
                                 Capitolo 0.1: Primo capitolo di prova
                                 Capitolo di prova. Leggibile in 5 minuti.

                                 0.1.1: La prima sezione
                                 Testo della sezione.
CYBEARLY|1111-2222-3333|Scuola di Prova
onavlisetnoM|3333-2222-1111|YLRAEBYC   Altro testo.
                                                                    S.r.l.
                                 Partita IVA 00000000000                                  www.bearit.com
\f                                 Recap del Capitolo 0.1
                                 Cosa hai imparato
                                 •                            Il primo punto, che va a
                                                              capo su due righe.
                                 •                            Il secondo punto.
                                 Concetti chiave in tabella

                                            Termine                     Significato

                                            CIA triad                   Riservatezza, integrità,
                                                                        disponibilità

                                            SOC                        Centro operativo
                                 Risorse per approfondire
                                 •                            esempio.org
                                 Mini-quiz di autovalutazione
                                 1. Una domanda
                                 su due righe?
                                 Risposta. La risposta.
                                 Capitolo completato. Prossimo: Cap R1.
\f                                 PARTE 4: RED TRACK
                                 Capitolo R1: Recon di prova
                                 Capitolo Red Track.

                                 R1.1: Nmap
                                 Testo.
                                 Recap del Capitolo R1
                                 Cosa è stato imparato
                                 •                            Recon prima di tutto.
                                 Mini-quiz di autovalutazione
                                 1. Cosa fa -sV?
                                 Risposta. Rileva le versioni.
                                 Capitolo completato.
\f                                 PARTE 5: APPENDICI
                                 Appendice A: Cheatsheet consolidato
                                 A.1: Recon (Cap R1)
                                 Port scanning

                                                     nmap -sV target
                                                     nmap -p- target
                                 Appendice B: Glossario
                                 A
                                 •                            AD (Active Directory). Gestione identità. Molto usato.
                                 •                            ATT&CK. Vedi MITRE ATT&CK.
                                 Appendice C: Bibliografia
"""


class FakeReleases:
    """A release feed that never touches the network."""

    def __init__(self, release=None):
        self.release = release
        self.downloads = []

    def latest(self):
        return self.release

    def download(self, asset, progress):
        progress(asset.size // 2, asset.size)
        progress(asset.size, asset.size)
        self.downloads.append(asset.name)
        return f"/tmp/{asset.name}"


class FakeInstaller:
    def __init__(self, supported=True, takes_over=False):
        self._supported = supported
        self.takes_over = takes_over
        self.installed = []

    def supported(self):
        return self._supported

    def pick(self, assets):
        return next((a for a in assets if a.name.endswith(".deb")), None)

    def install(self, path):
        self.installed.append(path)
        return self.takes_over
