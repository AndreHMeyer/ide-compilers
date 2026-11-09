"""Critérios da etapa 3 exercitados pelo scanner/parser reais, sem mocks."""

from itertools import product
from pathlib import Path
import unittest

from ide.compiler_service import Lexico, Semantico, Sintatico, analyze_source as compile_source
from Constants import PARSER_TABLE, SLRAction


class SemanticTests(unittest.TestCase):
    def valid(self, source):
        result = compile_source(source)
        self.assertEqual(result.kind, "success", result.message)
        self.assertTrue(result.success)
        self.assertFalse(result.symbols_partial)
        self.assertFalse(result.errors)
        return result

    def invalid(self, source, text="", kind="semantic_error"):
        result = compile_source(source)
        self.assertEqual(result.kind, kind, result.message)
        self.assertFalse(result.success)
        self.assertTrue(result.symbols_partial)
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(result.errors[0].severity, "error")
        self.assertEqual(result.errors[0].phase, kind.removesuffix("_error"))
        self.assertIn(text, result.message)
        self.assertFalse(result.warnings)
        return result

    def uninitialized(self, source, expected):
        result = self.valid(source)
        warnings = [warning for warning in result.warnings if warning.code == "uninitialized"]
        self.assertEqual(len(warnings), expected, [w.formatted for w in warnings])
        for warning in warnings:
            self.assertEqual(warning.severity, "warning")
            self.assertEqual(warning.phase, "semantic")
            self.assertIsNotNone(warning.line)
            self.assertIsNotNone(warning.column)
        return result

    def test_symbol_metadata_and_signatures(self):
        result = self.valid("int g=1; float v[3]; double f(int p, char a[]) { double local=p; return local; }")
        g, v, f, p, a, local = result.symbols
        self.assertEqual([s.name for s in result.symbols], ["g", "v", "f", "p", "a", "local"])
        self.assertEqual([s.type for s in result.symbols], ["int", "float", "double", "int", "char", "double"])
        self.assertEqual([s.modality for s in result.symbols], ["variável", "vetor", "função", "parâmetro", "parâmetro", "variável"])
        self.assertEqual((g.scope_id, g.scope, g.line, g.column), (0, "global", 1, 5))
        self.assertEqual((v.size, v.is_array), (3, True))
        self.assertEqual(f.signature, "double f(int, char[])")
        self.assertEqual(f.parameters, [p, a])
        self.assertEqual(p.scope_id, a.scope_id)
        self.assertEqual(p.scope_id, local.scope_id)
        self.assertEqual(p.parent_scope_id, 0)
        self.assertTrue(p.initialized and a.initialized and local.initialized)
        self.assertEqual(len({s.uid for s in result.symbols}), len(result.symbols))

    def test_all_types_and_multiple_declarators(self):
        result = self.valid('int a=1,b=2,v[3];float f=2.5;double d=f+a;char c=\'x\';string s="texto";bool ok=true;')
        self.assertEqual([s.type for s in result.symbols], ["int", "int", "int", "float", "double", "char", "string", "bool"])

    def test_global_lookup_and_scope_history(self):
        result = self.valid("int g=1; { int x=g; {int y=x;print(y);} } print(g);")
        self.assertEqual(len(result.symbols), 3)
        self.assertTrue(all(s.initialized and s.used for s in result.symbols))
        self.assertEqual([s.parent_scope_id for s in result.symbols], [None, 0, 1])

    def test_for_all_optional_combinations(self):
        for init, condition, increment in product(("", "i=0"), ("", "i<3"), ("", "i=i+1")):
            with self.subTest(init=init, condition=condition, increment=increment):
                self.valid(f"int i=0;for({init};{condition};{increment}){{print(i);}}")

    def test_for_multiple_declarations(self):
        result = self.valid("for(int i=0,j=1,v[2];i<j;i=i+1){v[0]=i;print(v[0]);}")
        self.assertEqual(len({s.scope_id for s in result.symbols}), 1)
        self.assertNotEqual(result.symbols[0].scope_id, 0)

    def test_unused_all_modalities(self):
        result = self.valid("int x=1; int v[2]; void f(int p){return;}")
        unused = [w for w in result.warnings if w.code == "unused"]
        self.assertEqual(len(unused), 4)
        self.assertTrue(all(not s.used for s in result.symbols))

    def test_writes_count_as_use_but_initializers_do_not(self):
        result = self.valid("int a=1,b;int v[2]; b=2;input(v[0]);")
        self.assertEqual([s.used for s in result.symbols], [False, True, True])
        self.assertEqual([s.reads for s in result.symbols], [0, 0, 0])
        self.assertEqual([s.writes for s in result.symbols], [1, 1, 1])
        self.assertEqual([w.code for w in result.warnings], ["unused"])

    def test_plain_assignment_is_not_read(self):
        self.uninitialized("int x;x=10;print(x);", 0)

    def test_read_then_write(self):
        self.uninitialized("int x;print(x);x=1;print(x);", 1)

    def test_self_assignment_reads_before_write(self):
        self.uninitialized("int x;x=x+1;print(x);", 1)

    def test_self_initializer(self):
        self.uninitialized("int x=x;print(x);", 1)

    def test_if_without_else(self):
        result = self.uninitialized("int x;if(true){x=1;}print(x);", 1)
        self.assertFalse(result.symbols[0].initialized)

    def test_if_else_both_paths(self):
        result = self.uninitialized("int x;if(true){x=1;}else{input(x);}print(x);", 0)
        self.assertTrue(result.symbols[0].initialized)

    def test_if_else_only_one_path(self):
        self.uninitialized("int x;if(true){x=1;}else{}print(x);", 1)

    def test_else_does_not_inherit_then(self):
        self.uninitialized("int x;if(true){x=1;}else{print(x);}", 1)

    def test_nested_conditionals(self):
        self.uninitialized("int x;if(true){if(false){x=1;}else{x=2;}}else{x=3;}print(x);", 0)
        self.uninitialized("int x;if(true){if(false){x=1;}}else{x=3;}print(x);", 1)

    def test_while_might_not_run(self):
        self.uninitialized("int x;while(true){x=1;}print(x);", 1)

    def test_while_condition_reads_before_body(self):
        self.uninitialized("int x;while(x<2){x=1;}", 1)

    def test_do_executes_once(self):
        self.uninitialized("int x;do{x=1;}while(x<2);print(x);", 0)

    def test_do_nested_if_is_not_definite(self):
        self.uninitialized("int x;do{if(true){x=1;}}while(false);print(x);", 1)

    def test_for_init_is_definite(self):
        self.uninitialized("int x;for(x=1;false;){}print(x);", 0)

    def test_for_body_might_not_run(self):
        self.uninitialized("int x;for(;false;){x=1;}print(x);", 1)

    def test_for_increment_cannot_initialize_first_body(self):
        result = self.uninitialized("int x;for(;true;x=1){print(x);}print(x);", 2)
        self.assertFalse(result.symbols[0].initialized)

    def test_for_increment_reads_state_after_body(self):
        self.uninitialized("int x;for(;true;x=x+1){x=1;}", 0)

    def test_for_increment_after_conditional_body(self):
        self.uninitialized("int x;for(;true;x=x+1){if(true){x=1;}}", 1)

    def test_nested_for_preserves_each_increment(self):
        self.uninitialized("int x;for(;true;x=x+1){for(;true;x=x+1){x=1;}}", 1)

    def test_shadow_does_not_initialize_outer(self):
        self.uninitialized("int x;{int x=1;print(x);}print(x);", 1)

    def test_array_elements_are_independent(self):
        result = self.uninitialized("int v[3];v[0]=1;print(v[0],v[1]);", 1)
        self.assertFalse(result.symbols[0].initialized)
        self.assertEqual(result.symbols[0].initialized_elements, (0,))

    def test_array_input_and_constant_index_expression(self):
        result = self.uninitialized("int v[3];input(v[1+1]);print(v[2]);", 0)
        self.assertEqual(result.symbols[0].initialized_elements, (2,))

    def test_array_dynamic_index_conservative(self):
        self.uninitialized("int v[2];int i=0;v[i]=1;print(v[0],v[i]);", 2)

    def test_all_elements_initialized_supports_dynamic_read(self):
        result = self.uninitialized("int v[2];int i=0;v[0]=1;v[1]=2;print(v[i]);", 0)
        self.assertTrue(result.symbols[0].initialized)

    def test_array_broadcast_initializer(self):
        result = self.uninitialized("int v[2]=3;print(v[0],v[1]);", 0)
        self.assertTrue(result.symbols[0].initialized)

    def test_array_branch_intersection(self):
        self.uninitialized("int v[2];if(true){v[0]=1;}else{v[1]=1;}print(v[0],v[1]);", 2)
        self.uninitialized("int v[2];if(true){v[0]=1;}else{v[0]=2;}print(v[0]);", 0)

    def test_array_complete_and_partial_branch_intersection(self):
        self.uninitialized("int v[2];if(true){v[0]=1;v[1]=1;}else{v[0]=2;}print(v[0],v[1]);", 1)

    def test_reference_survives_nested_calls_in_index(self):
        result = self.valid("int idx(){return 0;}int v[2];int i=0;v[i+idx()]=10;input(v[idx()]);print(v[idx()]);")
        self.assertEqual(result.symbols[1].writes, 2)
        self.assertEqual(result.symbols[1].reads, 1)

    def test_array_inside_array_index(self):
        self.valid("int a[3]=0,b[2]=1;a[b[0]]=b[a[0]];print(a[1]);")

    def test_function_parameters_start_initialized(self):
        self.uninitialized("int f(int x,int v[]){return x+v[0];}", 0)

    def test_function_definition_does_not_initialize_globals(self):
        self.uninitialized("int x;void f(){x=1;}print(x);", 1)

    def test_function_call_effects_are_not_assumed(self):
        self.uninitialized("int x;void f(){x=1;}f();print(x);", 1)

    def test_function_warnings_do_not_mutate_global_state(self):
        self.uninitialized("int x;void f(){x=1;}void g(){print(x);}input(x);print(x);", 1)

    def test_returning_branch_excluded_from_join(self):
        self.uninitialized("int f(bool c){int x;if(c){return 1;}else{x=2;}return x;}", 0)

    def test_unreachable_reads_after_return_do_not_warn(self):
        self.uninitialized("int f(){int x;return 1;print(x);}", 0)

    def test_return_preserves_initialization_of_closed_block(self):
        result = self.valid("int f(){{int x=1;return x;}}print(f());")
        self.assertTrue(result.symbols[1].initialized)

    def test_multiple_returns_intersect_scope_display_state(self):
        result = self.valid("int f(bool b){int x;if(b){return 1;}x=2;return x;}")
        self.assertTrue(result.symbols[1].initialized)
        self.assertFalse(result.symbols[2].initialized)

    def test_array_parameters_accept_arrays_only(self):
        self.uninitialized("int f(int a[]){return a[0];}int v[2]=1;print(f(v));", 0)

    def test_sized_array_parameter(self):
        self.valid("int f(int a[2]){return a[0];}int v[2]=1;print(f(v));")

    def test_nested_function_calls_keep_arguments_separate(self):
        self.uninitialized("int somar(int a,int b){return a+b;}int resultado=somar(somar(1,2),somar(3,4));print(resultado);", 0)

    def test_no_parameter_function_and_void_procedure(self):
        self.uninitialized('int f(){return 1;}void p(){print("ok");}p();print(f());', 0)

    def test_nested_block_can_shadow_function_parameter(self):
        result = self.valid("int f(int x){{int x=1;print(x);}return x;}print(f(1));")
        self.assertNotEqual(result.symbols[1].scope_id, result.symbols[2].scope_id)

    def test_all_paths_return(self):
        self.valid("int f(bool b){if(b){return 1;}else{return 2;}}print(f(true));")

    def test_dynamic_array_size(self):
        result = self.uninitialized("int n=2;int v[n];v[0]=1;print(v[0]);", 0)
        self.assertIsNone(result.symbols[1].size)

    def test_numeric_promotions_and_precedence(self):
        self.valid("int x=10;float y=x+2.5;double z=y+x;bool b=!(x>2)&&true||false;print(z,b);")

    def test_integer_constant_folding_matches_precedence(self):
        result = self.valid("int v[(2+3)*4-1];int w[8>>1+1];int u[-(-3)];")
        self.assertEqual([s.size for s in result.symbols], [19, 2, 3])

    def test_all_valid_operators(self):
        for op in ("+", "-", "*", "/", "%", "&", "|", "^", "<<", ">>"):
            with self.subTest(op=op):
                self.valid(f"int x=8 {op} 2;print(x);")
        for op in (">", "<", ">=", "<=", "==", "!="):
            with self.subTest(op=op):
                self.valid(f"bool x=1 {op} 2.5;print(x);")
        self.valid("bool b=true&&false||!false;int x=~(-1);char c='a';bool d=c<'z';")
        self.valid('bool b="a"=="b";bool c=true!=false;')

    def test_invalid_operator_type_matrix(self):
        for expr in ('"x"+1', '"x"-1', '"x"*2', '"x"/2', "1.5%2", "true+1", "1&&true",
                     "true||1", "!1", "~1.5", "-true", "1.5&1", "1|false", "1^2.5", "1<<2.5",
                     "1.5>>1", "true<false", '"a">"b"', '1=="a"', "'a'!=1"):
            with self.subTest(expr=expr):
                self.invalid(f"print({expr});", "operador")

    def test_literal_bases_char_string_and_comments(self):
        result = self.valid('/* cabeçalho */ int v[0b10+0xA]; // linha\nchar c=\'a\';string s="Olá";float r=1.25;')
        self.assertEqual(result.symbols[0].size, 12)

    def test_warnings_have_read_location_and_no_duplicates(self):
        result = self.uninitialized("int x;\nprint(x+x);", 2)
        self.assertEqual([(w.line, w.column) for w in result.warnings], [(2, 7), (2, 9)])
        self.assertEqual(len(set(result.warnings)), 2)

    def test_duplicate_reports_original_and_duplicate_positions(self):
        result = self.invalid("int x;\nfloat x;", "declaração original na linha 1, coluna 5")
        self.assertEqual((result.line, result.column), (2, 7))
        self.assertEqual(len(result.symbols), 1)

    def test_lexical_and_syntactic_errors_suppress_incomplete_warnings(self):
        for source, kind in (("int x;print(x);@", "lexical_error"),
                             ("int x;print(x);int y=;", "syntactic_error"),
                             ("missing=1;int y=;", "syntactic_error"),
                             ("missing=1;@", "lexical_error")):
            with self.subTest(source=source):
                self.invalid(source, kind=kind)

    def test_consecutive_compilations_are_isolated(self):
        first = self.valid("int x=1;print(x);")
        self.invalid('int x="a";')
        second = self.valid("int y;print(y);")
        self.assertEqual([s.name for s in second.symbols], ["y"])
        self.assertEqual([s.name for s in first.symbols], ["x"])
        self.assertEqual(first.warnings, ())
        self.assertEqual(first, compile_source("int x=1;print(x);"))
        self.assertFalse(compile_source("").symbols)

    def test_presentation_examples(self):
        folder = Path(__file__).resolve().parents[1] / "exemplos" / "semantica"
        paths = sorted(folder.glob("*.src"))
        self.assertEqual(len(paths), 4)
        for path in paths:
            with self.subTest(example=path.name):
                source = path.read_text(encoding="utf-8")
                if path.name.startswith(("03", "04")):
                    self.invalid(source)
                else:
                    result = self.valid(source)
                    expected = {"unused", "uninitialized"} if path.name.startswith("02") else set()
                    self.assertEqual({w.code for w in result.warnings}, expected)

    def test_reusing_exported_parser_and_semantic_resets_state(self):
        source = "int x;print(x);"
        parser, semantic = Sintatico(), Semantico(source)
        for _ in range(2):
            parser.parse(Lexico(source), semantic)
            self.assertEqual(len(semantic.symbols), 1)
            self.assertEqual(len(semantic.warnings), 1)
            self.assertTrue(semantic.complete)

    def test_all_exported_actions_are_implemented_and_executed(self):
        source = '''
        int f(int a, int v[], int w[2]) { int x=1; return a+x+v[0]+w[0]; }
        void p(){return;}
        int a=1,v[2]=1;float r=2.5;char c='a';string s="ok";
        bool b=!false||true&&a>0;int bits=~1 & 2 ^ 3 | 4;
        a=-(1+2)*3/4%5<<1>>1;input(a,v[0]);print(a,v[0]);p();
        print(f(a,v,v)); if(b){} if(b){}else{}
        while(b){}do{}while(b);for(int i=0;i<2;i=i+1){}
        '''
        semantic = Semantico(source)
        Sintatico().parse(Lexico(source), semantic)
        exported = {value for row in PARSER_TABLE for command, value in row if command == SLRAction.ACTION}
        self.assertEqual(exported, Semantico.ACTIONS)
        self.assertEqual(semantic.executed_actions, exported)
        self.assertTrue(semantic.complete)


