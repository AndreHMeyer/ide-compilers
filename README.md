# IDE Compiladores — quatro etapas e Assembly BIP IV

Compilador acadêmico com interface desktop Python/Tkinter. O botão **Compilar
(F9)** integra quatro etapas: scanner léxico gerado pelo WebGALS, parser SLR(1),
análise semântica e geração de assembly BIP IV a partir das ações da gramática.

A aplicação analisa o programa e gera assembly. A execução de `input` e `print`
acontece no **Bipide 3.0**, pelas portas de entrada e saída. A IDE não interpreta
o programa. Usa apenas a biblioteca padrão do Python, sem dependências adicionais.

## Executar

Requisitos: **Python 3.10 ou superior**, Tkinter/Tcl/Tk e sessão gráfica desktop.
Na raiz do projeto:

```console
python main.py
```

Se `python` apontar para o atalho da Microsoft Store, use a instalação real:

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe" main.py
```

O instalador deve incluir Tcl/Tk. No Linux, pode ser necessário `python3-tk`.
A aplicação não precisa de internet.

## Utilizar a IDE

Abra um `.src`/`.txt` ou digite no editor, compile e consulte as abas **Mensagens**
e **Tabela de Símbolos** e **Código Assembly**. Editor e mensagens mantêm fonte monoespaçada de **14
pontos**, tema escuro, rolagem e destaque da linha do erro. Avisos aparecem em
amarelo e não impedem o sucesso. A divisão entre editor e resultados é ajustável.

A tabela mostra os símbolos reais do analisador: identificador, tipo, modalidade,
escopo, utilização, inicialização, linha, coluna e dimensão/assinatura. Possui
rolagem horizontal/vertical e histórico dos escopos encerrados. Em erro, indica
**Tabela parcial** e inicialização **Não concluído**. Cada compilação limpa o
resultado anterior; uma edição sinaliza que a tabela pertence à última compilação.
Novo/Abrir também limpam a tabela.

A aba **Código Assembly** usa fonte monoespaçada de 14 pontos, somente leitura,
com rolagem horizontal e vertical. **Copiar ASM** copia o conteúdo inteiro;
**Salvar ASM** exporta exatamente esse conteúdo em UTF-8, sem modificar o fonte.
Compilações malsucedidas, edições, Novo e Abrir limpam o assembly anterior.
Sem resultado disponível, os botões orientam a compilar primeiro.

| Ação | Atalho |
| --- | --- |
| Novo | Ctrl+N |
| Abrir | Ctrl+O |
| Salvar | Ctrl+S |
| Salvar como | Ctrl+Shift+S |
| Compilar | F9, botão ou menu |
| Sair | Menu Arquivo ou fechar janela |

Preservados: UTF-8/BOM e quebras de linha do Windows, desfazer/refazer, tabulações
visuais de quatro espaços, título com alterações pendentes, confirmação de
salvar/descartar/cancelar, tratamento de falhas de arquivo e mensagens somente leitura.

## Arquitetura

```text
main.py                         Entrada da IDE
ide/app.py                      Tkinter: editor, arquivos, mensagens e tabela
ide/compiler_service.py         Integração e CompilationResult
codegen/ir.py                   Expressões e comandos construídos pelas ações
codegen/bip_generator.py        Gerador, alocador, validação e erros BIP
Analisador_Sintatico/
    Constants.py                Tokens e tabelas WebGALS
    Lexico.py                   Scanner com correções de compatibilidade
    Sintatico.py                Parser SLR gerado, preservado
    Token.py                    Token exportado, com TokenId corrigido
    Errors.py                   Exceções das três fases
    Semantico.py                execute_action: conexão com as 59 ações
    semantic_model.py           Símbolos, escopos, referências e diagnósticos
    semantic_types.py           Compatibilidade e tipos das expressões
    semantic_flow.py            Inicialização por caminhos de controle
    main.py                     Exemplo do gerador; não inicia a IDE
