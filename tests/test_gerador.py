"""Testes do gerador de código C da ZooLang.

Os testes de ponta a ponta compilam o C gerado e executam o programa. Eles
usam o gcc do PATH (ou o comando da variável ZOOC_CC) e são pulados se não
houver compilador C disponível.

Executar a partir da raiz do projeto:
    python -m unittest discover -s tests -v
"""

import os
import subprocess
import sys
import tempfile
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from zooc import comando_compilador, transpilar  # noqa: E402

EXEMPLOS = os.path.join(RAIZ, "exemplos")
CC = comando_compilador()


def gerar(corpo, imports=""):
    return transpilar(f"{imports}\nENTRAR_NA_JAULA\n{corpo}\nSAIR_DA_JAULA\n")[2]


def corpo_c(corpo, imports=""):
    """Linhas de main() sem indentação, sem o 'return 0;'."""
    c = gerar(corpo, imports)
    dentro = c.split("int main(void) {\n", 1)[1].rsplit("    return 0;", 1)[0]
    return [linha.strip() for linha in dentro.splitlines()]


def ler_exemplo(nome):
    with open(os.path.join(EXEMPLOS, nome), encoding="utf-8") as f:
        return f.read()


def executar(codigo_c, entrada=""):
    """Compila o código C e retorna a saída padrão do programa."""
    with tempfile.TemporaryDirectory() as tmp:
        fonte = os.path.join(tmp, "prog.c")
        exe = os.path.join(tmp, "prog.exe")
        with open(fonte, "w", encoding="utf-8") as f:
            f.write(codigo_c)
        r = subprocess.run(CC + ["-std=c99", "-Wall", "-Werror=implicit-function-declaration",
                                 fonte, "-o", exe], capture_output=True, text=True)
        if r.returncode != 0:
            raise AssertionError(f"o C gerado não compilou:\n{r.stderr}\n{codigo_c}")
        r = subprocess.run([exe], input=entrada, capture_output=True, text=True, timeout=10)
        return r.stdout.replace("\r\n", "\n")


class TestTraducao(unittest.TestCase):
    def test_declaracoes(self):
        self.assertEqual(corpo_c('carneirinho a = 1\ncamaleao b\ncobra c = "oi"\n'
                                 'vagalume d = vivo\nfossil carneirinho E = 5'),
                         ["int a = 1;", "double b = 0.0;", 'char c[256] = "oi";',
                          "bool d = true;", "const int E = 5;"])

    def test_includes(self):
        c = gerar("vagalume v = morto\ncobra a\ncobra b = a", imports="gato math")
        self.assertIn("#include <stdio.h>\n#include <stdbool.h>\n#include <string.h>\n"
                      "#include <math.h>\n", c)
        self.assertNotIn("stdbool", gerar("rugir(1)"))

    def test_cobra_usa_strcpy(self):
        self.assertEqual(corpo_c('cobra a\ncobra b = a\na = "x"'),
                         ['char a[256] = "";', 'char b[256] = "";', "strcpy(b, a);",
                          'strcpy(a, "x");'])

    def test_parenteses_gerados_pela_arvore(self):
        linhas = corpo_c("carneirinho x = 2 + 3 * 4\nx = (2 + 3) * 4\nx = 10 - (3 - 2)\n"
                         "x = (10 - 3) - 2\nx = -(x + 1)\nx = - -x")
        self.assertEqual(linhas, ["int x = 2 + 3 * 4;", "x = (2 + 3) * 4;", "x = 10 - (3 - 2);",
                                  "x = 10 - 3 - 2;", "x = -(x + 1);", "x = -(-x);"])

    def test_rugir_por_tipo(self):
        linhas = corpo_c('carneirinho n = 1\ncamaleao d = 1.5\ncobra s = "a"\nvagalume v = vivo\n'
                         'rugir(n)\nrugir(d)\nrugir(s)\nrugir(v)\nrugir(n > 0)\nrugir("100%")')
        self.assertEqual(linhas[4:], ['printf("%d\\n", n);', 'printf("%g\\n", d);',
                                      'printf("%s\\n", s);', 'printf("%s\\n", v ? "vivo" : "morto");',
                                      'printf("%s\\n", (n > 0) ? "vivo" : "morto");',
                                      'printf("100%%\\n");'])

    def test_rugir_com_concatenacao_vira_um_printf(self):
        linhas = corpo_c('carneirinho refeicao = 1\nrugir("Refeicao " + refeicao + " servida!")')
        self.assertEqual(linhas[1], 'printf("Refeicao %d servida!\\n", refeicao);')

    def test_capturar_por_tipo(self):
        linhas = corpo_c("carneirinho n\ncamaleao d\ncobra s\ncapturar(n)\ncapturar(d)\ncapturar(s)")
        self.assertEqual(linhas[3:], ['scanf("%d", &n);', 'scanf("%lf", &d);',
                                      'scanf("%255s", s);'])

    def test_controle_de_fluxo(self):
        linhas = corpo_c("carneirinho x = 1\n"
                         "se_tem_bicho (x > 1) { x = 1 } Se_for_outro_bixo (x > 0) { x = 2 }"
                         " nao_tem_bicho { x = 3 }\n"
                         "contar_carneirinho (x < 9) { x = x + 1 }\n"
                         "migrar (carneirinho i = 0; i < 3; i = i + 1) { fugir }")
        self.assertEqual(linhas[1:], [
            "if (x > 1) {", "x = 1;", "} else if (x > 0) {", "x = 2;", "} else {", "x = 3;", "}",
            "while (x < 9) {", "x = x + 1;", "}",
            "for (int i = 0; i < 3; i = i + 1) {", "break;", "}",
        ])

    def test_nomes_reservados_em_c_sao_renomeados(self):
        self.assertEqual(corpo_c("carneirinho int = 1\nrugir(int)"),
                         ["int int_zoo = 1;", 'printf("%d\\n", int_zoo);'])


