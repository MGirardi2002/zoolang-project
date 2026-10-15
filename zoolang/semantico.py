"""Análise semântica da ZooLang.

Percorre a AST produzida pelo parser, mantém a tabela de símbolos como uma
pilha de escopos e verifica as regras R1–R11 (seção 6 do relatório). Durante
o percurso, anota no campo ``tipo`` de cada expressão o tipo calculado, que o
gerador de código usa para escolher os especificadores de printf/scanf.

Escopos: o programa (ENTRAR_NA_JAULA ... SAIR_DA_JAULA), cada Bloco { } e o
cabeçalho de migrar. Um escopo interno pode redeclarar um nome de um escopo
externo (sombreamento), como em C.

O primeiro erro interrompe a análise com ErroSemantico.
"""

from dataclasses import dataclass

from . import ast
from .ast import CAMALEAO, CARNEIRINHO, COBRA, VAGALUME
from .erros import ErroSemantico

NUMERICOS = (CARNEIRINHO, CAMALEAO)
ARITMETICOS = ("+", "-", "*", "/")
BIBLIOTECAS_CONHECIDAS = ("math", "stdlib", "string", "time")

REGRAS = {
    "R1": "declarar antes de usar",
    "R2": "sem declaração duplicada no mesmo escopo",
    "R3": "compatibilidade de tipos na atribuição",
    "R4": "aritmética só com números",
    "R5": "concatenação só dentro de rugir",
    "R6": "comparação entre tipos compatíveis",
    "R7": "condição deve ser vagalume",
    "R8": "fossil é constante",
    "R9": "fugir só dentro de laço",
    "R10": "tipos aceitos por capturar",
    "R11": "bibliotecas conhecidas",
}


@dataclass
class Simbolo:
    nome: str
    tipo: str
    const: bool
    linha: int


def compativel(destino, valor):
    """Tabela 10: só é permitido o mesmo tipo ou a promoção carneirinho -> camaleao."""
    return destino == valor or (destino == CAMALEAO and valor == CARNEIRINHO)


