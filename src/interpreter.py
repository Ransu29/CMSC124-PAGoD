# references:
# - lolcode spec v1.2: https://github.com/justinmeza/lolcode-spec/blob/master/v1.2/lolcode-spec-v1.2.md
# - crafting interpreters evaluating expressions: https://craftinginterpreters.com/evaluating-expressions.html
# - crafting interpreters statements and state: https://craftinginterpreters.com/statements-and-state.html

from typing import Any, Callable

from ast_nodes import (
    Assignment,
    BinaryOp,
    BreakStmt,
    ExprStmt,
    FuncCall,
    FuncDef,
    IfStmt,
    InfiniteBoolExpr,
    InputStmt,
    Literal,
    LoopStmt,
    PrintStmt,
    RecastStmt,
    ReturnStmt,
    SmooshExpr,
    SwitchStmt,
    TypecastExpr,
    UnaryOp,
    VarDecl,
    VariableRef,
)
from errors import LolRuntimeError
from lol_types import (
    NOOB_VAL,
    LolValue,
    cast_value,
    coerce_numeric,
    to_troof,
    to_yarn,
    values_equal,
)
from parser import Program

# keep below python's ~1000 stack limit since each call uses ~5 python frames
MAX_RECURSION_DEPTH = 100

ARITHMETIC_OPS = {
    "SUM OF",
    "DIFF OF",
    "PRODUKT OF",
    "QUOSHUNT OF",
    "MOD OF",
    "BIGGR OF",
    "SMALLR OF",
}

BOOLEAN_BINARY_OPS = {"BOTH OF", "EITHER OF", "WON OF"}


# internal control-flow signals (never exposed outside interpreter)
class _BreakSignal(Exception):
    pass


class _ReturnSignal(Exception):
    def __init__(self, value: LolValue):
        self.value = value


class Environment:
    # symbol table holding variable -> LolValue bindings and implicit IT for one scope

    def __init__(self, parent: "Environment | None" = None):
        self.parent = parent
        self.bindings: dict[str, LolValue] = {"IT": NOOB_VAL}

    def declare(self, name: str, value: LolValue = NOOB_VAL, line: int = 0) -> None:
        if name == "IT":
            raise LolRuntimeError("Cannot declare reserved implicit variable 'IT'", line)
        if name in self.bindings:
            raise LolRuntimeError(f"Variable '{name}' is already declared", line)
        self.bindings[name] = value

    def assign(self, name: str, value: LolValue, line: int = 0) -> None:
        env: Environment | None = self
        while env is not None:
            if name in env.bindings:
                env.bindings[name] = value
                return
            env = env.parent
        raise LolRuntimeError(f"Variable '{name}' is not declared", line)

    def lookup(self, name: str, line: int = 0) -> LolValue:
        env: Environment | None = self
        while env is not None:
            if name in env.bindings:
                return env.bindings[name]
            env = env.parent
        raise LolRuntimeError(f"Variable '{name}' is not declared", line)

    def get_it(self) -> LolValue:
        return self.bindings["IT"]

    def set_it(self, value: LolValue) -> None:
        self.bindings["IT"] = value

    def snapshot(self) -> dict[str, LolValue]:
        # return a copy of current scope bindings for UI/test inspection
        return dict(self.bindings)


def _default_output(text: str) -> None:
    print(text, end="")


