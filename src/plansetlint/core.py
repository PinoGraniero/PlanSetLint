"""Read-only package checks, without GUI or network dependencies."""
import csv
import json
import math
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from string import Formatter
from pypdf import PdfReader

DEFAULT_TEMPLATE = "{drawing}_{title}_R{revision}.pdf"
PAPER = {"A0": (841, 1189), "A1": (594, 841), "A2": (420, 594), "A3": (297, 420), "A4": (210, 297)}


@dataclass
class Settings:
    naming_template: str = DEFAULT_TEMPLATE
    tolerance_mm: float = 3.0
    single_page: bool = True
    recursive: bool = False

    def validate(self):
        if not isinstance(self.naming_template, str):
            raise ValueError("Lo schema dei nomi deve essere un testo.")
        if isinstance(self.tolerance_mm, bool) or not isinstance(self.tolerance_mm, (int, float)) or not math.isfinite(self.tolerance_mm) or not 0 <= self.tolerance_mm <= 100:
            raise ValueError("La tolleranza deve essere tra 0 e 100 mm.")
        if type(self.single_page) is not bool or type(self.recursive) is not bool:
            raise ValueError("single_page e recursive devono essere true o false.")
        return compile_template(self.naming_template)


def compile_template(template):
    if not template.lower().endswith(".pdf") or "/" in template or "\\" in template:
        raise ValueError("Lo schema deve terminare con .pdf e descrivere solo il nome del file.")
    pieces, fields, previous = [], [], False
    for literal, field, spec, conversion in Formatter().parse(template):
        pieces.append(re.escape(literal))
        if field is not None:
            if field not in {"drawing", "title", "revision"} or field in fields or spec or conversion:
                raise ValueError("Usa una sola volta {drawing}, {title} e {revision}, senza formattazioni.")
            if previous and not literal:
                raise ValueError("Separa i campi con un trattino, underscore o altro testo.")
            fields.append(field)
            pieces.append(f"(?P<{field}>.+?)")
        previous = field is not None
    if set(fields) != {"drawing", "title", "revision"}:
        raise ValueError("Lo schema richiede {drawing}, {title} e {revision}.")
    return re.compile("".join(pieces), re.IGNORECASE)


def load_settings(path):
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict) or set(data) - set(Settings.__dataclass_fields__):
        raise ValueError("Profilo JSON non valido o con opzioni sconosciute.")
    settings = Settings(**data)
    settings.validate()
    return settings


def save_settings(settings, path):
    settings.validate()
    Path(path).write_text(json.dumps(asdict(settings), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def revision_key(value):
    value = value.strip().upper()
    return str(int(value)) if re.fullmatch(r"[0-9]+", value) else value


def paper_size(value):
    value = value.strip().upper()
    if not value:
        return None
    if value in PAPER:
        return PAPER[value]
    match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)\s*[X×]\s*([0-9]+(?:\.[0-9]+)?)\s*(?:MM)?", value)
    if match:
        size = tuple(sorted(float(x) for x in match.groups()))
        if all(math.isfinite(x) and x > 0 for x in size):
            return size
    raise ValueError(f"Formato non valido: {value}. Usa A0–A4 oppure 420x900 in millimetri.")


def read_manifest(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        sample = stream.read(4096)
        stream.seek(0)
        try:
            delimiter = csv.Sniffer().sniff(sample, delimiters=",;").delimiter
        except csv.Error:
            first_line = sample.splitlines()[0] if sample else ""
            delimiter = ";" if ";" in first_line else ","
        reader = csv.DictReader(stream, delimiter=delimiter)
        if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)) or not {"drawing", "revision", "paper"}.issubset(reader.fieldnames):
            raise ValueError("Il CSV richiede drawing,revision,paper, senza intestazioni duplicate.")
        expected = {}
        for line, row in enumerate(reader, 2):
            if None in row or any(row.get(k) is None for k in ("drawing", "revision", "paper")):
                raise ValueError(f"Numero di colonne non valido alla riga {line} del CSV.")
            drawing, revision, paper = (row[k].strip() for k in ("drawing", "revision", "paper"))
            if not drawing or not revision:
                raise ValueError(f"Numero tavola o revisione vuoti alla riga {line} del CSV.")
            drawing = drawing.upper()
            if drawing in expected:
                raise ValueError(f"Tavola duplicata nell'elenco: {drawing}.")
            expected[drawing] = (revision_key(revision), paper.upper(), paper_size(paper))
        if not expected:
            raise ValueError("L'elenco CSV non contiene tavole attese.")
        return expected


