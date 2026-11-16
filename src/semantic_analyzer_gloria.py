# references:
# - lolcode spec v1.2: https://github.com/justinmeza/lolcode-spec/blob/master/v1.2/lolcode-spec-v1.2.md
# - semantic analysis and symbol tables: https://www.cs.cornell.edu/courses/cs4120/2023sp/notes/semantic/

from typing import Any
from ast_nodes import *
from errors import SemanticError
from parser import Program


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
        # placeholder for expression checks, will be supplied in later commit
        pass


def analyze(program: Program) -> dict[str, dict[str, Any]]:
    # entrypoint helper fucntion for semantic analyzer
    return SemanticAnalyzer(program).analyze()