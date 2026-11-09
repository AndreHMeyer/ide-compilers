"""Extensão do WebGALS: uma única passagem sintática dispara toda a semântica."""

from dataclasses import dataclass, field

from Errors import SemanticError
from semantic_model import Reference, SymbolTable, Value
from semantic_types import assignable, binary, boolean, integer, scalar, unary
from semantic_flow import Access, Branch, Declare, FlowAnalyzer, FunctionBody, LeaveScope, Loop, Return
from codegen.ir import Expression, Statement


@dataclass
class Call:
    reference: Reference
    arguments: list[Value] = field(default_factory=list)


@dataclass
class Control:
    kind: str
    parent: list
    sections: list[list] = field(default_factory=list)


class Semantico:
    ACTIONS = frozenset({1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15,
                        18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 30, 31, 32,
                        33, 34, 40, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52,
                        60, 62, 63, 64, 65, 66, 67, 71, 72, 73, 74, 75, 76, 77, 78, 79})

    def __init__(self, source="", defer_errors=False):
        self.source = source
        self.defer_errors = defer_errors
        self._reset()

    def _reset(self):
        self.table = SymbolTable(self.source)
        self.values = []
        self.operators = []
        self.names = []
        self.targets = []
        self.calls = []
        self.controls = []
        self.operations = []
        self.current_operations = self.operations
        self.program = []
        self.current_statements = self.program
        self.function_statements_parent = None
        self.declared_type = None
        self.declared_token = None
        self.declaration = None
        self.function = None
        self.function_parent = None
        self.function_scope = None
        self.warnings = ()
        self.error = None
        self.complete = False
        self.executed_actions = set()

    @property
    def symbols(self):
        return tuple(self.table.symbols)

    def execute_action(self, action, token):
        if action == 50:
            self._reset()
        self.executed_actions.add(action)
        if self.error is not None:
            return
        try:
            self._execute(action, token)
        except SemanticError as error:
            self.error = error
            if not self.defer_errors:
                raise

    def _declare(self, modality, array=False):
        symbol = self.table.declare(self.declared_token, self.declared_type, modality, array)
        self.declaration = symbol
        if modality != "função":
            self.current_operations.append(Declare(symbol))
            self.current_statements.append(Statement("declare", symbol.position, symbol=symbol))
        return symbol

    def _access(self, ref, write=False, declaration=False):
        if not declaration:
            ref.symbol.used = True
        if write:
            ref.symbol.writes += 1
        else:
            ref.symbol.reads += 1
        self.current_operations.append(Access(ref, write))

    def _reference(self, indexed=False):
        index = None
        index_expression = None
        if indexed:
            value = self.values.pop()
            integer(value, "o índice do vetor")
            index = value.constant
            index_expression = value.expression
        ref = self.names.pop()
        symbol = ref.symbol
        if symbol.modality == "função":
            raise SemanticError(f"a função '{symbol.name}' deve ser utilizada por uma chamada.", ref.position)
        if indexed:
            if not symbol.is_array:
                raise SemanticError(f"o identificador '{symbol.name}' não é um vetor.", ref.position)
            if index is not None and (index < 0 or (symbol.size is not None and index >= symbol.size)):
                raise SemanticError(f"índice {index} fora dos limites do vetor '{symbol.name}'.", value.position)
        return Reference(symbol, ref.position, indexed, index, index_expression)

    def _target(self, indexed):
        ref = self._reference(indexed)
        if ref.symbol.is_array and not indexed:
            raise SemanticError(f"o vetor '{ref.symbol.name}' exige um índice como destino.", ref.position)
        self.targets.append(ref)

    def _read(self, indexed):
        ref = self._reference(indexed)
        self._access(ref)
        self.values.append(Value(ref.symbol.type, ref.position,
                                 array=ref.symbol if ref.symbol.is_array and not indexed else None,
                                 expression=Expression("reference", ref.symbol.type, ref.position, reference=ref)))

    def _dimension(self):
        value = self.values.pop()
        integer(value, "o tamanho do vetor")
        if value.constant is not None and value.constant <= 0:
            raise SemanticError("o tamanho do vetor deve ser positivo.", value.position)
        self.declaration.size = value.constant
        self.declaration.dimension_expression = value.expression

    def _begin_control(self, kind):
        self.controls.append(Control(kind, self.current_operations))
        self.current_operations = []

    def _next_section(self):
        self.controls[-1].sections.append(self.current_operations)
        self.current_operations = []

    def _end_control(self):
        self._next_section()
        control = self.controls.pop()
        self.current_operations = control.parent
        return control

    def _leave_scope(self):
        scope = self.table.leave()
        self.current_operations.append(LeaveScope(scope.uid))

    def _call_end(self):
        call = self.calls.pop()
        function = call.reference.symbol
        expected, received = len(function.parameters), len(call.arguments)
        if expected != received:
            raise SemanticError(f"a função '{function.name}' espera {expected} argumento(s), recebeu {received}.",
                                call.reference.position)
        for parameter, value in zip(function.parameters, call.arguments):
            if parameter.is_array:
                if value.array is None or parameter.type != value.type:
                    raise SemanticError(f"o parâmetro '{parameter.name}' exige um vetor de {parameter.type}.",
                                        value.position)
                if parameter.size is not None and value.array.size is not None and parameter.size != value.array.size:
                    raise SemanticError(f"o parâmetro '{parameter.name}' exige vetor de tamanho {parameter.size}.",
                                        value.position)
            else:
                assignable(parameter.type, value, value.position)
        self.values.append(Value(function.type, call.reference.position,
                                 expression=Expression("call", function.type, call.reference.position,
                                                       reference=call.reference,
                                                       operands=tuple(v.expression for v in call.arguments))))

    def _execute(self, action, token):
        if action == 50:
            return
        if action == 1:
            self.declared_type = token.lexeme
        elif action == 2:
            self.declared_token = token
        elif action in (3, 4):
            self._declare("vetor" if action == 4 else "variável", action == 4)
        elif action == 5:
            value = self.values.pop()
            assignable(self.declaration.type, value, self.declaration.position)
            # A produção vetor[n] = exp define preenchimento uniforme.
            self._access(Reference(self.declaration, self.declaration.position), True, True)
            self.current_statements.append(Statement("initialize", self.declaration.position,
                                                      value.expression, symbol=self.declaration))
        elif action in (6, 13):
            self._dimension()
        elif action == 7:
            value, ref = self.values.pop(), self.targets.pop()
            assignable(ref.symbol.type, value, ref.position)
            self._access(ref, True)
            self.current_statements.append(Statement("assign", ref.position, value.expression, target=ref))
        elif action == 8:
            ref = self.targets.pop()
            self._access(ref, True)
            self.current_statements.append(Statement("input", ref.position, target=ref))
        elif action == 9:
            value = self.values.pop()
            scalar(value)
            self.current_statements.append(Statement("print", value.position, value.expression))
        elif action == 10:
            self.function = self._declare("função")
            self.function.initialized = True
            self.table.enter(f"função {self.function.name}")
            self.function_scope = self.table.current_id
            self.function_parent = self.current_operations
            self.current_operations = []
            self.function_statements_parent = self.current_statements
            self.current_statements = []
        elif action in (11, 12):
            parameter = self._declare("parâmetro", action == 12)
            self.function.parameters.append(parameter)
        elif action == 14:
            pass  # Assinatura completa antes do corpo, permitindo recursão.
        elif action == 15:
            self.function_statements_parent.append(Statement(
                "function", self.function.position, symbol=self.function, body=self.current_statements))
            self.current_statements = self.function_statements_parent
            self.function_statements_parent = None
            body = self.current_operations
            self.current_operations = self.function_parent
            self.current_operations.append(FunctionBody(self.function, self.function_scope, body))
            self.table.leave()
            self.function = self.function_parent = self.function_scope = None
        elif action in (18, 19):
            value = None
            if self.function is None:
                raise SemanticError("return só pode ser usado dentro de uma função.", token.position)
            if action == 18:
                if self.function.type != "void":
                    raise SemanticError(f"a função '{self.function.name}' deve retornar {self.function.type}.", token.position)
            else:
                value = self.values.pop()
                if self.function.type == "void":
                    raise SemanticError("um procedimento void não pode retornar um valor.", value.position)
                assignable(self.function.type, value, value.position)
            scopes = []
            scope = self.table.current
            while scope.parent_id is not None:
                scopes.append(scope.uid)
                scope = self.table.scopes[scope.parent_id]
            self.current_operations.append(Return(tuple(scopes)))
            self.current_statements.append(Statement("return", token.position,
                                                      value.expression if value else None))
        elif action == 20:
            self.names.append(Reference(self.table.resolve(token), token.position))
        elif action in (21, 22):
            self._target(action == 22)
        elif action in (23, 24):
            self._read(action == 24)
        elif action == 25:
            ref = self.names.pop()
            if ref.symbol.modality != "função":
                raise SemanticError(f"o identificador '{ref.symbol.name}' não é uma função.", ref.position)
            ref.symbol.used = True
            self.calls.append(Call(ref))
        elif action == 26:
            self.calls[-1].arguments.append(self.values.pop())
        elif action == 27:
            self._call_end()
        elif action == 28:
            value = self.values.pop()
            self.current_statements.append(Statement("call", value.position, value.expression))
        elif action == 30:
            self.table.enter("bloco")
        elif action == 31:
            self._leave_scope()
        elif action == 32:
            boolean(self.values.pop())
        elif action == 33:
            self.current_statements.append(Statement("unsupported", token.position, detail="laço for"))
            self.table.enter("for")
            self._begin_control("for")
        elif action == 34:
            control = self._end_control()
            init, condition, increment, body = control.sections
            self.current_operations.append(Loop("for", init, condition, body, increment))
            self._leave_scope()
        elif action == 40:
            self.current_statements.append(Statement("unsupported", token.position, detail="condicional if/else"))
            self._begin_control("if")
        elif action == 42:
            self._next_section()
        elif action == 43:
            control = self._end_control()
            self.current_operations.append(Branch(control.sections[0],
                                                  control.sections[1] if len(control.sections) == 2 else []))
        elif action in (44, 46):
            self.current_statements.append(Statement("unsupported", token.position,
                                                      detail="laço while" if action == 44 else "laço do-while"))
            self._begin_control("while" if action == 44 else "do")
        elif action in (45, 47):
            control = self._end_control()
            self.current_operations.append(Loop(control.kind, [], [], control.sections[0], []))
        elif action in (48, 49, 52):
            self._next_section()
        elif action == 51:
            if any((self.values, self.operators, self.names, self.targets, self.calls, self.controls)) or self.table.current_id:
                raise RuntimeError("Estado semântico desbalanceado ao encerrar a análise")
            self.warnings = FlowAnalyzer(self.table).analyze(self.operations)
            self.complete = True
        elif action == 60:
            self.operators.append(token)
        elif action == 62:
            self.values.append(unary(self.operators.pop(), self.values.pop()))
        elif action == 63:
            lexeme = token.lexeme
            base = 16 if lexeme.lower().startswith("0x") else 2 if lexeme.lower().startswith("0b") else 10
            constant = int(lexeme, base) if len(lexeme) <= 1000 else None
            self.values.append(Value("int", token.position, constant,
                                     expression=Expression("literal", "int", token.position, literal=lexeme)))
        elif action in (64, 65, 66, 67):
            type_name = {64: "float", 65: "char", 66: "string", 67: "bool"}[action]
            self.values.append(Value(type_name, token.position,
                                     expression=Expression("literal", type_name, token.position, literal=token.lexeme)))
        elif 71 <= action <= 79:
            right, left = self.values.pop(), self.values.pop()
            self.values.append(binary(self.operators.pop(), left, right))
        else:
            raise RuntimeError(f"Ação semântica #{action} não implementada")
