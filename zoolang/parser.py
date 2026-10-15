"""Analisador sintático (parser) da ZooLang, por descida recursiva.

Cada não terminal da gramática (seção 5.2 do relatório) é um método
_<nao_terminal>. A gramática é LL(1): a escolha entre alternativas é feita
olhando só o token atual (self.atual), sem retrocesso.

    Programa       ::= { Importacao } "ENTRAR_NA_JAULA" { Instrucao } "SAIR_DA_JAULA"
    Importacao     ::= "gato" id
    Instrucao      ::= Declaracao | Comando
    Declaracao     ::= [ "fossil" ] Tipo id [ "=" Expressao ]
    Tipo           ::= "carneirinho" | "camaleao" | "cobra" | "vagalume"
    Comando        ::= Atribuicao | Leitura | Escrita | Condicional
                     | Enquanto | Para | Interrupcao
    Atribuicao     ::= id "=" Expressao
    Leitura        ::= "capturar" "(" id ")"
    Escrita        ::= "rugir" "(" Expressao ")"
    Condicional    ::= "se_tem_bicho" "(" Expressao ")" Bloco
                       { "Se_for_outro_bixo" "(" Expressao ")" Bloco }
                       [ "nao_tem_bicho" Bloco ]
    Enquanto       ::= "contar_carneirinho" "(" Expressao ")" Bloco
    Para           ::= "migrar" "(" InicioPara ";" Expressao ";" Atribuicao ")" Bloco
    InicioPara     ::= Tipo id "=" Expressao | Atribuicao
    Interrupcao    ::= "fugir"
    Bloco          ::= "{" { Instrucao } "}"
    Expressao      ::= ExprAritmetica [ OpRel ExprAritmetica ]
    OpRel          ::= "==" | "!=" | "<" | "<=" | ">" | ">="
    ExprAritmetica ::= Termo { ( "+" | "-" ) Termo }
    Termo          ::= Fator { ( "*" | "/" ) Fator }
    Fator          ::= num_int | num_real | string | "vivo" | "morto" | id
                     | "(" Expressao ")" | "-" Fator

O primeiro erro interrompe a análise com ErroSintatico, informando a linha,
a coluna, o que era esperado e o lexema encontrado.
"""

from . import ast
from .erros import ErroSintatico
from .lexer import tokenizar
from .tokens import RESERVADAS_FUTURAS, TokenType as T

TIPOS = {
    T.CARNEIRINHO: ast.CARNEIRINHO,
    T.CAMALEAO: ast.CAMALEAO,
    T.COBRA: ast.COBRA,
    T.VAGALUME: ast.VAGALUME,
}

OP_REL = {T.IGUAL, T.DIFERENTE, T.MENOR, T.MENOR_IGUAL, T.MAIOR, T.MAIOR_IGUAL}

