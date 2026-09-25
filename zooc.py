"""Interface de linha de comando do transpilador ZooLang.

Uso:
    python zooc.py programa.zoo            # executa as fases disponíveis
    python zooc.py programa.zoo --tokens   # exibe a tabela de tokens

Etapa atual: análise léxica. As fases de análise sintática (AST), análise
semântica e geração de código C serão encadeadas aqui nas próximas etapas.
"""

import argparse
import sys

from zoolang.erros import ZooLangError
from zoolang.lexer import tokenizar


def imprimir_tokens(tokens):
    print(f"{'LINHA:COL':<10} {'TOKEN':<20} LEXEMA")
    print("-" * 50)
    for tok in tokens:
        pos = f"{tok.linha}:{tok.coluna}"
        print(f"{pos:<10} {tok.tipo.name:<20} {tok.lexema}")


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="zooc",
        description="Transpilador ZooLang -> C (etapa atual: análise léxica)",
    )
    parser.add_argument("arquivo", help="arquivo-fonte ZooLang (.zoo)")
    parser.add_argument("--tokens", action="store_true", help="exibe a tabela de tokens reconhecidos")
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
        tokens = tokenizar(fonte)
    except ZooLangError as e:
        print(f"{args.arquivo}: {e}", file=sys.stderr)
        return 1

    if args.tokens:
        imprimir_tokens(tokens)
    print(f"Análise léxica concluída: {len(tokens)} tokens reconhecidos (incluindo EOF).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
