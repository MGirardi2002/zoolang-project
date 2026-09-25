# ZooLang — transpilador ZooLang → C

Trabalho Prático 1 de **Linguagens Formais e Compiladores** (UNIJUÍ, prof. Marcos Ronaldo Melo Cavalheiro).

**Grupo:** Matheus Girardi, Maiara Zucco, Anderson Scholz e Gustavo Drews.

ZooLang é uma linguagem temática de zoológico, inspirada na BIRL. O programa entra na jaula (`ENTRAR_NA_JAULA`) e sai dela (`SAIR_DA_JAULA`), conta carneirinhos em laços (`contar_carneirinho`) e ruge na saída (`rugir`).

```
ENTRAR_NA_JAULA
    carneirinho serie = 1
    contar_carneirinho (serie <= 3) {
        rugir("Serie " + serie + " concluida!")
        serie = serie + 1
    }
SAIR_DA_JAULA
```

## Estado das etapas

| Fase                            | Estado       |
|---------------------------------|--------------|
| Especificação léxica e GLC      | concluída (ver `docs/Relatorio_Tecnico_ZooLang.docx`) |
| Analisador léxico + erros       | **concluído** |
| Parser + AST + erros sintáticos | pendente     |
| Análise semântica               | pendente     |
| Geração de código C             | pendente     |

## Pré-requisitos

- Python 3.10 ou superior (usa só a biblioteca padrão, sem instalar pacotes)
- gcc, para compilar o C gerado (etapas futuras)

## Estrutura

```
zooc.py               CLI do transpilador
zoolang/tokens.py     tipos de token, palavras reservadas, operadores
zoolang/lexer.py      analisador léxico (scanner escrito à mão)
zoolang/erros.py      exceções (ErroLexico, ...)
tests/test_lexer.py   testes unitários do lexer
exemplos/             suíte obrigatória de testes (01 a 05) em .zoo
exemplos/saidas/      saída do transpilador para cada exemplo
docs/                 relatório técnico (.docx)
docs/fonte/           script que gera o relatório
```

Para regenerar o relatório depois de mudanças (precisa de Node.js):

```bash
npm install docx
node docs/fonte/gerar_relatorio.js
```

## Como usar

```bash
# roda as fases disponíveis (hoje: análise léxica)
python zooc.py exemplos/02_valido_completo.zoo

# mostra a tabela de tokens reconhecidos
python zooc.py exemplos/01_valido_basico.zoo --tokens

# roda os testes unitários
python -m unittest discover -s tests -v
```

Exemplo de saída com `--tokens`:

```
LINHA:COL  TOKEN                LEXEMA
--------------------------------------------------
3:1        ENTRAR_NA_JAULA      ENTRAR_NA_JAULA
4:5        COBRA                cobra
4:11       ID                   atleta
4:18       ATRIB                =
4:20       STRING               "Bambam"
...
```

Exemplo de erro léxico (o código de saída é 1):

```
$ python zooc.py exemplos/03_erro_lexico.zoo
exemplos/03_erro_lexico.zoo: Erro léxico [linha 5, coluna 19]: símbolo '@' não pertence ao alfabeto da ZooLang
```

## Suíte de testes

| Arquivo                  | Objetivo                                              | Resultado atual |
|--------------------------|-------------------------------------------------------|-----------------|
| `01_valido_basico`       | declaração, atribuição e saída                         | léxico OK |
| `02_valido_completo`     | if/else-if/else, while, for, break, entrada/saída, precedência | léxico OK |
| `03_erro_lexico`         | símbolo `@` fora do alfabeto                           | erro léxico (linha 5, coluna 19) |
| `04_erro_sintatico`      | declaração sem expressão após `=`                      | léxico OK; o erro será detectado pelo parser |
| `05_erro_semantico`      | atribuição a variável não declarada                    | léxico OK; o erro será detectado pela análise semântica |