docs/acoes_semanticas.md         Contrato completo dos marcadores
exemplos/                       13 exemplos anteriores preservados
exemplos/semantica/             Casos para apresentação da etapa 3
exemplos/bip/                   31 pares .src/.asm e manifesto de testes
docs/bip_iv.md                  Contrato do alvo, evidências e roteiro manual
docs/validacao_bipide.json       Resultados de execução no Bipide instalado
tests/                          Serviço, semântica e widgets reais
```

Cada compilação cria `Lexico(source)`, `Sintatico()` e
`Semantico(source, defer_errors=True)`, chamando a API real
`parser.parse(scanner, semantic)`. O serviço não importa Tkinter.

`CompilationResult` contém `kind`, `message`, `line`, `column`, `errors`,
`warnings`, `symbols`, `symbols_partial`, `assembly_code` e `codegen_status`,
com propriedades `success`, `analysis_success` e `diagnostics`. A mensagem
principal permanece separada dos avisos estruturados. `compile_source(source)`
executa as quatro etapas; `analyze_source(source)` preserva a análise das três
primeiras, inclusive funções, recursão, tipos e controles fora do alvo BIP.
Os imports absolutos dos arquivos exportados são resolvidos por inclusão temporária
de sua pasta no caminho de importação, sem deixar `Token.py` sombrear `token`.

## WebGALS e ações semânticas

A exportação atual tem **307 estados SLR, 123 produções, 59 ações semânticas e
51 estados léxicos**. A gramática exportada é a fonte de verdade da sintaxe.
Não foram editadas tabelas nem criado outro parser ou reconhecimento por regex.
Nenhum token, estado, produção ou tabela foi alterado nesta etapa.

O parser executa `SLRAction.ACTION` e chama
`execute_action(numero, previous_token)`. Pilhas distintas preservam valores,
operadores, identificadores, destinos e chamadas. As reduções determinam a
precedência. Em `#51`, a análise de inicialização percorre operações semânticas
já estruturadas pelas ações, sem reler ou analisar sintaticamente o código.
Assim o incremento do for pode ser analisado depois do corpo.

O [contrato completo das ações](docs/acoes_semanticas.md) explica os 59 marcadores,
seus pontos de disparo e o tratamento de chamadas, funções, blocos e laços.

### Compatibilidade e reexportação

`Token.py` preserva a correção `TokenID` → `TokenId`. Em `Lexico.py`, foram
restauradas correções perdidas na reexportação: aceitar somente estados com token
`>= 0`, usar `SCANNER_ERRORS`, diagnosticar corretamente tokens incompletos no EOF
e rejeitar caracteres fora das 256 colunas sem causar `IndexError`.

Não foi necessário alterar a gramática. O arquivo externo
`../Analisador_Sintatico.vgls` ainda é da etapa 2, sem ações, e não representa a
exportação Python atual. Antes de reexportar, versione a especificação atualizada
do WebGALS. Preserve `Semantico.py` e seus auxiliares para não sobrescrevê-los com
o stub do gerador. Os testes conferem a cobertura de todas as ações.

## Símbolos e escopos

Cada símbolo contém ID único, nome, tipo, modalidade, escopo/escopo pai,
posição/linha/coluna, usos de leitura/escrita, inicialização, elementos
inicializados, dimensão e parâmetros/assinatura.

As modalidades são **variável**, **vetor**, **parâmetro** e **função**. Parâmetro
vetorial mantém modalidade parâmetro e `is_array=True`. Procedimento é função
com retorno `void`. Todos compartilham um espaço de nomes, sem sobrecarga.

A resolução procura no escopo atual e ancestrais. Existem escopos global, de
função, de bloco e de for. Parâmetros e variáveis diretamente no corpo da função
compartilham escopo, pois esse corpo não dispara `#30/#31`. Blocos internos podem
sombrear nomes. Irmãos, funções distintas e blocos encerrados não são acessíveis.
A variável do cabeçalho de for deixa de ser acessível ao terminar o laço. O
histórico permanece na tabela, mas não participa da resolução fora do escopo.
Duplicidades incluem a posição da declaração original e da nova declaração.

## Regras de tipos

