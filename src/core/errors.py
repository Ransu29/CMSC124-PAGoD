# exception hierarchy for lexical, syntactic, semantic, and runtime errors


class LolcodeError(Exception):
    # base exception for all LOLCODE interpreter phases

    def __init__(self, message: str, line: int = 0):
        formatted = f"Error on line {line}: {message}" if line > 0 else message
        super().__init__(formatted)
        self.message = message
        self.line = line


class LexicalError(LolcodeError):
    # raised when an invalid lexeme or malformed token is encountered
    pass


class SyntaxError(LolcodeError):
    # raised when the token stream violates the LOLCODE grammar
    pass


class SemanticError(LolcodeError):
    # raised when a semantically invalid construct is detected before execution
    pass


class LolRuntimeError(LolcodeError):
    # raised when an error occurs during LOLCODE program evaluation
    pass
