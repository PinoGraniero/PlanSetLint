"""Validate filenames, drawing inventories, and PDF sheet sizes."""
import argparse
import csv
import json
import re
from pathlib import Path

from pypdf import PdfReader

NAME = re.compile(r"(?P<drawing>[A-Za-z][A-Za-z0-9]*-\d+)_(?P<title>.+)_R(?P<revision>\d+)\.pdf", re.IGNORECASE)
PAPER = {"A0": (841, 1189), "A1": (594, 841), "A2": (420, 594), "A3": (297, 420), "A4": (210, 297)}


def validate(folder, manifest=None):
    """Return structured errors; never modify input drawings."""
    folder = Path(folder)
    issues = []
    def add(code, file, message):
        issues.append({"code": code, "file": str(file), "message": message})
    if not folder.is_dir():
        add("INPUT_ERROR", folder, "Drawing directory does not exist.")
        return issues
    expected = {}
    if manifest is not None:
        try:
            with Path(manifest).open(encoding="utf-8-sig", newline="") as stream:
                reader = csv.DictReader(stream)
                if not {"drawing", "revision", "paper"}.issubset(reader.fieldnames or []):
                    raise ValueError("CSV requires drawing,revision,paper columns.")
                for line, row in enumerate(reader, 2):
                    drawing = row["drawing"].strip().upper()
                    revision = row["revision"].strip()
                    paper = row["paper"].strip().upper()
                    if not re.fullmatch(r"[A-Z][A-Z0-9]*-\d+", drawing) or not revision.isdigit() or (paper and paper not in PAPER):
                        raise ValueError(f"Invalid drawing, revision or paper on CSV line {line}.")
                    if drawing in expected:
                        raise ValueError(f"Duplicate drawing in CSV: {drawing}.")
                    expected[drawing] = (int(revision), paper)
        except (OSError, ValueError, csv.Error) as exc:
            add("MANIFEST_ERROR", manifest, str(exc))
            return issues
    files = sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == ".pdf")
    if not files:
        add("NO_PDFS", folder, "No PDF drawings found (scan is not recursive).")
    seen = {}
    for path in files:
        match = NAME.fullmatch(path.name)
        paper = ""
        if not match:
            add("INVALID_NAME", path.name, "Expected A-001_Title_R01.pdf naming convention.")
        else:
            drawing = match["drawing"].upper()
            if drawing in seen:
                add("DUPLICATE_DRAWING", path.name, f"Drawing {drawing} also appears in {seen[drawing]}.")
            seen[drawing] = path.name
            if manifest is not None:
                if drawing not in expected:
                    add("UNEXPECTED_DRAWING", path.name, f"Drawing {drawing} is absent from the manifest.")
                else:
                    revision, paper = expected[drawing]
                    if int(match["revision"]) != revision:
                        add("REVISION_MISMATCH", path.name, f"Expected revision R{revision:02d}.")
        try:
            reader = PdfReader(path)
            if reader.is_encrypted:
                add("ENCRYPTED_PDF", path.name, "Encrypted PDFs cannot be validated.")
                continue
            if len(reader.pages) != 1:
                add("PAGE_COUNT", path.name, "Expected one page per drawing file.")
            for number, page in enumerate(reader.pages, 1):
                scale = float(page.get("/UserUnit", 1)) * 25.4 / 72
                size = sorted((float(page.mediabox.width) * scale, float(page.mediabox.height) * scale))
                if paper and any(abs(a-b) > 3 for a, b in zip(size, PAPER[paper])):
                    add("PAPER_MISMATCH", path.name, f"Page {number}: {size[0]:.1f} x {size[1]:.1f} mm; expected {paper} (tolerance 3 mm).")
        except Exception as exc:
            add("UNREADABLE_PDF", path.name, f"Cannot inspect PDF: {exc}")
    for drawing in sorted(expected.keys() - seen.keys()):
        add("MISSING_DRAWING", manifest, f"Expected drawing {drawing} is missing.")
    return issues


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path, help="Directory containing single-page PDF drawings")
    parser.add_argument("--manifest", type=Path, help="CSV with drawing,revision,paper columns")
    parser.add_argument("--json", action="store_true", help="Print a machine-readable report")
    args = parser.parse_args(argv)
    issues = validate(args.folder, args.manifest)
    if args.json:
        print(json.dumps({"ok": not issues, "issues": issues}, indent=2))
    elif issues:
        for issue in issues:
            print(f"{issue['code']}: {issue['file']}: {issue['message']}")
    else:
        print("No issues found in the supported checks.")
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