# FIRST(Instrucao): tokens que podem iniciar uma instrução (Tabela 8 do relatório).
FIRST_INSTRUCAO = {T.FOSSIL, *TIPOS, T.ID, T.CAPTURAR, T.RUGIR, T.SE_TEM_BICHO,
                   T.CONTAR_CARNEIRINHO, T.MIGRAR, T.FUGIR}


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    # ------------------------------------------------------------------ util
    @property
    def atual(self):
        return self.tokens[self.pos]

    def _avancar(self):
        tok = self.atual
        if tok.tipo is not T.EOF:
            self.pos += 1
        return tok

    def _erro(self, esperado):
        tok = self.atual
        if tok.lexema in RESERVADAS_FUTURAS:
            raise ErroSintatico(
                f"'{tok.lexema}' é recurso reservado, não suportado nesta versão",
                tok.linha, tok.coluna, tok.lexema,
            )
        encontrado = "fim do arquivo" if tok.tipo is T.EOF else f"'{tok.lexema}'"
        raise ErroSintatico(f"esperado {esperado}, encontrado {encontrado}",
                            tok.linha, tok.coluna, tok.lexema)

    def _esperar(self, tipo, descricao=None):
        """Consome um token do tipo indicado ou lança erro sintático."""
        if self.atual.tipo is not tipo:
            self._erro(descricao or f"'{tipo.value}'")
        return self._avancar()

    # --------------------------------------------------------------- programa
    def analisar(self):
        programa = self._programa()
        if self.atual.tipo is not T.EOF:
            self._erro("fim do arquivo após 'SAIR_DA_JAULA'")
        return programa

    def _programa(self):
        imports = []
        while self.atual.tipo is T.GATO:
            imports.append(self._importacao())
        inicio = self._esperar(T.ENTRAR_NA_JAULA, "'ENTRAR_NA_JAULA' (ou 'gato')"
                               if not imports else "'ENTRAR_NA_JAULA'")
        instrucoes = self._lista_instrucoes(T.SAIR_DA_JAULA)
        self._esperar(T.SAIR_DA_JAULA, "instrução ou 'SAIR_DA_JAULA'")
        return ast.Programa(imports, ast.Bloco(instrucoes, inicio.linha), inicio.linha)

    def _importacao(self):
        gato = self._avancar()
        lib = self._esperar(T.ID, "nome de biblioteca após 'gato'")
        return ast.Importacao(lib.lexema, gato.linha)

    def _lista_instrucoes(self, fim):
        """{ Instrucao } até encontrar o token que fecha a lista (} ou SAIR_DA_JAULA)."""
        instrucoes = []
        while self.atual.tipo in FIRST_INSTRUCAO:
            instrucoes.append(self._instrucao())
        if self.atual.tipo is not fim:
            self._erro(f"instrução ou '{fim.value}'")
        return instrucoes

    def _bloco(self):
        abre = self._esperar(T.ABRE_CHAVE, "'{'")
        instrucoes = self._lista_instrucoes(T.FECHA_CHAVE)
        self._esperar(T.FECHA_CHAVE)
        return ast.Bloco(instrucoes, abre.linha)

    # ------------------------------------------------------------- instruções
    def _instrucao(self):
        t = self.atual.tipo
        if t is T.FOSSIL or t in TIPOS:
            return self._declaracao()
        if t is T.ID:
            return self._atribuicao()
        if t is T.CAPTURAR:
            return self._leitura()
        if t is T.RUGIR:
            return self._escrita()
        if t is T.SE_TEM_BICHO:
            return self._condicional()
        if t is T.CONTAR_CARNEIRINHO:
            return self._enquanto()
        if t is T.MIGRAR:
            return self._para()
        if t is T.FUGIR:
            return ast.Fugir(self._avancar().linha)
        self._erro("instrução")

    def _tipo(self):
        if self.atual.tipo not in TIPOS:
            self._erro("tipo (carneirinho, camaleao, cobra ou vagalume)")
        return TIPOS[self._avancar().tipo]

    def _declaracao(self):
        linha = self.atual.linha
        const = False
        if self.atual.tipo is T.FOSSIL:
            self._avancar()
            const = True
        tipo = self._tipo()
        nome = self._esperar(T.ID, "nome da variável").lexema
        expr = None
        if self.atual.tipo is T.ATRIB:
            self._avancar()
            expr = self._expressao()
        return ast.Declaracao(tipo, nome, const, expr, linha)

    def _atribuicao(self):
        nome = self._esperar(T.ID, "nome da variável")
        self._esperar(T.ATRIB, "'=' após o nome da variável")
        return ast.Atribuicao(nome.lexema, self._expressao(), nome.linha)

    def _leitura(self):
        cmd = self._avancar()
        self._esperar(T.ABRE_PAR, "'(' após 'capturar'")
        nome = self._esperar(T.ID, "nome da variável em capturar")
        self._esperar(T.FECHA_PAR)
        return ast.Leitura(nome.lexema, cmd.linha)

    def _escrita(self):
        cmd = self._avancar()
        self._esperar(T.ABRE_PAR, "'(' após 'rugir'")
        expr = self._expressao()
        self._esperar(T.FECHA_PAR)
        return ast.Escrita(expr, cmd.linha)

    def _condicao_entre_parenteses(self, palavra):
        self._esperar(T.ABRE_PAR, f"'(' após '{palavra}'")
        cond = self._expressao()
        self._esperar(T.FECHA_PAR)
        return cond

    def _condicional(self):
        cmd = self._avancar()
        ramos = [(self._condicao_entre_parenteses(cmd.lexema), self._bloco())]
        while self.atual.tipo is T.SE_FOR_OUTRO_BIXO:
            outro = self._avancar()
            ramos.append((self._condicao_entre_parenteses(outro.lexema), self._bloco()))
        senao = None
        if self.atual.tipo is T.NAO_TEM_BICHO:
            self._avancar()
            senao = self._bloco()
        return ast.Se(ramos, senao, cmd.linha)

    def _enquanto(self):
        cmd = self._avancar()
        cond = self._condicao_entre_parenteses(cmd.lexema)
        return ast.Enquanto(cond, self._bloco(), cmd.linha)

    def _para(self):
        cmd = self._avancar()
        self._esperar(T.ABRE_PAR, "'(' após 'migrar'")
        init = self._inicio_para()
        self._esperar(T.PONTO_VIRGULA, "';' no cabeçalho de migrar")
        cond = self._expressao()
        self._esperar(T.PONTO_VIRGULA, "';' no cabeçalho de migrar")
        passo = self._atribuicao()
        self._esperar(T.FECHA_PAR)
        return ast.Para(init, cond, passo, self._bloco(), cmd.linha)

    def _inicio_para(self):
        if self.atual.tipo in TIPOS:
            linha = self.atual.linha
            tipo = self._tipo()
            nome = self._esperar(T.ID, "nome da variável").lexema
            self._esperar(T.ATRIB, "'=' na inicialização de migrar")
            return ast.Declaracao(tipo, nome, False, self._expressao(), linha)
        if self.atual.tipo is T.ID:
            return self._atribuicao()
        self._erro("declaração ou atribuição no início de migrar")

    # ------------------------------------------------------------- expressões
    def _expressao(self):
        esq = self._expr_aritmetica()
        if self.atual.tipo in OP_REL:
            op = self._avancar()
            dir_ = self._expr_aritmetica()
            esq = ast.BinOp(op.lexema, esq, dir_, op.linha)
            if self.atual.tipo in OP_REL:
                tok = self.atual
                raise ErroSintatico(
                    f"operadores relacionais não podem ser encadeados "
                    f"(encontrado '{tok.lexema}' após '{op.lexema}')",
                    tok.linha, tok.coluna, tok.lexema,
                )
        return esq

    def _expr_aritmetica(self):
        esq = self._termo()
        while self.atual.tipo in (T.MAIS, T.MENOS):
            op = self._avancar()
            esq = ast.BinOp(op.lexema, esq, self._termo(), op.linha)
        return esq

    def _termo(self):
        esq = self._fator()
        while self.atual.tipo in (T.VEZES, T.DIVIDIDO):
            op = self._avancar()
            esq = ast.BinOp(op.lexema, esq, self._fator(), op.linha)
        return esq

    def _fator(self):
        tok = self.atual
        t = tok.tipo
        if t is T.NUM_INT:
            return ast.Literal(ast.CARNEIRINHO, self._avancar().lexema, tok.linha)
        if t is T.NUM_REAL:
            return ast.Literal(ast.CAMALEAO, self._avancar().lexema, tok.linha)
        if t is T.STRING:
            return ast.Literal(ast.COBRA, self._avancar().lexema, tok.linha)
        if t in (T.VIVO, T.MORTO):
            return ast.Literal(ast.VAGALUME, self._avancar().lexema, tok.linha)
        if t is T.ID:
            return ast.Var(self._avancar().lexema, tok.linha)
        if t is T.ABRE_PAR:
            self._avancar()
            expr = self._expressao()
            self._esperar(T.FECHA_PAR)
            return expr
        if t is T.MENOS:
            self._avancar()
            return ast.Unario("-", self._fator(), tok.linha)
        self._erro("expressão")


def analisar(fonte):
    """Atalho: texto-fonte -> AST (executa o lexer e o parser)."""
    return Parser(tokenizar(fonte)).analisar()
