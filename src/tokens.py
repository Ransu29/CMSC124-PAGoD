"""
references: https://docs.python.org/3/library/dataclasses.html
            https://docs.python.org/3/library/enum.html
            https://testdriven.io/tips/44b6ecc1-750c-4ba2-95fb-8e376c99da7a/
"""

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
    GIMMEH = auto()
    VISIBLE = auto()

    # identifiers (decided by the parser if its variable/function/loop)
    IDENTIFIER = auto()

    # literals
    NUMBR_LIT = auto()
    NUMBAR_LIT = auto()
    YARN_LIT = auto()
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
}


TYPE_NAMES = {"NUMBR", "NUMBAR", "YARN", "TROOF", "NOOB"}


@dataclass
class Token:
    type: T
    value: str
    line: int
