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

        messages_frame = ttk.Frame(self.panes)
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
        self.panes.add(messages_frame, weight=1)

        self.status = tk.StringVar(value="Pronto. F9 para compilar.")
        ttk.Label(self.root, textvariable=self.status, padding=(14, 5), anchor="w").grid(
            row=3, column=0, sticky="ew",
        )

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
            for widget in (self.root, self.editor, self.messages):
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
            self._update_title()

    def _update_title(self) -> None:
        filename = self.current_file.name if self.current_file else "Novo arquivo"
        marker = " *" if self.dirty else ""
        self.root.title(f"IDE Compiladores - {filename}{marker}")

    def _clear_output(self) -> None:
        self.editor.tag_remove("error_line", "1.0", "end")
        self._show_message("")

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
        self.status.set(result.message.splitlines()[0])
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
