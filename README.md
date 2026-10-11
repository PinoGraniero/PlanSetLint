# PlanSetLint

Check architectural PDF drawing packages before submission or handover, with a local Italian desktop interface and a scriptable command-line tool.

**Status: early prototype, version 0.2.0.** The desktop interface and initial validation features are implemented. Real-world workflows and installation on individual Mac/Windows computers still need user testing.

Small architecture practices often check drawing inventories, filenames, revisions and sheet sizes manually. PlanSetLint makes these repetitive checks accessible without requiring a document-management platform. PDF processing is local; the application makes no network requests while inspecting drawings.

## Start with the desktop interface

See **[Guida italiana — installazione e prima prova](GUIDA-ITALIANA.md)** for a step-by-step walkthrough.

1. Download and extract the source repository.
2. Install Python 3.10+ with Tkinter if needed.
3. Run `Avvia-PlanSetLint.bat` on Windows or `Avvia-PlanSetLint.command` on macOS. Alternatively, run `python3 launch.py` (`python launch.py` on Windows).
4. Choose a PDF folder, optionally load a CSV inventory, and select **Avvia controllo**.

The launcher creates an isolated `.venv` and installs dependencies from PyPI on first use. Internet is required for initial setup; later checks work offline. There is no standalone Windows executable or macOS `.app` yet.

The desktop interface includes a built-in synthetic demo, custom filename templates, saved JSON profiles, optional recursive checks, an issues table, a PDF inventory and HTML/CSV/JSON report export. HTML reports can be printed to PDF using a browser.

## Available checks

- Filename structure using a configurable template, such as `{drawing}_{title}_R{revision}.pdf`.
- Duplicate drawing identifiers, including different revisions of one drawing in the package.
- Missing or unexpected drawings and revision mismatches against an optional CSV inventory.
- Unreadable, encrypted, empty or unexpectedly multi-page PDFs.
- Expected A0–A4 or custom page dimensions, such as `420x900` mm, with configurable tolerance.
- Optional subdirectory scanning.

## CLI installation and use

```sh
python -m venv .venv
# macOS / Linux:
source .venv/bin/activate
# Windows PowerShell instead:
# .venv\Scripts\Activate.ps1
python -m pip install -e .

plansetlint ./drawings
plansetlint ./drawings --manifest examples/drawings.csv --output report.html
plansetlint ./drawings --config examples/profilo-studio.json --json
plansetlint ./drawings --template 'Tavola_{drawing}_{title}_Rev{revision}.pdf' --recursive
plansetlint-gui
```

The package is not published to PyPI. Install from this source repository. Exit codes are `0` for no issues and `1` for validation or input/export errors. JSON output contains settings, inspected files, page sizes, issue codes and metadata.

## Filename rules and inventories

The three required filename fields are `{drawing}`, `{title}`, and `{revision}`, each appearing exactly once and separated by literal characters. Templates are literal text with placeholders, not arbitrary regular expressions. For example:

```text
A-001_Pianta_R01.pdf       → {drawing}_{title}_R{revision}.pdf
Tavola_01_Pianta_RevB.pdf  → Tavola_{drawing}_{title}_Rev{revision}.pdf
```

Choose separators that do not occur inside drawing identifiers, and check the parsed identifiers in **PDF esaminati**. Ambiguous conventions cannot be inferred reliably. Drawing matching is case-insensitive, but `A-1` and `A-001` are different identifiers. Numeric revisions `1` and `01` are equivalent; letter revisions are accepted and compared case-insensitively. Titles are not checked against a title block.

CSV files must be UTF-8 (optional BOM), comma- or semicolon-separated, with exact `drawing`, `revision`, `paper` headers:

```csv
drawing,revision,paper
A-001,01,A3
A-002,B,420x900
A-003,01,
```

A blank `paper` skips the size comparison for that file. Custom sizes are in millimetres, with a decimal point when needed. Mixed paper sizes are allowed. A manifest must contain at least one drawing. Without a manifest, missing drawings, expected revisions and expected sheet sizes cannot be checked.

JSON profiles support `naming_template`, `tolerance_mm` (0–100), `single_page` and `recursive`. Defaults are 3 mm tolerance, one page per PDF and no recursive scan. Profiles store no document paths.

## Reports and limits

HTML reports contain a full inventory and issue table. CSV exports contain the issue table with spreadsheet formula prefixes neutralized. JSON exports contain the full report. HTML output escapes filenames and messages and loads no remote scripts or assets. Report output cannot overwrite source PDFs or the supplied inventory/configuration.

This prototype inspects filenames and PDF page metadata. It does not read title blocks, perform OCR, validate dimensions or drawing scale, inspect BIM models, or certify regulatory compliance. Page sizes use MediaBox and UserUnit, ignoring orientation and visible crop area. When multi-page files are allowed, every page is checked against the same expected size for that drawing.

Input drawings are not modified. Reports may contain local paths and file names; review them before sharing. A clean result means only that the enabled checks passed.

## Tests and contributions

```sh
python -m unittest discover -s tests -v
# With a desktop display, or using xvfb-run on Linux:
python tests/gui_smoke.py
```

GitHub Actions runs validation tests and a real Tk window smoke check on Python 3.10 and 3.13. User testing on macOS and Windows remains necessary.

Issues and pull requests are welcome. Include the OS, a reproducible example, expected behavior and actual report. Use synthetic or anonymized files; do not upload confidential client drawings.

## Next steps

- Test real studio naming conventions and refine usability.
- Build distributable desktop packages after verifying the launch workflow.
- Optional title-block text extraction, followed by OCR support where required.
- Richer drawing inventories and additional report formats.

## License

MIT. See [LICENSE](LICENSE).
