# references:
# - lolcode spec v1.2: https://github.com/justinmeza/lolcode-spec/blob/master/v1.2/lolcode-spec-v1.2.md
# - crafting interpreters ast: https://craftinginterpreters.com/representing-code.html
# - crafting interpreters parsing: https://craftinginterpreters.com/parsing-expressions.html
# - prefix notation (polish notation): https://en.wikipedia.org/wiki/Polish_notation
# - recursive descent parsing: https://en.wikipedia.org/wiki/Recursive_descent_parser
# - python dataclasses: https://docs.python.org/3/library/dataclasses.html

from dataclasses import dataclass, field
from typing import Any
from tokens import T, Token

class SyntaxError(Exception):
    def __init__(self, message: str, line: int):
        super().__init__(f"Error on line {line}: {message}")
        self.message = message
        self.line = line

# ast node definitions

# expressions
@dataclass
class Literal:
    value: Any
    type_name: str

@dataclass
class VariableRef:
    name: str

@dataclass
class BinaryOp:
    op: str
    left: Any
    right: Any

@dataclass
class UnaryOp:
    op: str
    operand: Any

@dataclass
class InfiniteBoolExpr:
    op: str
    operands: list[Any] = field(default_factory=list)

@dataclass
class SmooshExpr:
    operands: list[Any] = field(default_factory=list)

SmoothExpr = SmooshExpr  # alias for spec naming compatibility

@dataclass
class TypecastExpr:
    expr: Any
    target_type: str

@dataclass
class FuncCall:
    name: str
    args: list[Any] = field(default_factory=list)


# statements
@dataclass
class VarDecl:
    name: str
    value_expr: Any = None

@dataclass
class Assignment:
    var_name: str
    expr: Any = None

@dataclass
class RecastStmt:
    var_name: str
    target_type: str

@dataclass
class PrintStmt:
    operands: list[Any] = field(default_factory=list)
    suppress_newline: bool = False

@dataclass
class InputStmt:
    var_name: str

@dataclass
class ExprStmt:
    expr: Any

@dataclass
class IfStmt:
    cond_expr: Any = None
    then_body: list[Any] = field(default_factory=list)
    mebbe_clauses: list[tuple[Any, list[Any]]] = field(default_factory=list)
    else_body: list[Any] = field(default_factory=list)

@dataclass
class CaseClause:
    literal: Literal
    body: list[Any] = field(default_factory=list)

@dataclass
class SwitchStmt:
    cases: list[CaseClause] = field(default_factory=list)
    default_case: list[Any] | None = None

@dataclass
class LoopStmt:
    label: str
    operation: str
    var_name: str
    condition_type: str | None = None
    condition_expr: Any = None
    body: list[Any] = field(default_factory=list)

@dataclass
class FuncDef:
    name: str
    params: list[str] = field(default_factory=list)
    body: list[Any] = field(default_factory=list)

@dataclass
class ReturnStmt:
    expr: Any = None

@dataclass
class BreakStmt:
    pass

@dataclass
class Program:
    body: list[Any] = field(default_factory=list)
    wazzup: list[Any] = field(default_factory=list)
    functions: list[Any] = field(default_factory=list)

    def to_tuples(self) -> list[tuple]:
        # helper to convert ast to tuple list format
        res = [('START', 'HAI')]
        if self.wazzup:
            res.append(('SECTION', 'WAZZUP'))
            for decl in self.wazzup:
                val = decl.value_expr.value if isinstance(decl.value_expr, Literal) else decl.value_expr
                res.append(('DECLARATION', decl.name, val))
            res.append(('SECTION', 'BUHBYE'))
        for stmt in self.body:
            if isinstance(stmt, VarDecl):
                val = stmt.value_expr.value if isinstance(stmt.value_expr, Literal) else stmt.value_expr
                res.append(('DECLARATION', stmt.name, val))
            elif isinstance(stmt, Assignment):
                val = stmt.expr.value if isinstance(stmt.expr, Literal) else stmt.expr
                res.append(('ASSIGNMENT', stmt.var_name, val))
            elif isinstance(stmt, RecastStmt):
                res.append(('RECAST', stmt.var_name, stmt.target_type))
            elif isinstance(stmt, InputStmt):
                res.append(('INPUT', stmt.var_name))
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
            elif isinstance(stmt, ExprStmt):
                res.append(('EXPR_STMT', str(stmt.expr)))
            elif isinstance(stmt, IfStmt):
                res.append(('IF', 'O RLY?'))
            elif isinstance(stmt, SwitchStmt):
                res.append(('SWITCH', 'WTF?'))
            elif isinstance(stmt, LoopStmt):
                res.append(('LOOP', stmt.label))
            elif isinstance(stmt, FuncDef):
                res.append(('FUNC_DEF', stmt.name))
            elif isinstance(stmt, ReturnStmt):
                res.append(('RETURN', str(stmt.expr)))
            elif isinstance(stmt, BreakStmt):
                res.append(('BREAK', 'GTFO'))
        res.append(('END', 'KTHXBYE'))
        return res

