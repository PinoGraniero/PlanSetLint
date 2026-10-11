# PlanSetLint

A lightweight open-source command-line tool for checking architectural PDF drawing packages before submission or handover.

**Status: early prototype (0.1.0).** This is a new project with a small initial implementation. There are no claims of established adoption, production validation, or an existing community.

Small architecture practices often check drawing inventories, filenames, revisions and sheet sizes manually. PlanSetLint aims to make these repetitive checks accessible and scriptable without requiring a document-management platform.

## What works today

- Validate filenames such as `A-001_Ground-floor-plan_R01.pdf`.
- Find duplicate drawing identifiers, including different revisions of the same drawing in one package.
- Compare filenames with an optional CSV inventory to find missing or unexpected drawings and revision mismatches.
- Open PDFs and flag unreadable, encrypted or non-single-page files.
- Compare PDF page dimensions with an expected A0–A4 size from the CSV (portrait or landscape, 3 mm tolerance).
- Print a text or JSON report; exit with code `0` for no issues and `1` for issues.

## Installation

Requires Python 3.10 or newer. From this repository directory:

```sh
python -m venv .venv
# macOS / Linux:
source .venv/bin/activate
# Windows PowerShell instead:
# .venv\Scripts\Activate.ps1
python -m pip install -e .
```

The package has not been published to PyPI. Install from the source checkout.

## Usage

```sh
plansetlint ./drawings
plansetlint ./drawings --manifest examples/drawings.csv
plansetlint ./drawings --manifest examples/drawings.csv --json
```

Example inventory:

```csv
drawing,revision,paper
A-001,01,A3
A-002,02,A1
```

Use one PDF per drawing, named `<drawing>_<title>_R<revision>.pdf`. Drawing identifiers have an alphanumeric discipline prefix and numeric drawing number, separated by a hyphen. Identifier matching is case-insensitive, but `A-1` and `A-001` are different identifiers. Revisions are numeric: `R1` and `R01` match the same revision. Titles can contain spaces, underscores and accented characters.

The CSV is UTF-8, comma-separated, with required `drawing`, `revision`, `paper` columns. Leave `paper` empty to skip sheet-size checks for that drawing. Different expected sheet sizes are allowed within the same package.

Without a manifest, the tool cannot know which drawings are missing, which revision is expected, or which paper size is intended. Only immediate PDF files in the supplied directory are checked; subdirectories are not scanned.

## Limits

This prototype checks file metadata and naming, not architectural content. It does not read title blocks, perform OCR, validate dimensions or scale, inspect BIM models, or certify regulatory compliance. PDF dimensions use the MediaBox and UserUnit, not the visible cropped area. Input files are never modified. Reports can contain file names and local paths; review them before sharing.

## Roadmap

- Configurable naming rules for different studios.
- Optional title-block text extraction and comparison.
- Explicit support for multi-page drawing packages and custom sheet sizes.
- More accessible report formats and a possible graphical interface.

## Development and contributions

```sh
python -m unittest discover -s tests -v
```

Issues and pull requests are welcome. Include a reproducible example, the expected behavior and the actual report. Use synthetic or anonymized files; do not upload confidential client drawings. Start with a small focused change and add tests for new validation behavior.

## Italiano

PlanSetLint è un piccolo strumento open source per controllare i fascicoli PDF di elaborati architettonici prima della consegna. La prima versione controlla denominazioni, duplicati e leggibilità dei PDF; con un elenco CSV verifica anche tavole mancanti, revisioni e formati carta. È un prototipo iniziale e non sostituisce la verifica tecnica degli elaborati.

## License

MIT. See [LICENSE](LICENSE).
