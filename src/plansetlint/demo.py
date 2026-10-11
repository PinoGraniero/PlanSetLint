"""Create synthetic, blank PDF files for an offline first-use check."""
from pathlib import Path
from pypdf import PdfWriter


def create_demo(destination):
    root = Path(destination)
    root.mkdir(parents=True, exist_ok=False)
    for subdir in ("corretto", "da_verificare"):
        folder = root / subdir
        folder.mkdir()
        data = [("A-001_Pianta_R01.pdf", (297, 420)), ("A-002_Prospetto_R02.pdf", (420, 900))]
        if subdir == "da_verificare":
            data = [("A-001_Pianta_R01.pdf", (297, 420)), ("A-001_Pianta-copia_R01.pdf", (297, 420)),
                    ("A-002_Prospetto_R01.pdf", (210, 297)), ("A-004_Sezione_R01.pdf", (297, 420))]
        for name, size in data:
            writer = PdfWriter()
            writer.add_blank_page(width=size[0] * 72 / 25.4, height=size[1] * 72 / 25.4)
            writer.add_metadata({"/Title": "PlanSetLint — PDF dimostrativo vuoto"})
            with (folder / name).open("wb") as stream:
                writer.write(stream)
        csv = "drawing,revision,paper\nA-001,01,A3\nA-002,02,420x900\n"
        if subdir == "da_verificare":
            csv += "A-003,01,A3\n"
        (folder / "elenco.csv").write_text(csv, encoding="utf-8")
    return root
