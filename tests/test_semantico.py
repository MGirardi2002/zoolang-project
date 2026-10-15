"""Testes da análise semântica da ZooLang (regras R1–R11).

Executar a partir da raiz do projeto:
    python -m unittest discover -s tests -v
"""

import os
import sys
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from zoolang.erros import ErroSemantico  # noqa: E402
from zoolang.parser import analisar  # noqa: E402
from zoolang.semantico import analisar_semantica  # noqa: E402

EXEMPLOS = os.path.join(RAIZ, "exemplos")


def verificar(corpo, imports=""):
    return analisar_semantica(analisar(f"{imports}\nENTRAR_NA_JAULA\n{corpo}\nSAIR_DA_JAULA\n"))


def ler_exemplo(nome):
    with open(os.path.join(EXEMPLOS, nome), encoding="utf-8") as f:
        return f.read()


class TestCasosValidos(unittest.TestCase):
    def test_exemplos_validos(self):
        for nome in ("01_valido_basico.zoo", "02_valido_completo.zoo"):
            with self.subTest(arquivo=nome):
                analisar_semantica(analisar(ler_exemplo(nome)))

    def test_promocao_int_para_double(self):
        verificar("camaleao x = 1\nx = 2 * 3")

    def test_tipos_das_expressoes_sao_anotados(self):
        prog = verificar("carneirinho a = 1\ncamaleao b = a + 0.5\nvagalume c = a < b")
        _, decl_b, decl_c = prog.corpo.instrucoes
        self.assertEqual(decl_b.expr.tipo, "camaleao")
        self.assertEqual(decl_c.expr.tipo, "vagalume")

    def test_concatenacao_em_rugir(self):
        prog = verificar('carneirinho n = 1\nrugir("Jaula " + n + " limpa")')
        self.assertEqual(prog.corpo.instrucoes[1].expr.tipo, "cobra")

    def test_igualdade_entre_vagalumes(self):
        verificar("vagalume a = vivo\nse_tem_bicho (a == morto) { }")

    def test_sombreamento_em_bloco_interno(self):
        verificar("carneirinho x = 1\nse_tem_bicho (vivo) { cobra x = \"a\" }\nx = 2")

    def test_variavel_de_migrar_so_existe_no_laco(self):
        verificar("migrar (carneirinho i = 0; i < 3; i = i + 1) { }\n"
                  "migrar (carneirinho i = 0; i < 3; i = i + 1) { }")
        with self.assertRaises(ErroSemantico) as ctx:
            verificar("migrar (carneirinho i = 0; i < 3; i = i + 1) { }\nrugir(i)")
        self.assertEqual(ctx.exception.regra, "R1")

    def test_fugir_dentro_de_se_dentro_de_laco(self):
        verificar("contar_carneirinho (vivo) { se_tem_bicho (vivo) { fugir } }")

    def test_bibliotecas_conhecidas(self):
        verificar("", imports="gato math\ngato stdlib\ngato string\ngato time")


class TestRegras(unittest.TestCase):
    def regra(self, corpo, imports=""):
        with self.assertRaises(ErroSemantico) as ctx:
            verificar(corpo, imports)
        return ctx.exception

    def test_05_erro_semantico(self):
        with self.assertRaises(ErroSemantico) as ctx:
            analisar_semantica(analisar(ler_exemplo("05_erro_semantico.zoo")))
        self.assertEqual(str(ctx.exception),
                         "Erro semântico [linha 7]: variável 'filhotes' usada sem declaração "
                         "(regra R1: declarar antes de usar)")

    def test_r1_uso_antes_da_declaracao(self):
        self.assertEqual(self.regra("rugir(x)\ncarneirinho x = 1").regra, "R1")
        self.assertEqual(self.regra("capturar(x)").regra, "R1")
        self.assertEqual(self.regra("carneirinho x = x + 1").regra, "R1")

    def test_r1_variavel_de_bloco_nao_existe_fora(self):
        self.assertEqual(self.regra("se_tem_bicho (vivo) { carneirinho y = 1 }\ny = 2").regra,
                         "R1")

    def test_r2_duplicada(self):
        e = self.regra("carneirinho x\ncamaleao x")
        self.assertEqual(e.regra, "R2")
        self.assertIn("linha 3", e.mensagem)

    def test_r3_incompatibilidade(self):
        for corpo in ("carneirinho n = 2.5", 'carneirinho n = "a"', "vagalume b = 1",
                      "cobra s = 3", "carneirinho n\nn = vivo", "camaleao d = morto"):
            with self.subTest(corpo=corpo):
                self.assertEqual(self.regra(corpo).regra, "R3")

    def test_r4_aritmetica_nao_numerica(self):
        self.assertEqual(self.regra("rugir(vivo * 2)").regra, "R4")
        self.assertEqual(self.regra('rugir("a" - 1)').regra, "R4")
        self.assertEqual(self.regra("rugir(-morto)").regra, "R4")

    def test_r5_concatenacao_fora_de_rugir(self):
        self.assertEqual(self.regra('cobra s = "a" + 1').regra, "R5")
        self.assertEqual(self.regra('se_tem_bicho ("a" + 1 == 2) { }').regra, "R5")

    def test_r5_concatenacao_dentro_de_outro_operador(self):
        # a concatenação precisa ser o argumento direto de rugir, não um operando de '*'
        self.assertEqual(self.regra('rugir(("a" + 1) * 2)').regra, "R5")

    def test_r6_comparacoes_invalidas(self):
        self.assertEqual(self.regra('rugir("a" < 3)').regra, "R6")
        self.assertEqual(self.regra('rugir("a" == "a")').regra, "R6")
        self.assertEqual(self.regra("rugir(vivo < morto)").regra, "R6")

    def test_r7_condicao_nao_logica(self):
        for corpo in ("contar_carneirinho (1 + 1) { }", "se_tem_bicho (2) { }",
                      "se_tem_bicho (vivo) { } Se_for_outro_bixo (3) { }",
                      "migrar (carneirinho i = 0; i; i = i + 1) { }"):
            with self.subTest(corpo=corpo):
                self.assertEqual(self.regra(corpo).regra, "R7")

    def test_r8_fossil(self):
        self.assertEqual(self.regra("fossil carneirinho LOTACAO").regra, "R8")
        self.assertEqual(self.regra("fossil carneirinho LOTACAO = 1\nLOTACAO = 50").regra, "R8")
        self.assertEqual(self.regra("fossil carneirinho LOTACAO = 1\ncapturar(LOTACAO)").regra, "R8")

    def test_r9_fugir_fora_de_laco(self):
        self.assertEqual(self.regra("fugir").regra, "R9")
        self.assertEqual(self.regra("se_tem_bicho (vivo) { fugir }").regra, "R9")

    def test_r10_capturar_vagalume(self):
        self.assertEqual(self.regra("vagalume ok\ncapturar(ok)").regra, "R10")

    def test_r11_biblioteca_desconhecida(self):
        e = self.regra("", imports="gato numpy")
        self.assertEqual((e.regra, e.linha), ("R11", 1))

    def test_mensagem_tem_linha_e_regra(self):
        e = self.regra("carneirinho n\n\nn = 2.5")
        self.assertEqual(str(e), "Erro semântico [linha 5]: não é possível atribuir valor "
                                 "camaleao a 'n' (carneirinho) (regra R3: compatibilidade "
                                 "de tipos na atribuição)")


if __name__ == "__main__":
    unittest.main()
