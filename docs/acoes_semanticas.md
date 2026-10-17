# Contrato das ações semânticas

Referência da exportação Python presente em `Analisador_Sintatico/Constants.py`:
307 estados SLR, 123 produções, 59 números distintos de ações e
`FIRST_SEMANTIC_ACTION = 108`. A tabela léxica possui 51 estados.

`Sintatico.step()` trata `SLRAction.ACTION`, empilha a transição correspondente
e chama `semantic.execute_action(cmd[1], previous_token)`. O token recebido é
o último token deslocado, não necessariamente um identificador. Por exemplo,
`#10` recebe `(` e `#22` recebe `]`. A implementação guarda os identificadores
nas ações `#2` e `#20`, em vez de tentar recuperá-los desses delimitadores.

Os pontos abaixo foram conferidos por rastreamento do parser gerado. O teste
`test_all_exported_actions_are_implemented_and_executed` compara os números
efetivamente executados com todas as ações presentes na tabela exportada.
Não existe outro parser ou reconhecimento de sintaxe por expressões regulares.

| Ação | Ponto observado / responsabilidade |
| --- | --- |
| `#50` | Antes dos elementos do programa; reinicia símbolos, escopos, pilhas, avisos e fluxo. Pode receber token `None`. |
| `#51` | Após os elementos, no fim da entrada; verifica equilíbrio das pilhas, analisa inicialização e finaliza avisos. |
| `#1` | Após o tipo, inclusive `void` de procedimentos; guarda o tipo declarado. |
| `#2` | Após o ID declarado; guarda seu token e posição. Ainda não registra modalidade. |
| `#3` | Declarador escalar; insere variável antes de sua expressão inicializadora. |
| `#4` | Após `[` do declarador vetorial; insere vetor antes da expressão de tamanho. |
| `#5` | Após expressão inicializadora; verifica atribuição e registra escrita, sem contar a declaração como uso. |
| `#6` | Após `]` do declarador; valida tamanho inteiro positivo quando constante. |
| `#7` | Após expressão da atribuição; verifica destino/tipo e registra escrita depois das leituras do lado direito. |
| `#8` | Após cada lvalue de `input`; registra escrita sem ler o destino. |
| `#9` | Após cada expressão de `print`; exige valor escalar e consome o resultado. |
| `#10` | Após `(` na definição; registra função no escopo global e abre seu escopo antes dos parâmetros. |
| `#11` | Parâmetro escalar; registra símbolo e adiciona à assinatura. |
| `#12` | Após `[` de parâmetro vetorial; registra parâmetro com modalidade vetorial. |
| `#13` | Após `]` de parâmetro com tamanho; verifica dimensão. Não ocorre em `[]`. |
| `#14` | Após `)` da assinatura; delimitador de assinatura completa. Os parâmetros já foram registrados e a função está disponível para recursão. |
| `#15` | Após `}` do corpo da função; fecha o escopo da função e guarda seu fluxo isolado. |
| `#18` | Após `return;`; exige procedimento `void`. |
| `#19` | Após `return exp;`; exige função não void e retorno compatível. |
| `#20` | Após ID utilizado; resolve nome no escopo atual e ancestrais, empilhando uma referência independente. |
| `#21` | lvalue escalar; prepara destino sem registrar leitura. |
| `#22` | lvalue indexado, após `]`; valida vetor/índice e preserva referência ao destino. |
| `#23` | ID como expressão; registra leitura e empilha tipo escalar ou referência vetorial completa. |
| `#24` | Elemento como expressão, após `]`; valida índice, registra leitura do elemento e empilha tipo. |
| `#25` | Após `(` de chamada; exige função e abre uma lista de argumentos própria. |
| `#26` | Após cada argumento; transfere seu valor tipado à chamada mais interna. |
| `#27` | Após `)` de chamada; valida quantidade, tipos/modalidades/dimensões e empilha o tipo de retorno. |
| `#28` | Chamada em posição de comando; descarta o resultado, inclusive void. |
| `#30`, `#31` | Após `{` e `}` de bloco comum; abrem/encerram escopo e mantêm histórico dos símbolos. |
| `#32` | Após condição; exige bool e consome seu valor. No for ocorre antes do segundo `;`. |
| `#33` | Após `for`; abre escopo que inclui cabeçalho e corpo, e inicia registro de fluxo. |
| `#48` | Após primeiro `;` do for; termina inicialização e começa condição. |
| `#49` | Após segundo `;` do for; termina condição e começa incremento. |
| `#52` | Após `)` do for; termina incremento textual e começa corpo. |
| `#34` | Após bloco do for; organiza inicialização → condição → corpo → incremento e encerra escopo. |
| `#40` | Depois de verificar condição do if; inicia caminho then. |
| `#42` | Após `else`; encerra then e inicia caminho independente. |
| `#43` | Após último bloco do if; registra a junção dos caminhos. |
| `#44`, `#45` | Após `while` e após seu bloco; delimitam laço que pode não executar. |
| `#46`, `#47` | Após `do` e após `;` do while final; delimitam corpo executado antes da condição. |
| `#60` | Após operador; empilha token do operador, inclusive unário. |
| `#62` | Após operando unário; valida `-`, `!` ou `~`. |
| `#63` | Inteiros decimais, binários e hexadecimais. |
| `#64`, `#65`, `#66`, `#67` | Literais float, char, string e bool, respectivamente. |
| `#71`, `#72` | Combinações de `||` e `&&`. |
| `#73`, `#74`, `#75` | Combinações de `|`, `^` e `&`. |
| `#76` | Comparações relacionais e de igualdade; resultado bool. |
| `#77` | Deslocamentos `<<` e `>>`. |
| `#78` | Soma/subtração. |
| `#79` | Multiplicação/divisão/módulo. |

