import re
from tokens import *

# https://dev.to/frederikgramkortegaard/writing-your-first-compiler-part-3-lexical-analysis-4nn2

# Regex for identifier
IDEN = re.compile(r'^[a-zA-Z][a-zA-Z0-9_]*$ ')

# Regex for literals
NUMBR = re.compile(r'^-?[0-9]+$')
NUMBAR = re.compile(r'^-?[0-9]+\.[0-9]+$')
YARN = re.compile(r'^"[^"]*"$')
TROOF = re.compile(r'^(WIN|FAIL)$')
TYPE = re.compile(r'^(NOOB|NUMBR|NUMBAR|YARN|TROOF)$')
NEWLINE = re.compile(r"(\n)")

def tokenize(code: str) -> list[Token]:
    tokens = []
    line = 0

    code = NEWLINE.split(code)

    print(code)
    for word in code:
        if word == '\n':
            tokens.append(Token(word, T.NEWLINE, line))
            line += 1
            continue

        

    return tokens

    



