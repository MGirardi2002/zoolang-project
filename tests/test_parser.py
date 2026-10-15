"""Testes do analisador sintático (parser) e da AST da ZooLang.

Executar a partir da raiz do projeto:
    python -m unittest discover -s tests -v
"""

import os
import sys
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from zoolang import ast  # noqa: E402
from zoolang.ast import expr_str, formatar_ast  # noqa: E402
from zoolang.erros import ErroSintatico  # noqa: E402
from zoolang.parser import analisar  # noqa: E402

EXEMPLOS = os.path.join(RAIZ, "exemplos")


def programa(corpo, imports=""):
    return analisar(f"{imports}\nENTRAR_NA_JAULA\n{corpo}\nSAIR_DA_JAULA\n")


def instrucoes(corpo):
    return programa(corpo).corpo.instrucoes


def expressao(texto):
    """AST da expressão à direita de uma atribuição."""
    return instrucoes(f"x = {texto}")[0].expr


def ler_exemplo(nome):
    with open(os.path.join(EXEMPLOS, nome), encoding="utf-8") as f:
        return f.read()


class TestPrecedencia(unittest.TestCase):
    def test_multiplicacao_antes_da_soma(self):
        self.assertEqual(expr_str(expressao("2 + 3 * 4")), "Soma(2, Mult(3, 4))")

    def test_parenteses_mudam_a_arvore(self):
        self.assertEqual(expr_str(expressao("(2 + 3) * 4")), "Mult(Soma(2, 3), 4)")

    def test_associatividade_a_esquerda(self):
        self.assertEqual(expr_str(expressao("10 - 3 - 2")), "Sub(Sub(10, 3), 2)")
        self.assertEqual(expr_str(expressao("8 / 4 / 2")), "Div(Div(8, 4), 2)")

    def test_relacional_tem_a_menor_precedencia(self):
        self.assertEqual(expr_str(expressao("a + 1 >= b * 2")),
                         "MaiorIgual(Soma(a, 1), Mult(b, 2))")

    def test_menos_unario(self):
        self.assertEqual(expr_str(expressao("-a * 2")), "Mult(Neg(a), 2)")
        self.assertEqual(expr_str(expressao("- -5")), "Neg(Neg(5))")

    def test_literais(self):
        e = expressao('"oi"')
        self.assertEqual((type(e), e.tipo, e.valor), (ast.Literal, "cobra", '"oi"'))
        self.assertEqual(expressao("vivo"), ast.Literal("vagalume", "vivo", 3))
        self.assertEqual(expressao("2.5").tipo, "camaleao")

    def test_relacionais_nao_encadeiam(self):
        with self.assertRaises(ErroSintatico) as ctx:
            expressao("1 < 2 < 3")
        self.assertIn("não podem ser encadeados", ctx.exception.mensagem)


class TestInstrucoes(unittest.TestCase):
    def test_declaracoes(self):
        d1, d2 = instrucoes("fossil carneirinho LOTACAO = 100\ncobra nome")
        self.assertEqual((d1.tipo, d1.nome, d1.const, expr_str(d1.expr)),
                         ("carneirinho", "LOTACAO", True, "100"))
        self.assertEqual((d2.tipo, d2.nome, d2.const, d2.expr), ("cobra", "nome", False, None))

    def test_comandos_sem_terminador(self):
        # quebras de linha não importam: tudo numa linha só também é válido
        ins = instrucoes("carneirinho x = 1 x = x + 1 rugir(x) capturar(x)")
        self.assertEqual([type(i) for i in ins],
                         [ast.Declaracao, ast.Atribuicao, ast.Escrita, ast.Leitura])

    def test_else_if_encadeado(self):
        (se,) = instrucoes("""
            se_tem_bicho (x > 10) { rugir(1) }
            Se_for_outro_bixo (x > 5) { rugir(2) }
            Se_for_outro_bixo (x > 0) { rugir(3) }
            nao_tem_bicho { rugir(4) }""")
        self.assertIsInstance(se, ast.Se)
        self.assertEqual([expr_str(c) for c, _ in se.ramos],
                         ["Maior(x, 10)", "Maior(x, 5)", "Maior(x, 0)"])
        self.assertIsNotNone(se.senao)

    def test_se_sem_senao(self):
        (se,) = instrucoes("se_tem_bicho (vivo) { }")
        self.assertEqual((len(se.ramos), se.senao), (1, None))

    def test_enquanto(self):
        (w,) = instrucoes("contar_carneirinho (n <= 3) { n = n + 1 }")
        self.assertIsInstance(w, ast.Enquanto)
        self.assertEqual(len(w.bloco.instrucoes), 1)

    def test_migrar_com_declaracao(self):
        (p,) = instrucoes("migrar (carneirinho i = 10; i > 0; i = i - 1) { fugir }")
        self.assertIsInstance(p.init, ast.Declaracao)
        self.assertEqual(expr_str(p.cond), "Maior(i, 0)")
        self.assertEqual(expr_str(p.passo.expr), "Sub(i, 1)")
        self.assertIsInstance(p.bloco.instrucoes[0], ast.Fugir)

    def test_migrar_com_atribuicao(self):
        (p,) = instrucoes("migrar (i = 0; i < 3; i = i + 1) { }")
        self.assertIsInstance(p.init, ast.Atribuicao)

    def test_importacoes(self):
        prog = programa("", imports="gato math\ngato time")
        self.assertEqual([i.lib for i in prog.imports], ["math", "time"])

    def test_linhas_guardadas_nos_nos(self):
        ins = instrucoes("carneirinho a = 1\n\nrugir(a)")
        self.assertEqual([i.linha for i in ins], [3, 5])