As pilhas de valores, operadores, referências, destinos e chamadas são distintas.
Assim, em `vetor[i + obterIndice()] = somar(1, 2);`, a chamada no índice não
substitui o símbolo do vetor e a chamada do lado direito não substitui seu destino.
As reduções da gramática determinam precedência e associação das expressões.

## Fluxo e tratamento de erros

As ações verificam nomes e tipos imediatamente e constroem operações semânticas
de leitura, escrita, declaração, escopo, desvio, laço e retorno. O final `#51`
percorre somente essas operações já estruturadas. Não lê código-fonte, não
retokeniza, não reconhece produções e não executa o programa. Isso permite
analisar o incremento do for depois do corpo, embora venha antes no texto.

No serviço da IDE, `defer_errors=True` conserva o primeiro erro semântico e
interrompe as ações seguintes, deixando o mesmo parser concluir a verificação
léxica/sintática. Se uma dessas fases falhar, seu diagnóstico tem prioridade.
Não se publicam avisos incompletos em uma análise com erro. A API direta
`Semantico()` mantém o contrato de lançar `SemanticError` imediatamente.

## Reexportação do WebGALS

Não foi necessário acrescentar ações ou alterar produções/tabelas. Todas as
verificações solicitadas têm pontos suficientes na exportação atual.

O arquivo `../Analisador_Sintatico.vgls` encontrado fora deste repositório
contém a gramática da etapa anterior, sem as ações, e não corresponde às tabelas
Python atuais. Não foi alterado nem utilizado como substituto da exportação.
Antes de uma futura reexportação, salve também a especificação atualizada do
WebGALS no controle de versão. Reexportar aquele arquivo antigo removeria a
instrumentação necessária. O serviço detecta uma análise sem conclusão `#51`
e os testes conferem a cobertura dos marcadores.

Preserve `Semantico.py` e os módulos `semantic_*.py`, além das correções de
compatibilidade descritas no README. Não sobrescreva essa implementação com o
stub do gerador que apenas imprime ações.