# Os 16 exemplos obrigatórios têm nomes/resultados independentes no unittest.
REQUIRED = [
    ("01_success", "int x=10;print(x);", "success", None, ["x"]),
    ("02_undeclared", "x=10;", "semantic_error", None, []),
    ("03_duplicate", "int x;int x;", "semantic_error", None, ["x"]),
    ("04_unused", "int x=10;", "success", "unused", ["x"]),
    ("05_uninitialized", "int x;print(x);", "success", "uninitialized", ["x"]),
    ("06_input", "int x;input(x);print(x);", "success", None, ["x"]),
    ("07_assignment_type", 'int x="abc";', "semantic_error", None, ["x"]),
    ("08_expression_type", 'int x="abc"*2;', "semantic_error", None, ["x"]),
    ("09_closed_scope", "{int x=10;}print(x);", "semantic_error", None, ["x"]),
    ("10_shadow", "int x=10;{int x=20;print(x);}print(x);", "success", None, ["x", "x"]),
    ("11_bitwise", "int x=10;int y=2;x=x<<y;x=x>>1;x=x&y;print(x);", "success", None, ["x", "y"]),
    ("12_index_type", 'int vetor[10];print(vetor["abc"]);', "semantic_error", None, ["vetor"]),
    ("13_recursion", "int fatorial(int n){if(n<=1){return 1;}return n*fatorial(n-1);}int resultado=fatorial(5);print(resultado);",
     "success", None, ["fatorial", "n", "resultado"]),
    ("14_for_scope", "for(int i=0;i<5;i=i+1){print(i);}print(i);", "semantic_error", None, ["i"]),
    ("15_syntax", "int x=;", "syntactic_error", None, ["x"]),
    ("16_lexical", "int x;x=@;", "lexical_error", None, ["x"]),
]


