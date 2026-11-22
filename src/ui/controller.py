# decoupled controller connecting the interpreter pipeline to any UI (GUI or CLI)

from typing import Callable

from core.errors import LexicalError, LolRuntimeError, LolcodeError
from core.tokens import T, Token
from frontend import lexer, parser
from runtime.interpreter import Interpreter
from semantics.lol_types import LolValue
from semantics.semantic_analyzer import SemanticAnalyzer


def format_lol_value(lol_val: LolValue) -> str:
    # format a LolValue cleanly for symbol table display
    if lol_val.type_name == "NOOB":
        return "NOOB"
    if lol_val.type_name == "TROOF":
        state = "WIN" if lol_val.value else "FAIL"
        return f"{state} (TROOF)"
    if lol_val.type_name == "YARN":
        return f'"{lol_val.value}" (YARN)'
    return f"{lol_val.value} ({lol_val.type_name})"


def describe_lexical_error(tok: Token) -> str:
    #turns an ERROR token into a message the console can show
    if tok.value[:1] in ('"', "“"):
        return f"Unclosed string literal {tok.value}"
    if tok.value.startswith("OBTW ("):
        return f"Multi-line comment {tok.value}"
    return f"Unexpected or invalid lexeme '{tok.value}'"


class InterpreterController:
    # mediates between core compiler/interpreter modules and presentation callbacks

    def __init__(
        self,
        on_tokens_updated: Callable[[list[Token]], None] | None = None,
        on_symbols_updated: Callable[[dict[str, LolValue]], None] | None = None,
        on_stdout: Callable[[str], None] | None = None,
        request_stdin: Callable[[], str] | None = None,
        on_error: Callable[[LolcodeError], None] | None = None,
    ):
        self._on_tokens_updated_cb = on_tokens_updated
        self._on_symbols_updated_cb = on_symbols_updated
        self._on_stdout_cb = on_stdout
        self._request_stdin_cb = request_stdin
        self._on_error_cb = on_error

    def on_tokens_updated(self, tokens: list[Token]) -> None:
        if self._on_tokens_updated_cb is not None:
            self._on_tokens_updated_cb(tokens)

    def on_symbols_updated(self, symbols: dict[str, LolValue]) -> None:
        if self._on_symbols_updated_cb is not None:
            self._on_symbols_updated_cb(symbols)

    def on_stdout(self, text: str) -> None:
        if self._on_stdout_cb is not None:
            self._on_stdout_cb(text)

    def request_stdin(self) -> str:
        if self._request_stdin_cb is not None:
            return self._request_stdin_cb()
        return ""

    def on_error(self, error: LolcodeError) -> None:
        if self._on_error_cb is not None:
            self._on_error_cb(error)

    def execute(self, code: str) -> bool:
        # run lex -> parse -> semantic analysis -> interpret, reporting errors via on_error
        tokens = lexer.tokenize(code)
        self.on_tokens_updated(tokens)

        lex_errors = [t for t in tokens if t.type == T.ERROR]
        if lex_errors:
            for err in lex_errors:
                self.on_error(LexicalError(describe_lexical_error(err), err.line))
            return False

        try:
            program = parser.parse(tokens)
            SemanticAnalyzer(program).analyze()
            Interpreter(
                program,
                output_fn=self.on_stdout,
                input_fn=self.request_stdin,
                on_symbols_updated=self.on_symbols_updated,
            ).run()
            return True
        except LolcodeError as err:
            self.on_error(err)
            return False
        except RecursionError:
            self.on_error(LolRuntimeError('Stack overflow: nesting or recursion is too deep'))
            return False
        except Exception as exc:  #last-resort net so the GUI never fails silently
            self.on_error(LolRuntimeError(f'Internal error: {type(exc).__name__}: {exc}'))
            return False
