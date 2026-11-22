# references:
# - lolcode spec v1.2: https://github.com/justinmeza/lolcode-spec/blob/master/v1.2/lolcode-spec-v1.2.md
# - python dataclasses: https://docs.python.org/3/library/dataclasses.html
# - python enum: https://docs.python.org/3/library/enum.html
# - enum tips: https://testdriven.io/tips/44b6ecc1-750c-4ba2-95fb-8e376c99da7a/

from dataclasses import dataclass
from enum import Enum, auto

class T(Enum):
    EOF = auto()
    NEWLINE = auto()
    COMMA = auto()  # treat it like NEWLINE
    ERROR = auto()

    # comments
    BTW = auto()
    OBTW = auto()
    TLDR = auto()
    COMMENT_TEXT = auto()

    # program start and end
    HAI = auto()
    KTHXBYE = auto()
    WAZZUP = auto()
    BUHBYE = auto()

    # I/O
    BANG = auto()
    PLUS = auto()
    GIMMEH = auto()
    VISIBLE = auto()

    # identifiers (decided by the parser if its variable/function/loop)
    IDENTIFIER = auto()

    # literals
    NUMBR_LIT = auto()
    NUMBAR_LIT = auto()
    YARN_LIT = auto()
    STRING_DELIMITER = auto()
    WIN = auto()
    FAIL = auto()

    # type keyword (NUMBER/NUMBAR/YARN/TROOF/NOOB)
    TYPE = auto()

    # variables
    I_HAS_A = auto()
    ITZ = auto()
    R = auto()
    IS_NOW_A = auto()
    MAEK = auto()
    A = auto()
    AN = auto()
    MKAY = auto()
    SMOOSH = auto()

    # arithmetic operations
    ADD = auto()
    SUB = auto()
    MUL = auto()
    DIV = auto()
    MOD = auto()
    MAX = auto()
    MIN = auto()

    # logical operators
    AND = auto()
    OR = auto()
    XOR = auto()
    NOT = auto()
    ALL = auto()
    ANY = auto()

    # comparison operators
    EQUAL = auto()
    NOT_EQUAL = auto()
    GREATER = auto()
    LESS = auto()
    GREATER_EQUAL = auto()
    LESS_EQUAL = auto()

    # conditionals
    IF = auto()
    THEN = auto()
    ELIF = auto()
    ELSE = auto()
    ENDIF = auto()
    SWITCH = auto()
    CASE = auto()
    DEFAULT = auto()

    # loops
    LOOP_START = auto()
    LOOP_END = auto()
    INC = auto()
    DEC = auto()
    WHILE = auto()
    UNTIL = auto()
    BREAK = auto()
    YR = auto()

    # functions
    FUNCTION_START = auto()
    FUNCTION_END = auto()
    RETURN = auto()
    FUNCTION_CALL = auto()


# lexeme -> token type; check longest phrases first when matching
KEYWORDS: dict[str, T] = {
    "I HAS A": T.I_HAS_A,
    "IS NOW A": T.IS_NOW_A,
    "BOTH SAEM": T.EQUAL,
    "IM OUTTA YR": T.LOOP_END,
    "IM IN YR": T.LOOP_START,
    "IF U SAY SO": T.FUNCTION_END,
    "HOW IZ I": T.FUNCTION_START,
    "FOUND YR": T.RETURN,
    "SUM OF": T.ADD,
    "DIFF OF": T.SUB,
    "PRODUKT OF": T.MUL,
    "QUOSHUNT OF": T.DIV,
    "MOD OF": T.MOD,
    "BIGGR OF": T.MAX,
    "SMALLR OF": T.MIN,
    "BOTH OF": T.AND,
    "EITHER OF": T.OR,
    "WON OF": T.XOR,
    "ALL OF": T.ALL,
    "ANY OF": T.ANY,
    "O RLY?": T.IF,
    "YA RLY": T.THEN,
    "NO WAI": T.ELSE,
    "I IZ": T.FUNCTION_CALL,
    "HAI": T.HAI,
    "KTHXBYE": T.KTHXBYE,
    "VISIBLE": T.VISIBLE,
    "GIMMEH": T.GIMMEH,
    "ITZ": T.ITZ,
    "R": T.R,
    "A": T.A,
    "AN": T.AN,
    "MKAY": T.MKAY,
    "MAEK": T.MAEK,
    "SMOOSH": T.SMOOSH,
    "NOT": T.NOT,
    "DIFFRINT": T.NOT_EQUAL,
    "MEBBE": T.ELIF,
    "OIC": T.ENDIF,
    "WTF?": T.SWITCH,
    "OMG": T.CASE,
    "OMGWTF": T.DEFAULT,
    "UPPIN": T.INC,
    "NERFIN": T.DEC,
    "WILE": T.WHILE,
    "TIL": T.UNTIL,
    "YR": T.YR,
    "GTFO": T.BREAK,
    "WIN": T.WIN,
    "FAIL": T.FAIL,
    "WAZZUP": T.WAZZUP,
    "BUHBYE": T.BUHBYE,
    "BTW": T.BTW,
    "OBTW": T.OBTW,
    "TLDR": T.TLDR,
    "+": T.PLUS,
    ",": T.COMMA,
    "!": T.BANG,
}