| Operação | Regra |
| --- | --- |
| Atribuição, argumento e retorno escalar | Mesmo tipo ou promoção `int → float → double`; sem estreitamento |
| Literais | Decimal/binário/hexadecimal: int; real: float; caractere: char; texto: string; true/false: bool |
| `+ - * /` | Numéricos; resultado do tipo de maior precisão |
| `% & \| ^ << >>` | Dois int; resultado int |
| `&& \|\| !` | Somente bool |
| Unário `-` | Numérico, preservando tipo |
| Unário `~` | Somente int |
| `< > <= >=` | Dois numéricos ou dois char; resultado bool |
| `== !=` | Dois numéricos ou mesmo tipo escalar; resultado bool |
| Condições | Somente bool, inclusive nos laços |
| Dimensão/índice | int; positividade/limites verificados quando constantes |

Char, string e bool não se convertem implicitamente em números. Strings não
participam de aritmética nem concatenação via `+`. Void não produz valor. Vetores
inteiros não são escalares: exigem índice em atribuição, input, print e operações;
podem ser passados a parâmetros vetoriais do mesmo tipo, sem promoção de elementos.
Se os dois tamanhos forem conhecidos, devem coincidir. Tamanhos dinâmicos int são
aceitos, mas seus limites não são comprovados estaticamente.

A produção existente `int v[3] = 5;` adota **preenchimento uniforme**: a expressão
deve ser compatível com o tipo de elemento e inicializa todo o vetor. A gramática
não oferece listas de inicialização nem atribuição posterior de escalar ao vetor inteiro.

Funções são registradas antes do corpo para permitir recursão. Cada chamada
aninhada mantém argumentos próprios. Validam-se nome, modalidade, quantidade,
tipos e retorno. `return;` só vale em void; `return exp;` exige retorno não void
compatível. Funções não void precisam retornar em todos os caminhos que podem
terminar normalmente.

## Utilização e inicialização

Leitura, escrita ou chamada conta como utilização. A declaração, incluindo seu
inicializador, não conta como uso do símbolo declarado: `int x=1;` gera aviso de
não utilização; `int x;x=1;` conta como uso por escrita. Isso inclui vetores,
parâmetros e funções. Recursão conta como uso. Código inalcançável continua
validado em nomes/tipos e conta como referência, mas não gera aviso de leitura.

A inicialização é analisada por estados de cada caminho, não por uma flag única:

- Declaração sem inicializador começa sem valor; parâmetros começam inicializados.
- Atribuição e input inicializam depois das leituras necessárias. `x=x+1` lê antes
  de escrever; o destino de `x=1` não é leitura.
- If sem else intersecta entrada/then; if/else intersecta os dois caminhos.
  Caminhos que retornam são excluídos da junção dos caminhos que continuam.
- While/for podem executar zero vezes. Escritas exclusivas do corpo/incremento
  não são garantidas após o laço. A inicialização do cabeçalho é garantida.
- O incremento do for é analisado após o corpo e não inicializa sua primeira
  entrada. Seus avisos consideram também condicionais internas ao corpo.
- Do-while considera uma passagem pelo corpo antes da condição.
- Vetores controlam índices constantes individualmente. Escrita em índice dinâmico
  não garante elemento específico. Leitura dinâmica exige todos os elementos
  comprovadamente inicializados, senão avisa.
- A coluna Inicializado mostra garantias nas saídas do escopo, incluindo returns;
  pode mostrar inicialização parcial de elementos de vetor.

Avisos usam códigos `unused` e `uninitialized`, posição da declaração/leitura e
deduplicação por código, símbolo e posição. Leituras distintas podem gerar avisos
distintos. Avisos nunca tornam `success` falso.

## Erros e avisos

O serviço distingue erros léxicos, sintáticos, semânticos, de geração e internos. Linha/coluna
começam em 1; tabulação conta como um caractere. Preserva-se a mensagem léxica.
Erros sintáticos incluem token inesperado/EOF e mensagem original do WebGALS.
No EOF, usa-se a posição reportada pelo parser.

O primeiro erro semântico suspende as ações seguintes. O mesmo parser continua
para detectar erros léxicos/sintáticos, que têm prioridade. Em erro, não se
publicam avisos finais; a tabela é parcial. Cada compilação cria contexto limpo.
Entrada vazia conserva sua mensagem própria.

