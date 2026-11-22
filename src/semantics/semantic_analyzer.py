# references:
# - lolcode spec v1.2: https://github.com/justinmeza/lolcode-spec/blob/master/v1.2/lolcode-spec-v1.2.md
# - semantic analysis and symbol tables: https://www.cs.cornell.edu/courses/cs4120/2023sp/notes/semantic/

from typing import Any
from core.ast_nodes import *
from core.debug import log
from core.errors import SemanticError
from frontend.parser import Program
from semantics.lol_types import VALID_TYPES

class SemanticAnalyzer:
    # validates delcarations, variable scope, fucntion arity, and flow control
    def __init__(self, program: Program):
        self.program = program                                       # ast program root node
        self.function_arities: dict[str, int] = {}                   # maps func name to param count
        self.symbol_table: dict[str, dict[str, Any]] = {}            # symbol table for gui display

    def analyze(self) -> dict[str, dict[str, Any]]:
        # reset tables for each analysis run
        self.function_arities.clear()
        self.symbol_table.clear()
        declared_names: set[str] = {"IT"}                            # implicit variable it is always available

        # initalize implicit it in symbol table
        self.symbol_table["IT"] = {"type": "NOOB", "value": "WIN"}

        # pre register function arities and check param names so order of declaration does not matter
        for stmt in self.program.body:
            if isinstance(stmt, FuncDef):
                # reject duplicate function definitions across program
                if stmt.name in self.function_arities:
                    raise SemanticError(f"Function '{stmt.name}' is already declared", stmt.line)

                # check parameter names for duplicates and reserved it keyword
                seen_params: set[str] = set() # track parameter names seen in current fucntion
                for param in stmt.params:
                    # reject reserved implicit variable as parameter name
                    if param == "IT":
                        raise SemanticError("Cannot use reserved implicit variable 'IT' as a parameter", stmt.line)
                    # reject duplicate parameter name in same fucntion
                    if param in seen_params:
                        raise SemanticError(f"Duplicate parameter '{param}' in function '{stmt.name}'", stmt.line)
                    seen_params.add(param)

                # record function arity for call validation
                self.function_arities[stmt.name] = len(stmt.params)

        # analyze global declarations in wazzup section
        for decl in self.program.wazzup:
            self.analyze_decl(decl, declared_names)

        # analyze statements in program body
        for stmt in self.program.body:
            self.analyze_stmt(stmt, declared_names)

        log('SEMANTIC', f'analysis done: {len(self.symbol_table)} symbol(s), {len(self.function_arities)} function(s)')
        return self.symbol_table

    def analyze_decl(self, decl: VarDecl, declared_names: set[str]) -> None:
        # reject duplicate variable delcarations
        if decl.name in declared_names:
            raise SemanticError(f"Redefinition of existing variable at: '{decl.name}'", decl.line)

        # determine initial literal value and type if present
        init_val: Any = "NOOB"                                       # default uninitialized value
        init_type: str = "NOOB"                                      # default uninitialized type
        if isinstance(decl.value_expr, Literal):
            # format boolean troof values as win or fail
            init_val = "WIN" if decl.value_expr.value is True else ("FAIL" if decl.value_expr.value is False else decl.value_expr.value)
            init_type = decl.value_expr.type_name

        # analyze initial value expression if present
        if decl.value_expr is not None:
            self.analyze_expr(decl.value_expr, declared_names)

        # record variable name as declared and store in symbol table
        declared_names.add(decl.name)
        self.symbol_table[decl.name] = {"type": init_type, "value": init_val}

    def analyze_stmt(self, stmt: Any, declared_names: set[str], *, can_gtfo: bool = False, in_function: bool = False) -> None:
        # validate statment execution context, variable scoping, and control flow
        log('SEMANTIC', f'line {getattr(stmt, "line", 0)}: {type(stmt).__name__} (can_gtfo={can_gtfo}, in_function={in_function})')

        if isinstance(stmt, Assignment):
            # verify target variable is declared before assignment
            if stmt.var_name not in declared_names:
                raise SemanticError(f"Variable '{stmt.var_name}' is not declared", stmt.line)
            # analyze value expression
            self.analyze_expr(stmt.expr, declared_names)
            return

        if isinstance(stmt, RecastStmt):
            # verify target variable is declared before recast
            if stmt.var_name not in declared_names:
                raise SemanticError(f"Variable '{stmt.var_name}' is not declared", stmt.line)
            # verify target type is recognized lolcode type
            if stmt.target_type not in VALID_TYPES:
                raise SemanticError(f"Unknown type '{stmt.target_type}'", stmt.line)
            return

        if isinstance(stmt, InputStmt):
            # verify input target variable has been declared
            if stmt.var_name not in declared_names:
                raise SemanticError(f"Variable '{stmt.var_name}' is not declared", stmt.line)
            return

        if isinstance(stmt, PrintStmt):
            # analyze all operands to be printed
            for operand in stmt.operands:
                self.analyze_expr(operand, declared_names)
            return

        if isinstance(stmt, ExprStmt):
            # analyze standalone expression updating implicit it
            self.analyze_expr(stmt.expr, declared_names)
            return

        if isinstance(stmt, IfStmt):
            # analyze optional condition expression
            if stmt.cond_expr is not None:
                self.analyze_expr(stmt.cond_expr, declared_names)
            # analyze then block statments
            for child in stmt.then_body:
                self.analyze_stmt(child, declared_names, can_gtfo=can_gtfo, in_function=in_function)
            # analyze mebbe condition and block statments
            for cond, body in stmt.mebbe_clauses:
                self.analyze_expr(cond, declared_names)
                for child in body:
                    self.analyze_stmt(child, declared_names, can_gtfo=can_gtfo, in_function=in_function)
            # analyze else block statments
            for child in stmt.else_body:
                self.analyze_stmt(child, declared_names, can_gtfo=can_gtfo, in_function=in_function)
            return

        if isinstance(stmt, SwitchStmt):
            # analyze each switch case literal and body
            for case in stmt.cases:
                self.analyze_expr(case.literal, declared_names)
                for child in case.body:
                    self.analyze_stmt(child, declared_names, can_gtfo=True, in_function=in_function)
            # analyze optional default case block
            if stmt.default_case is not None:
                for child in stmt.default_case:
                    self.analyze_stmt(child, declared_names, can_gtfo=True, in_function=in_function)
            return

        if isinstance(stmt, LoopStmt):
            # verify loop counter variable is declared
            if stmt.var_name not in declared_names:
                raise SemanticError(f"Loop variable '{stmt.var_name}' is not declared", stmt.line)
            # analyze optional loop condition expression
            if stmt.condition_expr is not None:
                self.analyze_expr(stmt.condition_expr, declared_names)
            # analyze loop body statments with gtfo allowed
            for child in stmt.body:
                self.analyze_stmt(child, declared_names, can_gtfo=True, in_function=in_function)
            return

        if isinstance(stmt, FuncDef):
            # isolated scope for fucntion body containing parameters and local it
            func_scope: set[str] = {"IT", *stmt.params}              # local fucntion namespace
            for child in stmt.body:
                self.analyze_stmt(child, func_scope, can_gtfo=True, in_function=True)
            return

        if isinstance(stmt, ReturnStmt):
            # found yr is strictly valid only inside fucntions
            if not in_function:
                raise SemanticError("'FOUND YR' can only be used inside a function", stmt.line)
            # analyze return value expression if present
            if stmt.expr is not None:
                self.analyze_expr(stmt.expr, declared_names)
            return

        if isinstance(stmt, BreakStmt):
            # gtfo is valid only inside loops, switch blocks, or fucntions
            if not can_gtfo and not in_function:
                raise SemanticError("'GTFO' can only be used inside a loop, switch-case, or function", stmt.line)
            return

        # reject unhandled statment types
        raise SemanticError(f"Unsupported statement: {type(stmt).__name__}", getattr(stmt, "line", 0))

    def analyze_expr(self, expr: Any, declared_names: set[str]) -> None:
        # validate expression nodes recursively and verify declared names
        if isinstance(expr, Literal):
            # literal values are always valid
            return

        if isinstance(expr, VariableRef):
            # verify variable name has been declared in accessible scope
            if expr.name not in declared_names:
                raise SemanticError(f"Variable '{expr.name}' is not declared", expr.line)
            return

        if isinstance(expr, UnaryOp):
            # analyze inner operand expression
            self.analyze_expr(expr.operand, declared_names)
            return

        if isinstance(expr, BinaryOp):
            # analyze both left and right operand expressions
            self.analyze_expr(expr.left, declared_names)
            self.analyze_expr(expr.right, declared_names)
            return

        if isinstance(expr, (InfiniteBoolExpr, SmooshExpr)):
            # analyze all operand expressions in sequence
            for operand in expr.operands:
                self.analyze_expr(operand, declared_names)
            return

        if isinstance(expr, TypecastExpr):
            # analyze expression and verify target type is recognized
            self.analyze_expr(expr.expr, declared_names)
            if expr.target_type not in VALID_TYPES:
                raise SemanticError(f"Unknown type '{expr.target_type}'", expr.line)
            return

        if isinstance(expr, FuncCall):
            # verify fucntion has been declared
            if expr.name not in self.function_arities:
                raise SemanticError(f"Function '{expr.name}' is not declared", expr.line)

            # verify number of arguments matches fucntion parameter count
            expected = self.function_arities[expr.name] # expected argument count from definition
            actual = len(expr.args)  # actual arguments passed in call
            if actual != expected:
                raise SemanticError(
                    f"Function '{expr.name}' expects {expected} argument(s), got {actual}",
                    expr.line,
                )

            # analyze all argument expressions
            for arg in expr.args:
                self.analyze_expr(arg, declared_names)
            return

        # reject unrecognized expression types
        raise SemanticError(f"Unsupported expression: {type(expr).__name__}", getattr(expr, "line", 0))


def analyze(program: Program) -> dict[str, dict[str, Any]]:
    # entrypoint helper fucntion for semantic analyzer
    return SemanticAnalyzer(program).analyze()