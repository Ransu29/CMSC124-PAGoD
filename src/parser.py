# references:
# - lolcode spec v1.2: https://github.com/justinmeza/lolcode-spec/blob/master/v1.2/lolcode-spec-v1.2.md
# - crafting interpreters ast: https://craftinginterpreters.com/representing-code.html
# - crafting interpreters parsing: https://craftinginterpreters.com/parsing-expressions.html
# - prefix notation (polish notation): https://en.wikipedia.org/wiki/Polish_notation
# - recursive descent parsing: https://en.wikipedia.org/wiki/Recursive_descent_parser
# - python dataclasses: https://docs.python.org/3/library/dataclasses.html

from dataclasses import dataclass, field
from typing import Any

from ast_nodes import *
from errors import SyntaxError
from tokens import T, Token

# AST expression serialization helpers

def expr_to_tuple(expr: Any) -> Any:
    # convert an AST expression node into clean nested tuples or primitive values
    if expr is None:
        return None
    if isinstance(expr, Literal):
        return expr.value
    if isinstance(expr, VariableRef):
        return expr.name
    if isinstance(expr, BinaryOp):
        return (expr.op, expr_to_tuple(expr.left), expr_to_tuple(expr.right))
    if isinstance(expr, UnaryOp):
        return (expr.op, expr_to_tuple(expr.operand))
    if isinstance(expr, InfiniteBoolExpr):
        return (expr.op, *[expr_to_tuple(arg) for arg in expr.operands])
    if isinstance(expr, SmooshExpr):
        return ('SMOOSH', *[expr_to_tuple(arg) for arg in expr.operands])
    if isinstance(expr, TypecastExpr):
        return ('MAEK', expr_to_tuple(expr.expr), expr.target_type)
    if isinstance(expr, FuncCall):
        return ('CALL', expr.name, *[expr_to_tuple(arg) for arg in expr.args])
    return expr


def expr_to_str(expr: Any) -> str:
    # format an expression node into a readable string for PRINT statements
    if isinstance(expr, Literal):
        if expr.type_name == "YARN":
            return f'"{expr.value}"'
        return str(expr.value)
    if isinstance(expr, VariableRef):
        return expr.name
    return str(expr_to_tuple(expr))

def stmt_to_tuple(stmt: Any) -> tuple:
    # convert an AST statement node and its inner blocks into clean nested tuples
    if isinstance(stmt, VarDecl):
        return ('DECLARATION', stmt.name, expr_to_tuple(stmt.value_expr))
    if isinstance(stmt, Assignment):
        return ('ASSIGNMENT', stmt.var_name, expr_to_tuple(stmt.expr))
    if isinstance(stmt, RecastStmt):
        return ('RECAST', stmt.var_name, stmt.target_type)
    if isinstance(stmt, InputStmt):
        return ('INPUT', stmt.var_name)
    if isinstance(stmt, PrintStmt):
        return ('PRINT', " + ".join(expr_to_str(op) for op in stmt.operands))
    if isinstance(stmt, ExprStmt):
        return ('EXPR_STMT', expr_to_tuple(stmt.expr))
    if isinstance(stmt, IfStmt):
        return (
            'IF',
            expr_to_tuple(stmt.cond_expr),
            [stmt_to_tuple(s) for s in stmt.then_body],
            [(expr_to_tuple(cond), [stmt_to_tuple(s) for s in body]) for cond, body in stmt.mebbe_clauses],
            [stmt_to_tuple(s) for s in stmt.else_body],
        )
    if isinstance(stmt, SwitchStmt):
        cases = [(expr_to_tuple(c.literal), [stmt_to_tuple(s) for s in c.body]) for c in stmt.cases]
        default = [stmt_to_tuple(s) for s in stmt.default_case] if stmt.default_case else None
        return ('SWITCH', cases, default)
    if isinstance(stmt, LoopStmt):
        return (
            'LOOP',
            stmt.label,
            stmt.operation,
            stmt.var_name,
            stmt.condition_type,
            expr_to_tuple(stmt.condition_expr),
            [stmt_to_tuple(s) for s in stmt.body],
        )
    if isinstance(stmt, FuncDef):
        return ('FUNC_DEF', stmt.name, stmt.params, [stmt_to_tuple(s) for s in stmt.body])
    if isinstance(stmt, ReturnStmt):
        return ('RETURN', expr_to_tuple(stmt.expr))
    if isinstance(stmt, BreakStmt):
        return ('BREAK', 'GTFO')
    return ('UNKNOWN', str(stmt))

