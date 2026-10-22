CODE = """
HAI
VISIBLE "Hi"
KTHXBYE
"""

TOKEN_TYPE = {
    "HAI": "KEYWORD",
    "VISIBLE": "KEYWORD",
    "KTHXBYE": "KEYWORD"
}

TOKENS = []

class Token:
    def __init__(self, type, value, line, column):
        self.type = type
        self.value = value
        self.line = line
        self.column = column


def lexer(code):
    code = code.replace(",", "\n").split("\n") 

    for line_index, line in enumerate(code):
        line = line.split()
        for col_index, item in enumerate(line):
            item_type = TOKEN_TYPE.get(item)
            t = Token(item_type, item, line_index, col_index)
            TOKENS.append(t) 

print(TOKENS)
