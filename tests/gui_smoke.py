"""Real Tk smoke check; run with xvfb-run on Linux or with a desktop display."""
import tempfile
import time
import tkinter as tk
from pathlib import Path
from plansetlint.demo import create_demo
from plansetlint.gui import App


def main():
    with tempfile.TemporaryDirectory() as tmp:
        demo = create_demo(Path(tmp) / "demo")
        root = tk.Tk()
        app = App(root)
        try:
            root.update()
            for name, expected_count in (("da_verificare", 5), ("corretto", 0)):
                app.folder.set(str(demo / name))
                app.manifest.set(str(demo / name / "elenco.csv"))
                app.run()
                deadline = time.monotonic() + 15
                while app.busy and time.monotonic() < deadline:
                    root.update()
                    time.sleep(0.01)
                assert not app.busy, "GUI worker did not complete"
                assert app.report is not None
                assert len(app.report["issues"]) == expected_count
                assert len(app.issue_table.get_children()) == expected_count
                assert len(app.file_table.get_children()) == app.report["files_checked"]
            app.template.set("Tavola_{drawing}_{title}_Rev{revision}.pdf")
            assert app.report is None, "Changed settings must invalidate previous results"
        finally:
            root.destroy()
    print("GUI smoke passed: real Tk window, worker, reports and invalidation")


if __name__ == "__main__":
    main()