def check_package(folder, manifest=None, settings=None):
    settings = settings or Settings()
    folder = Path(folder)
    report = {"version": "0.2.0", "created_at": datetime.now(timezone.utc).isoformat(), "folder": str(folder.resolve()),
              "manifest": str(Path(manifest).resolve()) if manifest else None, "settings": asdict(settings),
              "ok": False, "files_checked": 0, "files": [], "issues": [], "protected_paths": []}

    def add(code, file, message):
        report["issues"].append({"code": code, "file": str(file), "message": message})

    try:
        pattern = settings.validate()
    except (ValueError, re.error) as exc:
        add("CONFIG_ERROR", "", str(exc))
        return report
    if not folder.is_dir():
        add("INPUT_ERROR", folder, "La cartella delle tavole non esiste.")
        return report
    expected = {}
    if manifest:
        report["protected_paths"].append(str(Path(manifest).resolve()))
        try:
            expected = read_manifest(manifest)
        except (OSError, ValueError, csv.Error) as exc:
            add("MANIFEST_ERROR", manifest, str(exc))
            return report
    try:
        candidates = folder.rglob("*") if settings.recursive else folder.iterdir()
        files = sorted(p for p in candidates if p.is_file() and p.suffix.lower() == ".pdf")
    except OSError as exc:
        add("INPUT_ERROR", folder, f"Impossibile leggere la cartella: {exc}")
        return report
    report["files_checked"] = len(files)
    report["protected_paths"].extend(str(p.resolve()) for p in files)
    if not files:
        add("NO_PDFS", folder, "Nessun file PDF trovato nella cartella selezionata.")
    seen = {}
    for path in files:
        filename = str(path.relative_to(folder))
        item = {"file": filename, "drawing": "", "revision": "", "pages": None, "sizes_mm": []}
        report["files"].append(item)
        match = pattern.fullmatch(path.name)
        expected_size, expected_paper = None, ""
        if not match:
            add("INVALID_NAME", filename, f"Nome non conforme allo schema: {settings.naming_template}")
        else:
            drawing, revision = match["drawing"].strip().upper(), match["revision"].strip()
            item.update(drawing=drawing, revision=revision)
            if not drawing or not revision or not match["title"].strip():
                add("INVALID_NAME", filename, "Numero tavola, titolo e revisione devono contenere testo.")
            elif drawing in seen:
                add("DUPLICATE_DRAWING", filename, f"La tavola {drawing} è presente anche in {seen[drawing]}.")
            if drawing:
                seen[drawing] = filename
            if manifest:
                if drawing not in expected:
                    add("UNEXPECTED_DRAWING", filename, f"La tavola {drawing} non è prevista nell'elenco.")
                else:
                    expected_revision, expected_paper, expected_size = expected[drawing]
                    if revision_key(revision) != expected_revision:
                        add("REVISION_MISMATCH", filename, f"Revisione {revision}; nell'elenco è prevista {expected_revision}.")
        try:
            with path.open("rb") as stream:
                reader = PdfReader(stream)
                if reader.is_encrypted:
                    add("ENCRYPTED_PDF", filename, "PDF protetto: controlli sulle pagine non eseguiti.")
                    continue
                item["pages"] = len(reader.pages)
                if not reader.pages or (settings.single_page and len(reader.pages) != 1):
                    add("PAGE_COUNT", filename, "È prevista una pagina per file." if settings.single_page else "Il PDF non contiene pagine.")
                for number, page in enumerate(reader.pages, 1):
                    scale = float(page.get("/UserUnit", 1)) * 25.4 / 72
                    size = sorted((abs(float(page.mediabox.width)) * scale, abs(float(page.mediabox.height)) * scale))
                    if not all(math.isfinite(x) and x > 0 for x in size):
                        raise ValueError("Dimensioni pagina non valide.")
                    item["sizes_mm"].append([round(x, 2) for x in size])
                    if expected_size and any(abs(a - b) > settings.tolerance_mm + 1e-6 for a, b in zip(size, expected_size)):
                        add("PAPER_MISMATCH", filename, f"Pagina {number}: {size[0]:.1f} × {size[1]:.1f} mm; previsto {expected_paper}; tolleranza {settings.tolerance_mm:g} mm.")
        except Exception as exc:
            add("UNREADABLE_PDF", filename, f"Impossibile ispezionare il PDF: {exc}")
    for drawing in sorted(expected.keys() - seen.keys()):
        add("MISSING_DRAWING", str(manifest), f"Manca la tavola {drawing} prevista nell'elenco.")
    report["ok"] = not report["issues"]
    return report
