# Contrato BIP IV e validação no Bipide 3.0

Validação realizada em **08/11/2026**, na instalação `D:\Bipide`.
Os hashes dos binários e resultados por programa estão em
[validacao_bipide.json](validacao_bipide.json). Nenhuma DLL foi modificada,
copiada para o projeto ou substituída por uma implementação própria.

## Fontes e confirmação do formato

Fontes primárias consultadas antes de implementar o gerador:

- Ajuda distribuída com a instalação: `D:\Bipide\Help\InstrucoesBip.html`,
  `BIP_IV.html` e `programacao.html` (HTML em UTF-16).
- Montador real `BIP.dll`, classe `BIP.Montador.Montador` e arquitetura
  `BIP.Montador.Arquitetura`.
- Rotina de compilação `Bipide.ucProgramacao.Executa` de `Bipide.exe`, resolução
  de endereços em `Classes.dll` e simulador `ucBip.Simulador` de `ucBipI.dll`.
- [Distribuição oficial Bipide 3.0](https://sourceforge.net/projects/bipide/files/Versao%203.0/)
  e [exemplos do autor](https://sourceforge.net/projects/bipide/files/Versao%203.0/Programas%20de%20Exemplo/).
- [Dissertação de Paulo Viníccius Vieira, UNIVALI, 2013](https://www.univali.br/Lists/TrabalhosMestrado/Attachments/751/Paulo%20Viniccius%20Vieira2013.pdf):
  arquitetura BIP IV e funcionalidades da versão 3.0.

A instalação registra `FileVersion=1.0.0.0` nas DLLs/executável; o código contém
o caminho de geração `D:\Bipide\3.0\Compilador\portugol.g`. Por isso, os hashes
são registrados para identificar precisamente a distribuição testada, sem
confundir a versão do arquivo .NET com a versão do produto.

| Item | Formato/limite conferido |
| --- | --- |
| Seções | `.data` seguida de `.text`; `.data` vazia é rejeitada |
| Escalar | `nome : 0` |
| Vetor | `nome : 0, 0, 0` |
| Identificadores emitidos | Letras ASCII seguidas de dígitos: `v0`, `t0`, `c0` |
| Rótulo de código | `inicio: LDI 1` é aceito; o subconjunto emitido não precisa de saltos |
| Comentários | `# comentário` é aceito; `;`, `//` e `/* */` foram rejeitados |
| Encerramento | `HLT`, sem operando |
| Complemento bit a bit | `NOT`, sem operando |
| Palavra de dados | 16 bits, interpretação com sinal −32768..32767 |
| Campo de operando | 11 bits |
| Imediatos | −1024..1023; o montador rejeitou −1025, 1024, 2047 e 32767 em LDI |
| Endereços codificáveis | 0..2047; **não** equivalem a 2048 palavras de RAM livre |
| RAM usada pelo simulador | 0..1023 |
| `$in_port` | 1024; entrada por `LD` |
| `$out_port` | 1025; saída por `STO` |
| `$indr` | 1073; índice configurado por `STO` |
| `LDV` / `STOV` | Acesso em `base + INDR` |
| `SLL n` / `SRL n` | Quantidade imediata; o gerador restringe a 0..15 |

O gerador escreve constantes decimais no ASM. A base binária/hexadecimal é
interpretada na IR antes da emissão. Números fora do intervalo permitido pelo
gerador são rejeitados mesmo se o montador aceitar valores maiores em `.data`.

## Diferenças verificadas na implementação do simulador

1. `ACCUMULATOR` é Int32. Executar diretamente `32767 + 1` devolve 32768.
2. `SRL` usa deslocamento com sinal: executar diretamente `-1 >> 1` devolve −1,
   embora a documentação descreva um deslocamento lógico.
3. `BIP.dll` isolada informa endereços que não incorporam corretamente o tamanho
   dos vetores seguintes. O fluxo da interface **converte os dados e recalcula
   os endereços** em `Classes.Codigo.SetEnderecoRotulosVariavel`. Usar só
   `Montador.Programa.Variaveis.EndMemoria` não reproduz a execução do Bipide.

Para garantir o mesmo padrão de 16 bits no hardware documentado e no simulador:

```text
signed16(x) = (x & 32767) - (((x >> 15) & 1) << 15)
```

O gerador emite essa normalização após soma, subtração, negação numérica e
shift à esquerda. Usa apenas `STO`, `LD`, `AND`, `SRL`, `ANDI`, `SLL` e `SUB`.
O resultado do SRL é mascarado para remover os bits de sinal introduzidos pela
implementação do simulador. As sequências também são corretas com um ACC físico
de 16 bits e SRL lógico. Por exemplo: `~10 = -11`, `-1 >> 1 = 32767`,
`16384 << 1 = -32768`, `32767+1 = -32768`.

Os vetores mantêm a declaração padrão com lista de valores. A validação passa
pela mesma rotina de compilação/resolução de endereços utilizada pela interface,
sem corrigir manualmente as tabelas ou campos do montador.

## Testes efetivamente realizados

**247 testes Python**, incluindo 144 de regressão da análise, 77 de geração e
26 de interface Tkinter, sem falhas nem skips. Incluem precedência, associação,
sombras, literais, memória, temporários, erros por fase, retorno de main,
recursos não suportados e recompilações sem estado residual. Os widgets, o
clipboard e os arquivos exportados são reais; somente diálogos de arquivo são
respondidos por mocks. O Tcl/Tk exigiu execução fora da sandbox.

**31 programas no Bipide real**, incluindo os 15 solicitados. O driver
[tests/run_bipide.ps1](../tests/run_bipide.ps1):

1. Monta cada `.asm` com `BIP.Montador.Montador.Executa` e exige ausência de erros.
2. Carrega o texto em um editor Assembly real, hospedado em janela transparente
   fora da barra de tarefas, e chama `Bipide.ucProgramacao.Executa`.
3. Usa `Classes.Codigo` e `SetEnderecoRotulosVariavel` exatamente como a interface
   principal, carregando as memórias de dados e programa no simulador original.
4. Seleciona processador 4 e chama os métodos originais de cada instrução montada.
   Não implementa aritmética BIP em PowerShell.
5. Preenche o controle original de entrada e marca o estado de confirmação do
   usuário antes de `LD $in_port`. O método LD faz a leitura real da porta.
6. Compara cada escrita em `$out_port`, inclusive valores repetidos, verifica
   todas as células de cada símbolo, exige consumo de todas as entradas e
   verifica chegada a HLT sem alteração de PC.

O verificador original de limites de vetores também é chamado antes de LDV/STOV,
para que uma falha gere uma exceção de teste em vez de um diálogo modal.
As comparações de memória excluem temporários: durante a normalização, o Int32
do simulador pode guardar 32768 onde o hardware representa o mesmo padrão como
−32768. Os valores dos símbolos e as saídas são sempre comparados com sinal.

**Limite da validação:** o driver controla a sequência de instruções, que é
linear neste subconjunto, e para em HLT. Não exercita cliques nos botões, a
temporização das animações nem o diálogo interativo de confirmação da entrada.
Esses aspectos visuais ficam para o roteiro manual abaixo. Não se afirma que
houve teste em hardware físico ou de exportação MIF/binária pelo Bipide.

O oráculo adicional `tests/bip_machine.py` tem palavras de 16 bits, entradas em
fila e observação de todas as saídas. Ele lê apenas assembly, não a linguagem
fonte; é independente da emissão, testa mnemônicos/operandos e não entra na IDE.

## Reproduzir

```powershell
python -m unittest discover -s tests -v
python -m tests.generate_bip_examples
powershell -NoProfile -STA -ExecutionPolicy Bypass -File tests/run_bipide.ps1 -BipidePath D:\Bipide
```

Se o comando `python` for um alias da Store, use o executável da instalação
Python real, como indicado no README. A validação real exige Windows, .NET/WPF
e os binários do Bipide; ela é separada do unittest para não fingir execução
do simulador em máquinas que não o tenham. Falta de binários encerra o script
com erro. A execução escreve somente o relatório de testes no repositório.

## Roteiro manual

1. Abra `python main.py`. Carregue um `.src` de `exemplos/bip/` e pressione F9.
2. Confirme a mensagem de geração e os avisos, se houver. Consulte a tabela e
   a aba **Código Assembly**. Use **Salvar ASM**.
3. No Bipide 3.0, crie/abra um documento **Assembly**. Se a extensão `.asm` não
   aparecer no filtro, selecione Todos os arquivos ou use **Copiar ASM** e cole
   em um novo documento Assembly. Não abra como Portugol.
4. Compile, selecione **BIP IV** e abra a simulação. Confira os rótulos e
   endereços consecutivos dos vetores na memória.
5. Use o modo passo a passo. Em cada `LD $in_port`, informe o próximo valor da
   coluna Entradas do [manifesto de exemplos](../exemplos/bip/README.md) e
   confirme/continue conforme a interface solicitar.
6. Anote cada valor gravado por `STO $out_port`, na ordem. A porta mostra o
   último valor; executar tudo de uma vez pode ocultar os anteriores.
7. Em `STO $indr`, acompanhe o índice. Em `LDV`/`STOV`, confira `base + índice`
   e o valor lido/gravado, especialmente em `19_preserva_indice` e
   `20_indices_aninhados`.
8. Confirme HLT e compare os valores finais com `casos.json`. Reinicie a
   simulação antes de repetir cada programa.

Casos essenciais: `01` → 10; `02` → 25,15; `03` → 10,20,30; `09`, entrada 5 →
15; `10`, entrada 10 → 15; `14` → 20,10; `17` verifica sinais e overflow;
`18` recebe 7,−3,42 e produz 7,−3,42,46; `22` → 13,17,22.

## Escopo e pendências

Os seis critérios obrigatórios estão implementados. Tipos não inteiros,
controle de fluxo, chamadas/funções comuns, multiplicação/divisão/módulo
executáveis, tamanho dinâmico e quantidade variável de shift têm diagnóstico
explícito. Índices variáveis devem permanecer dentro do vetor; não há checagem
inserida no código gerado. O limite de 2048 instruções também pode ser atingido
por inicializações uniformes de vetores grandes ou muitas normalizações.

Não foi necessária alteração de gramática ou dos marcadores WebGALS. Continua
pendente versionar a especificação `.vgls` atualizada das etapas anteriores:
o arquivo externo ainda não corresponde à exportação instrumentada, como já
documentado em `acoes_semanticas.md`. A revisão visual manual do Bipide está
separada dos testes de montagem/execução efetivamente realizados acima.
