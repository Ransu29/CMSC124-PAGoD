# decoupled controller connecting the interpreter pipeline to any UI (GUI or CLI)

from typing import Callable

import lexer
import parser
from errors import LexicalError, LolcodeError
from interpreter import Interpreter
from lol_types import LolValue
from semantic_analyzer import SemanticAnalyzer
from tokens import T, Token


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
                self.on_error(
                    LexicalError(f"Unexpected or invalid lexeme '{err.value}'", err.line)
                )
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