Erros do alvo usam `kind="codegen_error"`, `codegen_status="error"` e fase
`codegen`, com linha/coluna. Nesse caso, `analysis_success=True`, `success=False`,
símbolos completos e avisos preservados, mas `assembly_code=""`. Nenhum assembly
parcial é publicado. Avisos semânticos sozinhos nunca bloqueiam a geração.

## Exemplos

Os 13 exemplos anteriores permanecem em `exemplos/`; 11 e 12 contêm erros
sintático/léxico propositais. Casos da nova etapa em `exemplos/semantica/`:

| Arquivo | Resultado da análise das três primeiras etapas |
| --- | --- |
| `01_completo.src` | Sucesso: recursão, chamadas aninhadas, vetor e for |
| `02_avisos.src` | Sucesso com avisos de não utilização/inicialização |
| `03_erro_tipo.src` | Erro ao atribuir string a int |
| `04_erro_escopo.src` | Erro ao acessar i depois do for |

```c
int x;
input(x);
print(x); // sucesso sem aviso de leitura não inicializada
```

```c
int x;
if (true) { x=1; }
print(x); // sucesso com aviso conservador
```

```c
int x = "abc"; // erro semântico
```

## Testes

Validação da etapa 4 em **08/11/2026**: **247 testes unittest aprovados**, sem
falhas ou skips (144 de regressão das análises, 77 de geração e 26 de interface).
Inclui widgets Tkinter, arquivos e clipboard reais. Os testes antigos de análise
passaram a chamar `analyze_source`, preservando suas expectativas. A interface
agora distingue sucesso de análise e falha de geração nos exemplos fora do alvo.

Além disso, **31 programas passaram no montador e nas rotinas originais do
simulador Bipide instalado em `D:\Bipide`**, verificando entradas, saídas
sucessivas, memória dos símbolos e `HLT`. O driver usa a rotina real da
interface para resolver endereços dos vetores; não automatiza botões/animações.
Consulte as evidências em [docs/bip_iv.md](docs/bip_iv.md).

```console
python -m unittest discover -s tests -v
python -m unittest tests.test_codegen_bip -v
python -m tests.generate_bip_examples
```

Para repetir a validação no Bipide instalado (Windows PowerShell 5.1, STA):

```powershell
powershell -NoProfile -STA -ExecutionPolicy Bypass -File tests/run_bipide.ps1 -BipidePath D:\Bipide
```

O script lê `exemplos/bip/casos.json` e escreve `docs/validacao_bipide.json`.
Não instala nem altera o Bipide. O modelo Python em `tests/bip_machine.py` é
somente um oráculo adicional; não integra a IDE e não substitui as DLLs originais.

### Histórico da etapa 3

Validação em 17/10/2026, no Windows com Python 3.13.7: **163 testes aprovados**,
sendo 144 de serviço/semântica e 19 de interface, sem falhas ou testes ignorados.
As abas de mensagens e símbolos também foram inspecionadas visualmente na janela
real. O comando de entrada `main.py` também abriu em processo independente e
encerrou com código 0.
Na sandbox de desenvolvimento, Tcl não inicializou; os testes gráficos
passaram fora dela, usando a instalação existente, sem alterar a aplicação.

Suíte completa, incluindo janelas Tkinter temporárias:

```console
python -m unittest discover -s tests -v
```

Somente analisadores e serviço, sem sessão gráfica:

```console
python -m unittest tests.test_compiler_service tests.test_semantic -v
```

A suíte cobre os sete critérios, os 16 exemplos obrigatórios independentes,
todas as 59 ações, os oito formatos opcionais do for, escopos, funções/recursão,
operadores, inicialização por caminhos, vetores, diagnósticos e recompilações.
Os testes da IDE usam widgets e arquivos reais; apenas respostas de diálogos são
simuladas. Verificam fonte 14, arquivos, atalhos, redimensionamento, destaque,
avisos, tabela real/parcial, limpeza e `main.py` com event loop real do Tkinter.

