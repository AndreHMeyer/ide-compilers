"""Regenera exemplos e manifesto: python -m tests.generate_bip_examples."""

import json
from pathlib import Path

from ide.compiler_service import compile_source
from tests.bip_cases import CASES
from tests.bip_machine import execute


def main():
    folder = Path(__file__).resolve().parents[1] / "exemplos" / "bip"
    folder.mkdir(exist_ok=True)
    manifest = []
    for name, source, inputs, expected in CASES:
        result = compile_source(source)
        if not result.success:
            raise RuntimeError(f"{name}: {result.message}")
        actual, memory = execute(result.assembly_code, inputs)
        if actual != expected:
            raise AssertionError((name, actual, expected))
        (folder / f"{name}.src").write_text(source + "\n", encoding="utf-8", newline="\n")
        (folder / f"{name}.asm").write_text(result.assembly_code, encoding="utf-8", newline="\n")
        manifest.append({"name": name, "assembly": f"{name}.asm", "inputs": inputs, "outputs": expected,
                         "memory": {k: v for k, v in memory.items() if k.startswith("v")}})
    (folder / "casos.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# Exemplos BIP IV", "", "Os casos 01–15 correspondem aos testes funcionais do pedido. Os demais",
             "cobrem main, limites de 16 bits, entrada múltipla e índices aninhados.", "",
             "Compile o `.src` na IDE ou abra o `.asm` no editor Assembly do Bipide 3.0,",
             "selecione BIP IV e simule. Observe **cada** escrita na porta de saída.", "",
             "| Programa | Fonte | Assembly | Entradas, na ordem | Saídas, na ordem |",
             "| --- | --- | --- | --- | --- |"]
    for case in manifest:
        name = case["name"]
        inputs = ", ".join(map(str, case["inputs"])) or "—"
        outputs = ", ".join(map(str, case["outputs"])) or "—"
        lines.append(f"| {name} | [src]({name}.src) | [asm]({name}.asm) | {inputs} | {outputs} |")
    lines += ["", "O [manifesto](casos.json) também contém os valores finais de todas as células",
              "dos símbolos. [Roteiro manual e evidências](../../docs/bip_iv.md).", "",
              "O caso 29 conserva avisos semânticos; o alvo reserva memória inicialmente zero.",
              "No caso 16, comandos globais executam antes de main. No caso 27, HLT",
              "encerra no return; o print posterior é validado, mas não executa.", "",
              "Regenerar após mudanças no gerador: `python -m tests.generate_bip_examples`."]
    (folder / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"{len(manifest)} programas .src/.asm e manifesto gerados.")


if __name__ == "__main__":
    main()
