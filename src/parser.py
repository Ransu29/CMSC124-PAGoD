from tokens import T

def group_tokens_by_line(tokens):
    pass

def parse(tokens):
    # group tokens by line number
    lines = group_tokens_by_line(tokens)
    parsed_tree = []

    # first line HAI
    if lines[0][0].type != T.HAI:
        raise SyntaxError("Line 1: Code must start with HAI!")
    parsed_tree.append(('START', 'HAI'))

    # check each line in between
    for line in lines[1:-1]:
        first_token = line[0]
        if first_token.type == T.I_HAS_A:
            parsed_tree.append(parse_declaration(line))
        elif first_token.type == T.IDENTIFIER and len(line) > 1 and line[1].type == T.R:
            parsed_tree.append(parse_assignment(line))
        elif first_token.type == T.VISIBLE:
            parsed_tree.append(parse_print(line))
        else:
            raise SyntaxError(f"Line {first_token.line}: Invalid statement!")

    # last line KTHXBYE
    if lines[-1][0].type != T.KTHXBYE:
        raise SyntaxError(f"Line {lines[-1][0].line}: Code must end with KTHXBYE!")
    parsed_tree.append(('END', 'KTHXBYE'))

    return parsed_tree

def parse_declaration(line):
    var_name = line[1].value

    init_val = None # initial value, None in case uninitialized variable
    if len(line) == 4 and line[2].type == T.ITZ:
        init_val = line[3].value  # gets the value of the variable

    return ('VAR_DECL', var_name, init_val)

def parse_assignment(line):
    pass

def parse_print(line):
    pass

def print_parse_tree(line):
    pass


# expected output:
# [
#     ('START', 'HAI'),
#     ('DECLARATION', 'num', 10),
#     ('DECLARATION', 'name', 'Garfield'),
#     ('ASSIGNMENT', 'num', 20),
#     ('PRINT', '"Hello, " + name'),
#     ('END', 'KTHXBYE')
# ]