import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from pypdf import PdfWriter
from plansetlint.cli import main, validate


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def pdf(self, name="A-001_Plan_R01.pdf", size=(297, 420), pages=1, password=None):
        writer = PdfWriter()
        for _ in range(pages):
            writer.add_blank_page(width=size[0] * 72 / 25.4, height=size[1] * 72 / 25.4)
        if password:
            writer.encrypt(password)
        with (self.root / name).open("wb") as stream:
            writer.write(stream)

    def manifest(self, text="drawing,revision,paper\nA-001,01,A3\n"):
        path = self.root / "inventory.csv"
        path.write_text(text, encoding="utf-8")
        return path

    def codes(self, manifest=None):
        return {issue["code"] for issue in validate(self.root, manifest)}

    def test_valid_landscape_and_numeric_revision(self):
        self.pdf("A-001_Pianta_R1.pdf", size=(420, 297))
        self.assertEqual(validate(self.root, self.manifest()), [])

    def test_duplicates_missing_unexpected_and_revision(self):
        self.pdf()
        self.pdf("A-001_Plan_R02.pdf")
        self.pdf("A-003_Plan_R01.pdf")
        manifest = self.manifest("drawing,revision,paper\nA-001,03,A3\nA-002,01,A3\n")
        self.assertEqual(self.codes(manifest), {"DUPLICATE_DRAWING", "REVISION_MISMATCH", "MISSING_DRAWING", "UNEXPECTED_DRAWING"})

    def test_invalid_pdf_and_name(self):
        (self.root / "invalid.pdf").write_bytes(b"not a PDF")
        self.assertEqual(self.codes(), {"INVALID_NAME", "UNREADABLE_PDF"})

    def test_page_count_and_paper(self):
        self.pdf(size=(210, 297), pages=2)
        self.assertEqual(self.codes(self.manifest()), {"PAGE_COUNT", "PAPER_MISMATCH"})

    def test_encrypted(self):
        self.pdf(password="test")
        self.assertEqual(self.codes(), {"ENCRYPTED_PDF"})

    def test_bad_manifest(self):
        self.pdf()
        self.assertEqual(self.codes(self.manifest("drawing,revision,paper\nA-001,x,A9\n")), {"MANIFEST_ERROR"})

    def test_missing_folder_and_empty_folder(self):
        self.assertEqual(self.codes(), {"NO_PDFS"})
        self.assertEqual(validate(self.root / "missing")[0]["code"], "INPUT_ERROR")

    def test_json_and_exit_status(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = main([str(self.root), "--json"])
        self.assertEqual(status, 1)
        self.assertFalse(json.loads(output.getvalue())["ok"])
        self.pdf()
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main([str(self.root)]), 0)


if __name__ == "__main__":
    unittest.main()
