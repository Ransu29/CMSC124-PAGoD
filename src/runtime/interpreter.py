# references, lolcode spec v1 2, crafting interpreters statements and state

import sys
from typing import Any, Callable

from core.ast_nodes import FuncDef
from core.debug import log
from core.errors import LolRuntimeError
from runtime.environment import Environment
from runtime.evaluator import Evaluator, MAX_RECURSION_DEPTH
from runtime.executor import Executor
from frontend.parser import Program
from semantics.lol_types import LolValue

PY_FRAMES_PER_CALL = 25  #approximate number of Python stack frames used per interpreter call; used to calculate recursion limit


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
        #make sure MAX_RECURSION_DEPTH is reached before Python's own limit
        needed = MAX_RECURSION_DEPTH * PY_FRAMES_PER_CALL + 500
        previous_limit = sys.getrecursionlimit()
        if previous_limit < needed:
            log('RUNTIME', f'raising Python recursion limit {previous_limit} -> {needed}')
            sys.setrecursionlimit(needed)
        try:
            return self._run_program()
        except RecursionError:
            log('RUNTIME', f'Python RecursionError caught at call depth {self._call_depth}')
            raise LolRuntimeError('Stack overflow: recursion or expression nesting is too deep') from None
        finally:
            sys.setrecursionlimit(previous_limit)

    def _run_program(self) -> Environment:
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
                log('RUNTIME', f'registered function {stmt.name} ({len(stmt.params)} param(s))')

        # declare wazzup variables first in global scope
        log('RUNTIME', f'declaring {len(self.program.wazzup)} WAZZUP variable(s)')
        for decl in self.program.wazzup:
            self.exec_stmt(decl, self.global_env)

        # execute top level body statments
        log('RUNTIME', f'executing {len(self.program.body)} top-level statement(s)')
        for stmt in self.program.body:
            self.exec_stmt(stmt, self.global_env)

        self._notify_symbols()
        log('RUNTIME', 'program finished')
        return self.global_env

    def _notify_symbols(self) -> None:
        if self.on_symbols_updated is not None:
            self.on_symbols_updated(self.global_env.snapshot())

    def exec_block(self, statements: list[Any], env: Environment) -> None:
        # delegate block execution to executor module
        self.executor.execute_block(statements, env)

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