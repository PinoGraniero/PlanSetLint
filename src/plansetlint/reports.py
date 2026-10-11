"""Local report exports, with escaped HTML and spreadsheet-safe CSV."""
import csv
import html
import json
from pathlib import Path

LABELS = {"INPUT_ERROR": "Errore di lettura", "CONFIG_ERROR": "Profilo non valido", "MANIFEST_ERROR": "Elenco non valido",
          "NO_PDFS": "Nessun PDF", "INVALID_NAME": "Nome da verificare", "DUPLICATE_DRAWING": "Tavola duplicata",
          "UNEXPECTED_DRAWING": "Tavola non prevista", "REVISION_MISMATCH": "Revisione diversa", "MISSING_DRAWING": "Tavola mancante",
          "ENCRYPTED_PDF": "PDF protetto", "PAGE_COUNT": "Numero pagine", "PAPER_MISMATCH": "Formato diverso", "UNREADABLE_PDF": "PDF non leggibile"}


def csv_safe(value):
    value = str(value)
    return "'" + value if value.lstrip().startswith(("=", "+", "-", "@")) or value.startswith(("\t", "\r")) else value


def html_report(report):
    esc = lambda value: html.escape(str(value), quote=True)
    status = "Nessuna anomalia nei controlli eseguiti" if report["ok"] else f"{len(report['issues'])} anomalie da verificare"
    rows = "".join(f"<tr><td>{esc(LABELS.get(i['code'], i['code']))}</td><td>{esc(i['file'])}</td><td>{esc(i['message'])}</td></tr>" for i in report["issues"])
    files = "".join(f"<tr><td>{esc(i['file'])}</td><td>{esc(i['drawing'])}</td><td>{esc(i['revision'])}</td><td>{esc(i['pages'] if i['pages'] is not None else '—')}</td><td>{esc('; '.join(f'{s[0]:g} × {s[1]:g}' for s in i['sizes_mm']))}</td></tr>" for i in report["files"])
    settings = report["settings"]
    single = "Sì" if settings["single_page"] else "No"
    recursive = "Sì" if settings["recursive"] else "No"
    return f'''<!doctype html><html lang="it"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Rapporto PlanSetLint</title>
<style>body{{font:16px system-ui,sans-serif;color:#18303b;background:#f3f6f6;max-width:1100px;margin:40px auto;padding:0 24px}}h1{{font-size:32px}}section{{background:white;border:1px solid #d8e1e4;border-radius:12px;padding:24px;margin:20px 0}}table{{border-collapse:collapse;width:100%;font-size:14px}}th,td{{padding:10px;text-align:left;border-bottom:1px solid #d8e1e4;overflow-wrap:anywhere}}th{{background:#edf3f3}}.status{{font-size:22px;color:#176557}}small{{color:#52646c}}@media print{{body{{background:white;margin:0;padding:0;font-size:11pt}}tr{{break-inside:avoid}}}}</style>
<h1>PlanSetLint · Rapporto di controllo</h1><p class="status">{esc(status)}</p><p>{report['files_checked']} PDF esaminati · {esc(report['created_at'])}</p>
<section><h2>Impostazioni</h2><p>Cartella: {esc(report['folder'])}</p><p>Elenco atteso: {esc(report['manifest'] or 'Non caricato')}</p><p>Schema nomi: {esc(settings['naming_template'])}</p><p>Tolleranza: {esc(settings['tolerance_mm'])} mm · Una pagina per file: {single} · Sottocartelle: {recursive}</p></section>
<section><h2>Anomalie</h2><table><thead><tr><th>Controllo</th><th>File</th><th>Dettaglio</th></tr></thead><tbody>{rows or '<tr><td colspan="3">Nessuna anomalia rilevata.</td></tr>'}</tbody></table></section>
<section><h2>File esaminati</h2><table><thead><tr><th>File</th><th>Tavola</th><th>Revisione</th><th>Pagine</th><th>Dimensioni mm</th></tr></thead><tbody>{files}</tbody></table></section>
<small>Controlli su nomi e metadati dei PDF. Senza elenco atteso non sono verificate tavole mancanti, revisioni attese o formati attesi. Dimensioni MediaBox, senza distinzione tra orientamento verticale e orizzontale. Nessuna verifica del contenuto architettonico, del cartiglio, della scala o della conformità normativa. PlanSetLint {esc(report['version'])}.</small></html>'''


def export_report(report, path):
    path = Path(path)
    if path.suffix.lower() not in {".html", ".csv", ".json"}:
        raise ValueError("Salva il rapporto come .html, .csv oppure .json.")
    if str(path.resolve()) in report.get("protected_paths", []):
        raise ValueError("Il rapporto non può sovrascrivere un file di ingresso.")
    if path.suffix.lower() == ".html":
        path.write_text(html_report(report), encoding="utf-8")
    elif path.suffix.lower() == ".json":
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        with path.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.writer(stream, delimiter=";")
            writer.writerow(["Controllo", "File", "Dettaglio"])
            for issue in report["issues"]:
                writer.writerow([csv_safe(LABELS.get(issue["code"], issue["code"])), csv_safe(issue["file"]), csv_safe(issue["message"])])
            if not report["issues"]:
                writer.writerow(["Esito", "", "Nessuna anomalia nei controlli eseguiti"])
