# references:
# - lolcode spec v1.2: https://github.com/justinmeza/lolcode-spec/blob/master/v1.2/lolcode-spec-v1.2.md
# - Semantic Analysis and Symbol Tables: https://www.cs.cornell.edu/courses/cs4120/2023sp/notes/semantic/
from parser import Program
from ast_nodes import *
from errors import SemanticError


class SemanticAnalyzer:
    def __init__(self, program: Program):
        self.program = program

    def analyze(self):
        declared_names: set[str] = set()

        for decl in self.program.wazzup:
            if decl.name in declared_names:
                raise SemanticError(f"Redefinition of existing variable at: '{decl.name}'", decl.line)

            if decl.value_expr is not None:
                self.analyze_expr(decl.value_expr, declared_names)

            declared_names.add(decl.name)

        for stmt in self.program.body:
            pass

    def analyze_expr(self, expr, declared_names: set[str]) -> None:
        if isinstance(expr, Literal):
            return

        if isinstance(expr, VariableRef):
            if expr.name not in declared_names:
                raise SemanticError(f"Variable '{expr.name}' is not declared", expr.line)
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

        raise NotImplementedError(f"Unhandled expression: {type(expr).__name__}")
 