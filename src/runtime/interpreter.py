# references, lolcode spec v1 2, crafting interpreters statements and state

from typing import Any, Callable

from core.ast_nodes import FuncDef
from core.errors import LolRuntimeError
from runtime.environment import Environment
from runtime.evaluator import Evaluator
from runtime.executor import Executor
from frontend.parser import Program
from semantics.lol_types import LolValue


def _default_output(text: str) -> None:
    print(text, end="")


class Interpreter:
    # tree walking runtime coordinator for lolcode programs

    def __init__(
        self,
        program: Program,
        output_fn: Callable[[str], None] | None = None,
        input_fn: Callable[[], str] | None = None,
        on_symbols_updated: Callable[[dict[str, LolValue]], None] | None = None,
    ):
        self.program = program
        self.output_fn = output_fn if output_fn is not None else _default_output
        self.input_fn = input_fn if input_fn is not None else input
        self.on_symbols_updated = on_symbols_updated

        self.global_env = Environment()
        self.functions: dict[str, FuncDef] = {}
        self._call_depth = 0
        self.evaluator = Evaluator(self)
        self.executor = Executor(self)

    def run(self) -> Environment:
        # reset runtime state before execution
        self.global_env = Environment()
        self.functions = {}
        self._call_depth = 0

        # register top level fucntions before executing statments
        for stmt in self.program.body:
            if isinstance(stmt, FuncDef):
                if stmt.name in self.functions:
                    raise LolRuntimeError(f"Function '{stmt.name}' is already defined", stmt.line)
                self.functions[stmt.name] = stmt

        # declare wazzup variables first in global scope
        for decl in self.program.wazzup:
            self.exec_stmt(decl, self.global_env)

        # execute top level body statments
        for stmt in self.program.body:
            self.exec_stmt(stmt, self.global_env)

        self._notify_symbols()
        return self.global_env

    def _notify_symbols(self) -> None:
        if self.on_symbols_updated is not None:
            self.on_symbols_updated(self.global_env.snapshot())

    def exec_block(self, statements: list[Any], env: Environment) -> None:
        # delegate block execution to executor module
        self.executor.execute_block(statements, env)

    def _exec_block(self, statements: list[Any], env: Environment) -> None:
        self.exec_block(statements, env)

    def exec_stmt(self, stmt: Any, env: Environment) -> None:
        # delegate single statment execution to executor module
        self.executor.execute(stmt, env)

    def eval_expr(self, expr: Any, env: Environment) -> LolValue:
        # delegate expression evaluation to evaluator module
        return self.evaluator.eval(expr, env)


def interpret(
    program: Program,
    output_fn: Callable[[str], None] | None = None,
    input_fn: Callable[[], str] | None = None,
    on_symbols_updated: Callable[[dict[str, LolValue]], None] | None = None,
) -> Environment:
    return Interpreter(
        program,
        output_fn=output_fn,
        input_fn=input_fn,
        on_symbols_updated=on_symbols_updated,
    ).run()