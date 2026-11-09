"""Oráculo de testes do subconjunto BIP, separado do gerador.

Modelo de palavras de 16 bits conforme Help/InstrucoesBip.html. A validação
independente no montador/simulador instalado está em run_bipide.ps1.
Não é usado pela IDE nem substitui a validação no Bipide.
"""

import re


def execute(assembly, inputs=()):
    labels, memory, instructions = {}, [], []
    section = None
    for line in assembly.splitlines():
        line = line.strip()
        if not line:
            continue
        if line in (".data", ".text"):
            section = line
        elif section == ".data":
            name, data = line.split(":")
            name = name.strip()
            assert re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name), name
            assert name not in labels
            labels[name] = len(memory)
            values = [int(v.strip()) for v in data.split(",")]
            assert all(-32768 <= v <= 32767 for v in values)
            memory.extend(v & 65535 for v in values)
        elif section == ".text":
            parts = line.split()
            assert 1 <= len(parts) <= 2
            instructions.append(parts)
        else:
            raise AssertionError("Seção ausente")
    assert len(memory) <= 1024
    assert len(instructions) <= 2048
    assert instructions[-1] == ["HLT"]
    acc = index = 0
    queue = iter(inputs)
    output = []
    signed = lambda n: n if n < 32768 else n - 65536
    for parts in instructions:
        op = parts[0]
        arg = parts[1] if len(parts) == 2 else None
        if op in ("HLT", "NOT"):
            assert arg is None
            if op == "HLT":
                break
            acc = (~acc) & 65535
            continue
        assert arg is not None
        if op in ("LDI", "ADDI", "SUBI", "ANDI", "ORI", "XORI", "SLL", "SRL"):
            value = int(arg)
            assert -1024 <= value <= 1023
            if op in ("SLL", "SRL"):
                assert 0 <= value <= 15
        elif arg in ("$in_port", "$out_port", "$indr"):
            assert (op, arg) in (("LD", "$in_port"), ("STO", "$out_port"), ("STO", "$indr"))
            if arg == "$in_port":
                acc = next(queue) & 65535
            elif arg == "$out_port":
                output.append(signed(acc))
            else:
                index = signed(acc)
            continue
        else:
            assert arg in labels, arg
            address = labels[arg] + (index if op in ("LDV", "STOV") else 0)
            assert 0 <= address < len(memory), address
            value = memory[address]
        if op in ("LD", "LDI", "LDV"):
            acc = value
        elif op in ("STO", "STOV"):
            memory[address] = acc
        elif op in ("ADD", "ADDI"):
            acc += value
        elif op in ("SUB", "SUBI"):
            acc -= value
        elif op in ("AND", "ANDI"):
            acc &= value
        elif op in ("OR", "ORI"):
            acc |= value
        elif op in ("XOR", "XORI"):
            acc ^= value
        elif op == "SLL":
            acc <<= value
        elif op == "SRL":
            acc >>= value
        else:
            raise AssertionError(f"Instrução desconhecida: {op}")
        acc &= 65535
    else:
        raise AssertionError("Execução não terminou em HLT")
    assert list(queue) == [], "Entradas não consumidas"
    entries = list(labels.items())
    return output, {name: [signed(v) for v in memory[address:(entries[i+1][1] if i+1 < len(entries) else len(memory))]]
                    for i, (name, address) in enumerate(entries)}
