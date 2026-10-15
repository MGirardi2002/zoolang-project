"""Hierarquia de erros do transpilador ZooLang.

Cada fase do pipeline lança a sua própria exceção, todas derivadas de
ZooLangError, para que a CLI possa exibi-las de forma uniforme e interromper
o processamento no primeiro erro encontrado.
"""


class ZooLangError(Exception):
    """Erro base do transpilador. Guarda a posição (linha/coluna) da ocorrência."""

    categoria = "Erro"

    def __init__(self, mensagem, linha=None, coluna=None):
        self.mensagem = mensagem
        self.linha = linha
        self.coluna = coluna
        super().__init__(str(self))

    def __str__(self):
        if self.linha is None:
            return f"{self.categoria}: {self.mensagem}"
        if self.coluna is None:
            return f"{self.categoria} [linha {self.linha}]: {self.mensagem}"
        return f"{self.categoria} [linha {self.linha}, coluna {self.coluna}]: {self.mensagem}"


class ErroLexico(ZooLangError):
    """Símbolo ou lexema que não pertence a nenhum padrão de token da ZooLang."""

    categoria = "Erro léxico"

    def __init__(self, mensagem, linha, coluna, lexema=None):
        self.lexema = lexema
        super().__init__(mensagem, linha, coluna)


class ErroSintatico(ZooLangError):
    """Sequência de tokens que não pode ser derivada pela gramática da ZooLang."""

    categoria = "Erro sintático"

    def __init__(self, mensagem, linha, coluna, lexema=None):
        self.lexema = lexema
        super().__init__(mensagem, linha, coluna)


class ErroSemantico(ZooLangError):
    """Programa sintaticamente correto que viola uma regra semântica (R1–R11).

    Os nós da AST guardam só a linha, por isso a mensagem não traz coluna.
    """

    categoria = "Erro semântico"

    def __init__(self, mensagem, linha, regra=None):
        self.regra = regra
        super().__init__(mensagem, linha)