## Limitações conhecidas

- Funções devem ser definidas antes da chamada, exceto recursão direta. Sem
  protótipos, não há referências antecipadas nem recursão mútua.
- Chamadas não propagam escritas para globais/vetores. Corpos são analisados
  isoladamente, com globais no estado da definição e parâmetros inicializados.
  Passar vetor parcialmente inicializado pode avisar mesmo se a função só escrever
  nele; não existe análise interprocedimental.
- Condições constantes e curto-circuito não eliminam caminhos/leituras, podendo
  gerar avisos conservadores. Laços não provam preenchimento completo de vetores.
  For sem condição também é conservador quanto à terminação; função não void
  deve apresentar retorno comprovável.
- A dobra de constantes atende apenas expressões int pequenas: literais de até
  1000 caracteres e resultados de até 4096 bits. Não propaga valores de variáveis
  ou chamadas. Valores maiores ficam desconhecidos. Divisão inteira trunca em
  direção a zero; divisão por zero e overflow de máquina não são diagnósticos
  desta etapa. A dobra auxilia índices, sem executar programas.
- A gramática não oferece casts, sobrecarga, protótipos, vetores multidimensionais,
  listas de inicialização, break/continue ou `++`. Mantém `bool`, `input` e `print`;
  não traduz `boolean`, `cin` ou `cout`.
- O alfabeto é o da tabela léxica; caracteres fora dele são rejeitados.
- Informa-se o primeiro erro semântico, sem recuperação para erros derivados.

## Etapa 4: geração BIP IV

Ao iniciar esta etapa, uma reexportação havia substituído `Semantico.py` pelo
stub e removido as correções de `Lexico.py`. A implementação anterior foi
recuperada do histórico e seus 144 testes de análise passaram antes da extensão.
O parser SLR e suas tabelas não foram alterados. A alteração de espaço em branco
que já existia em `Sintatico.py` foi preservada.

### IR, WebGALS e geração

`Value.expression` guarda uma árvore `Expression`: tipo, posição, literal,
operador, operandos e referência ao símbolo real. `Reference.index_expression`
preserva índices aninhados; `Symbol.dimension_expression` preserva o tamanho.
`Statement` representa declarações, inicializações, atribuições, entrada, saída,
retornos e corpos de funções. As ações `#63–#67`, `#60/#62/#71–#79` constroem
expressões; `#20–#24` resolvem referências; `#5/#7/#8/#9` registram comandos;
`#10/#15` separam funções. `#50` reinicia o estado e `#51` conclui a análise.

As verificações de tipos e de inicialização continuam independentes. Somente
uma análise concluída sem erros alimenta `BIPCodeGenerator`. Os blocos
sequenciais mantêm a ordem e a identidade dos símbolos. Estruturas sem tradução
recebem marcadores explícitos que impedem a geração inteira, mesmo em código
inalcançável. Não há outro parser, regex sobre o fonte ou mudança na gramática.

### Dados, acumulador, índice e instruções

`MemoryAllocator` associa o ID único do símbolo a `v<ID>`, inclusive em escopos
distintos. `t<N>` identifica temporários reutilizáveis e `c<N>`, constantes
compartilhadas. Os nomes do usuário nunca colidem com esses rótulos.

`.data` declara escalares (`v0 : 0`) e vetores (`v1 : 0, 0, 0`), com base no
primeiro elemento e posições consecutivas. Dimensões constantes como `2+3` ou
`(2+3)*2` são calculadas; dimensões dinâmicas são rejeitadas. Limites: **1024
palavras de dados**, incluindo temporários/constantes, e **2048 instruções**.
A região a partir de 1024 contém E/S e não é alocada. Programas sem dados usam
`reserved : 0`, porque o montador exige uma declaração em `.data`.

Declarações sem inicializador não emitem execução. Inicializadores executam na
ordem do fonte; `int v[3]=5;` avalia uma vez e preenche todos os elementos. Os
avisos de leitura sem inicialização permanecem, mesmo com memória inicialmente zero.