TYPE_NAMES = {"NUMBR", "NUMBAR", "YARN", "TROOF", "NOOB"}


@dataclass
class Token:
    type: T
    value: str
    line: int

    @property
    def classification(self) -> str:
        return CLASSIFICATIONS.get(self.type, "Unknown")


# human-readable classifications
CLASSIFICATIONS: dict[T, str] = {
    # program & section delimiters
    T.HAI: "Code Delimiter",
    T.KTHXBYE: "Code Delimiter",
    T.WAZZUP: "Code Delimiter",
    T.BUHBYE: "Code Delimiter",

    # variable declaration & assignment
    T.I_HAS_A: "Variable Declaration",
    T.ITZ: "Variable Assignment",
    T.R: "Variable Assignment",
    T.IS_NOW_A: "Typecasting Keyword",
    T.MAEK: "Typecasting Keyword",
    T.A: "Type Delimiter",

    # identifiers
    T.IDENTIFIER: "Variable Identifier",

    # literals & delimiters
    T.NUMBR_LIT: "Literal",
    T.NUMBAR_LIT: "Literal",
    T.YARN_LIT: "Literal",
    T.STRING_DELIMITER: "String Delimiter",
    T.WIN: "Literal",
    T.FAIL: "Literal",
    T.TYPE: "Type Literal",

    # I/O
    T.VISIBLE: "Output Keyword",
    T.GIMMEH: "Input Keyword",
    T.BANG: "Suppress Newline",
    T.PLUS: "Plus Sign",
    T.COMMA: "Soft Linebreak",

    # arithmetic
    T.ADD: "Arithmetic Operator",
    T.SUB: "Arithmetic Operator",
    T.MUL: "Arithmetic Operator",
    T.DIV: "Arithmetic Operator",
    T.MOD: "Arithmetic Operator",
    T.MAX: "Arithmetic Operator",
    T.MIN: "Arithmetic Operator",

    # boolean & comparison
    T.AND: "Boolean Operator",
    T.OR: "Boolean Operator",
    T.XOR: "Boolean Operator",
    T.NOT: "Boolean Operator",
    T.ALL: "Infinite Arity Boolean Operator",
    T.ANY: "Infinite Arity Boolean Operator",
    T.EQUAL: "Comparison Operator",
    T.NOT_EQUAL: "Comparison Operator",
    T.GREATER: "Comparison Operator",
    T.LESS: "Comparison Operator",
    T.GREATER_EQUAL: "Comparison Operator",
    T.LESS_EQUAL: "Comparison Operator",

    # concatenation & delimiters
    T.SMOOSH: "Concatenation Operator",
    T.AN: "Parameter Separator",
    T.MKAY: "Expression Delimiter",

    # conditionals
    T.IF: "Conditional Delimiter",
    T.THEN: "If Keyword",
    T.ELIF: "Else-If Keyword",
    T.ELSE: "Else Keyword",
    T.ENDIF: "Control Delimiter",

    # switch-case
    T.SWITCH: "Switch-Case Delimiter",
    T.CASE: "Case Keyword",
    T.DEFAULT: "Default Case Keyword",

    # loops
    T.LOOP_START: "Loop Delimiter",
    T.LOOP_END: "Loop Delimiter",
    T.INC: "Increment Operator",
    T.DEC: "Decrement Operator",
    T.YR: "Parameter Delimiter",
    T.WHILE: "While Keyword",
    T.UNTIL: "Until Keyword",
    T.BREAK: "Break Statement",

    # functions
    T.FUNCTION_START: "Function Delimiter",
    T.FUNCTION_END: "Function Delimiter",
    T.RETURN: "Return Keyword",
    T.FUNCTION_CALL: "Function Call",

    # comments
    T.BTW: "Comment Delimiter",
    T.OBTW: "Comment Delimiter",
    T.TLDR: "Comment Delimiter",
    T.COMMENT_TEXT: "Comment Text",

    # structure & errors
    T.NEWLINE: "Newline",
    T.EOF: "End of File",
    T.ERROR: "Error",
}
