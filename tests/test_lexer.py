"""Testes do analisador léxico da ZooLang.

Executar a partir da raiz do projeto:
    python -m unittest discover -s tests -v
"""

import os
import sys
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from zoolang.erros import ErroLexico  # noqa: E402
from zoolang.lexer import tokenizar  # noqa: E402
from zoolang.tokens import TokenType as T  # noqa: E402

EXEMPLOS = os.path.join(RAIZ, "exemplos")


def tipos(fonte):
    """Tipos dos tokens, sem o EOF final."""
    return [t.tipo for t in tokenizar(fonte)][:-1]


def lexemas(fonte):
    return [t.lexema for t in tokenizar(fonte)][:-1]


def ler_exemplo(nome):
    with open(os.path.join(EXEMPLOS, nome), encoding="utf-8") as f:
        return f.read()


class TestPalavrasEIdentificadores(unittest.TestCase):
    def test_delimitadores_de_programa(self):
        self.assertEqual(tipos("ENTRAR_NA_JAULA SAIR_DA_JAULA"),
                         [T.ENTRAR_NA_JAULA, T.SAIR_DA_JAULA])

    def test_tipos(self):
        self.assertEqual(tipos("carneirinho camaleao cobra vagalume fossil"),
                         [T.CARNEIRINHO, T.CAMALEAO, T.COBRA, T.VAGALUME, T.FOSSIL])

    def test_controle_de_fluxo(self):
        fonte = "se_tem_bicho Se_for_outro_bixo nao_tem_bicho contar_carneirinho migrar fugir"
        self.assertEqual(tipos(fonte), [T.SE_TEM_BICHO, T.SE_FOR_OUTRO_BIXO, T.NAO_TEM_BICHO,
                                        T.CONTAR_CARNEIRINHO, T.MIGRAR, T.FUGIR])

    def test_reservadas_futuras_nao_sao_identificadores(self):
        fonte = "alcateia habitat zebra se_der_zebra abater bicho_solto CHEGOU_O_ZELADOR hakuna_matata"
        self.assertNotIn(T.ID, tipos(fonte))

    def test_prefixo_de_palavra_chave_vira_identificador(self):
        # longest match: o lexema inteiro é lido antes de consultar as palavras reservadas
        self.assertEqual(tipos("rugirX rugir_alto vivos cobra2 _gato"), [T.ID] * 5)

    def test_palavras_reservadas_diferenciam_maiusculas(self):
        self.assertEqual(tipos("RUGIR Rugir se_for_outro_bixo"), [T.ID, T.ID, T.ID])

    def test_identificador_com_digitos_e_sublinhado(self):
        toks = tokenizar("peso_supino2")
        self.assertEqual((toks[0].tipo, toks[0].lexema), (T.ID, "peso_supino2"))


class TestNumeros(unittest.TestCase):
    def test_inteiro_e_real(self):
        self.assertEqual(tipos("35 120.5 0.0"), [T.NUM_INT, T.NUM_REAL, T.NUM_REAL])
        self.assertEqual(lexemas("120.5"), ["120.5"])

    def test_real_sem_digito_apos_ponto(self):
        with self.assertRaises(ErroLexico) as ctx:
            tokenizar("x = 12.")
        self.assertIn("12.", str(ctx.exception))

    def test_numero_colado_em_letras(self):
        with self.assertRaises(ErroLexico) as ctx:
            tokenizar("carneirinho x = 12abc")
        self.assertEqual(ctx.exception.lexema, "12abc")

    def test_menos_nao_faz_parte_do_literal(self):
        self.assertEqual(tipos("-5"), [T.MENOS, T.NUM_INT])