@unittest.skipIf(CC is None, "gcc não encontrado (defina ZOOC_CC para usar outro compilador)")
class TestPontaAPonta(unittest.TestCase):
    def test_01_valido_basico(self):
        c = transpilar(ler_exemplo("01_valido_basico.zoo"))[2]
        self.assertEqual(executar(c), "ROARRR! BEM-VINDO AO ZOOLOGICO DA ZOOLANG!\n"
                                      "Leao Simba\n6\n15\nvivo\n")

    def test_02_valido_completo(self):
        c = transpilar(ler_exemplo("02_valido_completo.zoo"))[2]
        comum_fim = ("Refeicao 1 dos macacos servida!\nRefeicao 2 dos macacos servida!\n"
                     "Refeicao 3 dos macacos servida!\n"
                     "10\n9\n8\n7\n6\nO leao escapou! Todo mundo foge!\n")
        casos = {
            "120": ("BANANA PRA TODO MUNDO! OS MACACOS FIZERAM FESTA!\n", "180"),
            "60": ("Da pro gasto, mas o gorila ficou de olho.\n", "90"),
            "10": ("Pouca banana! Os macacos entraram em greve!\n", "15"),
        }
        for entrada, (mensagem, consumo) in casos.items():
            with self.subTest(entrada=entrada):
                self.assertEqual(executar(c, entrada + "\n"),
                                 "14\n20\nQuantas bananas chegaram para os macacos?\n"
                                 + mensagem + comum_fim + f"Bananas consumidas: {consumo}\n"
                                 "ZOOLOGICO FECHADO! BOA NOITE, BICHOS!\n")

    def test_tipos_e_concatenacao(self):
        c = gerar('cobra nome\ncamaleao d = 7 / 2\nvagalume ok = 3 > 2\ncapturar(nome)\n'
                  'rugir("Oi " + nome + ", d=" + d + " ok=" + ok + " " + 1 + 2)\n'
                  "rugir(1 + 2 + \"a\")\nrugir(-(-4) - 10 / 3)")
        self.assertEqual(executar(c, "Zoo\n"), "Oi Zoo, d=3 ok=vivo 12\n3a\n1\n")

    def test_sombreamento_e_migrar_com_atribuicao(self):
        c = gerar("carneirinho i = 100\ncarneirinho soma\n"
                  "migrar (i = 0; i < 4; i = i + 1) { carneirinho i2 = i * 2 soma = soma + i2 }\n"
                  "rugir(soma)\nrugir(i)\n"
                  'se_tem_bicho (vivo) { cobra i = "sombra" rugir(i) }')
        self.assertEqual(executar(c), "12\n4\nsombra\n")


if __name__ == "__main__":
    unittest.main()
