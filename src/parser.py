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


# Token Groups Used by the Parser

LINEBREAK_TOKENS = (T.NEWLINE, T.COMMA)

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

# tokens that can legally begin a standalone expression or expression statement
EXPRESSION_START_TOKENS = {
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
}

# Parse Tree / Tuple Serialization Helpers (for CLI & Debug Display)

def expr_to_tuple(expr: Any) -> Any:
    # convert an AST expression node into nested tuples or primitive values
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
    # format an expression node into a readable string for PRINT tuples
    if isinstance(expr, Literal):
        if expr.type_name == "YARN":
            return f'"{expr.value}"'
        return str(expr.value)
    if isinstance(expr, VariableRef):
        return expr.name
    return str(expr_to_tuple(expr))


def stmt_to_tuple(stmt: Any) -> tuple:
    # convert an AST statement node and its inner blocks into nested tuples
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
        then_tuples = [stmt_to_tuple(s) for s in stmt.then_body]
        mebbe_tuples = [
            (expr_to_tuple(cond), [stmt_to_tuple(s) for s in body])
            for cond, body in stmt.mebbe_clauses
        ]
        else_tuples = [stmt_to_tuple(s) for s in stmt.else_body]
        return ('IF', expr_to_tuple(stmt.cond_expr), then_tuples, mebbe_tuples, else_tuples)
    if isinstance(stmt, SwitchStmt):
        cases = [(expr_to_tuple(c.literal), [stmt_to_tuple(s) for s in c.body]) for c in stmt.cases]
        default = [stmt_to_tuple(s) for s in stmt.default_case] if stmt.default_case else None
        return ('SWITCH', cases, default)
    if isinstance(stmt, LoopStmt):
        body_tuples = [stmt_to_tuple(s) for s in stmt.body]
        return (
            'LOOP',
            stmt.label,
            stmt.operation,
            stmt.var_name,
            stmt.condition_type,
            expr_to_tuple(stmt.condition_expr),
            body_tuples,
        )
    if isinstance(stmt, FuncDef):
        return ('FUNC_DEF', stmt.name, stmt.params, [stmt_to_tuple(s) for s in stmt.body])
    if isinstance(stmt, ReturnStmt):
        return ('RETURN', expr_to_tuple(stmt.expr))
    if isinstance(stmt, BreakStmt):
        return ('BREAK', 'GTFO')
    return ('UNKNOWN', str(stmt))

# Program Root Node

@dataclass
class Program:
    body: list[Any] = field(default_factory=list)
    wazzup: list[Any] = field(default_factory=list)

    def to_tuples(self) -> list[tuple]:
        # convert the entire AST program into a flat list of tuples
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



# Recursive Descent Parser