def required_case(source, kind, warning, names):
    def test(self):
        result = self.valid(source) if kind == "success" else self.invalid(source, kind=kind)
        self.assertEqual([s.name for s in result.symbols], names)
        self.assertEqual([w.code for w in result.warnings], [warning] if warning else [])
    return test


for name, source, kind, warning, names in REQUIRED:
    setattr(SemanticTests, "test_required_" + name, required_case(source, kind, warning, names))


INVALID = {
    "sibling_scope": ("{int x=1;}{print(x);}", "não declarado"),
    "different_functions": ("void f(){int x;}void g(){print(x);}", "não declarado"),
    "duplicate_parameter": ("int f(int x,int x){return x;}", "já declarado"),
    "parameter_local_collision": ("int f(int x){int x;return x;}", "já declarado"),
    "duplicate_function": ("void f(){}void f(){}", "já declarado"),
    "function_variable_collision": ("int f;void f(){}", "já declarado"),
    "array_variable_collision": ("int x;float x[2];", "já declarado"),
    "for_header_body_visibility": ("for(;true;x=1){int x;}", "não declarado"),
    "narrow_float_to_int": ("int x=1.5;", "atribuir float a int"),
    "narrow_double_to_float": ("double d=1.5;float f=d;", "atribuir double a float"),
    "bool_to_int": ("int x=true;", "atribuir bool a int"),
    "int_to_char": ("char c=65;", "atribuir int a char"),
    "condition_int": ("if(1){}", "tipo bool"),
    "while_condition_string": ('while("s"){}', "tipo bool"),
    "do_condition_int": ("do{}while(1);", "tipo bool"),
    "for_condition_int": ("for(;1;){}", "tipo bool"),
    "scalar_index": ("int x=0;print(x[0]);", "não é um vetor"),
    "array_assignment_without_index": ("int v[2];v=1;", "exige um índice"),
    "array_as_scalar": ("int v[2];int x=v;", "valor escalar"),
    "array_arithmetic": ("int v[2];print(v+1);", "valor escalar"),
    "array_print": ("int v[2];print(v);", "valor escalar"),
    "array_input": ("int v[2];input(v);", "exige um índice"),
    "array_element_type": ('int v[2];v[0]="s";', "atribuir string a int"),
    "array_size_type": ("int v[2.5];", "tamanho do vetor"),
    "array_size_zero": ("int v[0];", "positivo"),
    "array_size_negative": ("int v[-1];", "positivo"),
    "array_negative_index": ("int v[2];print(v[-1]);", "fora dos limites"),
    "array_index_upper_bound": ("int v[2];v[2]=1;", "fora dos limites"),
    "array_bool_index": ("int v[2];print(v[true]);", "tipo int"),
    "missing_function": ("f();", "não declarado"),
    "forward_function": ("f();void f(){}", "não declarado"),
    "variable_called": ("int x=1;x();", "não é uma função"),
    "assign_to_function": ("void f(){}f=1;", "por uma chamada"),
    "read_function_without_call": ("int f(){return 1;}print(f);", "por uma chamada"),
    "too_few_arguments": ("int f(int x){return x;}f();", "espera 1"),
    "too_many_arguments": ("int f(){return 1;}f(1);", "espera 0"),
    "argument_type": ('int f(int x){return x;}f("s");', "atribuir string a int"),
    "array_argument_scalar": ("void f(int a[]){}f(1);", "exige um vetor"),
    "scalar_argument_array": ("void f(int a){}int v[2];f(v);", "valor escalar"),
    "array_argument_type": ("void f(float a[]){}int v[2];f(v);", "vetor de float"),
    "array_argument_size": ("void f(int a[2]){}int v[3];f(v);", "tamanho 2"),
    "void_value": ("void f(){}int x=f();", "não produz um valor"),
    "void_argument": ("void f(){}void g(int a){}g(f());", "não produz um valor"),
    "return_outside_function": ("return;", "dentro de uma função"),
    "return_empty_nonvoid": ("int f(){return;}", "deve retornar int"),
    "return_value_void": ("void f(){return 1;}", "não pode retornar um valor"),
    "return_type": ('int f(){return "s";}', "atribuir string a int"),
    "return_missing": ("int f(){}", "sem retornar int"),
    "return_only_one_path": ("int f(bool b){if(b){return 1;}}", "sem retornar int"),
}


def invalid_case(source, message):
    def test(self):
        self.invalid(source, message)
    return test


for name, (source, message) in INVALID.items():
    setattr(SemanticTests, "test_reject_" + name, invalid_case(source, message))


if __name__ == "__main__":
    unittest.main()
