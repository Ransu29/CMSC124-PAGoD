# references, lolcode spec v1 2, crafting interpreters statements and state

from typing import Any

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
from core.debug import log
from core.errors import LolRuntimeError
from runtime.environment import Environment, _BreakSignal, _ReturnSignal
from semantics.lol_types import (
    NOOB_VAL,
    LolValue,
    cast_value,
    coerce_numeric,
    to_troof,
    values_equal,
)


class Executor:
    # executes statments, declarations, control flow branches, loops, and io
    def __init__(self, runtime: Any):
        self.runtime = runtime                                       # reference to runtime coordinator
        self._depth = 0                                              # block depth, only used to indent logs

    def execute_block(self, statements: list[Any], env: Environment) -> None:
        # execute block of statments sequentially
        self._depth += 1
        log('EXEC', f'enter block ({len(statements)} stmt)', self._depth)
        try:
            for stmt in statements:
                self.execute(stmt, env)
        finally:
            log('EXEC', 'exit block', self._depth)
            self._depth -= 1

    def execute(self, stmt: Any, env: Environment) -> None:
        log('EXEC', f'line {getattr(stmt, "line", 0)}: {type(stmt).__name__}', self._depth)
        # execute variable delcaration with optional initial value
        if isinstance(stmt, VarDecl):
            init_val = NOOB_VAL
            if stmt.value_expr is not None:
                init_val = self.runtime.eval_expr(stmt.value_expr, env)
            env.declare(stmt.name, init_val, stmt.line)
            self.runtime._notify_symbols()
            return

        # execute variable assignment statment
        if isinstance(stmt, Assignment):
            val = self.runtime.eval_expr(stmt.expr, env)
            env.assign(stmt.var_name, val, stmt.line)
            self.runtime._notify_symbols()
            return

        # execute variable type recast statment
        if isinstance(stmt, RecastStmt):
            current = env.lookup(stmt.var_name, stmt.line)
            casted = cast_value(current, stmt.target_type, explicit=True, line=stmt.line)
            env.assign(stmt.var_name, casted, stmt.line)
            self.runtime._notify_symbols()
            return

        # execute print statment with optional newline
        if isinstance(stmt, PrintStmt):
            text = self.runtime.evaluator.concat_yarn(stmt.operands, env, stmt.line)
            if not stmt.suppress_newline:
                text += "\n"
            self.runtime.output_fn(text)
            return

        # execute input statment after verifying variable exists
        if isinstance(stmt, InputStmt):
            env.lookup(stmt.var_name, stmt.line)
            raw_input = self.runtime.input_fn().rstrip("\r\n")
            env.assign(stmt.var_name, LolValue("YARN", raw_input), stmt.line)
            self.runtime._notify_symbols()
            return

        # execute expression statment and update accumulator variable
        if isinstance(stmt, ExprStmt):
            result = self.runtime.eval_expr(stmt.expr, env)
            env.set_it(result)
            self.runtime._notify_symbols()
            return

        # execute conditional if branching
        if isinstance(stmt, IfStmt):
            self._exec_if(stmt, env)
            return

        # execute switch case selection with fallthrough
        if isinstance(stmt, SwitchStmt):
            self._exec_switch(stmt, env)
            return

        # execute loop iteration with counter step
        if isinstance(stmt, LoopStmt):
            self._exec_loop(stmt, env)
            return

        # fucntions are pre registered during setup and called explicitly
        if isinstance(stmt, FuncDef):
            return

        # signal return from fucntion call
        if isinstance(stmt, ReturnStmt):
            val = NOOB_VAL
            if stmt.expr is not None:
                val = self.runtime.eval_expr(stmt.expr, env)
            raise _ReturnSignal(val)

        # signal loop break or switch termination
        if isinstance(stmt, BreakStmt):
            raise _BreakSignal()

        # reject unsupported statment node
        raise LolRuntimeError(f"Unsupported statement: {type(stmt).__name__}", getattr(stmt, "line", 0))

    def _exec_if(self, stmt: IfStmt, env: Environment) -> None:
        it_val = env.get_it()
        truthy = to_troof(it_val).value
        log('IF', f'line {stmt.line}: IT=({it_val.type_name}) {it_val.value!r} -> {truthy}', self._depth)
        if truthy:
            log('IF', 'taking YA RLY', self._depth)
            self.execute_block(stmt.then_body, env)
            return

        for number, (cond_expr, mebbe_body) in enumerate(stmt.mebbe_clauses, start=1):
            cond = to_troof(self.runtime.eval_expr(cond_expr, env)).value
            log('IF', f'MEBBE #{number} -> {cond}', self._depth)
            if cond:
                self.execute_block(mebbe_body, env)
                return

        if stmt.else_body:
            log('IF', 'taking NO WAI', self._depth)
            self.execute_block(stmt.else_body, env)
        else:
            log('IF', 'no branch taken', self._depth)

    def _exec_switch(self, stmt: SwitchStmt, env: Environment) -> None:
        target = env.get_it()
        match_index: int | None = None
        for idx, case in enumerate(stmt.cases):
            case_val = LolValue(case.literal.type_name, case.literal.value)
            if values_equal(target, case_val):
                match_index = idx
                break

        if match_index is not None:
            outcome = f'matched OMG #{match_index + 1}'
        else:
            outcome = 'no match, using OMGWTF' if stmt.default_case is not None else 'no match and no OMGWTF'
        log('SWITCH', f'line {stmt.line}: IT={target.value!r} -> {outcome}', self._depth)

        try:
            if match_index is not None:
                # lolcode switch cases fall through until gtfo or oic
                for case in stmt.cases[match_index:]:
                    self.execute_block(case.body, env)
                if stmt.default_case is not None:
                    self.execute_block(stmt.default_case, env)
            elif stmt.default_case is not None:
                self.execute_block(stmt.default_case, env)
        except _BreakSignal:
            log('SWITCH', 'GTFO leaves the switch', self._depth)
            return

    def _exec_loop(self, stmt: LoopStmt, env: Environment) -> None:
        # verify loop counter exists and coerce numeric before loop entry
        coerce_numeric(env.lookup(stmt.var_name, stmt.line), stmt.line)
        delta = 1 if stmt.operation == "UPPIN" else -1

        while True:
            if stmt.condition_type == "TIL":
                if to_troof(self.runtime.eval_expr(stmt.condition_expr, env)).value:
                    break
            elif stmt.condition_type == "WILE":
                if not to_troof(self.runtime.eval_expr(stmt.condition_expr, env)).value:
                    break

            try:
                self.execute_block(stmt.body, env)
            except _BreakSignal:
                break

            current_num = coerce_numeric(env.lookup(stmt.var_name, stmt.line), stmt.line)
            env.assign(stmt.var_name, LolValue(current_num.type_name, current_num.value + delta), stmt.line)
            self.runtime._notify_symbols()


def execute_stmt(stmt: Any, env: Environment, runtime: Any) -> None:
    # entrypoint helper fucntion for statment execution
    Executor(runtime).execute(stmt, env)