class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.current = 0

        # single-keyword statement dispatch table
        self._statement_parsers = {
            T.I_HAS_A: self.parse_declaration,
            T.VISIBLE: self.parse_print,
            T.GIMMEH: self.parse_input,
            T.IF: self.parse_conditional,
            T.SWITCH: self.parse_switch,
            T.LOOP_START: self.parse_loop,
            T.FUNCTION_START: self.parse_func_def,
            T.RETURN: self.parse_return,
        }

    # --- Token Stream Navigation Helpers ---

    def peek(self) -> Token:
        # return current token without consuming it (falls back to EOF)
        if self.current < len(self.tokens):
            return self.tokens[self.current]
        return self.tokens[-1]

    def peek_next(self) -> Token:
        # 1-token lookahead used to distinguish assignments/recasts from expressions
        if self.current + 1 < len(self.tokens):
            return self.tokens[self.current + 1]
        return self.tokens[-1]

    def check(self, token_type: T) -> bool:
        return self.peek().type == token_type

    def match(self, token_type: T) -> bool:
        # consume current token only if it matches token_type
        if self.check(token_type):
            self.current += 1
            return True
        return False

    def consume(self, token_type: T, error_message: str) -> Token:
        # require current token to be token_type or halt with a clear SyntaxError
        tok = self.peek()
        if tok.type != token_type:
            raise SyntaxError(f"{error_message} (got '{tok.value}')", tok.line)
        self.current += 1
        return tok

    def skip_newlines(self) -> None:
        # advance past hard newlines and comma soft-linebreaks
        while self.peek().type in LINEBREAK_TOKENS:
            self.current += 1

    def consume_linebreak(self, error_message: str = "Expected newline or comma after statement") -> None:
        # require at least one newline or comma between consecutive statements
        if self.peek().type not in LINEBREAK_TOKENS:
            tok = self.peek()
            raise SyntaxError(f"{error_message} (got '{tok.value}')", tok.line)
        self.skip_newlines()

    def _finish_statement(self, stop_tokens: tuple[T, ...], error_message: str) -> None:
        # require a linebreak before the next statement unless a block-ending token follows
        if self.peek().type in stop_tokens:
            self.skip_newlines()
        else:
            self.consume_linebreak(error_message)

    # --- Expression Parsing (Prefix Notation) ---

    def parse_primary(self) -> Any:
        # grammar: <primary> ::= <literal> | varident
        #          <literal> ::= numbr | numbar | yarn | troof

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
        if self.match(T.IDENTIFIER):
            return VariableRef(tok.value, line=tok.line)
        raise SyntaxError(f"Unexpected token in expression: '{tok.value}'", tok.line)

    def _parse_an_operands(self) -> list[Any]:
        # parse one or more expressions separated by the 'AN' keyword
        operands = [self.parse_expression(nested = True)]
        while self.match(T.AN):
            operands.append(self.parse_expression(nested = True))
        return operands

    def parse_infinite_bool(self, op: str, line: int = 0) -> InfiniteBoolExpr:
        # grammar: (ALL OF | ANY OF) <expr> { AN <expr> } MKAY
        operands = self._parse_an_operands()
        self.consume(T.MKAY, f"Expected 'MKAY' to close '{op}' expression")
        return InfiniteBoolExpr(op, operands, line=line)

    def parse_smoosh(self, line: int = 0) -> SmooshExpr:
        # grammar: SMOOSH <expr> { AN <expr> } [ MKAY ]
        operands = self._parse_an_operands()
        self.match(T.MKAY)
        return SmooshExpr(operands, line=line)

    def parse_func_call(self, line: int = 0) -> FuncCall:
        # grammar: I IZ <funcident> [ YR <expr> { AN [ YR ] <expr> } ] MKAY
        name_tok = self.consume(T.IDENTIFIER, "Expected function name after 'I IZ'")
        args = []
        if self.match(T.YR):
            args.append(self.parse_expression())
            while self.match(T.AN):
                self.match(T.YR)
                args.append(self.parse_expression())
        self.consume(T.MKAY, "Expected 'MKAY' to close function call")
        return FuncCall(name_tok.value, args, line=line or name_tok.line)

    def parse_expression(self, nested: bool = False) -> Any:
        # prefix notation eliminates precedence tables: operators always precede operands
        tok = self.peek()
        # SMOOSH, ALL OF, and ANY OF cannot be operands of other operations
        if nested and tok.type in (T.ALL, T.ANY, T.SMOOSH):
            raise SyntaxError(f"'{tok.value}' cannot be nested inside another expression", tok.line)
        # binary operations: <op> <left_expr> AN <right_expr>
        if tok.type in BINARY_OPERATORS:
            self.current += 1
            op = tok.value
            left = self.parse_expression(nested = True)
            self.consume(T.AN, f"Expected 'AN' separating operands for '{op}'")
            right = self.parse_expression(nested = True)
            return BinaryOp(op, left, right, line=tok.line)

        # unary boolean negation: NOT <expr>
        if self.match(T.NOT):
            operand = self.parse_expression(nested = True)
            return UnaryOp("NOT", operand, line=tok.line)

        # infinite-arity boolean operations: ALL OF / ANY OF ... MKAY
        if self.match(T.ALL):
            return self.parse_infinite_bool("ALL OF", line=tok.line)
        if self.match(T.ANY):
            return self.parse_infinite_bool("ANY OF", line=tok.line)

        # string concatenation: SMOOSH ...
        if self.match(T.SMOOSH):
            return self.parse_smoosh(line=tok.line)

        # explicit typecasting: MAEK <expr> [A] <type>
        if self.match(T.MAEK):
            expr = self.parse_expression(nested = True)
            self.match(T.A)  # 'A' delimiter is optional in LOLCODE
            type_tok = self.consume(T.TYPE, "Expected type name after 'MAEK' (NUMBR, NUMBAR, YARN, TROOF, NOOB)")
            return TypecastExpr(expr, type_tok.value, line=tok.line)

        # function invocation: I IZ <name> ... MKAY
        if self.match(T.FUNCTION_CALL):
            return self.parse_func_call(line=tok.line)

        return self.parse_primary()

    # --- Variable Declaration Section (WAZZUP ... BUHBYE) ---

    def parse_var_section(self) -> list[VarDecl]:
        # grammar: WAZZUP <linebreaks> { <declaration> <linebreaks> } BUHBYE
        self.consume(T.WAZZUP, "Expected 'WAZZUP'")
        self.consume_linebreak("Expected newline or comma after 'WAZZUP'")

        decls = []
        stop_tokens = (T.BUHBYE, T.KTHXBYE, T.EOF)
        while self.peek().type not in stop_tokens:
            if not self.check(T.I_HAS_A):
                tok = self.peek()
                raise SyntaxError(
                    f"Only variable declarations ('I HAS A') are allowed in WAZZUP section, got '{tok.value}'",
                    tok.line,
                )
            decls.append(self.parse_declaration())
            self._finish_statement(stop_tokens, "Expected newline or comma after variable declaration")

        self.consume(T.BUHBYE, "Expected 'BUHBYE' to close 'WAZZUP' section")
        return decls

    parse_variable_section = parse_var_section

    # --- Simple Statement Parsers ---

    def parse_declaration(self) -> VarDecl:
        # grammar: I HAS A <varident> [ ITZ <expr> ]
        kw_tok = self.consume(T.I_HAS_A, "Expected 'I HAS A'")
        name_tok = self.consume(T.IDENTIFIER, "Expected variable name")
        init_val = self.parse_expression() if self.match(T.ITZ) else None
        return VarDecl(name_tok.value, init_val, line=kw_tok.line)

    def parse_assignment(self) -> Assignment:
        # grammar: <varident> R <expr>
        var_tok = self.consume(T.IDENTIFIER, "Expected variable name")
        self.consume(T.R, "Expected 'R'")
        expr = self.parse_expression()
        return Assignment(var_tok.value, expr, line=var_tok.line)

    def parse_recast(self) -> RecastStmt:
        # grammar: <varident> IS NOW A <type>
        var_tok = self.consume(T.IDENTIFIER, "Expected variable name")
        self.consume(T.IS_NOW_A, "Expected 'IS NOW A'")
        type_tok = self.consume(T.TYPE, "Expected type name after 'IS NOW A' (NUMBR, NUMBAR, YARN, TROOF, NOOB)")
        return RecastStmt(var_tok.value, type_tok.value, line=var_tok.line)

    def parse_print(self) -> PrintStmt:
        # grammar: VISIBLE <expr> { [+] <expr> } [!]
        vis_tok = self.consume(T.VISIBLE, "Expected 'VISIBLE'")
        operands = [self.parse_expression()]
        while self.peek().type not in (T.NEWLINE, T.COMMA, T.BANG, T.EOF):
            if self.match(T.PLUS):
                continue
            operands.append(self.parse_expression())
        suppress = self.match(T.BANG)
        return PrintStmt(operands, suppress_newline=suppress, line=vis_tok.line)

    def parse_input(self) -> InputStmt:
        # grammar: GIMMEH <varident>
        gim_tok = self.consume(T.GIMMEH, "Expected 'GIMMEH'")
        var_tok = self.consume(T.IDENTIFIER, "Expected variable name after 'GIMMEH'")
        return InputStmt(var_tok.value, line=gim_tok.line)

    def parse_return(self) -> ReturnStmt:
        # grammar: FOUND YR <expr>
        ret_tok = self.consume(T.RETURN, "Expected 'FOUND YR'")
        expr = self.parse_expression()
        return ReturnStmt(expr, line=ret_tok.line)

    # --- Block & Control-Flow Statement Parsers ---

    def parse_statement_block(self, stop_tokens: tuple[T, ...]) -> list[Any]:
        # parse statements inside a nested block until any stop token, KTHXBYE, or EOF
        # stopping at KTHXBYE/EOF lets the caller report the exact missing closing delimiter
        body = []
        block_end_tokens = stop_tokens + (T.KTHXBYE, T.EOF)
        self.skip_newlines()

        while self.peek().type not in block_end_tokens:
            if self.check(T.FUNCTION_START):
                raise SyntaxError("Function declarations are only allowed at the top level", self.peek().line)
            body.append(self.parse_statement())
            self._finish_statement(block_end_tokens, "Expected newline or comma after statement")

        return body

    def parse_conditional(self) -> IfStmt:
        # grammar: O RLY? <lb> YA RLY <lb> <block> { MEBBE <expr> <lb> <block> } [ NO WAI <lb> <block> ] OIC
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
        # grammar: WTF? <lb> { OMG <literal> <lb> <block> } [ OMGWTF <lb> <block> ] OIC
        sw_tok = self.consume(T.SWITCH, "Expected 'WTF?'")
        self.skip_newlines()

        cases = []
        while self.check(T.CASE):
            case_tok = self.consume(T.CASE, "Expected 'OMG'")
            if self.check(T.TYPE):
                raise SyntaxError(f"A type name ('{self.peek().value}') cannot be used as a case literal", self.peek().line)
            case_lit = self.parse_primary()
            if not isinstance(case_lit, Literal):
                raise SyntaxError(f"Expected literal value for case, got variable '{case_lit.name}'", case_tok.line)
            case_body = self.parse_statement_block((T.CASE, T.DEFAULT, T.ENDIF))
            cases.append(CaseClause(case_lit, case_body, line=case_tok.line))

        default_case = None
        if self.match(T.DEFAULT):
            default_case = self.parse_statement_block((T.ENDIF,))

        self.consume(T.ENDIF, "Expected 'OIC' to close switch block")
        return SwitchStmt(cases=cases, default_case=default_case, line=sw_tok.line)

    def parse_loop(self) -> LoopStmt:
        # grammar: IM IN YR <label> <UPPIN|NERFIN> YR <var> [TIL|WILE <expr>] <lb> <block> IM OUTTA YR <label>
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
        # grammar: HOW IZ I <name> [ YR <param> { AN YR <param> } ] <lb> <block> IF U SAY SO
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

    # --- Top-Level Statement & Program Dispatch ---

    def parse_statement(self) -> Any:
        self.skip_newlines()
        tok = self.peek()

        # WAZZUP is only valid immediately after HAI, never inside the body
        if tok.type == T.WAZZUP:
            raise SyntaxError("WAZZUP section must appear at the beginning of the program immediately after HAI", tok.line)

        if tok.type in self._statement_parsers:
            return self._statement_parsers[tok.type]()

        if tok.type == T.BREAK:
            brk_tok = self.consume(T.BREAK, "Expected 'GTFO'")
            return BreakStmt(line=brk_tok.line)

        # identifier statements need 1-token lookahead to detect assignment (R) or recast (IS NOW A)
        if tok.type == T.IDENTIFIER:
            next_tok = self.peek_next()
            if next_tok.type == T.R:
                return self.parse_assignment()
            if next_tok.type == T.IS_NOW_A:
                return self.parse_recast()

        # standalone expression updating the implicit IT variable
        if tok.type in BINARY_OPERATORS or tok.type in EXPRESSION_START_TOKENS:
            expr = self.parse_expression()
            return ExprStmt(expr, line=tok.line)

        raise SyntaxError(f"Invalid statement starting with '{tok.value}'", tok.line)

    def parse(self) -> Program:
        # grammar: { <function> <lb> } HAI [version] <lb> [WAZZUP ... BUHBYE <lb>]
        # { <statement> <lb> } KTHXBYE { <lb> <function> } <lb> EOF
        self.skip_newlines()
        # function definitions are allowed before  HAI
        body = []
        while self.check(T.FUNCTION_START):
            body.append(self.parse_func_def())
            self._finish_statement((T.HAI, T.FUNCTION_START), "Expected newline or comma after function definition")
        self.consume(T.HAI, "Program must start with 'HAI'")

        # optional LOLCODE version literal after HAI (e.g. HAI 1.2)
        if self.peek().type in (T.NUMBAR_LIT, T.NUMBR_LIT, T.YARN_LIT):
            self.current += 1

        program_end_tokens = (T.KTHXBYE, T.EOF)
        self._finish_statement(program_end_tokens, "Expected newline or comma after 'HAI'")

        # optional global variable declaration section
        wazzup_decls = []
        if self.check(T.WAZZUP):
            wazzup_decls = self.parse_var_section()
            self._finish_statement(program_end_tokens, "Expected newline or comma after 'BUHBYE'")

        # main program body statements (including top-level function definitions)
        while self.peek().type not in program_end_tokens:
            body.append(self.parse_statement())
            self._finish_statement(program_end_tokens, "Expected newline or comma after statement")

        self.consume(T.KTHXBYE, "Program must end with 'KTHXBYE'")
        self.skip_newlines()
        # function definitions are allowed after KTHXBYE; any other code is rejected
        while self.check(T.FUNCTION_START):
            body.append(self.parse_func_def())
            self._finish_statement((T.FUNCTION_START, T.EOF), "Expected newline or comma after function definition")
        self.consume(T.EOF, "Unexpected code after 'KTHXBYE'")
        return Program(body=body, wazzup=wazzup_decls)


def parse(tokens: list[Token]) -> Program:
    return Parser(tokens).parse()