class TestOperadoresMaiorCasamento(unittest.TestCase):
    def test_atribuicao_versus_igualdade(self):
        self.assertEqual(tipos("= == ==="), [T.ATRIB, T.IGUAL, T.IGUAL, T.ATRIB])

    def test_relacionais(self):
        self.assertEqual(tipos("< <= > >= !="),
                         [T.MENOR, T.MENOR_IGUAL, T.MAIOR, T.MAIOR_IGUAL, T.DIFERENTE])

    def test_relacionais_sem_espacos(self):
        self.assertEqual(tipos("a<=b"), [T.ID, T.MENOR_IGUAL, T.ID])
        self.assertEqual(tipos("a<-b"), [T.ID, T.MENOR, T.MENOS, T.ID])

    def test_aritmeticos_e_delimitadores(self):
        self.assertEqual(tipos("+-*/(){}[],;:"),
                         [T.MAIS, T.MENOS, T.VEZES, T.DIVIDIDO, T.ABRE_PAR, T.FECHA_PAR,
                          T.ABRE_CHAVE, T.FECHA_CHAVE, T.ABRE_COLCHETE, T.FECHA_COLCHETE,
                          T.VIRGULA, T.PONTO_VIRGULA, T.DOIS_PONTOS])

    def test_exclamacao_isolada(self):
        with self.assertRaises(ErroLexico) as ctx:
            tokenizar("se_tem_bicho (!vivo)")
        self.assertIn("!=", ctx.exception.mensagem)


class TestStrings(unittest.TestCase):
    def test_string_simples_mantem_aspas_no_lexema(self):
        toks = tokenizar('rugir("Ola, Zoo!")')
        self.assertEqual((toks[2].tipo, toks[2].lexema), (T.STRING, '"Ola, Zoo!"'))

    def test_string_com_escapes(self):
        self.assertEqual(lexemas(r'"linha\n\t\"aspas\" \\"'), [r'"linha\n\t\"aspas\" \\"'])

    def test_string_aceita_acentos_e_simbolos(self):
        self.assertEqual(tipos('"TÁ PAGO @ 100% ~ ok"'), [T.STRING])

    def test_string_nao_fechada(self):
        with self.assertRaises(ErroLexico) as ctx:
            tokenizar('ENTRAR_NA_JAULA\n  rugir("sem fim)\nSAIR_DA_JAULA')
        self.assertEqual((ctx.exception.linha, ctx.exception.coluna), (2, 9))

    def test_escape_invalido(self):
        with self.assertRaises(ErroLexico):
            tokenizar(r'"abc\q"')

    def test_aspas_tipograficas(self):
        with self.assertRaises(ErroLexico) as ctx:
            tokenizar("rugir(“mensagem”)")
        self.assertIn("aspas tipográficas", ctx.exception.mensagem)


class TestEspacosEComentarios(unittest.TestCase):
    def test_quebras_de_linha_sao_separadores(self):
        self.assertEqual(tipos("carneirinho\n\tx\r\n=\n1"),
                         [T.CARNEIRINHO, T.ID, T.ATRIB, T.NUM_INT])

    def test_comentario_descartado(self):
        self.assertEqual(tipos("~ comentario com = e == ~ rugir"), [T.RUGIR])

    def test_comentario_multilinha_preserva_contagem_de_linhas(self):
        toks = tokenizar("~ linha 1\nlinha 2\nlinha 3 ~\nfugir")
        self.assertEqual((toks[0].tipo, toks[0].linha, toks[0].coluna), (T.FUGIR, 4, 1))

    def test_comentario_nao_fechado(self):
        with self.assertRaises(ErroLexico) as ctx:
            tokenizar("ENTRAR_NA_JAULA\n~ esqueci de fechar\nSAIR_DA_JAULA")
        self.assertEqual(ctx.exception.linha, 2)

    def test_posicoes_linha_coluna(self):
        toks = tokenizar("ENTRAR_NA_JAULA\n    carneirinho x = 10")
        self.assertEqual([(t.linha, t.coluna) for t in toks],
                         [(1, 1), (2, 5), (2, 17), (2, 19), (2, 21), (2, 23)])

    def test_eof_sempre_presente(self):
        toks = tokenizar("")
        self.assertEqual(len(toks), 1)
        self.assertIs(toks[0].tipo, T.EOF)


