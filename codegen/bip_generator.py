"""Emissão para BIP IV/Bipide 3.0: ACC de 16 bits, imediatos de 11 bits.

Referência: ajuda e montador BIP.dll da instalação original (docs/bip_iv.md).
O gerador recebe IR tipada; não lê, tokeniza ou reconhece código-fonte.
"""

from contextlib import contextmanager
from dataclasses import dataclass, field
import re

from .ir import Expression, Statement


WORD_MIN, WORD_MAX = -32768, 32767
IMMEDIATE_MIN, IMMEDIATE_MAX = -1024, 1023
DATA_WORDS = 1024  # 0..1023; $in_port inicia a região de E/S em 1024.
CODE_WORDS = 2048
MEMORY_OPS = {"LD", "STO", "ADD", "SUB", "AND", "OR", "XOR", "LDV", "STOV"}
IMMEDIATE_OPS = {"LDI", "ADDI", "SUBI", "ANDI", "ORI", "XORI"}
BINARY = {"+": "ADD", "-": "SUB", "&": "AND", "|": "OR", "^": "XOR"}


class CodeGenerationError(Exception):
    def __init__(self, message, position=-1):
        super().__init__(message)
        self.message, self.position = message, position


def word(value):
    """Interpreta o padrão de 16 bits como complemento de dois."""
    return ((value + 32768) & 65535) - 32768


def literal_value(expr, allow_min_magnitude=False):
    text = expr.literal.lower()
    base = 16 if text.startswith("0x") else 2 if text.startswith("0b") else 10
    if len(text) > 1000:
        raise CodeGenerationError("constante fora do intervalo de 16 bits.", expr.position)
    value = int(text, base)
    limit = 65535 if base != 10 else 32768 if allow_min_magnitude else WORD_MAX
    if not 0 <= value <= limit:
        raise CodeGenerationError("constante fora do intervalo de 16 bits (-32768 a 32767).", expr.position)
    return word(value) if base != 10 else value


def is_min_magnitude(expr):
    return (expr.kind == "literal" and not expr.literal.lower().startswith(("0x", "0b"))
            and literal_value(expr, allow_min_magnitude=True) == 32768)


