"""Roda toda a suíte de testes da ZooLang e mostra a saída de cada caso.

Uso:
    python rodar_testes.py            # testes unitários + os 5 programas de exemplo
    python rodar_testes.py --salvar   # também grava as saídas em exemplos/saidas/

Para cada programa de exemplos/ o script executa o pipeline completo
(lexer -> parser -> semântica -> gerador de C). Nos programas válidos, compila
o C gerado com gcc (ou ZOOC_CC) e executa o programa; o 02 recebe a entrada
definida em ENTRADAS.
"""

import argparse
import glob
import os
import subprocess
import sys
import tempfile
import unittest

from zoolang.erros import ZooLangError
from zooc import comando_compilador, transpilar

RAIZ = os.path.dirname(os.path.abspath(__file__))
EXEMPLOS = os.path.join(RAIZ, "exemplos")
SAIDAS = os.path.join(EXEMPLOS, "saidas")
ENTRADAS = {"02_valido_completo": "120\n"}


def titulo(texto):
    print()
    print("=" * 70)
    print(texto)
    print("=" * 70)


def gravar(nome, conteudo):
    with open(os.path.join(SAIDAS, nome), "w", encoding="utf-8", newline="\n") as f:
        f.write(conteudo)


def executar_c(cc, codigo_c, entrada):
    with tempfile.TemporaryDirectory() as tmp:
        fonte = os.path.join(tmp, "prog.c")
        exe = os.path.join(tmp, "prog.exe")
        with open(fonte, "w", encoding="utf-8") as f:
            f.write(codigo_c)
        r = subprocess.run(cc + [fonte, "-o", exe], capture_output=True, text=True)
        if r.returncode != 0:
            return False, r.stderr
        r = subprocess.run([exe], input=entrada, capture_output=True, text=True, timeout=10)
        return True, r.stdout.replace("\r\n", "\n")


def rodar_exemplos(salvar):
    cc = comando_compilador()
    ok = True
    for caminho in sorted(glob.glob(os.path.join(EXEMPLOS, "*.zoo"))):
        nome = os.path.splitext(os.path.basename(caminho))[0]
        titulo(f"exemplos/{nome}.zoo")
        with open(caminho, encoding="utf-8") as f:
            fonte = f.read()
        espera_erro = "_erro_" in nome

        try:
            tokens, _, codigo = transpilar(fonte)
        except ZooLangError as e:
            mensagem = f"exemplos/{nome}.zoo: {e}\n"
            print(mensagem, end="")
            if salvar:
                gravar(f"{nome}.erro.txt", mensagem)
            if not espera_erro:
                ok = False
                print("FALHOU: era esperado um programa válido")
            continue

        if espera_erro:
            ok = False
            print("FALHOU: era esperado um erro, mas o programa foi aceito")
            continue

        print(f"Transpilação concluída ({len(tokens)} tokens). Código C gerado:\n")
        print(codigo)
        if salvar:
            gravar(f"{nome}.c", codigo)

        if cc is None:
            print("(gcc não encontrado: compilação e execução puladas)")
            continue
        entrada = ENTRADAS.get(nome, "")
        compilou, saida = executar_c(cc, codigo, entrada)
        if not compilou:
            ok = False
            print(f"FALHOU: o C gerado não compilou:\n{saida}")
            continue
        cabecalho = f"Execução (entrada: {entrada.strip()!r}):" if entrada else "Execução:"
        print(cabecalho)
        print(saida, end="")
        if salvar:
            gravar(f"{nome}.execucao.txt", f"{cabecalho}\n{saida}")
    return ok


def main():
    parser = argparse.ArgumentParser(description="Roda a suíte de testes da ZooLang")
    parser.add_argument("--salvar", action="store_true",
                        help="grava as saídas de cada caso em exemplos/saidas/")
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    os.chdir(RAIZ)

    titulo("Testes unitários (tests/)")
    suite = unittest.defaultTestLoader.discover(os.path.join(RAIZ, "tests"))
    resultado = unittest.TextTestRunner(verbosity=1).run(suite)

    if args.salvar:
        os.makedirs(SAIDAS, exist_ok=True)
    exemplos_ok = rodar_exemplos(args.salvar)

    titulo("Resumo")
    print(f"Testes unitários: {resultado.testsRun} executados, "
          f"{len(resultado.failures) + len(resultado.errors)} falhas, "
          f"{len(resultado.skipped)} pulados")
    print(f"Programas de exemplo: {'todos com o resultado esperado' if exemplos_ok else 'FALHAS'}")
    if args.salvar:
        print("Saídas gravadas em exemplos/saidas/")
    return 0 if resultado.wasSuccessful() and exemplos_ok else 1


if __name__ == "__main__":
    sys.exit(main())
