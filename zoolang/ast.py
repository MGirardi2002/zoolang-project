"""Nós da Árvore Sintática Abstrata (AST) da ZooLang.

O parser constrói a árvore com estes nós; a análise semântica percorre a
árvore, consulta a tabela de símbolos e anota o tipo de cada expressão no
campo ``tipo``; o gerador de código percorre a árvore anotada e emite C.

Os tipos são guardados com os nomes da ZooLang: "carneirinho", "camaleao",
"cobra" e "vagalume". Cada nó guarda a linha do token que o originou, usada
nas mensagens de erro semântico.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Union

CARNEIRINHO = "carneirinho"
CAMALEAO = "camaleao"
COBRA = "cobra"
VAGALUME = "vagalume"
TIPOS = (CARNEIRINHO, CAMALEAO, COBRA, VAGALUME)


# ------------------------------------------------------------------ expressões
@dataclass
class Literal:
    tipo: str                # tipo ZooLang do literal
    valor: str               # lexema original ("35", "120.5", '"Simba"', "vivo")
    linha: int = 0


@dataclass
class Var:
    nome: str
    linha: int = 0
    tipo: Optional[str] = field(default=None, compare=False)


@dataclass
class Unario:
    op: str                  # só "-" nesta versão
    expr: "Expr"
    linha: int = 0
    tipo: Optional[str] = field(default=None, compare=False)


@dataclass
class BinOp:
    op: str                  # + - * / == != < <= > >=
    esq: "Expr"
    dir: "Expr"
    linha: int = 0
    tipo: Optional[str] = field(default=None, compare=False)


Expr = Union[Literal, Var, Unario, BinOp]


# ----------------------------------------------------------------- instruções
@dataclass
class Bloco:
    instrucoes: List["Instrucao"]
    linha: int = 0


@dataclass
class Declaracao:
    tipo: str
    nome: str
    const: bool
    expr: Optional[Expr]
    linha: int = 0


@dataclass
class Atribuicao:
    nome: str
    expr: Expr
    linha: int = 0


@dataclass
class Leitura:
    nome: str
    linha: int = 0
    tipo: Optional[str] = field(default=None, compare=False)   # tipo da variável lida


@dataclass
class Escrita:
    expr: Expr
    linha: int = 0


@dataclass
class Se:
    ramos: List[Tuple[Expr, Bloco]]   # se_tem_bicho seguido dos Se_for_outro_bixo
    senao: Optional[Bloco]            # nao_tem_bicho
    linha: int = 0


@dataclass
class Enquanto:
    cond: Expr
    bloco: Bloco
    linha: int = 0


@dataclass
class Para:
    init: Union[Declaracao, Atribuicao]
    cond: Expr
    passo: Atribuicao
    bloco: Bloco
    linha: int = 0


@dataclass
class Fugir:
    linha: int = 0


Instrucao = Union[Declaracao, Atribuicao, Leitura, Escrita, Se, Enquanto, Para, Fugir]


@dataclass
class Importacao:
    lib: str
    linha: int = 0


@dataclass
class Programa:
    imports: List[Importacao]
    corpo: Bloco
    linha: int = 0


# ------------------------------------------------------------------ impressão
NOMES_OPERADORES = {
    "+": "Soma", "-": "Sub", "*": "Mult", "/": "Div",
    "==": "Igual", "!=": "Diferente", "<": "Menor", "<=": "MenorIgual",
    ">": "Maior", ">=": "MaiorIgual",
}


def expr_str(e):
    """Forma compacta de uma expressão: 2 + 3 * 4 -> 'Soma(2, Mult(3, 4))'."""
    if isinstance(e, Literal):
        return e.valor
    if isinstance(e, Var):
        return e.nome
    if isinstance(e, Unario):
        return f"Neg({expr_str(e.expr)})"
    return f"{NOMES_OPERADORES[e.op]}({expr_str(e.esq)}, {expr_str(e.dir)})"


def _rotulo_e_filhos(no):
    """Texto de uma linha da árvore e a lista de (rótulo do filho, nó filho)."""
    if isinstance(no, Programa):
        return "Programa", [(None, i) for i in no.imports] + [(None, no.corpo)]
    if isinstance(no, Importacao):
        return f"Importacao gato {no.lib}", []
    if isinstance(no, Bloco):
        return "Bloco", [(None, i) for i in no.instrucoes]
    if isinstance(no, Declaracao):
        const = "fossil " if no.const else ""
        return f"Declaracao {const}{no.tipo} {no.nome}", [] if no.expr is None else [(None, no.expr)]
    if isinstance(no, Atribuicao):
        return f"Atribuicao {no.nome}", [(None, no.expr)]
    if isinstance(no, Leitura):
        return f"Leitura capturar({no.nome})", []
    if isinstance(no, Escrita):
        return "Escrita rugir", [(None, no.expr)]
    if isinstance(no, Se):
        filhos = []
        for i, (cond, bloco) in enumerate(no.ramos):
            nome = "se_tem_bicho" if i == 0 else "Se_for_outro_bixo"
            filhos += [(f"{nome} cond", cond), (f"{nome} entao", bloco)]
        if no.senao is not None:
            filhos.append(("nao_tem_bicho", no.senao))
        return "Se", filhos
    if isinstance(no, Enquanto):
        return "Enquanto contar_carneirinho", [("cond", no.cond), ("corpo", no.bloco)]
    if isinstance(no, Para):
        return "Para migrar", [("init", no.init), ("cond", no.cond),
                               ("passo", no.passo), ("corpo", no.bloco)]
    if isinstance(no, Fugir):
        return "Fugir", []
    if isinstance(no, Literal):
        return f"Literal {no.tipo} {no.valor}", []
    if isinstance(no, Var):
        return f"Var {no.nome}", []
    if isinstance(no, Unario):
        return f"Unario {no.op}", [(None, no.expr)]
    if isinstance(no, BinOp):
        return f"{NOMES_OPERADORES[no.op]} {no.op}", [(None, no.esq), (None, no.dir)]
    raise TypeError(f"nó desconhecido: {no!r}")


def formatar_ast(no):
    """Árvore indentada, uma linha por nó (usada pela opção --ast da CLI)."""
    linhas = []

    def visitar(no, prefixo, conector, rotulo_pai):
        rotulo, filhos = _rotulo_e_filhos(no)
        if rotulo_pai:
            rotulo = f"{rotulo_pai}: {rotulo}"
        linhas.append(prefixo + conector + rotulo)
        if conector == "├── ":
            prefixo += "│   "
        elif conector == "└── ":
            prefixo += "    "
        for i, (rot, filho) in enumerate(filhos):
            ultimo = i == len(filhos) - 1
            visitar(filho, prefixo, "└── " if ultimo else "├── ", rot)

    visitar(no, "", "", None)
    return "\n".join(linhas)
