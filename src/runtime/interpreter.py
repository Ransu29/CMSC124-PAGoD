# references, lolcode spec v1 2, crafting interpreters statements and state

from typing import Any, Callable

from core.ast_nodes import (
    Assignment,
    BreakStmt,
    ExprStmt,
    FuncDef,
    IfStmt,
    InputStmt,
    LoopStmt,
    PrintStmt,
    RecastStmt,
    ReturnStmt,
    SwitchStmt,
    VarDecl,
)
from core.errors import LolRuntimeError
from runtime.environment import Environment, _BreakSignal, _ReturnSignal
from runtime.evaluator import Evaluator
from frontend.parser import Program
from semantics.lol_types import (
    NOOB_VAL,
    LolValue,
    cast_value,
    coerce_numeric,
    to_troof,
    values_equal,
)


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
        if output_fn is not None:
            self.output_fn = output_fn
        else:
            self.output_fn = _default_output

        if input_fn is not None:
            self.input_fn = input_fn
        else:
            self.input_fn = input

        self.on_symbols_updated = on_symbols_updated

        self.global_env = Environment()
        self.functions: dict[str, FuncDef] = {}
        self._call_depth = 0
        self.evaluator = Evaluator(self)

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

    # --- Statement Execution ---

    def exec_block(self, statements: list[Any], env: Environment) -> None:
        # execute block of statments sequentially
        for stmt in statements:
            self.exec_stmt(stmt, env)

    def _exec_block(self, statements: list[Any], env: Environment) -> None:
        self.exec_block(statements, env)

    def _concat_operands_as_yarn(self, operands: list[Any], env: Environment, line: int) -> str:
        return self.evaluator.concat_yarn(operands, env, line)

    def exec_stmt(self, stmt: Any, env: Environment) -> None:
        if isinstance(stmt, VarDecl):
            init_val = NOOB_VAL
            if stmt.value_expr is not None:
                init_val = self.eval_expr(stmt.value_expr, env)
            env.declare(stmt.name, init_val, stmt.line)
            self._notify_symbols()
            return

        if isinstance(stmt, Assignment):
            val = self.eval_expr(stmt.expr, env)
            env.assign(stmt.var_name, val, stmt.line)
            self._notify_symbols()
            return

        if isinstance(stmt, RecastStmt):
            current = env.lookup(stmt.var_name, stmt.line)
            casted = cast_value(current, stmt.target_type, explicit=True, line=stmt.line)
            env.assign(stmt.var_name, casted, stmt.line)
            self._notify_symbols()
            return

        if isinstance(stmt, PrintStmt):
            text = self.evaluator.concat_yarn(stmt.operands, env, stmt.line)
            if not stmt.suppress_newline:
                text += "\n"
            self.output_fn(text)
            return

        if isinstance(stmt, InputStmt):
            # verify variable exists before requesting input
            env.lookup(stmt.var_name, stmt.line)
            raw_input = self.input_fn().rstrip("\r\n")
            env.assign(stmt.var_name, LolValue("YARN", raw_input), stmt.line)
            self._notify_symbols()
            return

        if isinstance(stmt, ExprStmt):
            result = self.eval_expr(stmt.expr, env)
            env.set_it(result)
            self._notify_symbols()
            return

        if isinstance(stmt, IfStmt):
            self._exec_if(stmt, env)
            return

        if isinstance(stmt, SwitchStmt):
            self._exec_switch(stmt, env)
            return

        if isinstance(stmt, LoopStmt):
            self._exec_loop(stmt, env)
            return

        if isinstance(stmt, FuncDef):
            # functions are pre registered during run and executed only when called
            return

        if isinstance(stmt, ReturnStmt):
            val = NOOB_VAL
            if stmt.expr is not None:
                val = self.eval_expr(stmt.expr, env)
            raise _ReturnSignal(val)

        if isinstance(stmt, BreakStmt):
            raise _BreakSignal()

        raise LolRuntimeError(f"Unsupported statement: {type(stmt).__name__}", getattr(stmt, "line", 0))

    def _exec_if(self, stmt: IfStmt, env: Environment) -> None:
        if to_troof(env.get_it()).value:
            self.exec_block(stmt.then_body, env)
            return

        for cond_expr, mebbe_body in stmt.mebbe_clauses:
            if to_troof(self.eval_expr(cond_expr, env)).value:
                self.exec_block(mebbe_body, env)
                return

        if stmt.else_body:
            self.exec_block(stmt.else_body, env)

    def _exec_switch(self, stmt: SwitchStmt, env: Environment) -> None:
        target = env.get_it()
        match_index: int | None = None
        for idx, case in enumerate(stmt.cases):
            case_val = LolValue(case.literal.type_name, case.literal.value)
            if values_equal(target, case_val):
                match_index = idx
                break

        try:
            if match_index is not None:
                # lolcode switch cases fall through until gtfo or oic
                for case in stmt.cases[match_index:]:
                    self.exec_block(case.body, env)
                if stmt.default_case is not None:
                    self.exec_block(stmt.default_case, env)
            elif stmt.default_case is not None:
                self.exec_block(stmt.default_case, env)
        except _BreakSignal:
            return

    def _exec_loop(self, stmt: LoopStmt, env: Environment) -> None:
        # verify loop variable exists and is numeric before entering the loop
        coerce_numeric(env.lookup(stmt.var_name, stmt.line), stmt.line)
        delta = 1 if stmt.operation == "UPPIN" else -1

        while True:
            if stmt.condition_type == "TIL":
                if to_troof(self.eval_expr(stmt.condition_expr, env)).value:
                    break
            elif stmt.condition_type == "WILE":
                if not to_troof(self.eval_expr(stmt.condition_expr, env)).value:
                    break

            try:
                self.exec_block(stmt.body, env)
            except _BreakSignal:
                break

            current_num = coerce_numeric(env.lookup(stmt.var_name, stmt.line), stmt.line)
            env.assign(stmt.var_name, LolValue(current_num.type_name, current_num.value + delta), stmt.line)
            self._notify_symbols()

    # --- Expression Evaluation Delegation ---

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