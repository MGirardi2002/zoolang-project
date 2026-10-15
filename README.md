# ZooLang — transpilador ZooLang → C

Trabalho Prático 1 de **Linguagens Formais e Compiladores** (UNIJUÍ, prof. Marcos Ronaldo Melo Cavalheiro).

**Grupo:** Matheus Girardi, Maiara Zucco, Anderson Scholz e Gustavo Drews.

ZooLang é uma linguagem temática de zoológico, inspirada na BIRL. O programa entra na jaula (`ENTRAR_NA_JAULA`) e sai dela (`SAIR_DA_JAULA`), conta carneirinhos em laços (`contar_carneirinho`) e ruge na saída (`rugir`).

```
ENTRAR_NA_JAULA
    carneirinho jaula = 1
    contar_carneirinho (jaula <= 3) {
        rugir("Jaula " + jaula + " alimentada!")
        jaula = jaula + 1
    }
SAIR_DA_JAULA
```

## Estado das etapas

| Fase                            | Estado       |
|---------------------------------|--------------|
| Especificação léxica e GLC      | concluída (ver `docs/Relatorio_Tecnico_ZooLang.docx`) |
| Analisador léxico + erros       | **concluído** |
| Parser + AST + erros sintáticos | **concluído** |
| Análise semântica (R1–R11)      | **concluída** |
| Geração de código C             | **concluída** |

## Pré-requisitos

- Python 3.10 ou superior (usa só a biblioteca padrão, sem instalar pacotes)
- gcc, para compilar o C gerado (opção `--run` e testes de ponta a ponta).
  Outro compilador pode ser usado pela variável `ZOOC_CC` (ex.: `set ZOOC_CC=clang`).

## Estrutura

```
zooc.py                 CLI do transpilador
rodar_testes.py         roda os testes unitários e os 5 programas de exemplo
zoolang/tokens.py       tipos de token, palavras reservadas, operadores
zoolang/lexer.py        analisador léxico (scanner escrito à mão)
zoolang/ast.py          nós da AST e impressão da árvore (--ast)
zoolang/parser.py       analisador sintático por descida recursiva
zoolang/semantico.py    tabela de símbolos (pilha de escopos) e regras R1–R11
zoolang/gerador_c.py    geração de código C a partir da AST
zoolang/erros.py        exceções (ErroLexico, ErroSintatico, ErroSemantico)
tests/                  testes unitários (lexer, parser, semântica, gerador)
exemplos/               suíte obrigatória de testes (01 a 05) em .zoo
exemplos/saidas/        saídas: tokens, .c gerados, execução e mensagens de erro
docs/                   relatório técnico (.docx)
```

Para regenerar o relatório depois de mudanças (precisa de Node.js e do script
`docs/fonte/gerar_relatorio.js`, que fica fora do git):

```bash
npm install docx
node docs/fonte/gerar_relatorio.js
```

## Como usar

```bash
# transpila e grava exemplos/01_valido_basico.c
python zooc.py exemplos/01_valido_basico.zoo

# escolhe o arquivo de saída e mostra a AST e o C gerado
python zooc.py exemplos/02_valido_completo.zoo -o saida.c --ast --c

# mostra a tabela de tokens
python zooc.py exemplos/01_valido_basico.zoo --tokens

# transpila, compila com gcc e executa (o 02 lê do teclado quantas bananas chegaram)
python zooc.py exemplos/02_valido_completo.zoo --run
echo 120 | python zooc.py exemplos/02_valido_completo.zoo --run

# ou, passo a passo
python zooc.py exemplos/02_valido_completo.zoo -o macacos.c
gcc macacos.c -o macacos.exe
echo 120 | macacos.exe

# roda toda a suíte (testes unitários + 5 exemplos); --salvar grava exemplos/saidas/
python rodar_testes.py
python rodar_testes.py --salvar

# só os testes unitários
python -m unittest discover -s tests -v
```

Exemplo: `rugir("Refeicao " + refeicao + " dos macacos servida!")` vira um único
`printf("Refeicao %d dos macacos servida!\n", refeicao);` (o especificador sai do tipo que a
análise semântica calculou), e `resultado = (2 + 3) * 4` gera os parênteses a
partir da árvore.

Exemplo da AST (`--ast`) de `resultado = 2 + 3 * 4`:

```
Atribuicao resultado
└── Soma +
    ├── Literal carneirinho 2
    └── Mult *
        ├── Literal carneirinho 3
        └── Literal carneirinho 4
```

Erros (todas as fases param no primeiro erro, com código de saída 1):

```
$ python zooc.py exemplos/03_erro_lexico.zoo
exemplos/03_erro_lexico.zoo: Erro léxico [linha 5, coluna 19]: símbolo '@' não pertence ao alfabeto da ZooLang

$ python zooc.py exemplos/04_erro_sintatico.zoo
exemplos/04_erro_sintatico.zoo: Erro sintático [linha 6, coluna 5]: esperado expressão, encontrado 'rugir'

$ python zooc.py exemplos/05_erro_semantico.zoo
exemplos/05_erro_semantico.zoo: Erro semântico [linha 7]: variável 'filhotes' usada sem declaração (regra R1: declarar antes de usar)
```

## Suíte de testes

| Arquivo                  | Objetivo                                              | Resultado |
|--------------------------|-------------------------------------------------------|-----------|
| `01_valido_basico`       | declaração, atribuição e saída                         | gera `saidas/01_valido_basico.c`; compila e executa |
| `02_valido_completo`     | if/else-if/else, while, for, break, entrada/saída, precedência | gera `saidas/02_valido_completo.c`; compila e executa (entrada `120`) |
| `03_erro_lexico`         | símbolo `@` fora do alfabeto                           | erro léxico (linha 5, coluna 19) |
| `04_erro_sintatico`      | declaração sem expressão após `=`                      | erro sintático (linha 6, coluna 5) |
| `05_erro_semantico`      | atribuição a variável não declarada                    | erro semântico R1 (linha 7) |

Testes unitários: 102 (`tests/test_lexer.py`, `test_parser.py`, `test_semantico.py`,
`test_gerador.py`). Os testes de ponta a ponta compilam o C gerado e são pulados
se não houver gcc.
