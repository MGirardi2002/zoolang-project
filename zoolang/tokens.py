"""Definição dos tokens da ZooLang.

Cada categoria de token corresponde a uma linha da tabela de tokens do
relatório (categoria, expressão regular, exemplo de lexema, descrição).
"""

from dataclasses import dataclass
from enum import Enum


class TokenType(Enum):
    # --- Delimitação do programa e importação ---------------------------------
    ENTRAR_NA_JAULA = "ENTRAR_NA_JAULA"        # início do programa
    SAIR_DA_JAULA = "SAIR_DA_JAULA"            # fim do programa
    GATO = "gato"                              # importação (#include)

    # --- Tipos e modificadores -------------------------------------------------
    CARNEIRINHO = "carneirinho"                # int
    CAMALEAO = "camaleao"                      # float
    COBRA = "cobra"                            # string (char*)
    VAGALUME = "vagalume"                      # bool
    FOSSIL = "fossil"                          # const

    # --- Literais lógicos --------------------------------------------------
    VIVO = "vivo"                              # true
    MORTO = "morto"                            # false

    # --- Entrada e saída ---------------------------------------------------
    RUGIR = "rugir"                            # saída (printf)
    CAPTURAR = "capturar"                      # entrada (scanf)

    # --- Controle de fluxo -------------------------------------------------
    SE_TEM_BICHO = "se_tem_bicho"              # if
    SE_FOR_OUTRO_BIXO = "Se_for_outro_bixo"    # else if
    NAO_TEM_BICHO = "nao_tem_bicho"            # else
    CONTAR_CARNEIRINHO = "contar_carneirinho"  # while
    MIGRAR = "migrar"                          # for
    FUGIR = "fugir"                            # break

    # --- Palavras reservadas para versões futuras (fora da gramática atual) --
    ALCATEIA = "alcateia"                      # array / lista
    HABITAT = "habitat"                        # dicionário / map
    ZEBRA = "zebra"                            # try
    SE_DER_ZEBRA = "se_der_zebra"              # catch
    ABATER = "abater"                          # delete / free
    BICHO_SOLTO = "bicho_solto"                # null
    CHEGOU_O_ZELADOR = "CHEGOU_O_ZELADOR"      # return
    HAKUNA_MATATA = "hakuna_matata"            # pass

    # --- Identificadores e literais -----------------------------------------
    ID = "id"
    NUM_INT = "num_int"
    NUM_REAL = "num_real"
    STRING = "string"

    # --- Operadores aritméticos ----------------------------------------------
    MAIS = "+"
    MENOS = "-"
    VEZES = "*"
    DIVIDIDO = "/"

    # --- Atribuição e operadores relacionais -------------------------------
    ATRIB = "="
    IGUAL = "=="
    DIFERENTE = "!="
    MENOR = "<"
    MENOR_IGUAL = "<="
    MAIOR = ">"
    MAIOR_IGUAL = ">="

    # --- Delimitadores -----------------------------------------------------
    ABRE_PAR = "("
    FECHA_PAR = ")"
    ABRE_CHAVE = "{"
    FECHA_CHAVE = "}"
    ABRE_COLCHETE = "["
    FECHA_COLCHETE = "]"
    VIRGULA = ","
    PONTO_VIRGULA = ";"
    DOIS_PONTOS = ":"

    # --- Fim de arquivo ----------------------------------------------------
    EOF = "EOF"


# Palavras reservadas implementadas na gramática atual.
PALAVRAS_RESERVADAS = {
    t.value: t
    for t in (
        TokenType.ENTRAR_NA_JAULA, TokenType.SAIR_DA_JAULA, TokenType.GATO,
        TokenType.CARNEIRINHO, TokenType.CAMALEAO, TokenType.COBRA,
        TokenType.VAGALUME, TokenType.FOSSIL, TokenType.VIVO, TokenType.MORTO,
        TokenType.RUGIR, TokenType.CAPTURAR, TokenType.SE_TEM_BICHO,
        TokenType.SE_FOR_OUTRO_BIXO, TokenType.NAO_TEM_BICHO,
        TokenType.CONTAR_CARNEIRINHO, TokenType.MIGRAR, TokenType.FUGIR,
    )
}

# Palavras reservadas previstas na proposta do grupo, mas ainda não suportadas
# pelo parser. O lexer as reconhece para que não possam ser usadas como
# identificadores; o parser as rejeita com mensagem própria.
RESERVADAS_FUTURAS = {
    t.value: t
    for t in (
        TokenType.ALCATEIA, TokenType.HABITAT, TokenType.ZEBRA,
        TokenType.SE_DER_ZEBRA, TokenType.ABATER, TokenType.BICHO_SOLTO,
        TokenType.CHEGOU_O_ZELADOR, TokenType.HAKUNA_MATATA,
    )
}

KEYWORDS = {**PALAVRAS_RESERVADAS, **RESERVADAS_FUTURAS}

# Operadores e delimitadores. Os de dois caracteres são testados antes dos de
# um caractere (estratégia de maior casamento / longest match).
SIMBOLOS_DUPLOS = {
    "==": TokenType.IGUAL,
    "!=": TokenType.DIFERENTE,
    "<=": TokenType.MENOR_IGUAL,
    ">=": TokenType.MAIOR_IGUAL,
}

SIMBOLOS_SIMPLES = {
    "+": TokenType.MAIS,
    "-": TokenType.MENOS,
    "*": TokenType.VEZES,
    "/": TokenType.DIVIDIDO,
    "=": TokenType.ATRIB,
    "<": TokenType.MENOR,
    ">": TokenType.MAIOR,
    "(": TokenType.ABRE_PAR,
    ")": TokenType.FECHA_PAR,
    "{": TokenType.ABRE_CHAVE,
    "}": TokenType.FECHA_CHAVE,
    "[": TokenType.ABRE_COLCHETE,
    "]": TokenType.FECHA_COLCHETE,
    ",": TokenType.VIRGULA,
    ";": TokenType.PONTO_VIRGULA,
    ":": TokenType.DOIS_PONTOS,
}


@dataclass(frozen=True)
class Token:
    tipo: TokenType
    lexema: str
    linha: int
    coluna: int

    def __str__(self):
        return f"{self.linha}:{self.coluna}\t{self.tipo.name}\t{self.lexema!r}"
