"""Italian desktop interface; PDF processing runs away from the Tk event loop."""
import queue
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .core import DEFAULT_TEMPLATE, Settings, check_package, load_settings, save_settings
from .demo import create_demo
from .reports import LABELS, export_report


class App:
    def __init__(self, root):
        self.root = root
        root.title("PlanSetLint 0.2 · Controllo elaborati PDF")
        root.geometry("1040x780")
        root.minsize(800, 680)
        self.folder = tk.StringVar()
        self.manifest = tk.StringVar()
        self.template = tk.StringVar(value=DEFAULT_TEMPLATE)
        self.tolerance = tk.StringVar(value="3")
        self.single = tk.BooleanVar(value=True)
        self.recursive = tk.BooleanVar(value=False)
        self.status = tk.StringVar(value="Scegli una cartella per iniziare.")
        self.summary = tk.StringVar(value="Pronto per il primo controllo")
        self.report, self.busy, self.config_path = None, False, None
        self.results = queue.Queue()
        outer = ttk.Frame(root, padding=22)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="PlanSetLint", font=("TkDefaultFont", 24, "bold")).pack(anchor="w")
        ttk.Label(outer, text="Controlla il fascicolo prima della consegna · PDF elaborati sul tuo computer").pack(anchor="w", pady=(3, 16))
        inputs = ttk.LabelFrame(outer, text="1 · Scegli il fascicolo", padding=12)
        inputs.pack(fill="x")
        inputs.columnconfigure(1, weight=1)
        self.path_row(inputs, 0, "Cartella PDF", self.folder, self.choose_folder)
        self.path_row(inputs, 1, "Elenco CSV (facoltativo)", self.manifest, self.choose_manifest)
        ttk.Button(inputs, text="Rimuovi elenco", command=lambda: self.manifest.set("")).grid(row=2, column=2, sticky="e")
        ttk.Label(inputs, text="Con il CSV verifichi anche tavole mancanti, revisioni e formati attesi.").grid(row=2, column=0, columnspan=2, sticky="w", pady=5)
        rules = ttk.LabelFrame(outer, text="2 · Imposta i controlli", padding=12)
        rules.pack(fill="x", pady=12)
        rules.columnconfigure(1, weight=1)
        ttk.Label(rules, text="Schema dei nomi").grid(row=0, column=0, sticky="w", padx=(0, 10))
        ttk.Combobox(rules, textvariable=self.template, values=[DEFAULT_TEMPLATE, "Tavola_{drawing}_{title}_Rev{revision}.pdf", "{drawing} - {title} - rev{revision}.pdf"]).grid(row=0, column=1, columnspan=3, sticky="ew")
        ttk.Label(rules, text="Esempio: A-001_Pianta_R01.pdf · drawing = tavola, title = titolo, revision = revisione").grid(row=1, column=0, columnspan=4, sticky="w", pady=7)
        ttk.Label(rules, text="Tolleranza formato (mm)").grid(row=2, column=0, sticky="w")
        ttk.Spinbox(rules, from_=0, to=100, increment=0.5, textvariable=self.tolerance, width=7).grid(row=2, column=1, sticky="w")
        ttk.Checkbutton(rules, text="Una pagina per PDF", variable=self.single).grid(row=2, column=2, padx=8)
        ttk.Checkbutton(rules, text="Includi sottocartelle", variable=self.recursive).grid(row=2, column=3)
        profiles = ttk.Frame(rules)
        profiles.grid(row=3, column=0, columnspan=4, sticky="w", pady=(10, 0))
        ttk.Button(profiles, text="Carica profilo", command=self.load_profile).pack(side="left")
        ttk.Button(profiles, text="Salva profilo", command=self.save_profile).pack(side="left", padx=8)
        ttk.Button(profiles, text="Crea fascicolo dimostrativo", command=self.demo).pack(side="left")
        actions = ttk.Frame(outer)
        actions.pack(fill="x", pady=(0, 12))
        self.run_button = ttk.Button(actions, text="3 · Avvia controllo", command=self.run)
        self.run_button.pack(side="left")
        self.export_button = ttk.Button(actions, text="Esporta rapporto…", command=self.export, state="disabled")
        self.export_button.pack(side="left", padx=10)
        ttk.Label(outer, textvariable=self.summary, font=("TkDefaultFont", 14, "bold")).pack(anchor="w", pady=(0, 8))
        notebook = ttk.Notebook(outer)
        notebook.pack(fill="both", expand=True)
        self.issue_table = self.make_table(notebook, "Anomalie", ["Controllo", "File", "Dettaglio"], [160, 220, 500])
        self.file_table = self.make_table(notebook, "PDF esaminati", ["File", "Tavola", "Revisione", "Pagine", "Dimensioni mm"], [340, 100, 80, 60, 240])
        detail = ttk.Frame(outer)
        detail.pack(fill="x", pady=7)
        self.detail_text = tk.Text(detail, height=3, wrap="word", font=("TkDefaultFont", 10), state="disabled")
        self.detail_text.pack(fill="x")
        self.issue_table.bind("<<TreeviewSelect>>", self.show_detail)
        ttk.Label(outer, textvariable=self.status, wraplength=930).pack(anchor="w", pady=(5, 0))
        ttk.Label(outer, text="Verifica nomi e metadati. Cartigli, scala, contenuto architettonico e conformità normativa richiedono una verifica tecnica.", wraplength=930).pack(anchor="w", pady=(7, 0))
        for var in (self.folder, self.manifest, self.template, self.tolerance, self.single, self.recursive):
            var.trace_add("write", self.invalidate)
        root.after(100, self.poll)

    def path_row(self, parent, row, label, variable, command):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=(0, 10), pady=5)
        ttk.Entry(parent, textvariable=variable).grid(row=row, column=1, sticky="ew", pady=5)
        ttk.Button(parent, text="Scegli…", command=command).grid(row=row, column=2, padx=(8, 0), pady=5)

    def make_table(self, notebook, title, headings, widths):
        frame = ttk.Frame(notebook)
        notebook.add(frame, text=title)
        table = ttk.Treeview(frame, columns=list(range(len(headings))), show="headings", selectmode="browse")
        for i, (heading, width) in enumerate(zip(headings, widths)):
            table.heading(i, text=heading)
            table.column(i, width=width, minwidth=60)
        y = ttk.Scrollbar(frame, orient="vertical", command=table.yview)
        x = ttk.Scrollbar(frame, orient="horizontal", command=table.xview)
        table.configure(yscrollcommand=y.set, xscrollcommand=x.set)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        table.grid(row=0, column=0, sticky="nsew")
        y.grid(row=0, column=1, sticky="ns")
        x.grid(row=1, column=0, sticky="ew")
        return table

    def invalidate(self, *_):
        self.report = None
        self.export_button.configure(state="disabled")
        self.status.set("Impostazioni modificate: avvia un nuovo controllo.")

    def choose_folder(self):
        path = filedialog.askdirectory(title="Scegli la cartella delle tavole PDF")
        if path:
            self.folder.set(path)

    def choose_manifest(self):
        path = filedialog.askopenfilename(title="Scegli l'elenco delle tavole attese", filetypes=[("Elenco CSV", "*.csv")])
        if path:
            self.manifest.set(path)

    def settings(self):
        settings = Settings(self.template.get(), float(self.tolerance.get().replace(",", ".")), self.single.get(), self.recursive.get())
        settings.validate()
        return settings

    def apply_settings(self, settings):
        self.template.set(settings.naming_template)
        self.tolerance.set(str(settings.tolerance_mm))
        self.single.set(settings.single_page)
        self.recursive.set(settings.recursive)

    def load_profile(self):
        path = filedialog.askopenfilename(title="Carica profilo", filetypes=[("Profilo JSON", "*.json")])
        if path:
            try:
                settings = load_settings(path)
                self.apply_settings(settings)
                self.config_path = path
            except (OSError, ValueError) as exc:
                messagebox.showerror("Profilo non valido", str(exc))

    def save_profile(self):
        try:
            settings = self.settings()
            path = filedialog.asksaveasfilename(title="Salva profilo", defaultextension=".json", filetypes=[("Profilo JSON", "*.json")])
            if path:
                self.protect_input(path)
                save_settings(settings, path)
        except (OSError, ValueError) as exc:
            messagebox.showerror("Impossibile salvare", str(exc))

    def protect_input(self, path):
        target = Path(path).resolve()
        if target.suffix.lower() == ".pdf" or (self.manifest.get() and target == Path(self.manifest.get()).resolve()):
            raise ValueError("Scegli un percorso diverso dai PDF e dall'elenco di ingresso.")

    def demo(self):
        if self.busy:
            return
        parent = filedialog.askdirectory(title="Dove creare una nuova cartella PlanSetLint-demo?")
        if parent:
            try:
                folder = create_demo(Path(parent) / "PlanSetLint-demo") / "da_verificare"
                self.apply_settings(Settings())
                self.folder.set(str(folder))
                self.manifest.set(str(folder / "elenco.csv"))
                messagebox.showinfo("Demo pronta", "Creati PDF vuoti sintetici. Premi Avvia controllo: sono previste 5 anomalie. La cartella 'corretto' contiene un fascicolo senza anomalie.")
            except OSError as exc:
                messagebox.showerror("Impossibile creare la demo", str(exc))

    def run(self):
        if self.busy:
            return
        try:
            settings = self.settings()
            if not self.folder.get().strip():
                raise ValueError("Scegli prima la cartella delle tavole PDF.")
        except ValueError as exc:
            messagebox.showerror("Controlla le impostazioni", str(exc))
            return
        folder, manifest = self.folder.get(), self.manifest.get() or None
        fingerprint = self.fingerprint()
        self.report, self.busy = None, True
        self.run_button.configure(state="disabled")
        self.export_button.configure(state="disabled")
        self.summary.set("Controllo in corso…")
        self.status.set("Lettura dei PDF. I file originali non vengono modificati.")

        def worker():
            try:
                result = check_package(folder, manifest, settings)
                self.results.put((fingerprint, result, None))
            except Exception as exc:
                self.results.put((fingerprint, None, str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def fingerprint(self):
        return (self.folder.get(), self.manifest.get(), self.template.get(), self.tolerance.get(), self.single.get(), self.recursive.get())

    def poll(self):
        try:
            fingerprint, result, error = self.results.get_nowait()
        except queue.Empty:
            pass
        else:
            self.busy = False
            self.run_button.configure(state="normal")
            if error:
                self.summary.set("Controllo interrotto")
                messagebox.showerror("Errore di controllo", error)
            elif fingerprint != self.fingerprint():
                self.summary.set("Impostazioni modificate durante il controllo")
                self.status.set("Avvia nuovamente il controllo con le impostazioni attuali.")
            else:
                if self.config_path:
                    result["protected_paths"].append(str(Path(self.config_path).resolve()))
                self.display_result(result)
        self.root.after(100, self.poll)

    def display_result(self, report):
        self.report = report
        for table in (self.issue_table, self.file_table):
            for child in table.get_children():
                table.delete(child)
        self.detail_text.configure(state="normal")
        self.detail_text.delete("1.0", "end")
        self.detail_text.configure(state="disabled")
        for issue in report["issues"]:
            self.issue_table.insert("", "end", values=(LABELS.get(issue["code"], issue["code"]), issue["file"], issue["message"]))
        for item in report["files"]:
            sizes = "; ".join(f"{s[0]:g} × {s[1]:g}" for s in item["sizes_mm"])
            self.file_table.insert("", "end", values=(item["file"], item["drawing"], item["revision"], item["pages"] if item["pages"] is not None else "—", sizes))
        count = len(report["issues"])
        self.summary.set(f"{report['files_checked']} PDF esaminati · {count} anomalie da verificare" if count else f"{report['files_checked']} PDF esaminati · Nessuna anomalia nei controlli eseguiti")
        self.status.set("Seleziona un'anomalia per leggerne il dettaglio. Puoi esportare il rapporto." if report["manifest"] else "Elenco CSV non caricato: tavole mancanti, revisioni attese e formati attesi non sono stati verificati.")
        self.export_button.configure(state="normal")

    def show_detail(self, _event=None):
        selection = self.issue_table.selection()
        if selection:
            values = self.issue_table.item(selection[0], "values")
            self.detail_text.configure(state="normal")
            self.detail_text.delete("1.0", "end")
            self.detail_text.insert("1.0", f"{values[0]} · {values[1]}\n{values[2]}")
            self.detail_text.configure(state="disabled")

    def export(self):
        if self.report is None:
            return
        path = filedialog.asksaveasfilename(title="Esporta rapporto", initialfile="Rapporto-PlanSetLint.html", defaultextension=".html", filetypes=[("Rapporto stampabile", "*.html"), ("Anomalie CSV", "*.csv"), ("Rapporto JSON", "*.json")])
        if path:
            try:
                self.protect_input(path)
                export_report(self.report, path)
                messagebox.showinfo("Rapporto salvato", "Apri il rapporto HTML nel browser per leggerlo o stamparlo in PDF.")
            except (OSError, ValueError) as exc:
                messagebox.showerror("Impossibile esportare", str(exc))


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
