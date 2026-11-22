# references, lolcode spec v1 2, crafting interpreters evaluating expressions

from typing import Any
import math

from core.ast_nodes import (
    BinaryOp,
    FuncCall,
    InfiniteBoolExpr,
    Literal,
    SmooshExpr,
    TypecastExpr,
    UnaryOp,
    VariableRef,
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
    to_yarn,
    values_equal,
)

# max depth limit to prevent stack overflow on recursive calls
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


class Evaluator:
    # evaluates expressions, arithmetic, boolean operations, and function calls
    def __init__(self, runtime: Any = None):
        self.runtime = runtime                                       # reference to runtime coordinator

    def eval(self, expr: Any, env: Environment) -> LolValue:
        # evaluate literal constant
        if isinstance(expr, Literal):
            return LolValue(expr.type_name, expr.value)

        # evaluate variable lookup from scope environment
        if isinstance(expr, VariableRef):
            return env.lookup(expr.name, expr.line)

        # evaluate unary not operation on boolean troof
        if isinstance(expr, UnaryOp):
            operand_troof = to_troof(self.eval(expr.operand, env))
            return LolValue("TROOF", not operand_troof.value)

        # evaluate binary operations
        if isinstance(expr, BinaryOp):
            return self._eval_binary(expr, env)

        # evaluate infinite arity boolean operations
        if isinstance(expr, InfiniteBoolExpr):
            return self._eval_infinite_bool(expr, env)

        # evaluate smoosh string concatenation
        if isinstance(expr, SmooshExpr):
            text = self.concat_yarn(expr.operands, env, expr.line)
            return LolValue("YARN", text)

        # evaluate explicit typecasting
        if isinstance(expr, TypecastExpr):
            val = self.eval(expr.expr, env)
            return cast_value(val, expr.target_type, explicit=True, line=expr.line)

        # evaluate fucntion call invocation
        if isinstance(expr, FuncCall):
            return self._eval_func_call(expr, env)

        # reject unrecognized expression nodes
        raise LolRuntimeError(f"Unsupported expression: {type(expr).__name__}", getattr(expr, "line", 0))

    def concat_yarn(self, operands: list[Any], env: Environment, line: int, noob_as_text: bool = False) -> str:
        #noob_as_text=True is used by VISIBLE so a null variable prints as NOOB instead of raising
        parts: list[str] = []
        for operand in operands:
            val = self.eval(operand, env)
            if noob_as_text and val.type_name == "NOOB":
                log('EVAL', f'line {line}: VISIBLE operand is NOOB, printing NOOB')
                parts.append("NOOB")
                continue
            parts.append(to_yarn(val, explicit=False, line=line).value)
        return "".join(parts)

    def _eval_binary(self, expr: BinaryOp, env: Environment) -> LolValue:
        # evaluate boolean binary operations with short circuiting
        if expr.op in BOOLEAN_BINARY_OPS:
            return self._eval_boolean_binary(expr, env)

        # evaluate left and right operands
        left = self.eval(expr.left, env)
        right = self.eval(expr.right, env)

        # evaluate arithmetic math operations
        if expr.op in ARITHMETIC_OPS:
            return self._eval_arithmetic(expr.op, left, right, expr.line)

        # evaluate comparison operations
        if expr.op == "BOTH SAEM":
            return LolValue("TROOF", values_equal(left, right))
        if expr.op == "DIFFRINT":
            return LolValue("TROOF", not values_equal(left, right))

        raise LolRuntimeError(f"Unknown binary operator '{expr.op}'", expr.line)

    def _eval_boolean_binary(self, expr: BinaryOp, env: Environment) -> LolValue:
        left_val = self.eval(expr.left, env)
        left_bool = to_troof(left_val).value

        # short circuit both of when left is false
        if expr.op == "BOTH OF":
            if not left_bool:
                return LolValue("TROOF", False)
            right_bool = to_troof(self.eval(expr.right, env)).value
            return LolValue("TROOF", right_bool)

        # short circuit either of when left is true
        if expr.op == "EITHER OF":
            if left_bool:
                return LolValue("TROOF", True)
            right_bool = to_troof(self.eval(expr.right, env)).value
            return LolValue("TROOF", right_bool)

        # evaluate exclusive or operation
        if expr.op == "WON OF":
            right_bool = to_troof(self.eval(expr.right, env)).value
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

        # calculate arithmetic results
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
                # truncating integer quotient for two integer operands
                res = int(a / b)
        elif op == "MOD OF":
            if b == 0:
                raise LolRuntimeError("Modulo by zero", line)
            if use_float:
                res = a % b
            else:
                # truncating remainder matching integer quoshunt of behavior
                res = a - int(a / b) * b
        elif op == "BIGGR OF":
            res = a if a >= b else b
        elif op == "SMALLR OF":
            res = a if a <= b else b
        else:
            raise LolRuntimeError(f"Unknown arithmetic operator '{op}'", line)

        if use_float:
            return LolValue("NUMBAR", res)
        return LolValue("NUMBR", res)

    def _eval_infinite_bool(self, expr: InfiniteBoolExpr, env: Environment) -> LolValue:
        # evaluate all of with short circuiting on first fail
        if expr.op == "ALL OF":
            for operand in expr.operands:
                if not to_troof(self.eval(operand, env)).value:
                    return LolValue("TROOF", False)
            return LolValue("TROOF", True)

        # evaluate any of with short circuiting on first win
        if expr.op == "ANY OF":
            for operand in expr.operands:
                if to_troof(self.eval(operand, env)).value:
                    return LolValue("TROOF", True)
            return LolValue("TROOF", False)

        raise LolRuntimeError(f"Unknown boolean operator '{expr.op}'", expr.line)

    def _eval_func_call(self, expr: FuncCall, caller_env: Environment) -> LolValue:
        # lookup fucntion definition from runtime registry
        func = self.runtime.functions.get(expr.name) if self.runtime else None
        if func is None:
            raise LolRuntimeError(f"Function '{expr.name}' is not defined", expr.line)

        # verify parameter count matches argument count
        if len(expr.args) != len(func.params):
            raise LolRuntimeError(
                f"Function '{expr.name}' expects {len(func.params)} argument(s), got {len(expr.args)}",
                expr.line,
            )

        # guard against call stack overflow on deep recursion
        if self.runtime._call_depth >= MAX_RECURSION_DEPTH:
            raise LolRuntimeError("Maximum recursion depth exceeded", expr.line)

        # evaluate all argument expressions in caller scope before entering isolated function scope
        arg_values: list[LolValue] = []
        for arg_expr in expr.args:
            arg_values.append(self.eval(arg_expr, caller_env))

        # initalize isolated local environment with parameter bindings
        local_env = Environment(parent=None)
        for param_name, arg_val in zip(func.params, arg_values):
            local_env.declare(param_name, arg_val, expr.line)

        shown = [f'{v.type_name}:{v.value!r}' for v in arg_values]
        log('CALL', f'line {expr.line}: {expr.name}({shown}) depth={self.runtime._call_depth + 1}', self.runtime._call_depth)
        result = NOOB_VAL
        self.runtime._call_depth += 1
        try:
            self.runtime.exec_block(func.body, local_env)
        except _ReturnSignal as ret:
            result = ret.value
        except _BreakSignal:
            result = NOOB_VAL
        finally:
            self.runtime._call_depth -= 1

        log('CALL', f'{expr.name} returned ({result.type_name}) {result.value!r}', self.runtime._call_depth)
        # assign return value to caller accumulator variable
        caller_env.set_it(result)
        return result


def eval_expr(expr: Any, env: Environment, runtime: Any = None) -> LolValue:
    # entrypoint helper fucntion for expression evaluation
    return Evaluator(runtime).eval(expr, env)