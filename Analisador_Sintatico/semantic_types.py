"""Regras explícitas de tipos e dobra limitada de constantes inteiras."""

from Errors import SemanticError
from semantic_model import Value


NUMERIC = {"int": 0, "float": 1, "double": 2}


def scalar(value):
    if value.array is not None:
        raise SemanticError("um vetor inteiro não pode ser usado como valor escalar.", value.position)
    if value.type == "void":
        raise SemanticError("um procedimento void não produz um valor.", value.position)


def assignable(target, value, position):
    scalar(value)
    if target == value.type or (target in NUMERIC and value.type in NUMERIC
                                and NUMERIC[value.type] <= NUMERIC[target]):
        return
    raise SemanticError(f"não é possível atribuir {value.type} a {target}.", position)


def integer(value, label):
    scalar(value)
    if value.type != "int":
        raise SemanticError(f"{label} deve ter tipo int, recebeu {value.type}.", value.position)


def boolean(value):
    scalar(value)
    if value.type != "bool":
        raise SemanticError(f"a condição deve ter tipo bool, recebeu {value.type}.", value.position)


def unary(operator, value):
    scalar(value)
    op = operator.lexeme
    valid = ((op == "-" and value.type in NUMERIC) or (op == "!" and value.type == "bool")
             or (op == "~" and value.type == "int"))
    if not valid:
        raise SemanticError(f"operador '{op}' incompatível com {value.type}.", operator.position)
    constant = None
    if value.constant is not None:
        constant = -value.constant if op == "-" else ~value.constant if op == "~" else None
    return Value(value.type, operator.position, constant)


def _fold(op, a, b):
    # Somente constantes int pequenas, para dimensões/índices. Não executa chamadas.
    if a is None or b is None or max(a.bit_length(), b.bit_length()) > 4096:
        return None
    if op in ("<<", ">>") and not 0 <= b <= 4096:
        return None
    if op in ("/", "%") and b == 0:
        return None
    quotient = lambda: (abs(a) // abs(b)) * (-1 if (a < 0) != (b < 0) else 1)
    operations = {"+": lambda: a + b, "-": lambda: a - b, "*": lambda: a * b,
                  "/": quotient, "%": lambda: a - quotient() * b,
                  "<<": lambda: a << b, ">>": lambda: a >> b,
                  "&": lambda: a & b, "|": lambda: a | b, "^": lambda: a ^ b}
    result = operations[op]() if op in operations else None
    return result if result is None or result.bit_length() <= 4096 else None


def binary(operator, left, right):
    scalar(left)
    scalar(right)
    op, a, b = operator.lexeme, left.type, right.type
    numeric = a in NUMERIC and b in NUMERIC
    result = None
    if op in ("+", "-", "*", "/") and numeric:
        result = max((a, b), key=NUMERIC.get)
    elif op in ("%", "&", "|", "^", "<<", ">>") and a == b == "int":
        result = "int"
    elif op in ("&&", "||") and a == b == "bool":
        result = "bool"
    elif op in ("<", ">", "<=", ">=") and (numeric or a == b == "char"):
        result = "bool"
    elif op in ("==", "!=") and (numeric or a == b):
        result = "bool"
    if result is None:
        raise SemanticError(f"operador '{op}' incompatível com {a} e {b}.", operator.position)
    constant = _fold(op, left.constant, right.constant) if result == "int" else None
    return Value(result, operator.position, constant)
