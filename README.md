# IDE Compiladores

IDE desktop em Python/Tkinter para editar arquivos de código-fonte e
realizar análise léxica e sintática com os analisadores gerados pelo WebGALS.
**A aplicação não executa nem interpreta o programa, não gera código de máquina
e não realiza análise semântica.**

## Requisitos e execução

- Python **3.10 ou superior**: o parser exportado utiliza `match/case`.
- Tkinter com Tcl/Tk e um ambiente gráfico desktop.
- Somente bibliotecas da Standard Library; não é necessário instalar pacotes com pip.

Na pasta raiz deste projeto, execute:

```console
python main.py
```

No Windows, o instalador do Python deve incluir Tcl/Tk. Caso o comando `python`
aponte apenas para o atalho da Microsoft Store, utilize o executável da instalação
real. Nesta máquina, a alternativa no PowerShell é:

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe" main.py
```

No Linux, algumas distribuições fornecem Tkinter em um pacote separado
(`python3-tk`). Não é necessária conexão com a internet para usar a IDE.

## Como utilizar

1. Digite um programa ou use **Arquivo → Abrir...** para carregar um `.src` ou `.txt`.
2. Clique em **Compilar (F9)**, pressione **F9** ou use o menu **Compilar**.
3. Leia o resultado no painel **Mensagens**, abaixo do editor.
4. Use **Salvar** ou **Salvar como...** para gravar o código em UTF-8.

O editor e o painel de mensagens usam fonte monoespaçada de **14 pontos**.
A interface utiliza **tema escuro**, com mensagens de sucesso em verde e erros
em vermelho claro. A barra de título e os diálogos nativos de arquivos e
confirmações seguem a aparência definida pelo sistema operacional.
A fonte é escolhida entre Consolas, Courier New e a fonte monoespaçada padrão
do sistema. O editor possui rolagem vertical e horizontal, tabulações equivalentes
a quatro espaços na exibição e desfazer/refazer nativos do Tkinter.
O painel de mensagens é somente leitura e tem rolagem vertical.
A divisão entre os painéis pode ser arrastada e a janela pode ser redimensionada.

| Ação | Atalho / comportamento |
| --- | --- |
| Novo | Ctrl+N; limpa editor, mensagens e arquivo atual |
| Abrir | Ctrl+O; carrega um arquivo UTF-8, também aceitando BOM |
| Salvar | Ctrl+S; solicita o destino se o arquivo ainda não tiver nome |
| Salvar como | Ctrl+Shift+S; escolhe outro destino |
| Compilar | F9; limpa o resultado anterior e analisa todo o programa |
| Sair | Menu Arquivo ou botão de fechar da janela |

O título mostra o nome do arquivo e `*` quando existem alterações não salvas.
Ao criar, abrir ou fechar um documento alterado, é possível salvar, descartar ou
cancelar a operação. Cancelamentos e falhas de leitura/escrita preservam o documento.

## Integração com o WebGALS

Os arquivos exportados continuam em `Analisador_Sintatico/`. A IDE utiliza a API
real encontrada nesses arquivos:

```python
scanner = Lexico(codigo)
parser = Sintatico()
parser.parse(scanner, Semantico())
```

`Lexico(input)` inicializa o código usando `set_input(input)`. Durante o `parse`,
o próprio parser solicita tokens por `scanner.next_token()` até aceitar o final
da entrada. Cada compilação cria novas instâncias. A tabela SLR(1) fornecida possui
222 estados e 120 produções; a tabela léxica possui 51 estados.

A exportação atualmente presente usa `input(...)` para entrada, `print(...)`
para saída e `bool` para o tipo booleano. Os exemplos acompanham essa versão.
As construções antigas `cin >> ...`, `cout << ...` e declarações com `boolean`
não fazem parte da gramática atual; a IDE não traduz comandos nem altera as tabelas.

`Semantico()` é o objeto exportado que atende ao parâmetro obrigatório de `parse`.
Sua interface é `execute_action(action, token)`. A tabela fornecida não contém
ações semânticas, portanto esse método não é chamado.

Os imports absolutos dos arquivos gerados são resolvidos por uma inclusão
temporária da pasta no caminho de importação, dentro de `compiler_service.py`.
Isso evita mover os arquivos ou manter `Token.py` no caminho de busca do módulo
`token` da biblioteca padrão.

### Correções necessárias na exportação

Foram identificados e reproduzidos defeitos no código Python original. Somente
dois arquivos gerados receberam correções pontuais:

- `Token.py`: anotação `TokenID` corrigida para o enum existente `TokenId`, evitando
  `NameError` ao importar os analisadores.
- `Lexico.py`: referência `SCANNER_ERROR` corrigida para `SCANNER_ERRORS`; somente
  estados com token maior ou igual a zero são guardados como estados de aceitação.
  Assim o scanner preserva o último token válido, sem criar `TokenId(-1)` ou
  `TokenId(-2)`. O diagnóstico também considera o estado correto no fim da entrada,
  inclusive em comentários `/*` incompletos. Caracteres fora das 256 colunas da
  tabela retornam transição inválida, evitando `IndexError` e permitindo informar
  erro léxico.

**Nenhuma regra léxica, produção ou tabela foi modificada.** `Constants.py`,
`Sintatico.py`, `Errors.py`, `Semantico.py` e o `main.py` exportado foram preservados.
Não há scanner ou parser alternativo. Ao exportar novamente do WebGALS, verifique
se essas inconsistências da geração reapareceram e execute os testes.

### Resultados e posições

- Sucesso: **Compilação realizada com sucesso.**
- Editor vazio ou contendo somente espaços/quebras de linha:
  **Nenhum código-fonte informado.**
- `LexicalError`: mensagem original, linha e coluna.
- `SyntacticError`: token inesperado (ou fim da entrada), mensagem original,
  linha e coluna.
- Outras exceções: **Erro inesperado**, sem classificar a falha como erro da linguagem.

As exceções reais de `Errors.py` contêm `message` e `position`.
`position_to_line_column` converte a posição absoluta em linha/coluna a partir de 1.
Cada tabulação conta como um caractere nessa posição. A linha com erro recebe um
destaque que é removido na próxima compilação ou edição.

O exportador forneceu mensagens sintáticas genéricas, como `Erro estado 84`, sem
lista de símbolos esperados. A IDE conserva essa mensagem e acrescenta o token
real; não inventa sugestões. No fim da entrada, o parser informa a posição logo
após o último token, mesmo quando há espaços ou comentários posteriores.
O alfabeto disponível é o da tabela exportada; caracteres fora dele são rejeitados.

## Estrutura

```text
main.py                     Ponto de entrada da IDE
ide/
    __init__.py
    app.py                  Janela, editor, menus, mensagens e arquivos
    compiler_service.py     Integração WebGALS e conversão de erros
Analisador_Sintatico/
    Constants.py            Tokens, tabelas léxica/sintática e produções
    Errors.py               Exceções exportadas
    Lexico.py               Scanner gerado
    Sintatico.py            Parser SLR gerado
    Semantico.py            Objeto exigido pelo contrato do parser
    Token.py                Token exportado
    main.py                 Exemplo original do gerador; não inicia a IDE
exemplos/                   13 casos de teste adaptados à gramática atual
tests/
    test_compiler_service.py
    test_app.py
```

## Exemplos válidos

Declaração e repetição:

```cpp
int i;
for (i = 0; i < 10; i = i + 1) {
    print(i);
}
```

Função e chamada:

```cpp
int somar(int a, int b) {
    return a + b;
}

int resultado;
resultado = somar(10, 20);
```

Entrada, saída e tipo booleano:

```cpp
int a, vetor[10];
bool ativo;
ativo = true;
input(a, vetor[0]);
print("Valor", a, vetor[0], ativo);
```

Esses programas são apenas analisados: `input` não solicita valores e `print`
não produz saída da execução.
Os exemplos `01` a `10` e `13` são válidos. `11_erro_sintatico.src` e
`12_erro_lexico.src` contêm erros propositais para demonstrar os diagnósticos.

## Validação

Validação realizada no Windows com Python 3.13.7 e Tcl/Tk 8.6.15:
**29 testes aprovados**, incluindo 13 cenários adaptados à gramática atual,
tanto no serviço de compilação quanto pelo botão da interface. A janela também foi aberta e
inspecionada visualmente com compilação válida e erro léxico; ambos os painéis
utilizaram Consolas de 14 pontos. O seletor nativo de Abrir foi exercitado
adicionalmente com um arquivo temporário real.

Execute todos os testes, incluindo a interface real do Tkinter:

```console
python -m unittest discover -s tests -v
```

Os testes da interface precisam de uma sessão gráfica e abrem janelas temporárias.
Usam widgets e arquivos reais; as respostas dos seletores e das confirmações são
simuladas para permitir validação automática sem interação humana.
Cobrem os 13 exemplos pelo botão Compilar, Novo/Abrir/Salvar/Salvar como/Sair,
cancelamentos, erros de arquivo, F9, tabulação, destaque, fontes de 14 pontos e
redimensionamento. A integração também testa entrada vazia, consumo da entrada
completa, posições, tokens incompletos e erros inesperados. As regressões incluem
`input`/`print`/`bool`, comentários incompletos no fim da entrada e o retorno do
scanner ao último estado de aceitação.

Para testar somente os analisadores, sem abrir janelas:

```console
python -m unittest tests.test_compiler_service -v
```
