# references:
# - lolcode spec v1.2: https://github.com/justinmeza/lolcode-spec/blob/master/v1.2/lolcode-spec-v1.2.md
# - Semantic Analysis and Symbol Tables: https://www.cs.cornell.edu/courses/cs4120/2023sp/notes/semantic/
from parser import Program
from ast_nodes import *

class SemanticError(Exception):
    def __init__(self, message: str):
        super().__init__(f"{message}")
        self.message = message


def analyze_expr(expr, declared_names: set[str]) -> None:
    if isinstance(expr, Literal):
        return

    if isinstance(expr, VariableRef):
        if expr.name not in declared_names:
            raise SemanticError(f"Variable '{expr.name}' is not declared")
        return

    if isinstance(expr, UnaryOp):
        analyze(expr.operand, declared_names)

    if isinstance(expr, BinaryOp):
        analyze_expr(expr.left, declared_names)
        analyze_expr(expr.right, declared_names)
        return

    raise NotImplementedError(f"Unhandled expression: {type(expr).__name__}")


def analyze(program: Program):
    declared_names: set[str] = set()

    for decl in program.wazzup:
        if decl.name in declared_names:
            raise SemanticError(f"Redefinition of existing variable at: '{decl.name}'")

        if decl.value_expr is not None:
            analyze_expr(decl.value_expr, declared_names)

        declared_names.add(decl.name)

    for stmt in program.body:
        pass
 