class Interpreter:
    # tree-walking AST evaluator for LOLCODE programs

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

    def run(self) -> Environment:
        # reset runtime state so run() is repeatable
        self.global_env = Environment()
        self.functions = {}
        self._call_depth = 0

        # register top-level functions before executing statements
        for stmt in self.program.body:
            if isinstance(stmt, FuncDef):
                if stmt.name in self.functions:
                    raise LolRuntimeError(f"Function '{stmt.name}' is already defined", stmt.line)
                self.functions[stmt.name] = stmt

        # declare WAZZUP variables first in global scope
        for decl in self.program.wazzup:
            self.exec_stmt(decl, self.global_env)

        # execute top-level body statements
        for stmt in self.program.body:
            self.exec_stmt(stmt, self.global_env)

        self._notify_symbols()
        return self.global_env

    def _notify_symbols(self) -> None:
        if self.on_symbols_updated is not None:
            self.on_symbols_updated(self.global_env.snapshot())

    # --- Statement Execution ---

    def _exec_block(self, statements: list[Any], env: Environment) -> None:
        for stmt in statements:
            self.exec_stmt(stmt, env)

    def _concat_operands_as_yarn(self, operands: list[Any], env: Environment, line: int) -> str:
        # evaluate each operand in order and convert to YARN text without implicit NOOB casting
        parts: list[str] = []
        for operand in operands:
            val = self.eval_expr(operand, env)
            yarn_val = to_yarn(val, explicit=False, line=line)
            parts.append(yarn_val.value)
        return "".join(parts)

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
            text = self._concat_operands_as_yarn(stmt.operands, env, stmt.line)
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
            # functions are pre-registered during run() and executed only when called
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
            self._exec_block(stmt.then_body, env)
            return

        for cond_expr, mebbe_body in stmt.mebbe_clauses:
            if to_troof(self.eval_expr(cond_expr, env)).value:
                self._exec_block(mebbe_body, env)
                return

        if stmt.else_body:
            self._exec_block(stmt.else_body, env)

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
                # LOLCODE switch cases fall through until GTFO or OIC
                for case in stmt.cases[match_index:]:
                    self._exec_block(case.body, env)
                if stmt.default_case is not None:
                    self._exec_block(stmt.default_case, env)
            elif stmt.default_case is not None:
                self._exec_block(stmt.default_case, env)
        except _BreakSignal:
            return

    def _exec_loop(self, stmt: LoopStmt, env: Environment) -> None:
        # verify loop variable exists and is numeric before entering the loop
        coerce_numeric(env.lookup(stmt.var_name, stmt.line), stmt.line)
        if stmt.operation == "UPPIN":
            delta = 1
        else:
            delta = -1

        while True:
            if stmt.condition_type == "TIL":
                if to_troof(self.eval_expr(stmt.condition_expr, env)).value:
                    break
            elif stmt.condition_type == "WILE":
                if not to_troof(self.eval_expr(stmt.condition_expr, env)).value:
                    break

            try:
                self._exec_block(stmt.body, env)
            except _BreakSignal:
                break

            current_num = coerce_numeric(env.lookup(stmt.var_name, stmt.line), stmt.line)
            env.assign(stmt.var_name, LolValue(current_num.type_name, current_num.value + delta), stmt.line)
            self._notify_symbols()

    # --- Expression Evaluation ---

    def eval_expr(self, expr: Any, env: Environment) -> LolValue:
        if isinstance(expr, Literal):
            return LolValue(expr.type_name, expr.value)

        if isinstance(expr, VariableRef):
            return env.lookup(expr.name, expr.line)

        if isinstance(expr, UnaryOp):
            operand_troof = to_troof(self.eval_expr(expr.operand, env))
            return LolValue("TROOF", not operand_troof.value)

        if isinstance(expr, BinaryOp):
            return self._eval_binary(expr, env)

        if isinstance(expr, InfiniteBoolExpr):
            return self._eval_infinite_bool(expr, env)

        if isinstance(expr, SmooshExpr):
            text = self._concat_operands_as_yarn(expr.operands, env, expr.line)
            return LolValue("YARN", text)

        if isinstance(expr, TypecastExpr):
            val = self.eval_expr(expr.expr, env)
            return cast_value(val, expr.target_type, explicit=True, line=expr.line)

        if isinstance(expr, FuncCall):
            return self._eval_func_call(expr, env)

        raise LolRuntimeError(f"Unsupported expression: {type(expr).__name__}", getattr(expr, "line", 0))

    def _eval_binary(self, expr: BinaryOp, env: Environment) -> LolValue:
        if expr.op in BOOLEAN_BINARY_OPS:
            return self._eval_boolean_binary(expr, env)

        left = self.eval_expr(expr.left, env)
        right = self.eval_expr(expr.right, env)

        if expr.op in ARITHMETIC_OPS:
            return self._eval_arithmetic(expr.op, left, right, expr.line)

        if expr.op == "BOTH SAEM":
            return LolValue("TROOF", values_equal(left, right))
        if expr.op == "DIFFRINT":
            return LolValue("TROOF", not values_equal(left, right))

        raise LolRuntimeError(f"Unknown binary operator '{expr.op}'", expr.line)

    def _eval_boolean_binary(self, expr: BinaryOp, env: Environment) -> LolValue:
        left_val = self.eval_expr(expr.left, env)
        left_bool = to_troof(left_val).value

        # short-circuit BOTH OF and EITHER OF before evaluating the right operand
        if expr.op == "BOTH OF":
            if not left_bool:
                return LolValue("TROOF", False)
            right_bool = to_troof(self.eval_expr(expr.right, env)).value
            return LolValue("TROOF", right_bool)

        if expr.op == "EITHER OF":
            if left_bool:
                return LolValue("TROOF", True)
            right_bool = to_troof(self.eval_expr(expr.right, env)).value
            return LolValue("TROOF", right_bool)

        if expr.op == "WON OF":
            right_bool = to_troof(self.eval_expr(expr.right, env)).value
            return LolValue("TROOF", left_bool != right_bool)

        raise LolRuntimeError(f"Unknown boolean operator '{expr.op}'", expr.line)

    def _eval_arithmetic(self, op: str, left: LolValue, right: LolValue, line: int) -> LolValue:
        l_num = coerce_numeric(left, line)
        r_num = coerce_numeric(right, line)

        use_float = l_num.type_name == "NUMBAR" or r_num.type_name == "NUMBAR"
        if use_float:
            a = float(l_num.value)
            b = float(r_num.value)
        else:
            a = int(l_num.value)
            b = int(r_num.value)

        if op == "SUM OF":
            res = a + b
        elif op == "DIFF OF":
            res = a - b
        elif op == "PRODUKT OF":
            res = a * b
        elif op == "QUOSHUNT OF":
            if b == 0:
                raise LolRuntimeError("Division by zero", line)
            if use_float:
                res = a / b
            else:
                # two NUMBR operands produce truncating integer quotient
                res = int(a / b)
        elif op == "MOD OF":
            if b == 0:
                raise LolRuntimeError("Modulo by zero", line)
            if use_float:
                res = a % b
            else:
                # truncating remainder matches integer QUOSHUNT OF behavior for negative values
                res = a - int(a / b) * b
        elif op == "BIGGR OF":
            if a >= b:
                res = a
            else:
                res = b
        elif op == "SMALLR OF":
            if a <= b:
                res = a
            else:
                res = b
        else:
            raise LolRuntimeError(f"Unknown arithmetic operator '{op}'", line)

        if use_float:
            return LolValue("NUMBAR", res)
        return LolValue("NUMBR", res)

    def _eval_infinite_bool(self, expr: InfiniteBoolExpr, env: Environment) -> LolValue:
        if expr.op == "ALL OF":
            for operand in expr.operands:
                if not to_troof(self.eval_expr(operand, env)).value:
                    return LolValue("TROOF", False)
            return LolValue("TROOF", True)

        if expr.op == "ANY OF":
            for operand in expr.operands:
                if to_troof(self.eval_expr(operand, env)).value:
                    return LolValue("TROOF", True)
            return LolValue("TROOF", False)

        raise LolRuntimeError(f"Unknown boolean operator '{expr.op}'", expr.line)

    def _eval_func_call(self, expr: FuncCall, caller_env: Environment) -> LolValue:
        func = self.functions.get(expr.name)
        if func is None:
            raise LolRuntimeError(f"Function '{expr.name}' is not defined", expr.line)

        if len(expr.args) != len(func.params):
            raise LolRuntimeError(
                f"Function '{expr.name}' expects {len(func.params)} argument(s), got {len(expr.args)}",
                expr.line,
            )

        if self._call_depth >= MAX_RECURSION_DEPTH:
            raise LolRuntimeError("Maximum recursion depth exceeded", expr.line)

        # evaluate all argument expressions in caller scope before entering isolated function scope
        arg_values: list[LolValue] = []
        for arg_expr in expr.args:
            arg_values.append(self.eval_expr(arg_expr, caller_env))

        local_env = Environment(parent=None)
        for param_name, arg_val in zip(func.params, arg_values):
            local_env.declare(param_name, arg_val, expr.line)

        result = NOOB_VAL
        self._call_depth += 1
        try:
            self._exec_block(func.body, local_env)
        except _ReturnSignal as ret:
            result = ret.value
        except _BreakSignal:
            result = NOOB_VAL
        finally:
            self._call_depth -= 1

        # return values are also stored in caller's implicit IT variable
        caller_env.set_it(result)
        return result


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
