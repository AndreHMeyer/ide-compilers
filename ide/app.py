"""Editor Tkinter e operações de arquivos da IDE Compiladores."""

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, font, messagebox, ttk

from ide.compiler_service import compile_source


FILE_TYPES = [("Código-fonte", "*.src"), ("Arquivos de texto", "*.txt"), ("Todos os arquivos", "*.*")]

DARK_THEME = {
    "background": "#1b1f27",
    "surface": "#242b36",
    "editor": "#141820",
    "messages": "#191e28",
    "text": "#e6edf3",
    "muted": "#a7b3c5",
    "border": "#394355",
    "accent": "#2563eb",
    "accent_hover": "#3474f4",
    "accent_pressed": "#1d4ed8",
    "selection": "#334f75",
    "success": "#8dd9a8",
    "error": "#ff9a9e",
    "warning": "#f2ce78",
    "error_line": "#482c35",
}


class IDEApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.current_file: Path | None = None
        self.dirty = False
        self.root.title("IDE Compiladores - Novo arquivo")
        width = min(1100, max(700, self.root.winfo_screenwidth() - 100))
        height = min(760, max(480, self.root.winfo_screenheight() - 140))
        self.root.geometry(f"{width}x{height}")
        self.root.minsize(700, 480)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self._configure_theme()
        self.code_font = self._create_code_font()
        self._create_menu()
        self._create_widgets()
        self._bind_shortcuts()
        self.editor.bind("<<Modified>>", self._on_modified)
        self.editor.bind("<Tab>", self._insert_tab)
        self.editor.focus_set()

    def _configure_theme(self) -> None:
        colors = DARK_THEME
        self.root.configure(background=colors["background"])
        style = ttk.Style(self.root)
        # O tema clam permite aplicar as cores também nos controles do Windows.
        style.theme_use("clam")
        style.configure(
            ".", background=colors["background"], foreground=colors["text"],
            bordercolor=colors["border"], lightcolor=colors["border"],
            darkcolor=colors["border"], troughcolor=colors["editor"],
        )
        style.configure("TLabel", background=colors["background"], foreground=colors["muted"])
        style.configure("Heading.TLabel", foreground=colors["text"])
        style.configure("TButton", background=colors["accent"], foreground="#ffffff", borderwidth=0)
        style.map(
            "TButton",
            background=[("pressed", colors["accent_pressed"]), ("active", colors["accent_hover"])],
            foreground=[("disabled", colors["muted"])],
        )
        style.configure("TMenubutton", padding=(10, 5), borderwidth=0, arrowcolor=colors["muted"])
        style.map("TMenubutton", background=[("active", colors["surface"])])
        style.configure(
            "TScrollbar", background=colors["border"], arrowcolor=colors["muted"],
            borderwidth=0, relief="flat",
        )
        style.map("TScrollbar", background=[("active", colors["selection"]), ("pressed", colors["selection"])])
        style.configure("Sash", background=colors["background"], sashthickness=6)
        style.configure("Treeview", background=colors["editor"], fieldbackground=colors["editor"],
                        foreground=colors["text"], rowheight=28, font=("TkDefaultFont", 11))
        style.configure("Treeview.Heading", background=colors["surface"], foreground=colors["text"])
        style.map("Treeview", background=[("selected", colors["selection"])],
                  foreground=[("selected", "#ffffff")])
        style.map("TNotebook.Tab", background=[("selected", colors["surface"])])

    def _create_code_font(self) -> font.Font:
        available = set(font.families(self.root))
        fallback = font.nametofont("TkFixedFont", root=self.root).actual("family")
        family = next((name for name in ("Consolas", "Courier New") if name in available), fallback)
        return font.Font(root=self.root, family=family, size=14)

    def _create_menu(self) -> None:
        bar = ttk.Frame(self.root, padding=(4, 2))
        bar.grid(row=0, column=0, sticky="ew")
        menu_colors = {
            "background": DARK_THEME["surface"], "foreground": DARK_THEME["text"],
            "activebackground": DARK_THEME["selection"], "activeforeground": "#ffffff",
            "disabledforeground": DARK_THEME["muted"], "borderwidth": 0,
        }
        self.file_menu = tk.Menu(bar, tearoff=False, **menu_colors)
        self.file_menu.add_command(label="Novo", accelerator="Ctrl+N", command=self.new_file)
        self.file_menu.add_command(label="Abrir...", accelerator="Ctrl+O", command=self.open_file)
        self.file_menu.add_command(label="Salvar", accelerator="Ctrl+S", command=self.save_file)
        self.file_menu.add_command(label="Salvar como...", accelerator="Ctrl+Shift+S", command=self.save_as)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Sair", command=self.close)
        ttk.Menubutton(bar, text="Arquivo", menu=self.file_menu, underline=0).pack(side="left")

        self.compile_menu = tk.Menu(bar, tearoff=False, **menu_colors)
        self.compile_menu.add_command(label="Compilar", accelerator="F9", command=self.compile)
        ttk.Menubutton(bar, text="Compilar", menu=self.compile_menu, underline=0).pack(side="left")

    def _create_widgets(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(2, weight=1)

        toolbar = ttk.Frame(self.root, padding=(14, 10))
        toolbar.grid(row=1, column=0, sticky="ew")
        ttk.Label(toolbar, text="IDE Compiladores", style="Heading.TLabel", font=("TkDefaultFont", 12, "bold")).pack(side="left")
        self.compile_button = ttk.Button(toolbar, text="Compilar  (F9)", command=self.compile, padding=(18, 6))
        self.compile_button.pack(side="right")

        self.panes = ttk.Panedwindow(self.root, orient="vertical")
        self.panes.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 8))

        editor_frame = ttk.Frame(self.panes)
        editor_frame.columnconfigure(0, weight=1)
        editor_frame.rowconfigure(1, weight=1)
        ttk.Label(editor_frame, text="Código-fonte", padding=(0, 4, 0, 8)).grid(row=0, column=0, sticky="w")
        self.editor = tk.Text(
            editor_frame, font=self.code_font, wrap="none", undo=True,
            width=1, height=20, padx=12, pady=10, borderwidth=0, relief="flat",
            background=DARK_THEME["editor"], foreground=DARK_THEME["text"],
            insertbackground=DARK_THEME["text"], highlightthickness=1,
            highlightbackground=DARK_THEME["border"], highlightcolor=DARK_THEME["accent"],
            selectbackground=DARK_THEME["selection"], selectforeground="#ffffff",
            inactiveselectbackground=DARK_THEME["selection"],
            tabs=(self.code_font.measure("    "),), tabstyle="wordprocessor",
        )
        self.editor.grid(row=1, column=0, sticky="nsew")
        editor_y = ttk.Scrollbar(editor_frame, orient="vertical", command=self.editor.yview)
        editor_y.grid(row=1, column=1, sticky="ns")
        editor_x = ttk.Scrollbar(editor_frame, orient="horizontal", command=self.editor.xview)
        editor_x.grid(row=2, column=0, sticky="ew")
        self.editor.configure(yscrollcommand=editor_y.set, xscrollcommand=editor_x.set)
        self.editor.tag_configure("error_line", background=DARK_THEME["error_line"])
        self.panes.add(editor_frame, weight=4)

        self.results_tabs = ttk.Notebook(self.panes)
        messages_frame = ttk.Frame(self.results_tabs)
        self.results_tabs.add(messages_frame, text="Mensagens")
        messages_frame.columnconfigure(0, weight=1)
        messages_frame.rowconfigure(1, weight=1)
        ttk.Label(messages_frame, text="Mensagens", padding=(0, 8)).grid(row=0, column=0, sticky="w")
        self.messages = tk.Text(
            messages_frame, font=self.code_font, wrap="word", state="disabled",
            width=1, height=6, padx=12, pady=10, borderwidth=0, relief="flat",
            background=DARK_THEME["messages"], foreground=DARK_THEME["text"],
            highlightthickness=1, highlightbackground=DARK_THEME["border"],
            highlightcolor=DARK_THEME["accent"], selectbackground=DARK_THEME["selection"],
            selectforeground="#ffffff", inactiveselectbackground=DARK_THEME["selection"],
        )
        self.messages.grid(row=1, column=0, sticky="nsew")
        messages_y = ttk.Scrollbar(messages_frame, orient="vertical", command=self.messages.yview)
        messages_y.grid(row=1, column=1, sticky="ns")
        self.messages.configure(yscrollcommand=messages_y.set)
        self.messages.tag_configure("success", foreground=DARK_THEME["success"])
        self.messages.tag_configure("error", foreground=DARK_THEME["error"])
        self.messages.tag_configure("warning", foreground=DARK_THEME["warning"])
        self._create_symbol_table()
        self._create_assembly_panel()
        self.panes.add(self.results_tabs, weight=1)

        self.status = tk.StringVar(value="Pronto. F9 para compilar.")
        ttk.Label(self.root, textvariable=self.status, padding=(14, 5), anchor="w").grid(
            row=3, column=0, sticky="ew",
        )

    def _create_assembly_panel(self) -> None:
        frame = ttk.Frame(self.results_tabs)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)
        self.results_tabs.add(frame, text="Código Assembly")
        toolbar = ttk.Frame(frame, padding=(4, 6))
        toolbar.grid(row=0, column=0, sticky="ew")
        ttk.Button(toolbar, text="Copiar ASM", command=self.copy_assembly).pack(side="left", padx=(0, 6))
        ttk.Button(toolbar, text="Salvar ASM", command=self.save_assembly).pack(side="left")
        self.assembly = tk.Text(
            frame, font=self.code_font, wrap="none", state="disabled", width=1, height=6,
            padx=12, pady=10, borderwidth=0, background=DARK_THEME["editor"],
            foreground=DARK_THEME["text"], selectbackground=DARK_THEME["selection"],
            selectforeground="#ffffff", inactiveselectbackground=DARK_THEME["selection"],
        )
        self.assembly.grid(row=1, column=0, sticky="nsew")
        scroll_y = ttk.Scrollbar(frame, orient="vertical", command=self.assembly.yview)
        scroll_y.grid(row=1, column=1, sticky="ns")
        scroll_x = ttk.Scrollbar(frame, orient="horizontal", command=self.assembly.xview)
        scroll_x.grid(row=2, column=0, sticky="ew")
        self.assembly.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

    def _show_assembly(self, code: str) -> None:
        self.assembly.configure(state="normal")
        self.assembly.delete("1.0", "end")
        self.assembly.insert("1.0", code)
        self.assembly.configure(state="disabled")

    def _assembly_for_export(self) -> str:
        if self.editor.edit_modified():
            self._show_assembly("")
        code = self.assembly.get("1.0", "end-1c")
        if not code:
            messagebox.showinfo("Código Assembly", "Nenhum código assembly disponível. Compile um programa compatível com BIP IV.", parent=self.root)
        return code

    def copy_assembly(self) -> bool:
        code = self._assembly_for_export()
        if not code:
            return False
        self.root.clipboard_clear()
        self.root.clipboard_append(code)
        self.status.set("Código assembly copiado.")
        return True

    def save_assembly(self) -> bool:
        code = self._assembly_for_export()
        if not code:
            return False
        filename = filedialog.asksaveasfilename(
            parent=self.root, title="Salvar código Assembly BIP IV", defaultextension=".asm",
            filetypes=[("Assembly BIP", "*.asm"), ("Todos os arquivos", "*.*")],
            initialfile=(self.current_file.stem if self.current_file else "programa") + ".asm",
        )
        if not filename:
            return False
        path = Path(filename)
        if self.current_file and path.resolve() == self.current_file.resolve():
            messagebox.showerror("Salvar ASM", "Escolha um arquivo diferente do código-fonte original.", parent=self.root)
            return False
        try:
            path.write_text(code, encoding="utf-8", newline="\n")
        except (OSError, UnicodeError) as error:
            self._file_error("salvar ASM", error)
            return False
        self.status.set(f"Assembly salvo: {path.name}")
        return True

    def _create_symbol_table(self) -> None:
        frame = ttk.Frame(self.results_tabs)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)
        self.results_tabs.add(frame, text="Tabela de Símbolos")
        self.symbol_status = tk.StringVar(value="Nenhuma compilação realizada.")
        ttk.Label(frame, textvariable=self.symbol_status, padding=(4, 8)).grid(row=0, column=0, sticky="w")
        columns = ("name", "type", "modality", "scope", "used", "initialized", "line", "column", "detail")
        self.symbol_tree = ttk.Treeview(frame, columns=columns, show="headings", height=6)
        for key, title, width in zip(columns,
                                    ("Identificador", "Tipo", "Modalidade", "Escopo", "Utilizado",
                                     "Inicializado", "Linha", "Coluna", "Vetor / assinatura"),
                                    (130, 75, 110, 240, 85, 145, 60, 65, 240)):
            self.symbol_tree.heading(key, text=title)
            self.symbol_tree.column(key, width=width, minwidth=50, stretch=False)
        self.symbol_tree.grid(row=1, column=0, sticky="nsew")
        scroll_y = ttk.Scrollbar(frame, orient="vertical", command=self.symbol_tree.yview)
        scroll_y.grid(row=1, column=1, sticky="ns")
        scroll_x = ttk.Scrollbar(frame, orient="horizontal", command=self.symbol_tree.xview)
        scroll_x.grid(row=2, column=0, sticky="ew")
        self.symbol_tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

    def _show_symbols(self, result) -> None:
        for symbol in result.symbols:
            initialized = "Sim" if symbol.initialized else "Não"
            if symbol.is_array and not symbol.initialized and symbol.initialized_elements:
                initialized = "Parcial: " + ", ".join(map(str, symbol.initialized_elements))
            if result.symbols_partial:
                initialized = "Não concluído"
            detail = symbol.signature
            if symbol.is_array:
                detail = f"Tamanho: {symbol.size if symbol.size is not None else 'dinâmico/não especificado'}"
            self.symbol_tree.insert("", "end", iid=str(symbol.uid), values=(
                symbol.name, symbol.type, symbol.modality, symbol.scope,
                "Sim" if symbol.used else "Não", initialized, symbol.line or "", symbol.column or "", detail,
            ))
        if result.kind == "empty":
            self.symbol_status.set("Nenhum código-fonte informado.")
        elif result.symbols_partial:
            self.symbol_status.set(f"Tabela parcial — análise interrompida; {len(result.symbols)} símbolo(s).")
        else:
            self.symbol_status.set(f"Análise concluída — {len(result.symbols)} símbolo(s), incluindo escopos encerrados.")

    def _bind_shortcuts(self) -> None:
        for sequence, command in (
            ("<F9>", self.compile), ("<Control-n>", self.new_file),
            ("<Control-o>", self.open_file), ("<Control-s>", self.save_file),
            ("<Control-Shift-S>", self.save_as),
        ):
            def invoke(event: tk.Event, action=command) -> str:
                action()
                return "break"
            # Intercepta antes dos atalhos nativos de Text, como Ctrl+O,
            # que normalmente insere uma quebra de linha no editor.
            for widget in (self.root, self.editor, self.messages, self.assembly):
                widget.bind(sequence, invoke)

    def _insert_tab(self, event: tk.Event) -> str:
        self.editor.edit_separator()
        if self.editor.tag_ranges("sel"):
            self.editor.delete("sel.first", "sel.last")
        self.editor.insert("insert", "\t")
        self.editor.edit_separator()
        return "break"

    def _source(self) -> str:
        return self.editor.get("1.0", "end-1c")

    def _on_modified(self, event: tk.Event) -> None:
        if self.editor.edit_modified():
            self.dirty = True
            self.editor.edit_modified(False)
            self.editor.tag_remove("error_line", "1.0", "end")
            self.status.set("Código alterado. F9 para compilar.")
            self._show_assembly("")
            if self.symbol_tree.get_children():
                self.symbol_status.set("Resultado da última compilação — código alterado. F9 para atualizar.")
            self._update_title()

    def _update_title(self) -> None:
        filename = self.current_file.name if self.current_file else "Novo arquivo"
        marker = " *" if self.dirty else ""
        self.root.title(f"IDE Compiladores - {filename}{marker}")

    def _clear_output(self) -> None:
        self._show_assembly("")
        self.editor.tag_remove("error_line", "1.0", "end")
        self._show_message("")
        rows = self.symbol_tree.get_children()
        if rows:
            self.symbol_tree.delete(*rows)
        self.symbol_status.set("Nenhuma compilação realizada.")

    def _show_message(self, message: str, tag: str = "") -> None:
        self.messages.configure(state="normal")
        self.messages.delete("1.0", "end")
        self.messages.insert("1.0", message, (tag,) if tag else ())
        self.messages.configure(state="disabled")
        self.messages.see("1.0")

    def compile(self) -> None:
        # Consome o evento pendente de edição antes de aplicar o novo destaque.
        if self.editor.edit_modified():
            self.dirty = True
            self.editor.edit_modified(False)
            self._update_title()
        self._clear_output()
        result = compile_source(self._source())
        tag = "success" if result.kind == "success" else "error" if result.kind.endswith("error") else ""
        self._show_message(result.message, tag)
        if result.warnings:
            self.messages.configure(state="normal")
            for warning in result.warnings:
                self.messages.insert("end", "\n" + warning.formatted, ("warning",))
            self.messages.configure(state="disabled")
        self._show_symbols(result)
        self._show_assembly(result.assembly_code)
        self.results_tabs.select(0)
        count = f" {len(result.warnings)} aviso(s)." if result.warnings else ""
        self.status.set(result.message.splitlines()[0] + count)
        if result.line is not None:
            start = f"{result.line}.0"
            self.editor.tag_add("error_line", start, f"{start} lineend + 1c")
            self.editor.see(start)

    def _confirm_discard(self) -> bool:
        if not self.dirty and not self.editor.edit_modified():
            return True
        answer = messagebox.askyesnocancel(
            "Alterações não salvas", "Deseja salvar as alterações antes de continuar?", parent=self.root,
        )
        if answer is None:
            return False
        return self.save_file() if answer else True

    def _set_document(self, source: str, path: Path | None) -> None:
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", source)
        self.editor.mark_set("insert", "1.0")
        self.editor.edit_reset()
        self.editor.edit_modified(False)
        self.current_file = path
        self.dirty = False
        self._clear_output()
        self._update_title()
        self.editor.focus_set()

    def new_file(self) -> None:
        if self._confirm_discard():
            self._set_document("", None)
            self.status.set("Novo arquivo. F9 para compilar.")

    def open_file(self) -> None:
        if not self._confirm_discard():
            return
        filename = filedialog.askopenfilename(parent=self.root, title="Abrir código-fonte", filetypes=FILE_TYPES)
        if not filename:
            return
        path = Path(filename)
        try:
            source = path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError) as error:
            self._file_error("abrir", error)
            return
        self._set_document(source, path)
        self.status.set(f"Arquivo aberto: {path.name}")

    def save_file(self) -> bool:
        if self.current_file is None:
            return self.save_as()
        return self._write_file(self.current_file)

    def save_as(self) -> bool:
        options = {"initialfile": self.current_file.name, "initialdir": str(self.current_file.parent)} if self.current_file else {"initialfile": "programa.src"}
        filename = filedialog.asksaveasfilename(
            parent=self.root, title="Salvar código-fonte como", defaultextension=".src",
            filetypes=FILE_TYPES, **options,
        )
        return self._write_file(Path(filename)) if filename else False

    def _write_file(self, path: Path) -> bool:
        try:
            path.write_text(self._source(), encoding="utf-8")
        except (OSError, UnicodeError) as error:
            self._file_error("salvar", error)
            return False
        self.current_file = path
        self.dirty = False
        self.editor.edit_modified(False)
        self._update_title()
        self.status.set(f"Arquivo salvo: {path.name}")
        return True

    def _file_error(self, action: str, error: Exception) -> None:
        self._show_message(f"Não foi possível {action} o arquivo:\n{error}", "error")
        self.status.set(f"Falha ao {action} o arquivo.")

    def close(self) -> None:
        if self._confirm_discard():
            self.root.destroy()


def main() -> None:
    root = tk.Tk()
    IDEApp(root)
    root.mainloop()
