"""IR construída somente pelas ações semânticas do parser WebGALS.

Símbolos e referências são os próprios objetos da tabela semântica. Blocos
sequenciais mantêm a ordem; estruturas ainda não traduzidas têm marcadores
explícitos que impedem a emissão de um programa parcial.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Expression:
    kind: str
    type: str
    position: int
    literal: str = ""
    operator: str = ""
    operands: tuple["Expression", ...] = ()
    reference: Any = None


@dataclass
class Statement:
    kind: str
    position: int
    expression: Expression | None = None
    target: Any = None
    symbol: Any = None
    body: list["Statement"] = field(default_factory=list)
    detail: str = ""
