# references:
# - lolcode spec v1.2: https://github.com/justinmeza/lolcode-spec/blob/master/v1.2/lolcode-spec-v1.2.md
# - crafting interpreters parsing: https://craftinginterpreters.com/parsing-expressions.html

from dataclasses import dataclass, field
from typing import Any
from tokens import T, Token

try:
    from errors import SyntaxError
except ImportError:
    try:
        from src.errors import SyntaxError
    except ImportError:
        class SyntaxError(Exception):
            def __init__(self, message: str, line: int):
                super().__init__(f"Error on line {line}: {message}")
                self.message = message
                self.line = line

# ast node definitions
@dataclass
class Literal:
    value: Any
    type_name: str

@dataclass
class VariableRef:
    name: str

@dataclass
class VarDecl:
    name: str
    value_expr: Any = None

@dataclass
class Assignment:
    var_name: str
    expr: Any = None

@dataclass
class PrintStmt:
    operands: list[Any] = field(default_factory=list)
    suppress_newline: bool = False

@dataclass
class Program:
    body: list[Any] = field(default_factory=list)
    wazzup: list[Any] = field(default_factory=list)
    functions: list[Any] = field(default_factory=list)

    def to_tuples(self) -> list[tuple]:
        # helper to convert ast to tuple list format
        res = [('START', 'HAI')]
        for stmt in self.body:
            if isinstance(stmt, VarDecl):
                val = stmt.value_expr.value if isinstance(stmt.value_expr, Literal) else stmt.value_expr
                res.append(('DECLARATION', stmt.name, val))
            elif isinstance(stmt, Assignment):
                val = stmt.expr.value if isinstance(stmt.expr, Literal) else stmt.expr
                res.append(('ASSIGNMENT', stmt.var_name, val))
            elif isinstance(stmt, PrintStmt):
                op_strs = []
                for op in stmt.operands:
                    if isinstance(op, Literal) and op.type_name == "YARN":
                        op_strs.append(f'"{op.value}"')
                    elif isinstance(op, VariableRef):
                        op_strs.append(op.name)
                    elif isinstance(op, Literal):
                        op_strs.append(str(op.value))
                    else:
                        op_strs.append(str(op))
                res.append(('PRINT', " + ".join(op_strs)))
        res.append(('END', 'KTHXBYE'))
        return res

class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.current = 0

    def peek(self) -> Token:
        if self.current < len(self.tokens):
            return self.tokens[self.current]
        return self.tokens[-1]

    def skip_newlines(self) -> None:
        # advance past newlines and soft linebreaks
        while self.peek().type in (T.NEWLINE, T.COMMA):
            self.current += 1

    def check(self, token_type: T) -> bool:
        return self.peek().type == token_type

    def match(self, token_type: T) -> bool:
        if self.check(token_type):
            self.current += 1
            return True
        return False

    def consume(self, token_type: T, error_message: str) -> Token:
        tok = self.peek()
        if tok.type != token_type:
            raise SyntaxError(f"{error_message} (got '{tok.value}')", tok.line)
        self.current += 1
        return tok

    def parse_primary(self) -> Any:
        tok = self.peek()
        if self.match(T.NUMBR_LIT):
            return Literal(int(tok.value), "NUMBR")
        if self.match(T.NUMBAR_LIT):
            return Literal(float(tok.value), "NUMBAR")
        if self.match(T.WIN):
            return Literal(True, "TROOF")
        if self.match(T.FAIL):
            return Literal(False, "TROOF")
        if self.match(T.STRING_DELIMITER):
            yarn_tok = self.consume(T.YARN_LIT, "Expected string content")
            self.consume(T.STRING_DELIMITER, "Expected closing quote")
            return Literal(yarn_tok.value, "YARN")
        if self.match(T.YARN_LIT):
            return Literal(tok.value, "YARN")
        if self.match(T.IDENTIFIER):
            return VariableRef(tok.value)
        raise SyntaxError(f"Unexpected token in expression: '{tok.value}'", tok.line)

    def parse_expression(self) -> Any:
        # shortcut: prefix operators deferred, full expression parser in priority 2
        return self.parse_primary()

    def parse_declaration(self) -> VarDecl:
        self.consume(T.I_HAS_A, "Expected 'I HAS A'")
        name_tok = self.consume(T.IDENTIFIER, "Expected variable name")
        init_val = None
        if self.match(T.ITZ):
            init_val = self.parse_expression()
        return VarDecl(name_tok.value, init_val)

    def parse_assignment(self) -> Assignment:
        var_tok = self.consume(T.IDENTIFIER, "Expected variable name")
        self.consume(T.R, "Expected 'R'")
        expr = self.parse_expression()
        return Assignment(var_tok.value, expr)

    def parse_print(self) -> PrintStmt:
        self.consume(T.VISIBLE, "Expected 'VISIBLE'")
        operands = [self.parse_expression()]
        while self.peek().type not in (T.NEWLINE, T.COMMA, T.BANG, T.EOF):
            if self.match(T.PLUS):
                continue
            operands.append(self.parse_expression())
        suppress = self.match(T.BANG)
        return PrintStmt(operands, suppress_newline=suppress)

    def parse_statement(self) -> Any:
        # shortcut: wazzup block and control flow deferred, full statements in priority 2-3
        if self.check(T.I_HAS_A):
            return self.parse_declaration()
        if self.check(T.VISIBLE):
            return self.parse_print()
        if self.check(T.IDENTIFIER):
            if self.current + 1 < len(self.tokens) and self.tokens[self.current + 1].type == T.R:
                return self.parse_assignment()
        tok = self.peek()
        raise SyntaxError(f"Invalid statement starting with '{tok.value}'", tok.line)

    def parse(self) -> Program:
        self.skip_newlines()
        self.consume(T.HAI, "Program must start with 'HAI'")
        if self.peek().type in (T.NUMBAR_LIT, T.NUMBR_LIT, T.YARN_LIT):
            self.current += 1
        self.skip_newlines()

        body = []
        while not self.check(T.KTHXBYE) and not self.check(T.EOF):
            stmt = self.parse_statement()
            body.append(stmt)
            self.skip_newlines()

        self.consume(T.KTHXBYE, "Program must end with 'KTHXBYE'")
        return Program(body=body)

def parse(tokens: list[Token]) -> Program:
    return Parser(tokens).parse()
