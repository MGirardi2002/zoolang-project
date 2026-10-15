"""Gerador de código C a partir da AST anotada pela análise semântica.

A tradução percorre a árvore (não é substituição textual):

    carneirinho -> int      printf %d   scanf %d
    camaleao    -> double   printf %g   scanf %lf
    cobra       -> char x[256]  (atribuição com strcpy)  printf %s  scanf %255s
    vagalume    -> bool (stdbool.h), impresso como "vivo"/"morto"
    fossil T    -> const T

rugir(expr) vira um único printf terminado em "\\n"; quando há concatenação
com '+', cada parte vira um especificador de formato escolhido pelo tipo que
a análise semântica anotou. Os parênteses das expressões são gerados a partir
da forma da árvore e da precedência dos operadores de C, então só aparecem
quando são necessários.
"""

from . import ast
from .ast import CAMALEAO, CARNEIRINHO, COBRA, VAGALUME

TAM_COBRA = 256

TIPOS_C = {CARNEIRINHO: "int", CAMALEAO: "double", COBRA: "char", VAGALUME: "bool"}
VALOR_INICIAL = {CARNEIRINHO: "0", CAMALEAO: "0.0", COBRA: '""', VAGALUME: "false"}
FORMATO_PRINTF = {CARNEIRINHO: "%d", CAMALEAO: "%g", COBRA: "%s", VAGALUME: "%s"}
FORMATO_SCANF = {CARNEIRINHO: "%d", CAMALEAO: "%lf", COBRA: "%255s"}

# Precedência dos operadores em C (maior número = liga mais forte).
PRECEDENCIA = {"==": 1, "!=": 1, "<": 2, "<=": 2, ">": 2, ">=": 2,
               "+": 3, "-": 3, "*": 4, "/": 4}
PREC_UNARIO = 5
PREC_ATOMO = 6

# Identificadores válidos em ZooLang que não podem ser usados como nomes em C.
NOMES_PROIBIDOS_C = {
    "auto", "break", "case", "char", "const", "continue", "default", "do", "double",
    "else", "enum", "extern", "float", "for", "goto", "if", "inline", "int", "long",
    "register", "restrict", "return", "short", "signed", "sizeof", "static", "struct",
    "switch", "typedef", "union", "unsigned", "void", "volatile", "while", "_Bool",
    "bool", "true", "false", "main", "printf", "scanf", "strcpy", "NULL",
}

INCLUDES_GATO = {"math": "math.h", "stdlib": "stdlib.h", "string": "string.h", "time": "time.h"}


def nome_c(nome):
    return nome + "_zoo" if nome in NOMES_PROIBIDOS_C else nome


def _precedencia(e):
    if isinstance(e, ast.BinOp):
        return PRECEDENCIA[e.op]
    if isinstance(e, ast.Unario):
        return PREC_UNARIO
    return PREC_ATOMO


def _conteudo_formato(literal):
    """Conteúdo de um literal cobra para dentro do formato do printf.

    As sequências de escape da ZooLang (\\n \\t \\" \\\\) são as mesmas de C e
    são copiadas como estão; só '%' precisa virar '%%'.
    """
    return literal.valor[1:-1].replace("%", "%%")


