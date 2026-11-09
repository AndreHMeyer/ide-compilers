from pathlib import Path
import random
import unittest

from codegen.bip_generator import AssemblyProgram, BIPCodeGenerator, CodeGenerationError, MemoryAllocator
from ide.compiler_service import Lexico, Semantico, Sintatico, analyze_source, compile_source
from tests.bip_cases import CASES
from tests.bip_machine import execute


class CodeGenerationTests(unittest.TestCase):
    def compiled(self, source):
        result = compile_source(source)
        self.assertTrue(result.success, result.message)
        self.assertTrue(result.analysis_success)
        self.assertEqual(result.codegen_status, "success")
        self.assertFalse(result.errors)
        self.assertTrue(result.assembly_code.startswith(".data\n"))
        self.assertTrue(result.assembly_code.endswith("HLT\n"))
        return result

    def test_declarations_do_not_emit_execution(self):
        r = self.compiled("int a,b,v[3],w[5];")
        self.assertEqual(r.assembly_code.split(".text\n")[1], "    HLT\n")
        self.assertIn("v2 : 0, 0, 0\n", r.assembly_code)
        self.assertIn("v3 : 0, 0, 0, 0, 0\n", r.assembly_code)

    def test_exact_simple_fixture(self):
        r = self.compiled("int a=10;print(a);")
        self.assertEqual(r.assembly_code, ".data\nv0 : 0\n\n.text\n    LDI 10\n    STO v0\n    LD v0\n    STO $out_port\n    HLT\n")

    def test_large_literal_uses_memory_not_ldi(self):
        r = self.compiled("print(1023,1024,-1024,-1025,32767,-32768);")
        self.assertNotIn("LDI 1024", r.assembly_code)
        self.assertNotIn("LDI 32767", r.assembly_code)
        self.assertEqual(execute(r.assembly_code)[0], [1023, 1024, -1024, -1025, 32767, -32768])

    def test_symbol_identity_and_internal_names(self):
        r = self.compiled("int t0=1,c0=2,v0=3;{int t0=4;print(t0);}print(t0,c0,v0);")
        self.assertEqual(execute(r.assembly_code)[0], [4, 1, 2, 3])
        self.assertEqual(len({s.uid for s in r.symbols}), 4)

    def test_static_dimension_can_fold_non_runtime_operator(self):
        r = self.compiled("int v[(2+3)*2];v[9]=17;print(v[9]);")
        self.assertEqual(execute(r.assembly_code)[0], [17])

    def test_integer_ir_preserves_operator_and_symbol(self):
        source = "int a=10;int b=a-(2+1);"
        semantic = Semantico(source)
        Sintatico().parse(Lexico(source), semantic)
        expression = semantic.program[-1].expression
        self.assertEqual(expression.operator, "-")
        self.assertEqual(expression.operands[1].operator, "+")
        self.assertIs(expression.operands[0].reference.symbol, semantic.symbols[0])

    def test_consecutive_compilations_and_reusable_generator(self):
        first = self.compiled("int a[3]=2;print(a[1]+32767);")
        self.assertEqual(compile_source("print(1*2);").assembly_code, "")
        next_result = self.compiled("print(1);")
        self.assertEqual(next_result.assembly_code, compile_source("print(1);").assembly_code)
        self.assertNotIn("v0", next_result.assembly_code)
        semantic = Semantico("int x=1;")
        Sintatico().parse(Lexico("int x=1;"), semantic)
        generator = BIPCodeGenerator()
        self.assertEqual(generator.generate(semantic.program, semantic.symbols),
                         generator.generate(semantic.program, semantic.symbols))
        self.assertEqual(first.assembly_code, compile_source("int a[3]=2;print(a[1]+32767);").assembly_code)

    def test_random_nested_arithmetic(self):
        rng = random.Random(177)
        for _ in range(80):
            a, b, c, d = [rng.randint(-32767, 32767) for _ in range(4)]
            source = f"int a={a},b={b},c={c},d={d};print((a-b)-(c+d));"
            r = self.compiled(source)
            expected = ((a-b-c-d+32768) % 65536)-32768
            self.assertEqual(execute(r.assembly_code)[0], [expected])

    def test_frontend_failures_never_generate(self):
        for source, kind in (("int a=@;", "lexical_error"), ("int a=;", "syntactic_error"),
                             ("x=1;", "semantic_error"), ('int a="x";', "semantic_error"),
                             ("int a;int a;", "semantic_error"), ("", "empty")):
            with self.subTest(source=source):
                r = compile_source(source)
                self.assertEqual(r.kind, kind)
                self.assertFalse(r.assembly_code)
                self.assertEqual(r.codegen_status, "skipped")

    def test_generation_error_preserves_semantics_and_warnings(self):
        r = compile_source("int unused;\nprint(2*3);")
        self.assertEqual(r.kind, "codegen_error")
        self.assertFalse(r.success)
        self.assertTrue(r.analysis_success)
        self.assertEqual((r.line, r.column), (2, 8))
        self.assertEqual(r.errors[0].phase, "codegen")
        self.assertEqual(r.warnings[0].code, "unused")
        self.assertFalse(r.symbols_partial)
        self.assertFalse(r.assembly_code)

    def test_validator_rejects_invalid_instructions_and_operands(self):
        for instruction in (("MUL", "v0"), ("LDI", 1024), ("LD", "missing"),
                            ("SLL", "v0"), ("SRL", 16), ("NOT", 1), ("STO", "$in_port")):
            with self.subTest(instruction=instruction), self.assertRaises(CodeGenerationError):
                AssemblyProgram({"v0": (0,)}, [instruction, ("HLT", None)]).render()
        with self.assertRaises(CodeGenerationError):
            AssemblyProgram({"bad label": (0,)}, [("HLT", None)]).render()
        with self.assertRaises(CodeGenerationError):
            AssemblyProgram({}, [("LDI", 1)]).render()
        allocator = MemoryAllocator(AssemblyProgram())
        allocator.reserve("v0", [0])
        with self.assertRaises(CodeGenerationError):
            allocator.reserve("v0", [0])

    def test_full_memory_without_temporaries(self):
        r = self.compiled("int v[1024];")
        self.assertEqual(r.assembly_code.count(","), 1023)

    def test_fixtures_match_generation(self):
        folder = Path(__file__).resolve().parents[1] / "exemplos" / "bip"
        for name, source, inputs, outputs in CASES:
            with self.subTest(case=name):
                self.assertEqual((folder / (name + ".src")).read_text(encoding="utf-8").strip(), source)
                assembly = (folder / (name + ".asm")).read_text(encoding="utf-8")
                self.assertEqual(assembly, self.compiled(source).assembly_code)
                self.assertEqual(execute(assembly, inputs)[0], outputs)


