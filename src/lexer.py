import re
from tokens import *

# https://dev.to/frederikgramkortegaard/writing-your-first-compiler-part-3-lexical-analysis-4nn2

# Regex for identifier
IDEN = re.compile(r'^[a-zA-Z][a-zA-Z0-9_]*$')

# Regex for literals
NUMBR_LIT = re.compile(r'^-?[0-9]+$')
NUMBAR_LIT = re.compile(r'^-?[0-9]+\.[0-9]+$')
YARN_LIT = re.compile(r'^"[^"]*"$')
TROOF = re.compile(r'^(WIN|FAIL)$')
TYPE = re.compile(r'^(NOOB|NUMBR|NUMBAR|YARN|TROOF)$')
NEWLINE = re.compile(r"(\n)")

regexes = {
    NUMBR_LIT: "NUMBR_LIT",
    NUMBAR_LIT: "NUMBAR_LIT",
    YARN_LIT: "YARN_LIT",
    TROOF: "TROOF",
    TYPE: "TYPE"
}


def tokenize(code: str) -> list[Token]:
    tokens = []
    line = 0

    code = NEWLINE.split(code)
    print(code)

    for lexeme in code:
            
        # tokenize statement terminators (newline)
        if lexeme == '\n':
            tokens.append(Token(T.NEWLINE, lexeme, line))
            line += 1
            continue

        # tokenize literals
        for r, value in regexes.items():
            token = r.match(lexeme)
            if token:
                if value == "TYPE":
                    value = token.group(0)
                if value == "TROOF":
                    value = token.group(0)
                value = TYPES.get(value)
                tokens.append(Token(value, token.group(0), line))

    # append eof token after the loop (end of code)
    tokens.append(Token(T.EOF, lexeme, line))

    return tokens

    