class GeradorC:
    def __init__(self):
        self.linhas = []
        self.nivel = 1
        self.usa_bool = False
        self.usa_string = False

    def _emitir(self, texto):
        self.linhas.append("    " * self.nivel + texto)

    # --------------------------------------------------------------- programa
    def gerar(self, programa):
        self._instrucoes(programa.corpo.instrucoes)

        includes = ["stdio.h"]
        if self.usa_bool:
            includes.append("stdbool.h")
        if self.usa_string:
            includes.append("string.h")
        for imp in programa.imports:
            h = INCLUDES_GATO[imp.lib]
            if h not in includes:
                includes.append(h)

        saida = ["/* Gerado pelo transpilador ZooLang (zooc). */"]
        saida += [f"#include <{h}>" for h in includes]
        saida += ["", "int main(void) {"]
        saida += self.linhas
        saida += ["    return 0;", "}", ""]
        return "\n".join(saida)

    def _instrucoes(self, instrucoes):
        for instr in instrucoes:
            self._instrucao(instr)

    def _bloco_aberto(self, bloco):
        """Emite o conteúdo de um bloco já aberto com '{' e fecha o nível."""
        self.nivel += 1
        self._instrucoes(bloco.instrucoes)
        self.nivel -= 1

    # ------------------------------------------------------------- instruções
    def _instrucao(self, no):
        if isinstance(no, ast.Declaracao):
            for linha in self._declaracao(no):
                self._emitir(linha)
        elif isinstance(no, ast.Atribuicao):
            self._emitir(self._atribuicao(no) + ";")
        elif isinstance(no, ast.Leitura):
            self._leitura(no)
        elif isinstance(no, ast.Escrita):
            self._escrita(no)
        elif isinstance(no, ast.Se):
            self._se(no)
        elif isinstance(no, ast.Enquanto):
            self._emitir(f"while ({self._expr(no.cond)}) {{")
            self._bloco_aberto(no.bloco)
            self._emitir("}")
        elif isinstance(no, ast.Para):
            self._para(no)
        elif isinstance(no, ast.Fugir):
            self._emitir("break;")
        else:
            raise TypeError(f"instrução desconhecida: {no!r}")

    def _declaracao(self, no):
        """Retorna as linhas de C de uma declaração (sem indentação).

        Variáveis sem valor inicial recebem o valor neutro do tipo, para que o
        programa C nunca leia uma variável não inicializada.
        """
        nome = nome_c(no.nome)
        const = "const " if no.const else ""
        if no.tipo == VAGALUME:
            self.usa_bool = True

        if no.tipo == COBRA:
            if no.expr is None or isinstance(no.expr, ast.Literal):
                valor = no.expr.valor if no.expr is not None else '""'
                return [f"{const}char {nome}[{TAM_COBRA}] = {valor};"]
            # cobra inicializada com outra variável: copia com strcpy.
            # (fossil é garantido pela análise semântica, por isso sem const aqui)
            self.usa_string = True
            return [f"char {nome}[{TAM_COBRA}] = \"\";",
                    f"strcpy({nome}, {self._expr(no.expr)});"]

        valor = VALOR_INICIAL[no.tipo] if no.expr is None else self._expr(no.expr)
        return [f"{const}{TIPOS_C[no.tipo]} {nome} = {valor};"]

    def _atribuicao(self, no):
        """Atribuição como expressão C (sem ';'), para servir também no passo do for."""
        nome = nome_c(no.nome)
        if no.expr.tipo == COBRA:
            self.usa_string = True
            return f"strcpy({nome}, {self._expr(no.expr)})"
        return f"{nome} = {self._expr(no.expr)}"

    def _leitura(self, no):
        tipo = no.tipo   # anotado pela análise semântica
        nome = nome_c(no.nome)
        endereco = nome if tipo == COBRA else "&" + nome
        self._emitir(f'scanf("{FORMATO_SCANF[tipo]}", {endereco});')

    def _escrita(self, no):
        formato, args = [], []
        for parte in self._partes_concatenacao(no.expr):
            if isinstance(parte, ast.Literal) and parte.tipo == COBRA:
                formato.append(_conteudo_formato(parte))
            else:
                formato.append(FORMATO_PRINTF[parte.tipo])
                args.append(self._argumento_printf(parte))
        texto = '"' + "".join(formato) + '\\n"'
        self._emitir(f"printf({', '.join([texto] + args)});")

    def _partes_concatenacao(self, e):
        """Achata a cadeia de '+' de texto: "a" + x + "b" -> ["a", x, "b"].

        Só os nós '+' cujo tipo é cobra são concatenação; um '+' numérico
        dentro dela (ex.: (1 + 2) + "a") continua sendo uma única parte.
        """
        if isinstance(e, ast.BinOp) and e.op == "+" and e.tipo == COBRA:
            return self._partes_concatenacao(e.esq) + self._partes_concatenacao(e.dir)
        return [e]

    def _argumento_printf(self, e):
        if e.tipo == VAGALUME:
            self.usa_bool = True
            expr = self._expr(e)
            if _precedencia(e) < PREC_ATOMO:
                expr = f"({expr})"
            return f'{expr} ? "vivo" : "morto"'
        return self._expr(e)

    def _se(self, no):
        for i, (cond, bloco) in enumerate(no.ramos):
            if i == 0:
                self._emitir(f"if ({self._expr(cond)}) {{")
            else:
                self.linhas[-1] += f" else if ({self._expr(cond)}) {{"
            self._bloco_aberto(bloco)
            self._emitir("}")
        if no.senao is not None:
            self.linhas[-1] += " else {"
            self._bloco_aberto(no.senao)
            self._emitir("}")

    def _para(self, no):
        if isinstance(no.init, ast.Declaracao):
            linhas = self._declaracao(no.init)
            if len(linhas) > 1:
                # cobra inicializada com variável: declara antes, num bloco próprio
                # para manter a variável de controle restrita ao laço.
                self._emitir("{")
                self.nivel += 1
                for linha in linhas:
                    self._emitir(linha)
                self._emitir(f"for (; {self._expr(no.cond)}; {self._atribuicao(no.passo)}) {{")
                self._bloco_aberto(no.bloco)
                self._emitir("}")
                self.nivel -= 1
                self._emitir("}")
                return
            init = linhas[0][:-1]  # sem o ';'
        else:
            init = self._atribuicao(no.init)
        self._emitir(f"for ({init}; {self._expr(no.cond)}; {self._atribuicao(no.passo)}) {{")
        self._bloco_aberto(no.bloco)
        self._emitir("}")

    # ------------------------------------------------------------- expressões
    def _expr(self, e):
        if isinstance(e, ast.Literal):
            if e.tipo == VAGALUME:
                self.usa_bool = True
                return "true" if e.valor == "vivo" else "false"
            return e.valor
        if isinstance(e, ast.Var):
            return nome_c(e.nome)
        if isinstance(e, ast.Unario):
            operando = self._expr(e.expr)
            # parênteses se o operando liga mais fraco, e também em -(-x),
            # para não gerar o operador de decremento "--" de C.
            if _precedencia(e.expr) < PREC_UNARIO or isinstance(e.expr, ast.Unario):
                operando = f"({operando})"
            return f"-{operando}"

        p = PRECEDENCIA[e.op]
        esq = self._expr(e.esq)
        dir_ = self._expr(e.dir)
        # Associatividade à esquerda: o filho esquerdo só precisa de parênteses
        # se ligar mais fraco; o direito também quando tiver a mesma precedência
        # (a - (b - c) é diferente de a - b - c).
        if _precedencia(e.esq) < p:
            esq = f"({esq})"
        if _precedencia(e.dir) <= p:
            dir_ = f"({dir_})"
        return f"{esq} {e.op} {dir_}"


def gerar_c(programa):
    """Atalho: AST anotada pela análise semântica -> código C (texto)."""
    return GeradorC().gerar(programa)
