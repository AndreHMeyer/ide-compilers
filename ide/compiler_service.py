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
    from Errors import AnalysisError, LexicalError, SyntacticError, SemanticError
    from Lexico import Lexico
    from Semantico import Semantico
    from Sintatico import Sintatico
    from semantic_model import Diagnostic, Symbol
finally:
    sys.path.remove(_GENERATED_DIR)


@dataclass(frozen=True)
class CompilationResult:
    kind: Literal["success", "empty", "lexical_error", "syntactic_error", "semantic_error", "unexpected_error"]
    message: str
    line: int | None = None
    column: int | None = None
    warnings: tuple[Diagnostic, ...] = ()
    errors: tuple[Diagnostic, ...] = ()
    symbols: tuple[Symbol, ...] = ()
    symbols_partial: bool = False

    @property
    def success(self) -> bool:
        return self.kind == "success"

    @property
    def diagnostics(self) -> tuple[Diagnostic, ...]:
        return self.errors + self.warnings


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
    kind: Literal["lexical_error", "syntactic_error", "semantic_error"],
    label: str,
    detail: str,
    symbols: tuple[Symbol, ...] = (),
) -> CompilationResult:
    location = position_to_line_column(source, error.position)
    line, column = location if location else (None, None)
    heading = label
    if location:
        heading += f" na linha {line}, coluna {column}"
    diagnostic = Diagnostic("error", kind.removesuffix("_error"), kind, detail, error.position, line, column)
    return CompilationResult(kind, f"{heading}:\n{detail}", line, column,
                             errors=(diagnostic,), symbols=symbols, symbols_partial=True)


def compile_source(source: str) -> CompilationResult:
    """Consome a entrada usando exclusivamente o scanner e o parser exportados."""
    if not source.strip():
        return CompilationResult("empty", "Nenhum código-fonte informado.")

    parser = None
    semantic = Semantico(source, defer_errors=True)
    try:
        scanner = Lexico(source)
        parser = Sintatico()
        # Continua o mesmo parse após o primeiro erro semântico, sem executar
        # novas ações, para priorizar eventuais falhas léxicas/sintáticas.
        parser.parse(scanner, semantic)
        if semantic.error is not None:
            raise semantic.error
        if not semantic.complete:
            raise RuntimeError("A exportação do WebGALS não concluiu as ações semânticas #50/#51.")
    except LexicalError as error:
        return _analysis_error(source, error, "lexical_error", "Erro léxico", error.message, semantic.symbols)
    except SyntacticError as error:
        token = parser.current_token if parser is not None else None
        if token is None or token.lexeme == "$":
            detail = "Fim do código-fonte inesperado."
        else:
            detail = f"Token inesperado: {token.lexeme!r}."
        detail += f"\nMensagem do WebGALS: {error.message}."
        return _analysis_error(source, error, "syntactic_error", "Erro sintático", detail, semantic.symbols)
    except SemanticError as error:
        return _analysis_error(source, error, "semantic_error", "Erro semântico", error.message, semantic.symbols)
    except Exception as error:
        detail = f"{type(error).__name__}: {error}"
        return CompilationResult(
            "unexpected_error",
            f"Erro inesperado: {detail}",
            errors=(Diagnostic("error", "internal", "unexpected_error", detail),),
            symbols=semantic.symbols, symbols_partial=True,
        )

    return CompilationResult("success", "Compilação realizada com sucesso.",
                             warnings=semantic.warnings, symbols=semantic.symbols)
