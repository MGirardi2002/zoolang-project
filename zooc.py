"""Interface de linha de comando do transpilador ZooLang.

Uso:
    python zooc.py programa.zoo                # transpila e grava programa.c
    python zooc.py programa.zoo -o saida.c     # escolhe o arquivo de saída
    python zooc.py programa.zoo --tokens       # exibe também a tabela de tokens
    python zooc.py programa.zoo --ast          # exibe também a AST
    python zooc.py programa.zoo --c            # exibe o C gerado no terminal
    python zooc.py programa.zoo --run          # compila com gcc e executa

Pipeline: lexer -> parser (AST) -> análise semântica -> gerador de C.
O primeiro erro de qualquer fase interrompe o processamento (código de saída 1).

Compilador C usado por --run: gcc, ou o comando da variável de ambiente
ZOOC_CC (ex.: ZOOC_CC="clang").
"""

import argparse
import os
import shlex
import shutil
import subprocess
import sys
import tempfile

from zoolang.ast import formatar_ast
from zoolang.erros import ZooLangError
from zoolang.gerador_c import gerar_c
from zoolang.lexer import tokenizar
from zoolang.parser import Parser
from zoolang.semantico import analisar_semantica


def imprimir_tokens(tokens):
    print(f"{'LINHA:COL':<10} {'TOKEN':<20} LEXEMA")
    print("-" * 50)
    for tok in tokens:
        pos = f"{tok.linha}:{tok.coluna}"
        print(f"{pos:<10} {tok.tipo.name:<20} {tok.lexema}")


def transpilar(fonte):
    """Executa todas as fases e retorna (tokens, ast, codigo_c)."""
    tokens = tokenizar(fonte)
    arvore = Parser(tokens).analisar()
    analisar_semantica(arvore)
    return tokens, arvore, gerar_c(arvore)


def comando_compilador():
    """Comando do compilador C (lista de argumentos) ou None se não houver."""
    cc = os.environ.get("ZOOC_CC")
    if cc:
        return shlex.split(cc, posix=False)
    gcc = shutil.which("gcc")
    return [gcc] if gcc else None


def compilar_e_executar(arquivo_c):
    cc = comando_compilador()
    if cc is None:
        print("Erro: gcc não encontrado no PATH (ou defina ZOOC_CC).", file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory() as tmp:
        exe = os.path.join(tmp, "programa.exe" if os.name == "nt" else "programa")
        r = subprocess.run(cc + [arquivo_c, "-o", exe], capture_output=True, text=True)
        if r.returncode != 0:
            print(f"Erro ao compilar '{arquivo_c}':\n{r.stderr}", file=sys.stderr)
            return 2
        sys.stdout.flush()
        return subprocess.run([exe]).returncode


def main(argv=None):
    parser = argparse.ArgumentParser(prog="zooc", description="Transpilador ZooLang -> C")
    parser.add_argument("arquivo", help="arquivo-fonte ZooLang (.zoo)")
    parser.add_argument("-o", "--saida", help="arquivo C de saída (padrão: mesmo nome com .c)")
    parser.add_argument("--tokens", action="store_true", help="exibe a tabela de tokens")
    parser.add_argument("--ast", action="store_true", help="exibe a árvore sintática abstrata")
    parser.add_argument("--c", dest="mostrar_c", action="store_true",
                        help="exibe o código C gerado")
    parser.add_argument("--run", action="store_true",
                        help="compila o C gerado com gcc e executa o programa")
    args = parser.parse_args(argv)

    # Garante acentuação correta no terminal do Windows.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

    try:
        with open(args.arquivo, encoding="utf-8") as f:
            fonte = f.read()
    except OSError as e:
        print(f"Erro: não foi possível abrir '{args.arquivo}': {e.strerror}", file=sys.stderr)
        return 2

    try:
        if args.tokens:
            imprimir_tokens(tokenizar(fonte))
            print()
        tokens, arvore, codigo = transpilar(fonte)
    except ZooLangError as e:
        print(f"{args.arquivo}: {e}", file=sys.stderr)
        return 1

    if args.ast:
        print(formatar_ast(arvore))
        print()
    if args.mostrar_c:
        print(codigo)

    saida = args.saida or os.path.splitext(args.arquivo)[0] + ".c"
    with open(saida, "w", encoding="utf-8", newline="\n") as f:
        f.write(codigo)
    print(f"Transpilação concluída: {args.arquivo} -> {saida}")

    if args.run:
        print("-" * 50)
        return compilar_e_executar(saida)
    return 0


if __name__ == "__main__":
    sys.exit(main())
