"""Inicialização definida sobre operações construídas pelas ações do WebGALS.

Não lê tokens nem reconhece sintaxe. Cada lista já corresponde a um caminho
delimitado pelas ações da gramática. None em um estado significa todos os
elementos inicializados; uma chave ausente significa nenhuma inicialização.
"""

from dataclasses import dataclass

from Errors import SemanticError
from semantic_model import Diagnostic, Reference, Symbol, location


@dataclass
class Access:
    reference: Reference
    write: bool = False


@dataclass
class Declare:
    symbol: Symbol


@dataclass
class LeaveScope:
    scope_id: int


@dataclass
class Branch:
    then_body: list
    else_body: list


@dataclass
class Loop:
    kind: str
    init: list
    condition: list
    body: list
    increment: list


@dataclass
class FunctionBody:
    symbol: Symbol
    scope_id: int
    body: list


@dataclass
class Return:
    scope_ids: tuple[int, ...]


def intersect(states):
    states = [state for state in states if state is not None]
    if not states:
        return None
    result = states[0].copy()
    for state in states[1:]:
        for uid in list(result):
            if uid not in state:
                del result[uid]
            elif result[uid] is None:
                result[uid] = state[uid]
            elif state[uid] is not None:
                result[uid] = result[uid] & state[uid]
    return result


class FlowAnalyzer:
    def __init__(self, table):
        self.table = table
        self.warnings = []
        self.reported = set()
        self.scope_exits = {}

    def warn(self, code, symbol, position, message):
        key = code, symbol.uid, position
        if key not in self.reported:
            self.reported.add(key)
            line, column = location(self.table.source, position)
            self.warnings.append(Diagnostic("warning", "semantic", code, message, position, line, column))

    def _all_initialized(self, symbol, state):
        if symbol.uid not in state:
            return False
        elements = state[symbol.uid]
        return elements is None or (symbol.size is not None and len(elements) == symbol.size)

    def snapshot(self, scope_id, state):
        for symbol in self.table.scopes[scope_id].symbols.values():
            if symbol.modality == "função":
                symbol.initialized = True
                continue
            symbol.initialized = self._all_initialized(symbol, state)
            symbol.initialized_elements = tuple(sorted(state.get(symbol.uid) or ()))

    def record_exit(self, scope_id, state):
        # Um bloco pode encerrar normalmente ou por diferentes returns.
        symbols = self.table.scopes[scope_id].symbols.values()
        projected = {symbol.uid: state[symbol.uid] for symbol in symbols if symbol.uid in state}
        self.scope_exits.setdefault(scope_id, []).append(projected)

    def walk(self, operations, state):
        state = state.copy()
        for node in operations:
            if state is None:
                break
            if isinstance(node, Declare):
                state.pop(node.symbol.uid, None)
                if node.symbol.modality == "parâmetro":
                    state[node.symbol.uid] = None
            elif isinstance(node, Access):
                ref = node.reference
                symbol, uid = ref.symbol, ref.symbol.uid
                if node.write:
                    if not ref.element:
                        state[uid] = None
                    elif ref.index is not None and not self._all_initialized(symbol, state):
                        state[uid] = state.get(uid, frozenset()) | {ref.index}
                else:
                    initialized = self._all_initialized(symbol, state)
                    if ref.element and ref.index is not None:
                        initialized |= ref.index in (state.get(uid) or ())
                    if not initialized:
                        item = f"'{symbol.name}'"
                        if ref.element:
                            item += f"[{ref.index if ref.index is not None else '?'}]"
                        self.warn("uninitialized", symbol, ref.position,
                                  f"{item} pode estar sendo utilizado sem inicialização (possível lixo de memória).")
            elif isinstance(node, LeaveScope):
                self.record_exit(node.scope_id, state)
                for symbol in self.table.scopes[node.scope_id].symbols.values():
                    state.pop(symbol.uid, None)
            elif isinstance(node, Branch):
                state = intersect([self.walk(node.then_body, state),
                                   self.walk(node.else_body, state)])
            elif isinstance(node, Loop):
                state = self.walk(node.init, state)
                if node.kind == "do":
                    state = self.walk(node.body, state)
                    if state is not None:
                        state = self.walk(node.condition, state)
                else:
                    state = self.walk(node.condition, state)
                    body_state = self.walk(node.body, state)
                    if body_state is not None:
                        self.walk(node.increment, body_state)
                    # while/for podem executar zero vezes.
            elif isinstance(node, FunctionBody):
                end = self.walk(node.body, state)
                if node.symbol.type != "void" and end is not None:
                    raise SemanticError(f"a função '{node.symbol.name}' pode terminar sem retornar {node.symbol.type}.",
                                        node.symbol.position)
                if end is not None:
                    self.record_exit(node.scope_id, end)
            elif isinstance(node, Return):
                for scope_id in node.scope_ids:
                    self.record_exit(scope_id, state)
                state = None
            else:
                raise RuntimeError(f"Operação de fluxo desconhecida: {type(node).__name__}")
        return state

    def analyze(self, operations):
        state = self.walk(operations, {})
        for scope_id, exits in self.scope_exits.items():
            self.snapshot(scope_id, intersect(exits) or {})
        self.snapshot(0, state or {})
        for symbol in self.table.symbols:
            if not symbol.used:
                self.warn("unused", symbol, symbol.position,
                          f"o identificador '{symbol.name}' foi declarado, mas não utilizado.")
        return tuple(sorted(self.warnings, key=lambda warning: (warning.position, warning.code)))