class AnalisadorSemantico:
    def __init__(self):
        self.escopos = []        # pilha de dicionários nome -> Simbolo
        self.profundidade_laco = 0

    # ------------------------------------------------------------------ util
    def _erro(self, regra, linha, mensagem):
        raise ErroSemantico(f"{mensagem} (regra {regra}: {REGRAS[regra]})", linha, regra)

    def _abrir_escopo(self):
        self.escopos.append({})

    def _fechar_escopo(self):
        self.escopos.pop()

    def _declarar(self, nome, tipo, const, linha):
        escopo = self.escopos[-1]
        if nome in escopo:
            anterior = escopo[nome]
            self._erro("R2", linha, f"variável '{nome}' já foi declarada neste escopo "
                                    f"(linha {anterior.linha})")
        escopo[nome] = Simbolo(nome, tipo, const, linha)

    def _buscar(self, nome, linha):
        for escopo in reversed(self.escopos):
            if nome in escopo:
                return escopo[nome]
        self._erro("R1", linha, f"variável '{nome}' usada sem declaração")

    # --------------------------------------------------------------- programa
    def analisar(self, programa):
        for imp in programa.imports:
            if imp.lib not in BIBLIOTECAS_CONHECIDAS:
                self._erro("R11", imp.linha,
                           f"biblioteca '{imp.lib}' desconhecida; use "
                           + ", ".join(BIBLIOTECAS_CONHECIDAS))
        self._abrir_escopo()
        self._instrucoes(programa.corpo.instrucoes)
        self._fechar_escopo()
        return programa

    def _instrucoes(self, instrucoes):
        for instr in instrucoes:
            self._instrucao(instr)

    def _bloco(self, bloco):
        self._abrir_escopo()
        self._instrucoes(bloco.instrucoes)
        self._fechar_escopo()

    # ------------------------------------------------------------- instruções
    def _instrucao(self, no):
        metodo = getattr(self, "_" + type(no).__name__.lower())
        metodo(no)

    def _declaracao(self, no):
        if no.expr is None:
            if no.const:
                self._erro("R8", no.linha, f"constante fossil '{no.nome}' deve ser "
                                           f"inicializada na declaração")
        else:
            # A expressão é avaliada antes de declarar o nome: em
            # "carneirinho x = x + 1" o x da direita precisa já existir.
            tipo_expr = self._expressao(no.expr)
            if not compativel(no.tipo, tipo_expr):
                self._erro("R3", no.linha, f"não é possível inicializar '{no.nome}' "
                                           f"({no.tipo}) com valor {tipo_expr}")
        self._declarar(no.nome, no.tipo, no.const, no.linha)

    def _atribuicao(self, no):
        simbolo = self._buscar(no.nome, no.linha)
        if simbolo.const:
            self._erro("R8", no.linha, f"'{no.nome}' é fossil (constante) e não pode "
                                       f"receber atribuição")
        tipo_expr = self._expressao(no.expr)
        if not compativel(simbolo.tipo, tipo_expr):
            self._erro("R3", no.linha, f"não é possível atribuir valor {tipo_expr} a "
                                       f"'{no.nome}' ({simbolo.tipo})")

    def _leitura(self, no):
        simbolo = self._buscar(no.nome, no.linha)
        if simbolo.const:
            self._erro("R8", no.linha, f"'{no.nome}' é fossil (constante) e não pode "
                                       f"ser lida com capturar")
        if simbolo.tipo == VAGALUME:
            self._erro("R10", no.linha, f"capturar não aceita a variável '{no.nome}' "
                                        f"do tipo vagalume")
        no.tipo = simbolo.tipo

    def _escrita(self, no):
        self._expressao(no.expr, permitir_concat=True)

    def _condicao(self, cond, comando):
        tipo = self._expressao(cond)
        if tipo != VAGALUME:
            self._erro("R7", cond.linha, f"a condição de {comando} deve ser vagalume, "
                                         f"mas é {tipo}")

    def _se(self, no):
        for i, (cond, bloco) in enumerate(no.ramos):
            self._condicao(cond, "se_tem_bicho" if i == 0 else "Se_for_outro_bixo")
            self._bloco(bloco)
        if no.senao is not None:
            self._bloco(no.senao)

    def _enquanto(self, no):
        self._condicao(no.cond, "contar_carneirinho")
        self.profundidade_laco += 1
        self._bloco(no.bloco)
        self.profundidade_laco -= 1

    def _para(self, no):
        self._abrir_escopo()          # escopo do cabeçalho: a variável de controle
        self._instrucao(no.init)
        self._condicao(no.cond, "migrar")
        self._atribuicao(no.passo)
        self.profundidade_laco += 1
        self._bloco(no.bloco)
        self.profundidade_laco -= 1
        self._fechar_escopo()

    def _fugir(self, no):
        if self.profundidade_laco == 0:
            self._erro("R9", no.linha, "fugir usado fora de contar_carneirinho ou migrar")

    # ------------------------------------------------------------- expressões
    def _expressao(self, no, permitir_concat=False):
        """Calcula, anota (no.tipo) e retorna o tipo de uma expressão.

        permitir_concat só é verdadeiro para o argumento de rugir e, a partir
        dele, para os operandos de '+' encadeados (concatenação da esquerda
        para a direita, como em Java): "a" + 1 + 2 imprime "a12".
        """
        if isinstance(no, ast.Literal):
            return no.tipo
        if isinstance(no, ast.Var):
            no.tipo = self._buscar(no.nome, no.linha).tipo
            return no.tipo
        if isinstance(no, ast.Unario):
            tipo = self._expressao(no.expr)
            if tipo not in NUMERICOS:
                self._erro("R4", no.linha, f"menos unário exige operando numérico, "
                                           f"encontrado {tipo}")
            no.tipo = tipo
            return tipo

        concat_filhos = permitir_concat and no.op == "+"
        esq = self._expressao(no.esq, concat_filhos)
        dir_ = self._expressao(no.dir, concat_filhos)

        if no.op in ARITMETICOS:
            if no.op == "+" and COBRA in (esq, dir_):
                if not permitir_concat:
                    self._erro("R5", no.linha, "concatenação com '+' envolvendo cobra só "
                                               "é permitida dentro de rugir")
                no.tipo = COBRA
            elif esq in NUMERICOS and dir_ in NUMERICOS:
                no.tipo = CARNEIRINHO if esq == dir_ == CARNEIRINHO else CAMALEAO
            else:
                invalido = esq if esq not in NUMERICOS else dir_
                self._erro("R4", no.linha, f"operador '{no.op}' exige operandos numéricos, "
                                           f"encontrado {invalido}")
            return no.tipo

        # relacionais
        if esq in NUMERICOS and dir_ in NUMERICOS:
            pass
        elif no.op in ("==", "!=") and esq == dir_ == VAGALUME:
            pass
        else:
            self._erro("R6", no.linha, f"não é possível comparar {esq} com {dir_} "
                                       f"usando '{no.op}'")
        no.tipo = VAGALUME
        return VAGALUME


def analisar_semantica(programa):
    """Atalho: verifica a AST (lança ErroSemantico) e a retorna anotada."""
    return AnalisadorSemantico().analisar(programa)