class TestErrosSintaticos(unittest.TestCase):
    def erro(self, fonte):
        with self.assertRaises(ErroSintatico) as ctx:
            analisar(fonte)
        return ctx.exception

    def test_04_erro_sintatico(self):
        e = self.erro(ler_exemplo("04_erro_sintatico.zoo"))
        self.assertEqual(str(e), "Erro sintático [linha 6, coluna 5]: "
                                 "esperado expressão, encontrado 'rugir'")

    def test_chave_nao_fechada(self):
        e = self.erro("ENTRAR_NA_JAULA\nse_tem_bicho (vivo) {\n rugir(1)\nSAIR_DA_JAULA")
        self.assertEqual(e.mensagem, "esperado instrução ou '}', encontrado 'SAIR_DA_JAULA'")
        self.assertEqual((e.linha, e.coluna), (4, 1))

    def test_sem_sair_da_jaula(self):
        e = self.erro("ENTRAR_NA_JAULA\nrugir(1)\n")
        self.assertEqual(e.mensagem,
                         "esperado instrução ou 'SAIR_DA_JAULA', encontrado fim do arquivo")

    def test_sem_entrar_na_jaula(self):
        e = self.erro("rugir(1)\nSAIR_DA_JAULA")
        self.assertIn("esperado 'ENTRAR_NA_JAULA'", e.mensagem)

    def test_parentese_nao_fechado(self):
        e = self.erro("ENTRAR_NA_JAULA\nrugir(1 + 2\nSAIR_DA_JAULA")
        self.assertEqual(e.mensagem, "esperado ')', encontrado 'SAIR_DA_JAULA'")

    def test_ponto_e_virgula_fora_de_migrar(self):
        e = self.erro("ENTRAR_NA_JAULA\ncarneirinho x = 1;\nSAIR_DA_JAULA")
        self.assertEqual(e.mensagem, "esperado instrução ou 'SAIR_DA_JAULA', encontrado ';'")

    def test_codigo_depois_de_sair_da_jaula(self):
        e = self.erro("ENTRAR_NA_JAULA\nSAIR_DA_JAULA\nrugir(1)")
        self.assertIn("fim do arquivo", e.mensagem)

    def test_fossil_no_cabecalho_de_migrar(self):
        e = self.erro("ENTRAR_NA_JAULA\nmigrar (fossil carneirinho i = 0; i < 3; i = i + 1) { }"
                      "\nSAIR_DA_JAULA")
        self.assertIn("declaração ou atribuição no início de migrar", e.mensagem)

    def test_reservadas_futuras_sao_rejeitadas(self):
        for palavra in ("alcateia", "habitat", "zebra", "se_der_zebra", "abater",
                        "bicho_solto", "CHEGOU_O_ZELADOR", "hakuna_matata"):
            with self.subTest(palavra=palavra):
                e = self.erro(f"ENTRAR_NA_JAULA\n{palavra}\nSAIR_DA_JAULA")
                self.assertEqual(e.mensagem, f"'{palavra}' é recurso reservado, "
                                             f"não suportado nesta versão")

    def test_reservada_futura_em_expressao(self):
        e = self.erro("ENTRAR_NA_JAULA\ncobra s = bicho_solto\nSAIR_DA_JAULA")
        self.assertIn("recurso reservado", e.mensagem)

    def test_colchetes_nao_fazem_parte_da_gramatica(self):
        e = self.erro("ENTRAR_NA_JAULA\nx = [1]\nSAIR_DA_JAULA")
        self.assertEqual(e.mensagem, "esperado expressão, encontrado '['")


class TestProgramasDeExemplo(unittest.TestCase):
    def test_validos_e_05_sao_sintaticamente_corretos(self):
        for nome in ("01_valido_basico.zoo", "02_valido_completo.zoo", "05_erro_semantico.zoo"):
            with self.subTest(arquivo=nome):
                self.assertIsInstance(analisar(ler_exemplo(nome)), ast.Programa)

    def test_formatar_ast(self):
        texto = formatar_ast(programa("resultado = 2 + 3 * 4"))
        self.assertEqual(texto.splitlines(), [
            "Programa",
            "└── Bloco",
            "    └── Atribuicao resultado",
            "        └── Soma +",
            "            ├── Literal carneirinho 2",
            "            └── Mult *",
            "                ├── Literal carneirinho 3",
            "                └── Literal carneirinho 4",
        ])


if __name__ == "__main__":
    unittest.main()