class TestErrosDeAlfabeto(unittest.TestCase):
    def test_arroba_indica_linha_e_coluna(self):
        with self.assertRaises(ErroLexico) as ctx:
            tokenizar("ENTRAR_NA_JAULA\n  x = y @ 2\nSAIR_DA_JAULA")
        e = ctx.exception
        self.assertEqual((e.linha, e.coluna, e.lexema), (2, 9, "@"))
        self.assertEqual(str(e), "Erro léxico [linha 2, coluna 9]: "
                                 "símbolo '@' não pertence ao alfabeto da ZooLang")

    def test_outros_simbolos_invalidos(self):
        for simbolo in ["#", "$", "&", "|", "?", ".", "'", "%"]:
            with self.subTest(simbolo=simbolo):
                with self.assertRaises(ErroLexico):
                    tokenizar(f"x = 1 {simbolo} 2")

    def test_letra_acentuada_fora_de_string(self):
        with self.assertRaises(ErroLexico) as ctx:
            tokenizar("carneirinho número = 1")
        self.assertEqual(ctx.exception.lexema, "ú")


class TestProgramasDeExemplo(unittest.TestCase):
    def test_01_valido_basico(self):
        toks = tokenizar(ler_exemplo("01_valido_basico.zoo"))
        self.assertIs(toks[0].tipo, T.ENTRAR_NA_JAULA)
        self.assertIs(toks[-2].tipo, T.SAIR_DA_JAULA)

    def test_02_valido_completo(self):
        ts = [t.tipo for t in tokenizar(ler_exemplo("02_valido_completo.zoo"))]
        for esperado in (T.GATO, T.FOSSIL, T.CAPTURAR, T.SE_TEM_BICHO, T.SE_FOR_OUTRO_BIXO,
                         T.NAO_TEM_BICHO, T.CONTAR_CARNEIRINHO, T.MIGRAR, T.FUGIR):
            self.assertIn(esperado, ts)

    def test_03_erro_lexico(self):
        with self.assertRaises(ErroLexico) as ctx:
            tokenizar(ler_exemplo("03_erro_lexico.zoo"))
        self.assertEqual((ctx.exception.linha, ctx.exception.coluna), (5, 19))

    def test_04_e_05_sao_lexicamente_validos(self):
        # Os erros destes arquivos são sintático e semântico, detectados em fases posteriores.
        for nome in ("04_erro_sintatico.zoo", "05_erro_semantico.zoo"):
            with self.subTest(arquivo=nome):
                self.assertIs(tokenizar(ler_exemplo(nome))[-1].tipo, T.EOF)

    def test_exemplo_final_da_proposta_do_grupo(self):
        # "Exemplo Completo Final" do documento ZooLang.pdf, restrito ao escopo atual
        # (sem zebra/se_der_zebra/abater, que são reservadas).
        fonte = '''
        ~ PROGRAMA PRINCIPAL EM ZOOLANG ~
        gato math
        ENTRAR_NA_JAULA
        cobra atleta = "Bambam"
        fossil carneirinho META = 100
        carneirinho carga
        vagalume esta_pronto = vivo
        rugir("Qual a carga no supino?")
        capturar(carga)
        se_tem_bicho (carga >= META) {
           rugir(atleta + " BATEU A META DE " + META + "KG! MONSTRO!")
        } Se_for_outro_bixo (carga >= 50) {
           rugir("Ta no caminho certo, vai subir o peso!")
        } nao_tem_bicho {
           rugir("Carga de frango!")
        }
        carneirinho serie = 1
        contar_carneirinho (serie <= 3) {
           rugir("Serie " + serie + " concluida!")
           serie = serie + 1
        }
        rugir("TREINO FINALIZADO! TÁ PAGO!")
        SAIR_DA_JAULA
        '''
        toks = tokenizar(fonte)
        self.assertIs(toks[-1].tipo, T.EOF)
        self.assertEqual(sum(t.tipo is T.RUGIR for t in toks), 6)


if __name__ == "__main__":
    unittest.main()
