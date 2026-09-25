"""Analisador léxico (scanner) da ZooLang.

O scanner é escrito à mão: percorre o código-fonte caractere a caractere e,
a cada posição, decide pelo primeiro caractere qual autômato aplicar. Cada
método _ler_* implementa o autômato de uma expressão regular da tabela de
tokens:

    espaço     [ \\t\\r\\n]+                       (descartado)
    comentário ~[^~]*~                          (descartado)
    id / palavra reservada  [a-zA-Z_][a-zA-Z0-9_]*
    num_int    [0-9]+
    num_real   [0-9]+\\.[0-9]+
    string     "([^"\\\\\\n] | \\\\[nt"\\\\])*"
    operadores == != <= >= + - * / = < >
    delimitadores ( ) { } [ ] , ; :

Sempre é reconhecido o maior lexema possível (longest match): "==" nunca é
lido como dois "=", e "rugir_alto" é um identificador, não "rugir" + "_alto".
O primeiro erro léxico interrompe a análise com ErroLexico.
"""

from .erros import ErroLexico
from .tokens import KEYWORDS, SIMBOLOS_DUPLOS, SIMBOLOS_SIMPLES, Token, TokenType

ESPACOS = " \t\r\n"
DIGITOS = "0123456789"
LETRAS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_"
ESCAPES_VALIDOS = 'nt"\\'
ASPAS_TIPOGRAFICAS = "“”‘’"  # “ ” ‘ ’


class Lexer:
    def __init__(self, fonte):
        self.fonte = fonte
        self.pos = 0
        self.linha = 1
        self.coluna = 1

    # ------------------------------------------------------------------ util
    def _atual(self):
        return self.fonte[self.pos] if self.pos < len(self.fonte) else ""

    def _proximo(self):
        p = self.pos + 1
        return self.fonte[p] if p < len(self.fonte) else ""

    def _avancar(self):
        c = self.fonte[self.pos]
        self.pos += 1
        if c == "\n":
            self.linha += 1
            self.coluna = 1
        else:
            self.coluna += 1
        return c

    # ------------------------------------------------------------- interface
    def tokens(self):
        """Retorna a lista completa de tokens, terminada por EOF."""
        lista = []
        while True:
            tok = self.proximo_token()
            lista.append(tok)
            if tok.tipo is TokenType.EOF:
                return lista

    def proximo_token(self):
        self._pular_espacos_e_comentarios()

        linha, coluna = self.linha, self.coluna
        c = self._atual()

        if c == "":
            return Token(TokenType.EOF, "", linha, coluna)
        if c in LETRAS:
            return self._ler_identificador(linha, coluna)
        if c in DIGITOS:
            return self._ler_numero(linha, coluna)
        if c == '"':
            return self._ler_string(linha, coluna)
        return self._ler_simbolo(linha, coluna)

    # ------------------------------------------- espaços e comentários ~ ~
    def _pular_espacos_e_comentarios(self):
        while True:
            c = self._atual()
            if c != "" and c in ESPACOS:
                self._avancar()
            elif c == "~":
                self._pular_comentario()
            else:
                return

    def _pular_comentario(self):
        linha, coluna = self.linha, self.coluna
        self._avancar()  # ~ de abertura
        while self._atual() != "~":
            if self._atual() == "":
                raise ErroLexico(
                    f"comentário iniciado na linha {linha} não foi fechado com '~'",
                    linha, coluna, "~",
                )
            self._avancar()
        self._avancar()  # ~ de fechamento

    # ------------------------------------ identificadores e palavras-chave
    def _ler_identificador(self, linha, coluna):
        inicio = self.pos
        while self._atual() != "" and (self._atual() in LETRAS or self._atual() in DIGITOS):
            self._avancar()
        lexema = self.fonte[inicio:self.pos]
        tipo = KEYWORDS.get(lexema, TokenType.ID)
        return Token(tipo, lexema, linha, coluna)

    # --------------------------------------------------------------- números
    def _ler_numero(self, linha, coluna):
        inicio = self.pos
        tipo = TokenType.NUM_INT
        self._consumir_digitos()

        if self._atual() == ".":
            self._avancar()
            if self._atual() == "" or self._atual() not in DIGITOS:
                lexema = self.fonte[inicio:self.pos]
                raise ErroLexico(
                    f"número real malformado '{lexema}': esperado dígito após o ponto",
                    linha, coluna, lexema,
                )
            self._consumir_digitos()
            tipo = TokenType.NUM_REAL

        # Um número não pode ser seguido imediatamente por letra ou '_'
        # (ex.: 12abc). Sem esta verificação o lexer produziria NUM_INT + ID.
        if self._atual() != "" and self._atual() in LETRAS:
            while self._atual() != "" and (self._atual() in LETRAS or self._atual() in DIGITOS):
                self._avancar()
            lexema = self.fonte[inicio:self.pos]
            raise ErroLexico(
                f"lexema inválido '{lexema}': identificadores não podem começar com dígito",
                linha, coluna, lexema,
            )

        return Token(tipo, self.fonte[inicio:self.pos], linha, coluna)

    def _consumir_digitos(self):
        while self._atual() != "" and self._atual() in DIGITOS:
            self._avancar()

    # --------------------------------------------------------------- strings
    def _ler_string(self, linha, coluna):
        inicio = self.pos
        self._avancar()  # aspa de abertura
        while True:
            c = self._atual()
            if c == "" or c == "\n":
                raise ErroLexico(
                    "string não foi fechada com '\"' antes do fim da linha",
                    linha, coluna, self.fonte[inicio:self.pos],
                )
            if c == '"':
                self._avancar()
                return Token(TokenType.STRING, self.fonte[inicio:self.pos], linha, coluna)
            if c == "\\":
                l_esc, c_esc = self.linha, self.coluna
                self._avancar()
                esc = self._atual()
                if esc == "" or esc not in ESCAPES_VALIDOS:
                    raise ErroLexico(
                        f"sequência de escape inválida '\\{esc}' (válidas: \\n \\t \\\" \\\\)",
                        l_esc, c_esc, "\\" + esc,
                    )
            self._avancar()

    # ------------------------------------------- operadores e delimitadores
    def _ler_simbolo(self, linha, coluna):
        c = self._atual()
        dois = c + self._proximo()

        if dois in SIMBOLOS_DUPLOS:
            self._avancar()
            self._avancar()
            return Token(SIMBOLOS_DUPLOS[dois], dois, linha, coluna)
        if c in SIMBOLOS_SIMPLES:
            self._avancar()
            return Token(SIMBOLOS_SIMPLES[c], c, linha, coluna)

        if c == "!":
            raise ErroLexico(
                "símbolo '!' isolado não é reconhecido; você quis dizer '!='?",
                linha, coluna, c,
            )
        if c in ASPAS_TIPOGRAFICAS:
            raise ErroLexico(
                f"aspas tipográficas '{c}' não são aceitas; use aspas retas '\"'",
                linha, coluna, c,
            )
        raise ErroLexico(
            f"símbolo '{c}' não pertence ao alfabeto da ZooLang",
            linha, coluna, c,
        )


def tokenizar(fonte):
    """Atalho: retorna a lista de tokens de um texto-fonte."""
    return Lexer(fonte).tokens()
