# references:
# - lolcode spec v1.2: https://github.com/justinmeza/lolcode-spec/blob/master/v1.2/lolcode-spec-v1.2.md
# - Semantic Analysis and Symbol Tables: https://www.cs.cornell.edu/courses/cs4120/2023sp/notes/semantic/
from parser import Program
from ast_nodes import *

class SemanticError(Exception):
    def __init__(self, message: str):
        super().__init__(f"{message}")
        self.message = message


class SemanticAnalyzer:
    def __init__(self, program: Program):
        self.program = program
        self.function_arities: dict[str, int] = {}     # reject a second declaration of a function with a pre-existing name and check function arity

    def analyze(self):
        self.function_arities.clear()
        declared_names: set[str] = {"IT"}

        for decl in self.program.wazzup:
            self.analyze_decl(decl, declared_names)

        for stmt in self.program.body:
            if isinstance(stmt, FuncDef):
                if stmt.name in self.function_arities:
                    raise SemanticError(f"Function '{stmt.name}' is already declared")
                self.function_arities[stmt.name] = len(stmt.params)
                
            self.analyze_stmt(stmt, declared_names)


    def analyze_decl(self, decl, declared_names: set[str]) -> None:
        if decl.name in declared_names:
            raise SemanticError(f"Redefinition of existing variable at: '{decl.name}'")

        if decl.value_expr is not None:
            self.analyze_expr(decl.value_expr, declared_names)

        declared_names.add(decl.name)


    def analyze_stmt(self, stmt, declared_names: set[str], *, can_gtfo: bool = False) -> None:
        # For debugging
        # print(stmt)

        if isinstance(stmt, Assignment):
            if stmt.var_name not in declared_names:
                raise SemanticError(f"Variable '{stmt.var_name}' is not declared")
            self.analyze_expr(stmt.expr, declared_names)
            return

        if isinstance(stmt, (RecastStmt, InputStmt)):
            if stmt.var_name not in declared_names:
                raise SemanticError(f"Variable '{stmt.var_name}' is not declared")
            return

        if isinstance(stmt, PrintStmt):
            for operand in stmt.operands:
                self.analyze_expr(operand, declared_names)
            return

        if isinstance(stmt, ExprStmt):
            self.analyze_expr(stmt.expr, declared_names)
            return

        if isinstance(stmt, IfStmt):
            if stmt.cond_expr is not None:
                self.analyze_expr(stmt.cond_expr, declared_names)
            for child in stmt.then_body:
                self.analyze_stmt(child, declared_names, can_gtfo=can_gtfo)
            for condition, body in stmt.mebbe_clauses:
                self.analyze_expr(condition, declared_names)
                for child in body:
                    self.analyze_stmt(child, declared_names, can_gtfo=can_gtfo)
            for child in stmt.else_body:
                self.analyze_stmt(child, declared_names, can_gtfo=can_gtfo)
            return

        if isinstance(stmt, CaseClause):
            self.analyze_expr(stmt.literal, declared_names)
            for child in stmt.body:
                self.analyze_stmt(child, declared_names, can_gtfo=can_gtfo)
            return

        if isinstance(stmt, SwitchStmt):
            for case in stmt.cases:
                self.analyze_stmt(case, declared_names, can_gtfo=True)
            if stmt.default_case is not None:
                for def_case in stmt.default_case:
                    self.analyze_stmt(def_case, declared_names, can_gtfo=True)
            return

        if isinstance(stmt, LoopStmt):
            if stmt.condition_expr is not None:
                self.analyze_expr(stmt.condition_expr, declared_names)
            for child in stmt.body:
                self.analyze_stmt(child, declared_names, can_gtfo=True)
            return

        if isinstance(stmt, FuncDef):
            function_names = {"IT", *stmt.params}
            for child in stmt.body:
                self.analyze_stmt(child, function_names, can_gtfo=True)
            return

        if isinstance(stmt, ReturnStmt):
            self.analyze_expr(stmt.expr, declared_names)
            return

        if isinstance(stmt, BreakStmt):
            if not can_gtfo:
                raise SemanticError("GTFO must be inside a loop, switch, or function")
            return
        
        raise NotImplementedError(f"Unhandled statement: {type(stmt).__name__}")


    def analyze_expr(self, expr, declared_names: set[str]) -> None:
        if isinstance(expr, Literal):
            return

        if isinstance(expr, VariableRef):
            if expr.name not in declared_names:
                raise SemanticError(f"Variable '{expr.name}' is not declared")
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

        # evaluator handles type casting to target type is allowed
        if isinstance(expr, TypecastExpr):
            self.analyze_expr(expr.expr, declared_names)
            return

        if isinstance(expr, FuncCall):
            if expr.name not in self.function_arities:
                raise SemanticError(f"Function '{expr.name}' is not declared")

            expected = self.function_arities[expr.name]
            actual = len(expr.args)
            if actual != expected:
                raise SemanticError(
                    f"Function '{expr.name}' expects {expected} argument(s), got {actual}"
                )

            for arg in expr.args:
                self.analyze_expr(arg, declared_names)
            return 
        
        raise NotImplementedError(f"Unhandled expression: {type(expr).__name__}")

def analyze(program: Program) -> None:
    return SemanticAnalyzer(program).analyze()