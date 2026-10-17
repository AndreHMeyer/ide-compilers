# IDE Compiladores — análise léxica, sintática e semântica

Compilador acadêmico com interface desktop Python/Tkinter. O botão **Compilar
(F9)** integra as três etapas: scanner léxico gerado pelo WebGALS, parser SLR(1)
gerado e análise semântica conduzida pelas ações da gramática.

A aplicação faz análise estática. Não executa `input`, `print`, funções ou laços,
não interpreta programas e não gera código de máquina. Usa apenas a biblioteca
padrão do Python, sem dependências adicionais de execução.

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
e **Tabela de Símbolos**. Editor e mensagens mantêm fonte monoespaçada de **14
pontos**, tema escuro, rolagem e destaque da linha do erro. Avisos aparecem em
amarelo e não impedem o sucesso. A divisão entre editor e resultados é ajustável.

A tabela mostra os símbolos reais do analisador: identificador, tipo, modalidade,
escopo, utilização, inicialização, linha, coluna e dimensão/assinatura. Possui
rolagem horizontal/vertical e histórico dos escopos encerrados. Em erro, indica
**Tabela parcial** e inicialização **Não concluído**. Cada compilação limpa o
resultado anterior; uma edição sinaliza que a tabela pertence à última compilação.
Novo/Abrir também limpam a tabela.

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
tests/                          Serviço, semântica e widgets reais
```

Cada compilação cria `Lexico(source)`, `Sintatico()` e
`Semantico(source, defer_errors=True)`, chamando a API real
`parser.parse(scanner, semantic)`. O serviço não importa Tkinter.

`CompilationResult` contém `kind`, `message`, `line`, `column`, `errors`,
`warnings`, `symbols` e `symbols_partial`, com propriedades `success` e
`diagnostics`. A mensagem principal permanece separada dos avisos estruturados.
Os imports absolutos dos arquivos exportados são resolvidos por inclusão temporária
de sua pasta no caminho de importação, sem deixar `Token.py` sombrear `token`.

## WebGALS e ações semânticas

A exportação atual tem **307 estados SLR, 123 produções, 59 ações semânticas e
51 estados léxicos**. A gramática exportada é a fonte de verdade da sintaxe.
Não foram editadas tabelas nem criado outro parser ou reconhecimento por regex.
`Constants.py` já estava atualizado ao iniciar esta etapa: sua diferença no Git
pertence à reexportação anterior e foi preservada.

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

O serviço distingue erros léxicos, sintáticos, semânticos e internos. Linha/coluna
começam em 1; tabulação conta como um caractere. Preserva-se a mensagem léxica.
Erros sintáticos incluem token inesperado/EOF e mensagem original do WebGALS.
No EOF, usa-se a posição reportada pelo parser.

O primeiro erro semântico suspende as ações seguintes. O mesmo parser continua
para detectar erros léxicos/sintáticos, que têm prioridade. Em erro, não se
publicam avisos finais; a tabela é parcial. Cada compilação cria contexto limpo.
Entrada vazia conserva sua mensagem própria.

## Exemplos

Os 13 exemplos anteriores permanecem em `exemplos/`; 11 e 12 contêm erros
sintático/léxico propositais. Casos da nova etapa em `exemplos/semantica/`:

| Arquivo | Resultado |
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
