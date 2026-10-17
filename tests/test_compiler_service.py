from pathlib import Path
import unittest
from unittest.mock import patch

from ide.compiler_service import compile_source, position_to_line_column


EXAMPLES = Path(__file__).resolve().parent.parent / "exemplos"


class CompilerServiceTests(unittest.TestCase):
    def test_thirteen_examples_with_current_webgals_grammar(self) -> None:
        examples = sorted(EXAMPLES.glob("*.src"))
        self.assertEqual(len(examples), 13)
        for path in examples:
            with self.subTest(example=path.name):
                expected = "success"
                if path.name.startswith("11_"):
                    expected = "syntactic_error"
                elif path.name.startswith("12_"):
                    expected = "lexical_error"
                result = compile_source(path.read_text(encoding="utf-8"))
                self.assertEqual(result.kind, expected, result.message)
                if expected == "success":
                    self.assertEqual(result.message, "Compilação realizada com sucesso.")

    def test_lexical_error_position(self) -> None:
        result = compile_source("int a;\na = @;")
        self.assertEqual(result.kind, "lexical_error")
        self.assertEqual((result.line, result.column), (2, 5))
        self.assertIn("Caractere não esperado", result.message)

    def test_syntactic_error_position_and_actual_token(self) -> None:
        result = compile_source("int a;\na = ;")
        self.assertEqual(result.kind, "syntactic_error")
        self.assertEqual((result.line, result.column), (2, 5))
        self.assertIn("Token inesperado: ';'", result.message)
        self.assertIn("Mensagem do WebGALS: Erro estado", result.message)

    def test_end_of_input_uses_position_reported_by_parser(self) -> None:
        result = compile_source("int a\n  ")
        self.assertEqual(result.kind, "syntactic_error")
        self.assertEqual((result.line, result.column), (1, 6))
        self.assertIn("Fim do código-fonte inesperado", result.message)

    def test_empty_editor(self) -> None:
        for source in ("", " \n\t\r\n"):
            with self.subTest(source=source):
                result = compile_source(source)
                self.assertEqual(result.kind, "empty")
                self.assertEqual(result.message, "Nenhum código-fonte informado.")

    def test_incomplete_tokens_are_lexical_errors(self) -> None:
        for source in ('print("aberto;', "int a; /* aberto", "char a; a = 'x;"):
            with self.subTest(source=source):
                result = compile_source(source)
                self.assertEqual(result.kind, "lexical_error", result.message)

    def test_unclosed_comment_immediately_at_end_of_input(self) -> None:
        for source in ("int a; /*", "int a; /**"):
            with self.subTest(source=source):
                result = compile_source(source)
                self.assertEqual(result.kind, "lexical_error", result.message)
                self.assertEqual((result.line, result.column), (1, 8))
                self.assertIn("Erro identificando <ignorar>", result.message)

    def test_scanner_backtracks_to_last_accepting_state(self) -> None:
        # A tabela reconhece DECIMAL e PONTO; um REAL precisa de dígitos após o ponto.
        result = compile_source("int a; a = 1.;")
        self.assertEqual(result.kind, "syntactic_error", result.message)
        self.assertIn("Token inesperado: '.'", result.message)
        self.assertEqual((result.line, result.column), (1, 13))

    def test_current_input_print_and_bool_syntax(self) -> None:
        source = (
            "bool ativo; ativo = true;\n"
            "int a, vetor[10];\n"
            "input(a, vetor[0]);\n"
            'print("Valor", a, vetor[0], ativo);'
        )
        result = compile_source(source)
        self.assertEqual(result.kind, "success", result.message)

    def test_legacy_io_syntax_is_not_silently_translated(self) -> None:
        for source in ('cout << "Valor";', "int a; cin >> a;"):
            with self.subTest(source=source):
                self.assertEqual(compile_source(source).kind, "syntactic_error")

    def test_character_outside_generated_alphabet_is_lexical_error(self) -> None:
        result = compile_source("int a;\na = λ;")
        self.assertEqual(result.kind, "lexical_error")
        self.assertEqual((result.line, result.column), (2, 5))

    def test_entire_input_is_analyzed(self) -> None:
        self.assertEqual(compile_source("int a; @").kind, "lexical_error")
        self.assertEqual(compile_source("int a; }").kind, "syntactic_error")

    def test_analysis_checks_declarations_without_executing(self) -> None:
        result = compile_source("int x; while (true) { x = 1 / 0; }")
        self.assertEqual(result.kind, "success", result.message)
        self.assertEqual(compile_source("while (true) { desconhecida = 1; }").kind, "semantic_error")

    def test_fresh_analyzers_after_error(self) -> None:
        self.assertEqual(compile_source("int a = ;").kind, "syntactic_error")
        self.assertEqual(compile_source("int a;").kind, "success")

    def test_unexpected_application_error(self) -> None:
        with patch("ide.compiler_service.Sintatico", side_effect=RuntimeError("falha de teste")):
            result = compile_source("int a;")
        self.assertEqual(result.kind, "unexpected_error")
        self.assertIn("RuntimeError: falha de teste", result.message)
        self.assertIsNone(result.line)

    def test_position_conversion(self) -> None:
        for source, position, expected in (
            ("", 0, (1, 1)), ("abc", 0, (1, 1)), ("abc", 3, (1, 4)),
            ("a\nb", 2, (2, 1)), ("a\nb", 3, (2, 2)),
            ("a\r\nb", 3, (2, 1)), ("\t@", 1, (1, 2)),
            ("a\n", 2, (2, 1)), ("a", -1, None), ("a", 2, None),
        ):
            with self.subTest(source=source, position=position):
                self.assertEqual(position_to_line_column(source, position), expected)


if __name__ == "__main__":
    unittest.main()
