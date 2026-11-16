# references:
# - lolcode spec v1.2: https://github.com/justinmeza/lolcode-spec/blob/master/v1.2/lolcode-spec-v1.2.md
# - semantic analysis and symbol tables: https://www.cs.cornell.edu/courses/cs4120/2023sp/notes/semantic/

from typing import Any
from ast_nodes import *
from errors import SemanticError
from parser import Program

VALID_TYPES = ("NOOB", "NUMBR", "NUMBAR", "YARN", "TROOF") # valid lolcode type names

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

        return self.symbol_table

    def analyze_decl(self, decl: VarDecl, declared_names: set[str]) -> None:
        # reject duplicate variable delcarations
        if decl.name in declared_names:
            raise SemanticError(f"Redefinition of existing variable at: '{decl.name}'", decl.line)

        # analyze initial value expression if present
        if decl.value_expr is not None:
            self.analyze_expr(decl.value_expr, declared_names)

        # record variable name as declared and store in symbol table
        declared_names.add(decl.name)
        self.symbol_table[decl.name] = {"type": "NOOB", "value": "NOOB"}

    def analyze_stmt(self, stmt: Any, declared_names: set[str], *, can_gtfo: bool = False, in_function: bool = False) -> None:
        # placeholder for statement checks, will be supplied in later commit
        pass

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
            expected = self.function_arities[expr.name]              # expected argument count from definition
            actual = len(expr.args)                                  # actual arguments passed in call
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