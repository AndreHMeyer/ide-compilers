from pathlib import Path
from tempfile import TemporaryDirectory
import tkinter as tk
from tkinter import font
import unittest
from unittest.mock import patch

from ide.app import IDEApp
from tests.test_compiler_service import EXAMPLES


class IDEAppTests(unittest.TestCase):
    """Widgets e arquivos reais; somente a escolha nos diálogos é simulada."""

    def setUp(self) -> None:
        self.root = tk.Tk()
        self.app = IDEApp(self.root)
        self.root.update()
        self.root.withdraw()
        self.temp = TemporaryDirectory()
        self.folder = Path(self.temp.name)

    def tearDown(self) -> None:
        try:
            if self.root.winfo_exists():
                self.root.destroy()
        except tk.TclError:
            pass
        self.temp.cleanup()

    def enter(self, source: str) -> None:
        self.app.editor.delete("1.0", "end")
        self.app.editor.insert("1.0", source)
        self.root.update()

    def output(self) -> str:
        return self.app.messages.get("1.0", "end-1c")

    def test_fonts_size_fourteen_and_read_only_messages(self) -> None:
        for widget in (self.app.editor, self.app.messages):
            actual = font.Font(root=self.root, font=widget.cget("font"))
            self.assertEqual(actual.actual("size"), 14)
            self.assertEqual(actual.metrics("fixed"), 1)
        self.app.messages.insert("1.0", "não deve entrar")
        self.assertEqual(self.output(), "")
        self.assertEqual(self.app.messages.cget("state"), "disabled")

    def test_all_examples_through_compile_button(self) -> None:
        for path in sorted(EXAMPLES.glob("*.src")):
            with self.subTest(example=path.name):
                self.enter(path.read_text(encoding="utf-8"))
                self.app.compile_button.invoke()
                if path.name.startswith("11_"):
                    self.assertIn("Erro sintático na linha 1, coluna 9", self.output())
                elif path.name.startswith("12_"):
                    self.assertIn("Erro léxico na linha 2, coluna 5", self.output())
                else:
                    self.assertEqual(self.output(), "Compilação realizada com sucesso.")

    def test_error_highlight_is_cleared_by_next_compilation(self) -> None:
        self.enter("int a;\na = @;")
        self.app.compile()
        self.assertEqual(str(self.app.editor.tag_ranges("error_line")[0]), "2.0")
        self.enter("int a;")
        self.app.compile_menu.invoke(0)
        self.assertFalse(self.app.editor.tag_ranges("error_line"))
        self.assertEqual(self.output(), "Compilação realizada com sucesso.")
        self.enter("")
        self.app.compile()
        self.assertEqual(self.output(), "Nenhum código-fonte informado.")

    def test_new_open_save_and_save_as(self) -> None:
        first = self.folder / "primeiro.src"
        second = self.folder / "segundo.txt"
        self.enter('int a;\nprint("Olá");\n')
        with patch("ide.app.filedialog.asksaveasfilename", return_value=str(first)):
            self.assertTrue(self.app.save_file())
        self.assertEqual(first.read_text(encoding="utf-8"), self.app._source())
        self.assertEqual(self.root.title(), "IDE Compiladores - primeiro.src")
        self.enter("int b;\n")
        self.assertTrue(self.app.save_file())
        self.assertEqual(first.read_text(encoding="utf-8"), "int b;\n")
        with patch("ide.app.filedialog.asksaveasfilename", return_value=str(second)):
            self.assertTrue(self.app.save_as())
        self.assertEqual(second.read_text(encoding="utf-8"), "int b;\n")
        self.app.compile()
        self.app.file_menu.invoke(0)
        self.assertEqual(self.app._source(), "")
        self.assertEqual(self.output(), "")
        self.assertIsNone(self.app.current_file)
        self.assertEqual(self.root.title(), "IDE Compiladores - Novo arquivo")
        with patch("ide.app.filedialog.askopenfilename", return_value=str(first)):
            self.app.file_menu.invoke(1)
        self.assertEqual(self.app._source(), "int b;\n")
        self.assertEqual(self.app.current_file, first)
        self.assertFalse(self.app.dirty)

    def test_cancel_preserves_unsaved_work(self) -> None:
        self.enter("int a;")
        with patch("ide.app.messagebox.askyesnocancel", return_value=None):
            self.app.new_file()
            self.app.open_file()
            self.app.close()
        self.assertEqual(self.app._source(), "int a;")
        self.assertTrue(self.root.winfo_exists())
        with patch("ide.app.messagebox.askyesnocancel", return_value=True), patch(
            "ide.app.filedialog.asksaveasfilename", return_value="",
        ):
            self.app.new_file()
        self.assertEqual(self.app._source(), "int a;")

    def test_save_before_new_and_discard_before_exit(self) -> None:
        path = self.folder / "salvo.src"
        self.enter("int a;")
        with patch("ide.app.messagebox.askyesnocancel", return_value=True), patch(
            "ide.app.filedialog.asksaveasfilename", return_value=str(path),
        ):
            self.app.new_file()
        self.assertEqual(path.read_text(encoding="utf-8"), "int a;")
        self.assertEqual(self.app._source(), "")
        self.enter("int b;")
        with patch("ide.app.messagebox.askyesnocancel", return_value=False):
            self.app.close()

    def test_file_dialog_cancellation(self) -> None:
        with patch("ide.app.filedialog.askopenfilename", return_value=""):
            self.app.open_file()
        with patch("ide.app.filedialog.asksaveasfilename", return_value=""):
            self.assertFalse(self.app.save_as())
        self.assertIsNone(self.app.current_file)

    def test_file_failures_preserve_document_and_current_path(self) -> None:
        self.enter("int a;")
        self.app.dirty = False
        with patch("ide.app.filedialog.askopenfilename", return_value=str(self.folder / "ausente.src")):
            self.app.open_file()
        self.assertIn("Não foi possível abrir", self.output())
        self.assertEqual(self.app._source(), "int a;")
        with patch("ide.app.filedialog.asksaveasfilename", return_value=str(self.folder / "ausente" / "a.src")):
            self.assertFalse(self.app.save_as())
        self.assertIn("Não foi possível salvar", self.output())
        self.assertIsNone(self.app.current_file)
        self.assertEqual(self.app._source(), "int a;")

    def test_utf8_bom_and_windows_line_endings(self) -> None:
        path = self.folder / "acentos.src"
        path.write_bytes('\ufeffint a;\r\nprint("Olá");\r\n'.encode("utf-8"))
        with patch("ide.app.filedialog.askopenfilename", return_value=str(path)):
            self.app.open_file()
        self.assertEqual(self.app._source(), 'int a;\nprint("Olá");\n')
        self.app.compile()
        self.assertEqual(self.output(), "Compilação realizada com sucesso.")

    def test_invalid_utf8_does_not_replace_open_document(self) -> None:
        path = self.folder / "invalido.src"
        path.write_bytes(b"\xff\xfe")
        with patch("ide.app.filedialog.askopenfilename", return_value=str(path)):
            self.app.open_file()
        self.assertIn("Não foi possível abrir", self.output())
        self.assertIsNone(self.app.current_file)

    def test_f9_and_tab(self) -> None:
        self.root.deiconify()
        self.root.update()
        self.app.editor.focus_force()
        self.enter("int a;")
        self.app.editor.event_generate("<F9>")
        self.root.update()
        self.assertEqual(self.output(), "Compilação realizada com sucesso.")
        self.app.editor.mark_set("insert", "1.0")
        self.app.editor.event_generate("<Tab>")
        self.root.update()
        self.assertEqual(self.app._source(), "\tint a;")

    def test_panes_resize_with_window(self) -> None:
        self.root.deiconify()
        self.root.geometry("800x550")
        self.root.update()
        widths = self.app.editor.winfo_width(), self.app.messages.winfo_width()
        heights = self.app.editor.winfo_height(), self.app.messages.winfo_height()
        self.root.geometry("1100x760")
        self.root.update()
        self.assertGreater(self.app.editor.winfo_width(), widths[0])
        self.assertGreater(self.app.messages.winfo_width(), widths[1])
        self.assertGreater(self.app.editor.winfo_height(), heights[0])
        self.assertGreater(self.app.messages.winfo_height(), heights[1])
        self.assertGreater(self.app.editor.winfo_height(), self.app.messages.winfo_height())

    def test_file_shortcuts_do_not_insert_text(self) -> None:
        self.root.deiconify()
        self.root.update()
        self.app.editor.focus_force()
        with patch("ide.app.filedialog.askopenfilename", return_value=""), patch(
            "ide.app.messagebox.askyesnocancel",
        ) as confirm:
            self.app.editor.event_generate("<Control-o>")
            self.root.update()
        confirm.assert_not_called()
        self.assertEqual(self.app._source(), "")
        self.assertFalse(self.app.dirty)

        self.enter("int a;")
        first = self.folder / "atalho.src"
        second = self.folder / "copia.src"
        for sequence, path in (("<Control-s>", first), ("<Control-Shift-S>", second)):
            with patch("ide.app.filedialog.asksaveasfilename", return_value=str(path)):
                self.app.editor.event_generate(sequence)
                self.root.update()
            self.assertEqual(path.read_text(encoding="utf-8"), "int a;")
        self.app.editor.event_generate("<Control-n>")
        self.root.update()
        self.assertEqual(self.app._source(), "")
        self.assertIsNone(self.app.current_file)


if __name__ == "__main__":
    unittest.main()