def constant_value(expr, dimension=False):
    """Avalia somente árvores constantes. Dimensões usam inteiros matemáticos.

Em expressões executáveis, cada operação obedece ao tamanho de palavra e SRL
é lógico. Multiplicação/divisão/módulo só são dobrados em dimensões estáticas.
"""
    if expr is None or expr.type != "int":
        return None
    if expr.kind == "literal":
        return literal_value(expr)
    if expr.kind == "unary":
        child = expr.operands[0]
        if expr.operator == "-" and is_min_magnitude(child):
            return WORD_MIN
        value = constant_value(child, dimension)
        if value is None:
            return None
        result = -value if expr.operator == "-" else ~value
    elif expr.kind == "binary":
        left, right = (constant_value(x, dimension) for x in expr.operands)
        if left is None or right is None:
            return None
        op = expr.operator
        if op in ("<<", ">>") and not 0 <= right <= 15:
            raise CodeGenerationError("deslocamento exige quantidade constante entre 0 e 15.", expr.position)
        if op in ("/", "%") and right == 0:
            raise CodeGenerationError("divisão por zero na dimensão do vetor.", expr.position)
        quotient = lambda: (abs(left) // abs(right)) * (-1 if (left < 0) != (right < 0) else 1)
        operations = {"+": lambda: left + right, "-": lambda: left - right,
                      "&": lambda: left & right, "|": lambda: left | right, "^": lambda: left ^ right,
                      "<<": lambda: left << right,
                      ">>": lambda: (left if dimension else left & 65535) >> right}
        if dimension:
            operations.update({"*": lambda: left * right, "/": quotient, "%": lambda: left - quotient() * right})
        if op not in operations:
            return None
        result = operations[op]()
    else:
        return None
    return result if dimension else word(result)


@dataclass
class AssemblyProgram:
    data: dict[str, tuple[int, ...]] = field(default_factory=dict)
    instructions: list[tuple[str, str | int | None]] = field(default_factory=list)

    def validate(self):
        if sum(map(len, self.data.values())) > DATA_WORDS:
            raise CodeGenerationError("memória de dados excede 1024 palavras (região de E/S reservada).")
        if len(self.instructions) > CODE_WORDS:
            raise CodeGenerationError("memória de programa excede 2048 instruções.")
        for label, values in self.data.items():
            if not re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", label):
                raise CodeGenerationError(f"rótulo de memória inválido: {label!r}.")
            if not values or any(not WORD_MIN <= v <= WORD_MAX for v in values):
                raise CodeGenerationError(f"dados inválidos para o rótulo '{label}'.")
        for op, operand in self.instructions:
            if op in MEMORY_OPS:
                special = {"LD": {"$in_port"}, "STO": {"$out_port", "$indr"}}
                if operand not in self.data and operand not in special.get(op, set()):
                    raise CodeGenerationError(f"referência/endereço inválido: {op} {operand}.")
            elif op in IMMEDIATE_OPS:
                if not isinstance(operand, int) or not IMMEDIATE_MIN <= operand <= IMMEDIATE_MAX:
                    raise CodeGenerationError(f"operando imediato não representável: {op} {operand}.")
            elif op in ("SLL", "SRL"):
                if not isinstance(operand, int) or not 0 <= operand <= 15:
                    raise CodeGenerationError(f"deslocamento inválido: {op} {operand}.")
            elif op in ("NOT", "HLT"):
                if operand is not None:
                    raise CodeGenerationError(f"{op} não aceita operando.")
            else:
                raise CodeGenerationError(f"instrução não suportada: {op}.")
        if not self.instructions or self.instructions[-1] != ("HLT", None):
            raise CodeGenerationError("programa sem encerramento HLT.")

    def render(self):
        self.validate()
        lines = [".data"]
        lines += [f"{label} : " + ", ".join(map(str, values)) for label, values in self.data.items()]
        lines += ["", ".text"]
        lines += [f"    {op}" + (f" {operand}" if operand is not None else "")
                  for op, operand in self.instructions]
        return "\n".join(lines) + "\n"


class MemoryAllocator:
    def __init__(self, program):
        self.program = program
        self.symbols = {}
        self.constants = {}
        self.free_temps = []
        self.temp_count = 0
        self.words = 0

    def reserve(self, label, values, position=-1):
        if label in self.program.data:
            raise CodeGenerationError(f"rótulo duplicado: '{label}'.", position)
        if self.words + len(values) > DATA_WORDS:
            raise CodeGenerationError("memória de dados excede 1024 palavras, incluindo temporários e constantes.", position)
        self.program.data[label] = tuple(values)
        self.words += len(values)
        return label

    def declare(self, symbol):
        if symbol.uid in self.symbols:
            raise CodeGenerationError("identificador de símbolo duplicado na IR.", symbol.position)
        if symbol.type != "int":
            raise CodeGenerationError(f"tipo '{symbol.type}' não suportado pelo gerador BIP IV; utilize int.", symbol.position)
        size = 1
        if symbol.is_array:
            size = constant_value(symbol.dimension_expression, dimension=True)
            if size is None:
                raise CodeGenerationError(f"dimensão do vetor '{symbol.name}' não é uma expressão constante.", symbol.position)
            if not 1 <= size <= DATA_WORDS:
                raise CodeGenerationError(f"dimensão inválida do vetor '{symbol.name}': {size}; permitido 1 a 1024.", symbol.position)
        label = self.reserve(f"v{symbol.uid}", (0,) * size, symbol.position)
        self.symbols[symbol.uid] = (symbol, label)

    def label(self, symbol, position=-1):
        item = self.symbols.get(symbol.uid)
        if item is None or item[0] is not symbol:
            raise CodeGenerationError(f"referência inválida ao símbolo '{symbol.name}'.", position)
        return item[1]

    def constant(self, value, position):
        if value not in self.constants:
            self.constants[value] = self.reserve(f"c{len(self.constants)}", (value,), position)
        return self.constants[value]

    @contextmanager
    def temporary(self, position):
        if self.free_temps:
            label = self.free_temps.pop()
        else:
            label = self.reserve(f"t{self.temp_count}", (0,), position)
            self.temp_count += 1
        try:
            yield label
        finally:
            self.free_temps.append(label)


class BIPCodeGenerator:
    def generate(self, statements, symbols):
        # Também permite reutilizar a instância sem carregar estado anterior.
        self.program = AssemblyProgram()
        self.memory = MemoryAllocator(self.program)
        main = None
        global_body = []
        for statement in statements:
            if statement.kind == "function":
                symbol = statement.symbol
                if symbol.name != "main" or symbol.parameters or symbol.type not in ("int", "void"):
                    raise CodeGenerationError("funções comuns/parametrizadas não suportadas; ponto de entrada: int main() ou void main().",
                                              statement.position)
                if main is not None:
                    raise CodeGenerationError("mais de um ponto de entrada main.", statement.position)
                main = statement
            else:
                global_body.append(statement)
        body = global_body + (main.body if main else [])
        # Verifica inclusive comandos inalcançáveis; nunca descarta operações sem tradução.
        for statement in body:
            if statement.kind == "unsupported":
                raise CodeGenerationError(f"geração BIP IV não implementada para {statement.detail}.", statement.position)
        for symbol in symbols:
            if symbol.modality != "função":
                self.memory.declare(symbol)
        for statement in body:
            self.statement(statement)
        if not self.program.instructions or self.program.instructions[-1][0] != "HLT":
            self.emit("HLT", position=body[-1].position if body else -1)
        if not self.program.data:
            # A gramatica do montador 3.0 exige ao menos uma declaracao em .data.
            self.memory.reserve("reserved", (0,))
        return self.program.render()

    def emit(self, op, operand=None, position=-1):
        if len(self.program.instructions) >= CODE_WORDS:
            raise CodeGenerationError("memória de programa excede 2048 instruções.", position)
        self.program.instructions.append((op, operand))

    def load_constant(self, value, position):
        if IMMEDIATE_MIN <= value <= IMMEDIATE_MAX:
            self.emit("LDI", value, position)
        else:
            self.emit("LD", self.memory.constant(value, position), position)

    def normalize_word(self, position):
        """Normaliza também o simulador 3.0, cujo ACC interno é Int32.

        signed16(x) = (x & 32767) - (((x >> 15) & 1) << 15).
        No hardware a subtração do bit de sinal tem o mesmo padrão de 16 bits.
        A sequência funciona com SRL lógico ou aritmético e não exige desvios.
        """
        with self.memory.temporary(position) as original, self.memory.temporary(position) as low:
            self.emit("STO", original, position)
            self.emit("AND", self.memory.constant(32767, position), position)
            self.emit("STO", low, position)
            self.emit("LD", original, position)
            self.emit("SRL", 15, position)
            self.emit("ANDI", 1, position)
            self.emit("SLL", 15, position)
            self.emit("STO", original, position)
            self.emit("LD", low, position)
            self.emit("SUB", original, position)

    def check_reference(self, ref):
        label = self.memory.label(ref.symbol, ref.position)
        if ref.element != ref.symbol.is_array:
            raise CodeGenerationError("referência escalar/vetorial inconsistente na IR.", ref.position)
        if ref.element:
            if ref.index_expression is None:
                raise CodeGenerationError("índice vetorial ausente na IR.", ref.position)
            index = constant_value(ref.index_expression)
            if index is not None and not 0 <= index < len(self.program.data[label]):
                raise CodeGenerationError("índice constante fora dos limites do vetor no alvo de 16 bits.", ref.position)
        return label

    def expression(self, expr):
        if expr is None:
            raise CodeGenerationError("expressão ausente na IR.")
        if expr.kind == "call":
            raise CodeGenerationError("chamadas de funções/recursão não suportadas no gerador BIP IV.", expr.position)
        if expr.type != "int":
            raise CodeGenerationError(f"expressão de tipo '{expr.type}' não suportada no BIP IV.", expr.position)
        if expr.kind == "literal":
            self.load_constant(literal_value(expr), expr.position)
        elif expr.kind == "reference":
            label = self.check_reference(expr.reference)
            if expr.reference.element:
                self.expression(expr.reference.index_expression)
                self.emit("STO", "$indr", expr.position)
                self.emit("LDV", label, expr.position)
            else:
                self.emit("LD", label, expr.position)
        elif expr.kind == "unary":
            child = expr.operands[0]
            if expr.operator not in ("-", "~"):
                raise CodeGenerationError(f"operador '{expr.operator}' não suportado.", expr.position)
            if expr.operator == "-" and is_min_magnitude(child):
                self.load_constant(WORD_MIN, expr.position)
                return
            self.expression(child)
            self.emit("NOT", position=expr.position)
            if expr.operator == "-":
                self.emit("ADDI", 1, expr.position)
                self.normalize_word(expr.position)
        elif expr.kind == "binary":
            left, right = expr.operands
            op = expr.operator
            if op in ("<<", ">>"):
                # O campo do shift é imediato; nunca se emite SLL/SRL com um rótulo.
                count = constant_value(right)
                if count is None or not 0 <= count <= 15:
                    raise CodeGenerationError("deslocamento exige quantidade constante entre 0 e 15; quantidade variável não suportada.", right.position)
                self.expression(left)
                self.emit("SLL" if op == "<<" else "SRL", count, expr.position)
                if op == "<<" and count:
                    self.normalize_word(expr.position)
                elif op == ">>" and count:
                    mask = (1 << (16 - count)) - 1
                    if mask <= IMMEDIATE_MAX:
                        self.emit("ANDI", mask, expr.position)
                    else:
                        self.emit("AND", self.memory.constant(mask, expr.position), expr.position)
            elif op in BINARY:
                self.expression(left)
                if right.kind == "literal":
                    value = literal_value(right)
                    if IMMEDIATE_MIN <= value <= IMMEDIATE_MAX:
                        self.emit(BINARY[op] + "I", value, expr.position)
                    else:
                        self.emit(BINARY[op], self.memory.constant(value, right.position), expr.position)
                elif right.kind == "reference" and not right.reference.element:
                    self.emit(BINARY[op], self.check_reference(right.reference), expr.position)
                else:
                    with self.memory.temporary(expr.position) as lhs:
                        self.emit("STO", lhs, expr.position)
                        self.expression(right)
                        with self.memory.temporary(expr.position) as rhs:
                            self.emit("STO", rhs, expr.position)
                            self.emit("LD", lhs, expr.position)
                            self.emit(BINARY[op], rhs, expr.position)
                if op in ("+", "-"):
                    self.normalize_word(expr.position)
            else:
                raise CodeGenerationError(f"operação '{op}' não suportada pelo gerador BIP IV.", expr.position)
        else:
            raise CodeGenerationError(f"expressão sem tradução: {expr.kind}.", expr.position)

    def store(self, target, expression=None):
        label = self.check_reference(target)
        if target.element:
            # Calcula o destino antes do RHS/input; protege-o de LDV/STOV aninhados.
            self.expression(target.index_expression)
            with self.memory.temporary(target.position) as index:
                self.emit("STO", index, target.position)
                self.expression(expression) if expression else self.emit("LD", "$in_port", target.position)
                with self.memory.temporary(target.position) as value:
                    self.emit("STO", value, target.position)
                    self.emit("LD", index, target.position)
                    self.emit("STO", "$indr", target.position)
                    self.emit("LD", value, target.position)
                    self.emit("STOV", label, target.position)
        else:
            self.expression(expression) if expression else self.emit("LD", "$in_port", target.position)
            self.emit("STO", label, target.position)

    def statement(self, stmt):
        if stmt.kind == "declare":
            self.memory.label(stmt.symbol, stmt.position)
        elif stmt.kind == "initialize":
            label = self.memory.label(stmt.symbol, stmt.position)
            self.expression(stmt.expression)
            if stmt.symbol.is_array:
                # Inicializador uniforme é avaliado uma vez, conforme a semântica existente.
                with self.memory.temporary(stmt.position) as value:
                    self.emit("STO", value, stmt.position)
                    for index in range(len(self.program.data[label])):
                        self.load_constant(index, stmt.position)
                        self.emit("STO", "$indr", stmt.position)
                        self.emit("LD", value, stmt.position)
                        self.emit("STOV", label, stmt.position)
            else:
                self.emit("STO", label, stmt.position)
        elif stmt.kind in ("assign", "input"):
            self.store(stmt.target, stmt.expression)
        elif stmt.kind == "print":
            self.expression(stmt.expression)
            self.emit("STO", "$out_port", stmt.position)
        elif stmt.kind == "return":
            if stmt.expression is not None:
                # Valida a árvore inteira, mesmo se seu resultado puder ser dobrado.
                self.expression(stmt.expression)
                if constant_value(stmt.expression) != 0:
                    raise CodeGenerationError("main suporta apenas return 0; ou return; em void.", stmt.position)
            self.emit("HLT", position=stmt.position)
        elif stmt.kind == "call":
            self.expression(stmt.expression)
        else:
            raise CodeGenerationError(f"comando sem tradução: {stmt.detail or stmt.kind}.", stmt.position)
