# Exemplos BIP IV

Os casos 01–15 correspondem aos testes funcionais do pedido. Os demais
cobrem main, limites de 16 bits, entrada múltipla e índices aninhados.

Compile o `.src` na IDE ou abra o `.asm` no editor Assembly do Bipide 3.0,
selecione BIP IV e simule. Observe **cada** escrita na porta de saída.

| Programa | Fonte | Assembly | Entradas, na ordem | Saídas, na ordem |
| --- | --- | --- | --- | --- |
| 01_atribuicao | [src](01_atribuicao.src) | [asm](01_atribuicao.asm) | — | 10 |
| 02_soma_subtracao | [src](02_soma_subtracao.src) | [asm](02_soma_subtracao.asm) | — | 25, 15 |
| 03_vetor | [src](03_vetor.src) | [asm](03_vetor.asm) | — | 10, 20, 30 |
| 04_indice_variavel | [src](04_indice_variavel.src) | [asm](04_indice_variavel.asm) | — | 50 |
| 05_parenteses | [src](05_parenteses.src) | [asm](05_parenteses.asm) | — | -5 |
| 06_soma_vetores | [src](06_soma_vetores.src) | [asm](06_soma_vetores.asm) | — | 30 |
| 07_bit_a_bit | [src](07_bit_a_bit.src) | [asm](07_bit_a_bit.asm) | — | 11 |
| 08_shift | [src](08_shift.src) | [asm](08_shift.asm) | — | 20 |
| 09_input | [src](09_input.src) | [asm](09_input.asm) | 5 | 15 |
| 10_input_vetor | [src](10_input_vetor.src) | [asm](10_input_vetor.asm) | 10 | 15 |
| 11_associatividade | [src](11_associatividade.src) | [asm](11_associatividade.asm) | — | 13 |
| 12_expressao_vetores | [src](12_expressao_vetores.src) | [asm](12_expressao_vetores.asm) | — | 13 |
| 13_mesmo_vetor | [src](13_mesmo_vetor.src) | [asm](13_mesmo_vetor.asm) | — | -10 |
| 14_escopos | [src](14_escopos.src) | [asm](14_escopos.asm) | — | 20, 10 |
| 15_negacao | [src](15_negacao.src) | [asm](15_negacao.asm) | — | 5 |
| 16_main | [src](16_main.src) | [asm](16_main.asm) | — | 5, 10 |
| 17_limites | [src](17_limites.src) | [asm](17_limites.asm) | — | -32768, 32767, -32768, -11, 32767, -32768, -1, -1 |
| 18_input_multiplo | [src](18_input_multiplo.src) | [asm](18_input_multiplo.asm) | 7, -3, 42 | 7, -3, 42, 46 |
| 19_preserva_indice | [src](19_preserva_indice.src) | [asm](19_preserva_indice.asm) | — | 10, 15 |
| 20_indices_aninhados | [src](20_indices_aninhados.src) | [asm](20_indices_aninhados.asm) | — | 1 |
| 21_operadores_vetores | [src](21_operadores_vetores.src) | [asm](21_operadores_vetores.asm) | — | 2, 11, 9, -11, 20, 5 |
| 22_ordem | [src](22_ordem.src) | [asm](22_ordem.asm) | — | 13, 17, 22 |
| 23_constantes | [src](23_constantes.src) | [asm](23_constantes.asm) | — | 1024, -1025, 32767, 32767, 10, 10 |
| 24_dimensao | [src](24_dimensao.src) | [asm](24_dimensao.asm) | — | 40 |
| 25_multiplas_atribuicoes | [src](25_multiplas_atribuicoes.src) | [asm](25_multiplas_atribuicoes.asm) | — | 10, 10, 10, 12, 20 |
| 26_constantes_aritmeticas | [src](26_constantes_aritmeticas.src) | [asm](26_constantes_aritmeticas.asm) | — | 3, -2, 5, 20 |
| 27_main_void | [src](27_main_void.src) | [asm](27_main_void.asm) | — | 7 |
| 28_memoria_limite | [src](28_memoria_limite.src) | [asm](28_memoria_limite.asm) | — | 30 |
| 29_unused | [src](29_unused.src) | [asm](29_unused.asm) | — | 0 |
| 30_imediatos | [src](30_imediatos.src) | [asm](30_imediatos.asm) | — | 2, 11, 9, 13, 7, 5, 5 |
| 31_input_indice_aninhado | [src](31_input_indice_aninhado.src) | [asm](31_input_indice_aninhado.asm) | -20 | -20 |

O [manifesto](casos.json) também contém os valores finais de todas as células
dos símbolos. [Roteiro manual e evidências](../../docs/bip_iv.md).

O caso 29 conserva avisos semânticos; o alvo reserva memória inicialmente zero.
No caso 16, comandos globais executam antes de main. No caso 27, HLT
encerra no return; o print posterior é validado, mas não executa.

Regenerar após mudanças no gerador: `python -m tests.generate_bip_examples`.