BINARY_OPERATORS = {
    # arithmetic
    T.ADD,
    T.SUB,
    T.MUL,
    T.DIV,
    T.MOD,
    T.MAX,
    T.MIN,
    # boolean
    T.AND,
    T.OR,
    T.XOR,
    # comparison
    T.EQUAL,
    T.NOT_EQUAL,
}

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
        if self.match(T.TYPE):
            return Literal(tok.value, "TYPE")
        if self.match(T.IDENTIFIER):
            return VariableRef(tok.value)
        raise SyntaxError(f"Unexpected token in expression: '{tok.value}'", tok.line)

    def parse_infinite_bool(self, op: str) -> InfiniteBoolExpr:
        operands = [self.parse_expression()]
        while self.match(T.AN):
            operands.append(self.parse_expression())
        self.consume(T.MKAY, f"Expected 'MKAY' to close '{op}' expression")
        return InfiniteBoolExpr(op, operands)

    def parse_smoosh(self) -> SmooshExpr:
        operands = [self.parse_expression()]
        while self.match(T.AN):
            operands.append(self.parse_expression())
        if self.check(T.MKAY):
            self.match(T.MKAY)
        return SmooshExpr(operands)

    def parse_func_call(self) -> FuncCall:
        name_tok = self.consume(T.IDENTIFIER, "Expected function name after 'I IZ'")
        args = []
        if self.match(T.YR):
            args.append(self.parse_expression())
            while self.match(T.AN):
                self.match(T.YR)
                args.append(self.parse_expression())
        self.consume(T.MKAY, "Expected 'MKAY' to close function call")
        return FuncCall(name_tok.value, args)

    def parse_expression(self) -> Any:
        tok = self.peek()

        # binary operators: arithmetic, boolean binary, comparison
        if tok.type in BINARY_OPERATORS:
            self.current += 1
            op = tok.value
            left = self.parse_expression()
            self.consume(T.AN, f"Expected 'AN' separating operands for '{op}'")
            right = self.parse_expression()
            return BinaryOp(op, left, right)

        # unary operator: NOT
        if self.match(T.NOT):
            operand = self.parse_expression()
            return UnaryOp("NOT", operand)

        # infinite arity boolean: ALL OF, ANY OF
        if self.match(T.ALL):
            return self.parse_infinite_bool("ALL OF")
        if self.match(T.ANY):
            return self.parse_infinite_bool("ANY OF")

        # concatenation: SMOOSH
        if self.match(T.SMOOSH):
            return self.parse_smoosh()

        # typecasting: MAEK <expr> [A] <type>
        if self.match(T.MAEK):
            expr = self.parse_expression()
            self.match(T.A)  # optional 'A' delimiter
            type_tok = self.consume(T.TYPE, "Expected type name after 'MAEK' (NUMBR, NUMBAR, YARN, TROOF, NOOB)")
            return TypecastExpr(expr, type_tok.value)

        # function call: I IZ <name> [YR <arg1> [AN YR <arg2>...]] MKAY
        if self.match(T.FUNCTION_CALL):
            return self.parse_func_call()

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

    def parse_input(self) -> InputStmt:
        self.consume(T.GIMMEH, "Expected 'GIMMEH'")
        var_tok = self.consume(T.IDENTIFIER, "Expected variable name after 'GIMMEH'")
        return InputStmt(var_tok.value)

    def parse_recast(self) -> RecastStmt:
        var_tok = self.consume(T.IDENTIFIER, "Expected variable name")
        self.consume(T.IS_NOW_A, "Expected 'IS NOW A'")
        type_tok = self.consume(T.TYPE, "Expected type name after 'IS NOW A' (NUMBR, NUMBAR, YARN, TROOF, NOOB)")
        return RecastStmt(var_tok.value, type_tok.value)

    def parse_statement_block(self, stop_tokens: tuple[T, ...]) -> list[Any]:
        body = []
        self.skip_newlines()
        while (
            self.peek().type not in stop_tokens
            and self.peek().type not in (T.KTHXBYE, T.EOF)
        ):
            stmt = self.parse_statement()
            body.append(stmt)
            self.skip_newlines()
        return body

    def parse_conditional(self) -> IfStmt:
        self.consume(T.IF, "Expected 'O RLY?'")
        self.skip_newlines()
        self.consume(T.THEN, "Expected 'YA RLY' after 'O RLY?'")
        then_body = self.parse_statement_block((T.ELIF, T.ELSE, T.ENDIF))

        mebbe_clauses = []
        while self.match(T.ELIF):
            cond_expr = self.parse_expression()
            mebbe_body = self.parse_statement_block((T.ELIF, T.ELSE, T.ENDIF))
            mebbe_clauses.append((cond_expr, mebbe_body))

        else_body = []
        if self.match(T.ELSE):
            else_body = self.parse_statement_block((T.ENDIF,))

        self.consume(T.ENDIF, "Expected 'OIC' to close conditional block")
        return IfStmt(then_body=then_body, mebbe_clauses=mebbe_clauses, else_body=else_body)

    def parse_switch(self) -> SwitchStmt:
        self.consume(T.SWITCH, "Expected 'WTF?'")
        self.skip_newlines()

        cases = []
        while self.match(T.CASE):
            case_lit = self.parse_primary()
            if not isinstance(case_lit, Literal):
                raise SyntaxError(f"Expected literal value for case, got '{case_lit}'", self.peek().line)
            case_body = self.parse_statement_block((T.CASE, T.DEFAULT, T.ENDIF))
            cases.append(CaseClause(case_lit, case_body))

        default_case = None
        if self.match(T.DEFAULT):
            default_case = self.parse_statement_block((T.ENDIF,))

        self.consume(T.ENDIF, "Expected 'OIC' to close switch block")
        return SwitchStmt(cases=cases, default_case=default_case)

    def parse_loop(self) -> LoopStmt:
        self.consume(T.LOOP_START, "Expected 'IM IN YR'")
        start_label = self.consume(T.IDENTIFIER, "Expected loop label after 'IM IN YR'").value

        op_tok = self.peek()
        if op_tok.type not in (T.INC, T.DEC):
            raise SyntaxError(f"Expected 'UPPIN' or 'NERFIN' in loop header, got '{op_tok.value}'", op_tok.line)
        self.current += 1
        operation = op_tok.value

        self.consume(T.YR, "Expected 'YR' before loop variable")
        var_name = self.consume(T.IDENTIFIER, "Expected loop variable name").value

        cond_type = None
        cond_expr = None
        if self.match(T.UNTIL):
            cond_type = "TIL"
            cond_expr = self.parse_expression()
        elif self.match(T.WHILE):
            cond_type = "WILE"
            cond_expr = self.parse_expression()

        body = self.parse_statement_block((T.LOOP_END,))

        self.consume(T.LOOP_END, f"Expected 'IM OUTTA YR' to close loop '{start_label}'")
        end_label_tok = self.consume(T.IDENTIFIER, "Expected loop label after 'IM OUTTA YR'")
        if end_label_tok.value != start_label:
            raise SyntaxError(
                f"Mismatched loop label: started with '{start_label}' but ended with '{end_label_tok.value}'",
                end_label_tok.line,
            )

        return LoopStmt(
            label=start_label,
            operation=operation,
            var_name=var_name,
            condition_type=cond_type,
            condition_expr=cond_expr,
            body=body,
        )

    def parse_func_def(self) -> FuncDef:
        self.consume(T.FUNCTION_START, "Expected 'HOW IZ I'")
        name = self.consume(T.IDENTIFIER, "Expected function name after 'HOW IZ I'").value

        params = []
        if self.match(T.YR):
            params.append(self.consume(T.IDENTIFIER, "Expected parameter name after 'YR'").value)
            while self.match(T.AN):
                self.consume(T.YR, "Expected 'YR' after 'AN' in parameter list")
                params.append(self.consume(T.IDENTIFIER, "Expected parameter name after 'YR'").value)

        body = self.parse_statement_block((T.FUNCTION_END,))
        self.consume(T.FUNCTION_END, f"Expected 'IF U SAY SO' to close function '{name}'")
        return FuncDef(name=name, params=params, body=body)

    def parse_return(self) -> ReturnStmt:
        self.consume(T.RETURN, "Expected 'FOUND YR'")
        expr = self.parse_expression()
        return ReturnStmt(expr)

    def parse_statement(self) -> Any:
        self.skip_newlines()

        # Variable declaration
        if self.check(T.I_HAS_A):
            return self.parse_declaration()

        # Output
        if self.check(T.VISIBLE):
            return self.parse_print()

        # Input
        if self.check(T.GIMMEH):
            return self.parse_input()

        # Conditional (O RLY?)
        if self.check(T.IF):
            return self.parse_conditional()

        # Switch-case (WTF?)
        if self.check(T.SWITCH):
            return self.parse_switch()

        # Loop (IM IN YR)
        if self.check(T.LOOP_START):
            return self.parse_loop()

        # Function definition (HOW IZ I)
        if self.check(T.FUNCTION_START):
            return self.parse_func_def()

        # Return (FOUND YR)
        if self.check(T.RETURN):
            return self.parse_return()

        # Break (GTFO)
        if self.check(T.BREAK):
            self.consume(T.BREAK, "Expected 'GTFO'")
            return BreakStmt()

        # Identifier statements: assignment, recast, or expression statement
        if self.check(T.IDENTIFIER):
            if self.current + 1 < len(self.tokens):
                next_tok = self.tokens[self.current + 1]
                if next_tok.type == T.R:
                    return self.parse_assignment()
                if next_tok.type == T.IS_NOW_A:
                    return self.parse_recast()

        # Expression statements (standalone expression, function call, comparison, variable reference)
        tok = self.peek()
        if (
            tok.type in BINARY_OPERATORS
            or tok.type in (
                T.FUNCTION_CALL,
                T.NOT,
                T.ALL,
                T.ANY,
                T.SMOOSH,
                T.MAEK,
                T.IDENTIFIER,
                T.NUMBR_LIT,
                T.NUMBAR_LIT,
                T.STRING_DELIMITER,
                T.YARN_LIT,
                T.WIN,
                T.FAIL,
                T.TYPE,
            )
        ):
            expr = self.parse_expression()
            return ExprStmt(expr)

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