| Construção | Tradução |
| --- | --- |
| Literal | `LDI` para −1024..1023; demais constantes válidas em `.data` com `LD` |
| Variável / atribuição | `LD` / `STO` |
| Soma/subtração | `ADD`/`ADDI`, `SUB`/`SUBI`, com temporários para subexpressões |
| `&`, `\|`, `^`, `~` | `AND`/`ANDI`, `OR`/`ORI`, `XOR`/`XORI`, `NOT` |
| Negação numérica | `NOT`, `ADDI 1`, normalização de 16 bits |
| `<<`, `>>` | `SLL`, `SRL`, com quantidade constante entre 0 e 15 |
| Leitura de vetor | Calcula índice em `ACC`, `STO $indr`, `LDV base` |
| Escrita de vetor | Salva índice e valor, restaura `$indr`, `STOV base` |
| `input` | `LD $in_port`, seguido de armazenamento no destino |
| `print` | Calcula expressão e emite `STO $out_port` por argumento |
| Finalização | `HLT`, sem operando |

`ACC` guarda cada resultado. Temporários preservam subárvores e a ordem da
subtração; o índice do destino permanece salvo durante todo o RHS, mesmo com
outros acessos que alterem `INDR`. Entradas e saídas respeitam a ordem dos
argumentos. **A porta de saída não é um console de texto**: observe cada escrita.

### Tipos, entrada do programa e limites

Somente `int` é traduzido. Decimais aceitam −32768..32767, incluindo `-32768`;
binários/hexadecimais aceitam padrões de até 16 bits (`0xFFFF` representa −1).
As operações usam complemento de dois: `32767+1` produz −32768. O deslocamento
à direita é lógico: `-1 >> 1` produz 32767. Sequências de normalização/máscaras
compensam o ACC Int32 e o SRL com sinal do simulador, com instruções BIP reais.

Sem `main`, executam-se os comandos globais. Com `int main()` ou `void main()`
sem parâmetros, executam-se primeiro **todos os comandos globais em ordem
textual**, depois o corpo de main uma vez, independentemente da posição da
definição. `return 0;` em int e `return;` em void emitem `HLT`. Código após
retorno continua validado. Chamadas explícitas a main não são suportadas; o
aviso semântico anterior de função não utilizada é preservado.

Float, double, char, string e bool não são convertidos silenciosamente.
Multiplicação/divisão/módulo executáveis, comparações, lógica, condicionais,
laços, funções comuns e chamadas/recursão geram **erro de geração**. Também são
rejeitados shifts de quantidade variável, dimensões dinâmicas e retorno não
zero em main. Esses recursos permanecem nas análises anteriores. Operações
constantes adicionais são permitidas em dimensões, sem gerar instruções.

Índices constantes têm limites verificados. Índices dinâmicos devem estar
dentro do vetor; não são inseridas verificações de limites em tempo de execução.
Normalizações priorizam correção e consomem instruções; exceder a capacidade
produz diagnóstico, nunca truncamento. O formato binário/MIF exportado diretamente
pela DLL isolada do montador não é um produto desta IDE; a resolução de vetores
deve passar pelo fluxo completo do Bipide, conforme [evidências](docs/bip_iv.md).

### Exemplos e uso no Bipide

Os [31 pares de programas e assembly](exemplos/bip/README.md) incluem todos os
15 casos do pedido, entradas/saídas e testes extras de limites, main e vetores.
Por exemplo, `01_atribuicao` produz 10; `03_vetor`, 10/20/30;
`09_input` recebe 5 e produz 15; `14_escopos`, 20/10;
`22_ordem`, 13/17/22.

Compile um `.src`, abra **Código Assembly**, clique **Salvar ASM** e abra esse
arquivo em um documento **Assembly** do Bipide 3.0. Se necessário, escolha
Todos os arquivos ou cole o conteúdo. Selecione **BIP IV**, compile e simule.
O [roteiro detalhado](docs/bip_iv.md) explica entradas, memória e acompanhamento
das saídas. A revisão visual dos botões/animações permanece manual; montagem
e execução das instruções foram efetivamente testadas. Nenhum ajuste na
gramática do WebGALS foi necessário.
