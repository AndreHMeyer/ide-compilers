from pathlib import Path
import runpy
from tempfile import TemporaryDirectory
import tkinter as tk
from tkinter import font
import unittest
from unittest.mock import patch

from ide.app import IDEApp
from ide.compiler_service import compile_source
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
                    result = compile_source(path.read_text(encoding="utf-8"))
                    self.assertTrue(result.analysis_success)
                    self.assertTrue(self.output().startswith(result.message))
                    self.assertEqual(self.app.assembly.get("1.0", "end-1c"), result.assembly_code)

    def test_error_highlight_is_cleared_by_next_compilation(self) -> None:
        self.enter("int a;\na = @;")
        self.app.compile()
        self.assertEqual(str(self.app.editor.tag_ranges("error_line")[0]), "2.0")
        self.enter("int a;")
        self.app.compile_menu.invoke(0)
        self.assertFalse(self.app.editor.tag_ranges("error_line"))
        self.assertTrue(self.output().startswith("Compilação realizada com sucesso."))
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
        self.assertIn("Erro de geração de código", self.output())
        self.assertIn("string", self.output())
        self.assertNotIn("Tabela parcial", self.app.symbol_status.get())

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
        self.assertTrue(self.output().startswith("Compilação realizada com sucesso."))
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

    def test_real_symbol_table_and_scope_history(self) -> None:
        source = "int x=1;{int x=2;print(x);}print(x);"
        self.enter(source)
        self.app.compile_button.invoke()
        expected = compile_source(source).symbols
        rows = self.app.symbol_tree.get_children()
        self.assertEqual(len(rows), len(expected))
        for row, symbol in zip(rows, expected):
            values = self.app.symbol_tree.item(row, "values")
            self.assertEqual(values[:4], (symbol.name, symbol.type, symbol.modality, symbol.scope))
            self.assertEqual(values[4:6], ("Sim", "Sim"))
        self.assertIn("Análise concluída", self.app.symbol_status.get())
        self.app.results_tabs.select(1)
        self.root.update()
        self.assertEqual(self.app.results_tabs.tab(1, "text"), "Tabela de Símbolos")
        self.assertTrue(self.app.symbol_tree.cget("xscrollcommand"))
        self.assertTrue(self.app.symbol_tree.cget("yscrollcommand"))

    def test_semantic_warning_is_nonblocking_and_has_own_color(self) -> None:
        self.enter("int x;print(x);")
        self.app.compile()
        self.assertIn("Compilação realizada com sucesso.", self.output())
        self.assertIn("Aviso semântico", self.output())
        self.assertTrue(self.app.messages.tag_ranges("warning"))
        self.assertFalse(self.app.editor.tag_ranges("error_line"))
        self.assertIn("1 aviso(s)", self.app.status.get())

    def test_semantic_error_highlight_partial_table_and_reset(self) -> None:
        self.enter("int old=1;print(old);")
        self.app.compile()
        self.enter('int x;\nx="abc";')
        self.app.compile()
        self.assertIn("Erro semântico na linha 2, coluna 1", self.output())
        self.assertEqual(str(self.app.editor.tag_ranges("error_line")[0]), "2.0")
        self.assertIn("Tabela parcial", self.app.symbol_status.get())
        rows = self.app.symbol_tree.get_children()
        self.assertEqual(len(rows), 1)
        self.assertEqual(self.app.symbol_tree.item(rows[0], "values")[0], "x")
        self.assertEqual(self.app.symbol_tree.item(rows[0], "values")[5], "Não concluído")
        self.enter("int new=2;print(new);")
        self.app.compile()
        self.assertNotIn("Tabela parcial", self.app.symbol_status.get())
        self.assertNotIn("Aviso", self.output())
        self.assertFalse(self.app.editor.tag_ranges("error_line"))
        self.enter("")
        self.app.compile()
        self.assertFalse(self.app.symbol_tree.get_children())

    def test_new_document_clears_symbols(self) -> None:
        self.enter("int x;")
        self.app.compile()
        with patch("ide.app.messagebox.askyesnocancel", return_value=False):
            self.app.new_file()
        self.assertFalse(self.app.symbol_tree.get_children())
        self.assertEqual(self.app.symbol_status.get(), "Nenhuma compilação realizada.")

    def test_edits_label_previous_compilation(self) -> None:
        self.enter("int x;")
        self.app.compile()
        self.enter("int y;")
        self.assertIn("código alterado", self.app.symbol_status.get())

    def test_assembly_tab_font_scrolling_and_read_only(self) -> None:
        self.enter("int x=10;print(x);")
        self.app.compile()
        self.assertEqual(self.app.results_tabs.tab(2, "text"), "Código Assembly")
        self.app.results_tabs.select(2)
        self.root.update()
        widget = self.app.assembly
        actual = font.Font(root=self.root, font=widget.cget("font"))
        self.assertEqual(actual.actual("size"), 14)
        self.assertEqual(actual.metrics("fixed"), 1)
        self.assertEqual(widget.cget("wrap"), "none")
        self.assertTrue(widget.cget("xscrollcommand"))
        self.assertTrue(widget.cget("yscrollcommand"))
        expected = compile_source(self.app._source()).assembly_code
        widget.insert("1.0", "invalid")
        self.assertEqual(widget.get("1.0", "end-1c"), expected)
        self.assertEqual(widget.cget("state"), "disabled")

    def test_copy_and_export_exact_assembly(self) -> None:
        self.enter("int v[3];v[1]=20;print(v[1]);")
        source_path = self.folder / "original.src"
        self.app._write_file(source_path)
        self.app.compile()
        code = self.app.assembly.get("1.0", "end-1c")
        self.assertTrue(self.app.copy_assembly())
        self.assertEqual(self.root.clipboard_get(), code)
        output_path = self.folder / "programa.asm"
        with patch("ide.app.filedialog.asksaveasfilename", return_value=str(output_path)):
            self.assertTrue(self.app.save_assembly())
        self.assertEqual(output_path.read_bytes(), code.encode("utf-8"))
        self.assertEqual(self.app.current_file, source_path)
        self.assertEqual(source_path.read_text(encoding="utf-8"), self.app._source())
        self.assertFalse(self.app.dirty)

    def test_export_does_not_overwrite_source(self) -> None:
        self.enter("print(10);")
        path = self.folder / "program.src"
        self.app._write_file(path)
        self.app.compile()
        with patch("ide.app.filedialog.asksaveasfilename", return_value=str(path)), patch(
            "ide.app.messagebox.showerror",
        ) as error:
            self.assertFalse(self.app.save_assembly())
        error.assert_called_once()
        self.assertEqual(path.read_text(encoding="utf-8"), "print(10);")

    def test_no_assembly_copy_or_export_before_success(self) -> None:
        with patch("ide.app.messagebox.showinfo") as info, patch(
            "ide.app.filedialog.asksaveasfilename",
        ) as dialog:
            self.assertFalse(self.app.copy_assembly())
            self.assertFalse(self.app.save_assembly())
        self.assertEqual(info.call_count, 2)
        dialog.assert_not_called()

    def test_failed_generation_clears_old_assembly_and_keeps_complete_symbols(self) -> None:
        self.enter("int a=10;print(a);")
        self.app.compile()
        self.assertTrue(self.app.assembly.get("1.0", "end-1c"))
        self.enter("int a=10;\nprint(a*2);")
        self.app.compile()
        self.assertFalse(self.app.assembly.get("1.0", "end-1c"))
        self.assertIn("Erro de geração de código", self.output())
        self.assertNotIn("Tabela parcial", self.app.symbol_status.get())
        self.assertTrue(self.app.symbol_tree.get_children())
        self.assertEqual(str(self.app.editor.tag_ranges("error_line")[0]), "2.0")
        self.enter("int a=;")
        self.app.compile()
        self.assertFalse(self.app.assembly.get("1.0", "end-1c"))

    def test_edit_new_and_open_clear_assembly(self) -> None:
        self.enter("print(10);")
        self.app.compile()
        self.enter("print(20);")
        self.assertFalse(self.app.assembly.get("1.0", "end-1c"))
        self.app.compile()
        with patch("ide.app.messagebox.askyesnocancel", return_value=False):
            self.app.new_file()
        self.assertFalse(self.app.assembly.get("1.0", "end-1c"))
        self.enter("print(10);")
        self.app.compile()
        path = self.folder / "other.src"
        path.write_text("print(30);", encoding="utf-8")
        with patch("ide.app.messagebox.askyesnocancel", return_value=False), patch(
            "ide.app.filedialog.askopenfilename", return_value=str(path),
        ):
            self.app.open_file()
        self.assertFalse(self.app.assembly.get("1.0", "end-1c"))

    def test_assembly_export_cancel_and_file_failure(self) -> None:
        self.enter("print(10);")
        self.app.compile()
        with patch("ide.app.filedialog.asksaveasfilename", return_value=""):
            self.assertFalse(self.app.save_assembly())
        with patch("ide.app.filedialog.asksaveasfilename", return_value=str(self.folder / "absent" / "x.asm")):
            self.assertFalse(self.app.save_assembly())
        self.assertIn("Não foi possível salvar ASM", self.output())
        self.assertTrue(self.app.assembly.get("1.0", "end-1c"))

    def test_main_entry_point_starts_real_event_loop(self) -> None:
        created = []

        def create_app(root):
            app = IDEApp(root)
            created.append(app)

            def finish():
                root.quit()
                root.destroy()

            root.after(100, finish)
            return app

        with patch("ide.app.IDEApp", side_effect=create_app):
            runpy.run_path(str(Path(__file__).resolve().parents[1] / "main.py"), run_name="__main__")
        self.assertEqual(len(created), 1)


if __name__ == "__main__":
    unittest.main()
