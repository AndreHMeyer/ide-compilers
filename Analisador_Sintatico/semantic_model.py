"""Símbolos, escopos e diagnósticos; independente de Tkinter e do parser."""

from dataclasses import dataclass, field

from Errors import SemanticError


def location(source, position):
    if 0 <= position <= len(source):
        return source.count("\n", 0, position) + 1, position - source.rfind("\n", 0, position)
    return None, None


@dataclass(frozen=True)
class Diagnostic:
    severity: str
    phase: str
    code: str
    message: str
    position: int = -1
    line: int | None = None
    column: int | None = None

    @property
    def formatted(self):
        phase = {"semantic": "semântico", "lexical": "léxico", "syntactic": "sintático", "internal": "interno"}[self.phase]
        label = ("Aviso " if self.severity == "warning" else "Erro ") + phase
        place = f" na linha {self.line}, coluna {self.column}" if self.line else ""
        return f"{label}{place}: {self.message}"


@dataclass
class Symbol:
    uid: int
    name: str
    type: str
    modality: str
    scope_id: int
    scope: str
    parent_scope_id: int | None
    position: int
    line: int | None
    column: int | None
    is_array: bool = False
    size: int | None = None
    parameters: list["Symbol"] = field(default_factory=list)
    used: bool = False
    reads: int = 0
    writes: int = 0
    initialized: bool = False
    initialized_elements: tuple[int, ...] = ()

    @property
    def signature(self):
        if self.modality != "função":
            return ""
        params = ", ".join(p.type + ("[]" if p.is_array else "") for p in self.parameters)
        return f"{self.type} {self.name}({params})"


@dataclass
class Scope:
    uid: int
    name: str
    parent_id: int | None
    symbols: dict[str, Symbol] = field(default_factory=dict)


class SymbolTable:
    def __init__(self, source=""):
        self.source = source
        self.symbols: list[Symbol] = []
        self.scopes = [Scope(0, "global", None)]
        self.current_id = 0

    @property
    def current(self):
        return self.scopes[self.current_id]

    def enter(self, label):
        uid = len(self.scopes)
        self.scopes.append(Scope(uid, f"{self.current.name}/{label}#{uid}", self.current_id))
        self.current_id = uid

    def leave(self):
        scope = self.current
        if scope.parent_id is None:
            raise RuntimeError("Tentativa de encerrar o escopo global")
        self.current_id = scope.parent_id
        return scope

    def declare(self, token, type_name, modality, is_array=False):
        scope = self.current
        original = scope.symbols.get(token.lexeme)
        if original:
            where = f" na linha {original.line}, coluna {original.column}" if original.line else ""
            raise SemanticError(
                f"identificador '{token.lexeme}' já declarado neste escopo; declaração original{where}.",
                token.position,
            )
        line, column = location(self.source, token.position)
        symbol = Symbol(len(self.symbols), token.lexeme, type_name, modality, scope.uid,
                        scope.name, scope.parent_id, token.position, line, column, is_array)
        scope.symbols[symbol.name] = symbol
        self.symbols.append(symbol)
        return symbol

    def resolve(self, token):
        scope = self.current
        while True:
            if token.lexeme in scope.symbols:
                return scope.symbols[token.lexeme]
            if scope.parent_id is None:
                raise SemanticError(f"identificador '{token.lexeme}' não declarado.", token.position)
            scope = self.scopes[scope.parent_id]


@dataclass(frozen=True)
class Reference:
    symbol: Symbol
    position: int
    element: bool = False
    index: int | None = None


@dataclass(frozen=True)
class Value:
    type: str
    position: int
    constant: int | None = None
    array: Symbol | None = None
