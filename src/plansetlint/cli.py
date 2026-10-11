"""Command-line interface and compatibility entry point."""
import argparse
import json
from pathlib import Path
from .core import Settings, check_package, load_settings
from .reports import export_report


def validate(folder, manifest=None, settings=None):
    return check_package(folder, manifest, settings)["issues"]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Controlla un fascicolo di tavole PDF in locale.")
    parser.add_argument("folder", type=Path, help="Cartella delle tavole PDF")
    parser.add_argument("--manifest", type=Path, help="Elenco CSV: drawing,revision,paper")
    parser.add_argument("--config", type=Path, help="Profilo JSON")
    parser.add_argument("--template", help="Schema con {drawing}, {title} e {revision}")
    parser.add_argument("--recursive", action="store_true", help="Includi sottocartelle")
    parser.add_argument("--json", action="store_true", help="Stampa rapporto JSON")
    parser.add_argument("--output", type=Path, help="Rapporto .html, .csv o .json")
    args = parser.parse_args(argv)
    try:
        settings = load_settings(args.config) if args.config else Settings()
        if args.template:
            settings.naming_template = args.template
        if args.recursive:
            settings.recursive = True
        report = check_package(args.folder, args.manifest, settings)
        if args.config:
            report["protected_paths"].append(str(args.config.resolve()))
        if args.output:
            export_report(report, args.output)
    except (OSError, ValueError) as exc:
        report = {"ok": False, "issues": [{"code": "INPUT_ERROR", "file": "", "message": str(exc)}]}
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    elif report["issues"]:
        for issue in report["issues"]:
            print(f"{issue['code']}: {issue['file']}: {issue['message']}")
    else:
        print("Nessuna anomalia nei controlli eseguiti.")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