@dataclass
class Program:
    body: list[Any] = field(default_factory=list)
    wazzup: list[Any] = field(default_factory=list)

    def to_tuples(self) -> list[tuple]:
        # convert the entire AST program into a list of tuples
        res = [('START', 'HAI')]
        if self.wazzup:
            res.append(('SECTION', 'WAZZUP'))
            for decl in self.wazzup:
                res.append(stmt_to_tuple(decl))
            res.append(('SECTION', 'BUHBYE'))
        for stmt in self.body:
            res.append(stmt_to_tuple(stmt))
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

    def consume_linebreak(self, error_message: str = "Expected newline or comma after statement") -> None:
        if self.peek().type not in (T.NEWLINE, T.COMMA):
            tok = self.peek()
            raise SyntaxError(f"{error_message} (got '{tok.value}')", tok.line)
        self.skip_newlines()

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
            return Literal(int(tok.value), "NUMBR", line=tok.line)
        if self.match(T.NUMBAR_LIT):
            return Literal(float(tok.value), "NUMBAR", line=tok.line)
        if self.match(T.WIN):
            return Literal(True, "TROOF", line=tok.line)
        if self.match(T.FAIL):
            return Literal(False, "TROOF", line=tok.line)
        if self.match(T.STRING_DELIMITER):
            yarn_tok = self.consume(T.YARN_LIT, "Expected string content")
            self.consume(T.STRING_DELIMITER, "Expected closing quote")
            return Literal(yarn_tok.value, "YARN", line=tok.line)
        if self.match(T.YARN_LIT):
            return Literal(tok.value, "YARN", line=tok.line)
        if self.match(T.TYPE):
            return Literal(tok.value, "TYPE", line=tok.line)
        if self.match(T.IDENTIFIER):
            return VariableRef(tok.value, line=tok.line)
        raise SyntaxError(f"Unexpected token in expression: '{tok.value}'", tok.line)

    def parse_infinite_bool(self, op: str, line: int = 0) -> InfiniteBoolExpr:
        operands = [self.parse_expression()]
        while self.match(T.AN):
            operands.append(self.parse_expression())
        self.consume(T.MKAY, f"Expected 'MKAY' to close '{op}' expression")
        return InfiniteBoolExpr(op, operands, line=line)

    def parse_smoosh(self, line: int = 0) -> SmooshExpr:
        operands = [self.parse_expression()]
        while self.match(T.AN):
            operands.append(self.parse_expression())
        if self.check(T.MKAY):
            self.match(T.MKAY)
        return SmooshExpr(operands, line=line)

    def parse_func_call(self, line: int = 0) -> FuncCall:
        name_tok = self.consume(T.IDENTIFIER, "Expected function name after 'I IZ'")
        args = []
        if self.match(T.YR):
            args.append(self.parse_expression())
            while self.match(T.AN):
                self.match(T.YR)
                args.append(self.parse_expression())
        self.consume(T.MKAY, "Expected 'MKAY' to close function call")
        return FuncCall(name_tok.value, args, line=line or name_tok.line)

    def parse_expression(self) -> Any:
        tok = self.peek()

        # binary operators: arithmetic, boolean binary, comparison
        if tok.type in BINARY_OPERATORS:
            self.current += 1
            op = tok.value
            left = self.parse_expression()
            self.consume(T.AN, f"Expected 'AN' separating operands for '{op}'")
            right = self.parse_expression()
            return BinaryOp(op, left, right, line=tok.line)

        # unary operator: NOT
        if self.match(T.NOT):
            operand = self.parse_expression()
            return UnaryOp("NOT", operand, line=tok.line)

        # infinite arity boolean: ALL OF, ANY OF
        if self.match(T.ALL):
            return self.parse_infinite_bool("ALL OF", line=tok.line)
        if self.match(T.ANY):
            return self.parse_infinite_bool("ANY OF", line=tok.line)

        # concatenation: SMOOSH
        if self.match(T.SMOOSH):
            return self.parse_smoosh(line=tok.line)

        # typecasting: MAEK <expr> [A] <type>
        if self.match(T.MAEK):
            expr = self.parse_expression()
            self.match(T.A)  # optional 'A' delimiter
            type_tok = self.consume(T.TYPE, "Expected type name after 'MAEK' (NUMBR, NUMBAR, YARN, TROOF, NOOB)")
            return TypecastExpr(expr, type_tok.value, line=tok.line)

        # function call: I IZ <name> [YR <arg1> [AN YR <arg2>...]] MKAY
        if self.match(T.FUNCTION_CALL):
            return self.parse_func_call(line=tok.line)

        return self.parse_primary()

    def parse_var_section(self) -> list[VarDecl]:
        self.consume(T.WAZZUP, "Expected 'WAZZUP'")
        self.consume_linebreak("Expected newline or comma after 'WAZZUP'")
        decls = []
        while (
            not self.check(T.BUHBYE)
            and not self.check(T.KTHXBYE)
            and not self.check(T.EOF)
        ):
            if not self.check(T.I_HAS_A):
                tok = self.peek()
                raise SyntaxError(
                    f"Only variable declarations ('I HAS A') are allowed in WAZZUP section, got '{tok.value}'",
                    tok.line,
                )
            decls.append(self.parse_declaration())
            if not self.check(T.BUHBYE) and not self.check(T.KTHXBYE) and not self.check(T.EOF):
                self.consume_linebreak("Expected newline or comma after variable declaration")
            else:
                self.skip_newlines()
        self.consume(T.BUHBYE, "Expected 'BUHBYE' to close 'WAZZUP' section")
        return decls

    parse_variable_section = parse_var_section
    
    def parse_declaration(self) -> VarDecl:
        kw_tok = self.consume(T.I_HAS_A, "Expected 'I HAS A'")
        name_tok = self.consume(T.IDENTIFIER, "Expected variable name")
        init_val = None
        if self.match(T.ITZ):
            init_val = self.parse_expression()
        return VarDecl(name_tok.value, init_val, line=kw_tok.line)

    def parse_assignment(self) -> Assignment:
        var_tok = self.consume(T.IDENTIFIER, "Expected variable name")
        self.consume(T.R, "Expected 'R'")
        expr = self.parse_expression()
        return Assignment(var_tok.value, expr, line=var_tok.line)

    def parse_print(self) -> PrintStmt:
        vis_tok = self.consume(T.VISIBLE, "Expected 'VISIBLE'")
        operands = [self.parse_expression()]
        while self.peek().type not in (T.NEWLINE, T.COMMA, T.BANG, T.EOF):
            if self.match(T.PLUS):
                continue
            operands.append(self.parse_expression())
        suppress = self.match(T.BANG)
        return PrintStmt(operands, suppress_newline=suppress, line=vis_tok.line)

    def parse_input(self) -> InputStmt:
        gim_tok = self.consume(T.GIMMEH, "Expected 'GIMMEH'")
        var_tok = self.consume(T.IDENTIFIER, "Expected variable name after 'GIMMEH'")
        return InputStmt(var_tok.value, line=gim_tok.line)

    def parse_recast(self) -> RecastStmt:
        var_tok = self.consume(T.IDENTIFIER, "Expected variable name")
        self.consume(T.IS_NOW_A, "Expected 'IS NOW A'")
        type_tok = self.consume(T.TYPE, "Expected type name after 'IS NOW A' (NUMBR, NUMBAR, YARN, TROOF, NOOB)")
        return RecastStmt(var_tok.value, type_tok.value, line=var_tok.line)

    def parse_statement_block(self, stop_tokens: tuple[T, ...]) -> list[Any]:
        body = []
        self.skip_newlines()
        while (
            self.peek().type not in stop_tokens
            and self.peek().type not in (T.KTHXBYE, T.EOF)
        ):
            if self.check(T.FUNCTION_START):
                raise SyntaxError("Function declarations are only allowed at the top level", self.peek().line)
            stmt = self.parse_statement()
            body.append(stmt)
            if (
                self.peek().type not in stop_tokens
                and self.peek().type not in (T.KTHXBYE, T.EOF)
            ):
                self.consume_linebreak("Expected newline or comma after statement")
            else:
                self.skip_newlines()
        return body

    def parse_conditional(self) -> IfStmt:
        if_tok = self.consume(T.IF, "Expected 'O RLY?'")
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
        return IfStmt(then_body=then_body, mebbe_clauses=mebbe_clauses, else_body=else_body, line=if_tok.line)

    def parse_switch(self) -> SwitchStmt:
        sw_tok = self.consume(T.SWITCH, "Expected 'WTF?'")
        self.skip_newlines()

        cases = []
        while self.check(T.CASE):
            case_tok = self.consume(T.CASE, "Expected 'OMG'")
            case_lit = self.parse_primary()
            if not isinstance(case_lit, Literal):
                raise SyntaxError(f"Expected literal value for case, got '{case_lit}'", self.peek().line)
            case_body = self.parse_statement_block((T.CASE, T.DEFAULT, T.ENDIF))
            cases.append(CaseClause(case_lit, case_body, line=case_tok.line))

        default_case = None
        if self.match(T.DEFAULT):
            default_case = self.parse_statement_block((T.ENDIF,))

        self.consume(T.ENDIF, "Expected 'OIC' to close switch block")
        return SwitchStmt(cases=cases, default_case=default_case, line=sw_tok.line)

    def parse_loop(self) -> LoopStmt:
        loop_tok = self.consume(T.LOOP_START, "Expected 'IM IN YR'")
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
            line=loop_tok.line,
        )

    def parse_func_def(self) -> FuncDef:
        fn_tok = self.consume(T.FUNCTION_START, "Expected 'HOW IZ I'")
        name = self.consume(T.IDENTIFIER, "Expected function name after 'HOW IZ I'").value

        params = []
        if self.match(T.YR):
            params.append(self.consume(T.IDENTIFIER, "Expected parameter name after 'YR'").value)
            while self.match(T.AN):
                self.consume(T.YR, "Expected 'YR' after 'AN' in parameter list")
                params.append(self.consume(T.IDENTIFIER, "Expected parameter name after 'YR'").value)

        body = self.parse_statement_block((T.FUNCTION_END,))
        self.consume(T.FUNCTION_END, f"Expected 'IF U SAY SO' to close function '{name}'")
        return FuncDef(name=name, params=params, body=body, line=fn_tok.line)

    def parse_return(self) -> ReturnStmt:
        ret_tok = self.consume(T.RETURN, "Expected 'FOUND YR'")
        expr = self.parse_expression()
        return ReturnStmt(expr, line=ret_tok.line)

    def parse_statement(self) -> Any:
        self.skip_newlines()

        # Reject WAZZUP if it appears inside the body
        if self.check(T.WAZZUP):
            tok = self.peek()
            raise SyntaxError("WAZZUP section must appear at the beginning of the program immediately after HAI", tok.line)

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
            brk_tok = self.consume(T.BREAK, "Expected 'GTFO'")
            return BreakStmt(line=brk_tok.line)

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
            return ExprStmt(expr, line=tok.line)

        raise SyntaxError(f"Invalid statement starting with '{tok.value}'", tok.line)

    def parse(self) -> Program:
        self.skip_newlines()
        self.consume(T.HAI, "Program must start with 'HAI'")
        if self.peek().type in (T.NUMBAR_LIT, T.NUMBR_LIT, T.YARN_LIT):
            self.current += 1
        if not self.check(T.KTHXBYE) and not self.check(T.EOF):
            self.consume_linebreak("Expected newline or comma after 'HAI'")
        else:
            self.skip_newlines()

        # Variable Section (WAZZUP ... BUHBYE)
        wazzup_decls = []
        if self.check(T.WAZZUP):
            wazzup_decls = self.parse_var_section()
            if not self.check(T.KTHXBYE) and not self.check(T.EOF):
                self.consume_linebreak("Expected newline or comma after 'BUHBYE'")
            else:
                self.skip_newlines()

        # parse main program body statements
        body = []
        while not self.check(T.KTHXBYE) and not self.check(T.EOF):
            stmt = self.parse_statement()
            body.append(stmt)
            if not self.check(T.KTHXBYE) and not self.check(T.EOF):
                self.consume_linebreak("Expected newline or comma after statement")
            else:
                self.skip_newlines()

        self.consume(T.KTHXBYE, "Program must end with 'KTHXBYE'")
        self.skip_newlines()
        self.consume(T.EOF, "Unexpected code after 'KTHXBYE'")
        return Program(body=body, wazzup=wazzup_decls)

def parse(tokens: list[Token]) -> Program:
    return Parser(tokens).parse()