def functional_case(source, inputs, outputs):
    def test(self):
        result = self.compiled(source)
        actual, memory = execute(result.assembly_code, inputs)
        self.assertEqual(actual, outputs)
        if "input(" in source:
            self.assertIn("LD $in_port", result.assembly_code)
        if "print(" in source:
            self.assertIn("STO $out_port", result.assembly_code)
        if "numeros[" in source or "v[" in source:
            self.assertIn("$indr", result.assembly_code)
    return test


for name, source, inputs, outputs in CASES:
    setattr(CodeGenerationTests, "test_execution_" + name, functional_case(source, inputs, outputs))


UNSUPPORTED = {
    "float": "float x=8.5;", "double": "double x=1;", "char": "char x='a';",
    "bool": "bool x=true;", "string": 'print("texto");',
    "multiply": "print(2*3);", "divide": "print(8/2);", "modulo": "print(8%3);",
    "comparison": "print(1<2);", "logical": "print(true&&false);",
    "if": "if(true){print(1);}", "while": "while(false){}",
    "do": "do{}while(false);", "for": "for(;;){}",
    "function": "int f(){return 1;}", "recursion": "int f(int n){if(n<1){return 0;}return f(n-1);}",
    "main_call": "int main(){return 0;}main();", "main_args": "int main(int n){return 0;}",
    "main_return": "int main(){return 1;}", "main_unreachable": "int main(){return 0;print(1*2);}",
    "large_decimal": "print(32768);", "negative_underflow": "print(-32769);",
    "large_hex": "print(0x10000);", "huge_literal": "print(" + "9"*1001 + ");",
    "dynamic_size": "int n=3;int v[n];", "large_size": "int v[1025];",
    "data_overflow": "int v[1024],x;", "temps_overflow": "int v[1024];v[0]=1;",
    "code_overflow": "print(1);" * 1024,
    "dynamic_shift": "int n=2;print(5<<n);", "negative_shift": "print(5<<-1);",
    "large_shift": "print(5>>16);", "invalid_dimension": "int v[2/0];",
}


def unsupported_case(source):
    def test(self):
        self.assertTrue(analyze_source(source).success, source)
        result = compile_source(source)
        self.assertEqual(result.kind, "codegen_error", result.message)
        self.assertFalse(result.assembly_code)
        self.assertFalse(result.symbols_partial)
        self.assertEqual(result.codegen_status, "error")
        self.assertIsNotNone(result.line)
    return test


for name, source in UNSUPPORTED.items():
    setattr(CodeGenerationTests, "test_unsupported_" + name, unsupported_case(source))


if __name__ == "__main__":
    unittest.main()
