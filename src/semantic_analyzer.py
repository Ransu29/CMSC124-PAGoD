# references:
# - lolcode spec v1.2: https://github.com/justinmeza/lolcode-spec/blob/master/v1.2/lolcode-spec-v1.2.md
# - semantic analysis and symbol tables: https://www.cs.cornell.edu/courses/cs4120/2023sp/notes/semantic/

from typing import Any

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
from errors import SemanticError
from lol_types import VALID_TYPES
from parser import Program


class SemanticAnalyzer:
    # validates declarations, variable/function scopes, call arity, and control-flow context

    def __init__(self, program: Program):
        self.program = program
        self.functions: dict[str, FuncDef] = {}

    def analyze(self) -> None:
        # IT is always implicitly available in each scope
        declared_names: set[str] = {"IT"}
        self.functions = {}

        # pre-register top-level function signatures so calls work regardless of definition order
        for stmt in self.program.body:
            if isinstance(stmt, FuncDef):
                self._register_function(stmt)

        # validate WAZZUP global declarations first
        for decl in self.program.wazzup:
            self._declare_variable(decl, declared_names)

        # validate top-level statements and function bodies
        for stmt in self.program.body:
            self.analyze_stmt(
                stmt,
                declared_names,
                in_function=False,
                loop_depth=0,
                switch_depth=0,
            )

    def _register_function(self, func: FuncDef) -> None:
        if func.name in self.functions:
            raise SemanticError(f"Redefinition of existing function '{func.name}'", func.line)

        seen_params: set[str] = set()
        for param in func.params:
            if param == "IT":
                raise SemanticError("Cannot use reserved implicit variable 'IT' as a parameter", func.line)
            if param in seen_params:
                raise SemanticError(f"Duplicate parameter '{param}' in function '{func.name}'", func.line)
            seen_params.add(param)

        self.functions[func.name] = func

    def _declare_variable(self, decl: VarDecl, declared_names: set[str]) -> None:
        if decl.name == "IT":
            raise SemanticError("Cannot declare reserved implicit variable 'IT'", decl.line)
        if decl.name in declared_names:
            raise SemanticError(f"Redefinition of existing variable at: '{decl.name}'", decl.line)

        # validate initializer before registering the new name so self-referential init fails
        if decl.value_expr is not None:
            self.analyze_expr(decl.value_expr, declared_names)

        declared_names.add(decl.name)

    def _require_declared(self, name: str, declared_names: set[str], line: int) -> None:
        if name not in declared_names:
            raise SemanticError(f"Variable '{name}' is not declared", line)

    def _analyze_block(
        self,
        statements: list[Any],
        declared_names: set[str],
        in_function: bool,
        loop_depth: int,
        switch_depth: int,
    ) -> None:
        # copy scope set so declarations inside mutually exclusive branches do not conflict
        block_names = set(declared_names)
        for stmt in statements:
            self.analyze_stmt(stmt, block_names, in_function, loop_depth, switch_depth)

    def _analyze_func_def(self, func: FuncDef) -> None:
        # functions have isolated local scopes: only parameters and local IT are visible
        func_names: set[str] = {"IT"}
        for param in func.params:
            func_names.add(param)

        for inner_stmt in func.body:
            self.analyze_stmt(
                inner_stmt,
                func_names,
                in_function=True,
                loop_depth=0,
                switch_depth=0,
            )

    def analyze_stmt(
        self,
        stmt: Any,
        declared_names: set[str],
        in_function: bool = False,
        loop_depth: int = 0,
        switch_depth: int = 0,
    ) -> None:
        if isinstance(stmt, VarDecl):
            self._declare_variable(stmt, declared_names)
            return

        if isinstance(stmt, Assignment):
            self._require_declared(stmt.var_name, declared_names, stmt.line)
            if stmt.expr is not None:
                self.analyze_expr(stmt.expr, declared_names)
            return

        if isinstance(stmt, RecastStmt):
            self._require_declared(stmt.var_name, declared_names, stmt.line)
            if stmt.target_type not in VALID_TYPES:
                raise SemanticError(f"Unknown type '{stmt.target_type}'", stmt.line)
            return

        if isinstance(stmt, PrintStmt):
            for operand in stmt.operands:
                self.analyze_expr(operand, declared_names)
            return

        if isinstance(stmt, InputStmt):
            self._require_declared(stmt.var_name, declared_names, stmt.line)
            return

        if isinstance(stmt, ExprStmt):
            self.analyze_expr(stmt.expr, declared_names)
            return

        if isinstance(stmt, IfStmt):
            if stmt.cond_expr is not None:
                self.analyze_expr(stmt.cond_expr, declared_names)
            self._analyze_block(stmt.then_body, declared_names, in_function, loop_depth, switch_depth)
            for cond_expr, mebbe_body in stmt.mebbe_clauses:
                self.analyze_expr(cond_expr, declared_names)
                self._analyze_block(mebbe_body, declared_names, in_function, loop_depth, switch_depth)
            self._analyze_block(stmt.else_body, declared_names, in_function, loop_depth, switch_depth)
            return

        if isinstance(stmt, SwitchStmt):
            for case in stmt.cases:
                self.analyze_expr(case.literal, declared_names)
                self._analyze_block(case.body, declared_names, in_function, loop_depth, switch_depth + 1)
            if stmt.default_case is not None:
                self._analyze_block(stmt.default_case, declared_names, in_function, loop_depth, switch_depth + 1)
            return

        if isinstance(stmt, LoopStmt):
            self._require_declared(stmt.var_name, declared_names, stmt.line)
            if stmt.condition_expr is not None:
                self.analyze_expr(stmt.condition_expr, declared_names)
            self._analyze_block(stmt.body, declared_names, in_function, loop_depth + 1, switch_depth)
            return

        if isinstance(stmt, FuncDef):
            self._analyze_func_def(stmt)
            return

        if isinstance(stmt, ReturnStmt):
            if not in_function:
                raise SemanticError("'FOUND YR' can only be used inside a function", stmt.line)
            if stmt.expr is not None:
                self.analyze_expr(stmt.expr, declared_names)
            return

        if isinstance(stmt, BreakStmt):
            if not in_function and loop_depth == 0 and switch_depth == 0:
                raise SemanticError("'GTFO' can only be used inside a loop, switch-case, or function", stmt.line)
            return

        raise SemanticError(f"Unsupported statement: {type(stmt).__name__}", getattr(stmt, "line", 0))

    def analyze_expr(self, expr: Any, declared_names: set[str]) -> None:
        if isinstance(expr, Literal):
            return

        if isinstance(expr, VariableRef):
            self._require_declared(expr.name, declared_names, expr.line)
            return

        if isinstance(expr, UnaryOp):
            self.analyze_expr(expr.operand, declared_names)
            return

        if isinstance(expr, BinaryOp):
            self.analyze_expr(expr.left, declared_names)
            self.analyze_expr(expr.right, declared_names)
            return

        if isinstance(expr, (InfiniteBoolExpr, SmooshExpr)):
            for operand in expr.operands:
                self.analyze_expr(operand, declared_names)
            return

        if isinstance(expr, TypecastExpr):
            self.analyze_expr(expr.expr, declared_names)
            if expr.target_type not in VALID_TYPES:
                raise SemanticError(f"Unknown type '{expr.target_type}'", expr.line)
            return

        if isinstance(expr, FuncCall):
            if expr.name not in self.functions:
                raise SemanticError(f"Function '{expr.name}' is not defined", expr.line)
            expected_count = len(self.functions[expr.name].params)
            actual_count = len(expr.args)
            if actual_count != expected_count:
                raise SemanticError(
                    f"Function '{expr.name}' expects {expected_count} argument(s), got {actual_count}",
                    expr.line,
                )
            for arg in expr.args:
                self.analyze_expr(arg, declared_names)
            return

        raise SemanticError(f"Unhandled expression: {type(expr).__name__}", getattr(expr, "line", 0))
