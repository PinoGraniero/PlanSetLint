import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from pypdf import PdfWriter
from pypdf.generic import FloatObject, NameObject

from plansetlint.cli import main
from plansetlint.core import Settings, check_package, compile_template, load_settings, paper_size, save_settings
from plansetlint.demo import create_demo
from plansetlint.reports import export_report, html_report


class ExtendedTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def pdf(self, name="A-001_Pianta_R01.pdf", size=(297, 420), pages=1, unit=1):
        writer = PdfWriter()
        for _ in range(pages):
            page = writer.add_blank_page(width=size[0] * 72 / 25.4 / unit, height=size[1] * 72 / 25.4 / unit)
            page[NameObject("/UserUnit")] = FloatObject(unit)
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as stream:
            writer.write(stream)
        return path

    def csv(self, content):
        path = self.root / "elenco.csv"
        path.write_text(content, encoding="utf-8-sig")
        return path

    def test_custom_template_letters_and_semicolon_csv(self):
        self.pdf("Tavola_01_Pianta_RevB.pdf", size=(900, 420))
        settings = Settings(naming_template="Tavola_{drawing}_{title}_Rev{revision}.pdf")
        manifest = self.csv("drawing;revision;paper\n01;b;420x900\n")
        report = check_package(self.root, manifest, settings)
        self.assertTrue(report["ok"], report["issues"])
        self.assertEqual(report["files"][0]["sizes_mm"], [[420.0, 900.0]])

    def test_short_csv_empty_and_duplicate_rows_are_reported(self):
        self.pdf()
        cases = ["", "drawing,revision,paper\n", "drawing,revision,paper\nA-001,01\n",
                 "drawing,revision,paper\nA-001,01,A3,extra\n", "drawing,revision,paper\nA-001,01,A3\nA-001,02,A3\n"]
        for text in cases:
            with self.subTest(text=text):
                report = check_package(self.root, self.csv(text))
                self.assertEqual(report["issues"][0]["code"], "MANIFEST_ERROR")

    def test_empty_paper_skips_size_check(self):
        self.pdf(size=(100, 600))
        self.assertTrue(check_package(self.root, self.csv("drawing,revision,paper\nA-001,01,\n"))["ok"])

    def test_invalid_templates(self):
        for template in ("{drawing}{title}_{revision}.pdf", "{drawing}_{drawing}_{revision}.pdf", "{drawing}_R{revision}.pdf", "../{drawing}_{title}_{revision}.pdf", "{drawing!r}_{title}_{revision}.pdf", "{drawing}_{title}_{revision}.txt", "{bad}_{title}_{revision}.pdf"):
            with self.subTest(template=template), self.assertRaises(ValueError):
                compile_template(template)

    def test_invalid_settings_and_profile_round_trip(self):
        for settings in (Settings(tolerance_mm=float("nan")), Settings(tolerance_mm=-1), Settings(single_page="yes")):
            self.assertEqual(check_package(self.root, settings=settings)["issues"][0]["code"], "CONFIG_ERROR")
        path = self.root / "profilo.json"
        settings = Settings(tolerance_mm=1.5, recursive=True)
        save_settings(settings, path)
        self.assertEqual(settings, load_settings(path))
        path.write_text('{"unknown": true}')
        with self.assertRaises(ValueError):
            load_settings(path)

    def test_recursive_and_multiple_pages(self):
        self.pdf("sub/A-001_Pianta_R01.pdf", pages=2)
        self.assertEqual(check_package(self.root)["issues"][0]["code"], "NO_PDFS")
        report = check_package(self.root, settings=Settings(recursive=True, single_page=False))
        self.assertTrue(report["ok"])
        self.assertEqual(report["files"][0]["pages"], 2)

    def test_user_unit_and_tolerance_boundary(self):
        self.pdf(size=(300, 423), unit=2)
        manifest = self.csv("drawing,revision,paper\nA-001,01,A3\n")
        self.assertTrue(check_package(self.root, manifest)["ok"])
        report = check_package(self.root, manifest, Settings(tolerance_mm=2.9))
        self.assertEqual(report["issues"][0]["code"], "PAPER_MISMATCH")

    def test_custom_paper_validation(self):
        self.assertEqual(paper_size("900 x 420 mm"), (420, 900))
        for text in ("0x420", "nanx420", "-1x420", "A9"):
            with self.assertRaises(ValueError):
                paper_size(text)

    def test_demo_has_known_results_and_does_not_overwrite(self):
        demo = create_demo(self.root / "demo")
        report = check_package(demo / "corretto", demo / "corretto/elenco.csv")
        self.assertTrue(report["ok"])
        report = check_package(demo / "da_verificare", demo / "da_verificare/elenco.csv")
        self.assertEqual(len(report["issues"]), 5)
        self.assertEqual({i["code"] for i in report["issues"]}, {"DUPLICATE_DRAWING", "REVISION_MISMATCH", "PAPER_MISMATCH", "UNEXPECTED_DRAWING", "MISSING_DRAWING"})
        with self.assertRaises(FileExistsError):
            create_demo(demo)

    def test_exports_escape_and_protect_inputs(self):
        pdf = self.pdf("<img>_Pianta_R01.pdf")
        manifest = self.csv("drawing,revision,paper\n<img>,01,A3\n")
        report = check_package(self.root, manifest)
        self.assertIn("&lt;img&gt;", html_report(report))
        self.assertNotIn("<img>", html_report(report))
        before = manifest.read_bytes()
        with self.assertRaises(ValueError):
            export_report(report, manifest)
        self.assertEqual(manifest.read_bytes(), before)
        with self.assertRaises(ValueError):
            export_report(report, pdf)
        for suffix in ("html", "csv", "json"):
            path = self.root / f"report.{suffix}"
            export_report(report, path)
            self.assertGreater(path.stat().st_size, 0)
        self.assertEqual(json.loads((self.root / "report.json").read_text())["files_checked"], 1)

    def test_csv_formula_is_neutralized_and_cli_exports(self):
        self.pdf("=SUM(1)_Pianta_R01.pdf")
        manifest = self.csv("drawing,revision,paper\n=SUM(1),02,A3\n")
        report = check_package(self.root, manifest)
        path = self.root / "report.csv"
        export_report(report, path)
        self.assertIn("'=SUM(1)", path.read_text(encoding="utf-8-sig"))
        with contextlib.redirect_stdout(io.StringIO()):
            status = main([str(self.root), "--manifest", str(manifest), "--output", str(self.root / "report.html")])
        self.assertEqual(status, 1)
        self.assertTrue((self.root / "report.html").exists())


if __name__ == "__main__":
    unittest.main()
