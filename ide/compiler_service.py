"""Integração com o WebGALS, sem dependência da interface gráfica."""

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Literal


# Os arquivos exportados usam imports absolutos entre si. O caminho temporário
# preserva esses imports sem deixar Token.py sombrear o módulo padrão token.
_GENERATED_DIR = str(Path(__file__).resolve().parent.parent / "Analisador_Sintatico")
sys.path.insert(0, _GENERATED_DIR)
try:
    from Errors import AnalysisError, LexicalError, SyntacticError
    from Lexico import Lexico
    from Semantico import Semantico
    from Sintatico import Sintatico
finally:
    sys.path.remove(_GENERATED_DIR)


@dataclass(frozen=True)
class CompilationResult:
    kind: Literal["success", "empty", "lexical_error", "syntactic_error", "unexpected_error"]
    message: str
    line: int | None = None
    column: int | None = None


def position_to_line_column(source: str, position: int) -> tuple[int, int] | None:
    """Converte o índice do WebGALS em linha/coluna (base 1).

    A coluna conta caracteres, incluindo cada tabulação como um caractere.
    Posições ausentes ou fora da entrada não recebem uma localização inventada.
    """
    if not 0 <= position <= len(source):
        return None
    line = source.count("\n", 0, position) + 1
    column = position - source.rfind("\n", 0, position)
    return line, column


def _analysis_error(
    source: str,
    error: AnalysisError,
    kind: Literal["lexical_error", "syntactic_error"],
    label: str,
    detail: str,
) -> CompilationResult:
    location = position_to_line_column(source, error.position)
    line, column = location if location else (None, None)
    heading = label
    if location:
        heading += f" na linha {line}, coluna {column}"
    return CompilationResult(kind, f"{heading}:\n{detail}", line, column)


def compile_source(source: str) -> CompilationResult:
    """Consome a entrada usando exclusivamente o scanner e o parser exportados."""
    if not source.strip():
        return CompilationResult("empty", "Nenhum código-fonte informado.")

    parser = None
    try:
        scanner = Lexico(source)
        parser = Sintatico()
        # O objeto exportado atende ao contrato parse(scanner, semantic).
        # A tabela atual não contém ações semânticas.
        parser.parse(scanner, Semantico())
    except LexicalError as error:
        return _analysis_error(source, error, "lexical_error", "Erro léxico", error.message)
    except SyntacticError as error:
        token = parser.current_token if parser is not None else None
        if token is None or token.lexeme == "$":
            detail = "Fim do código-fonte inesperado."
        else:
            detail = f"Token inesperado: {token.lexeme!r}."
        detail += f"\nMensagem do WebGALS: {error.message}."
        return _analysis_error(source, error, "syntactic_error", "Erro sintático", detail)
    except Exception as error:
        return CompilationResult(
            "unexpected_error",
            f"Erro inesperado: {type(error).__name__}: {error}",
        )

    return CompilationResult("success", "Compilação realizada com sucesso.")
