# references:
# - lolcode spec v1.2: https://github.com/justinmeza/lolcode-spec/blob/master/v1.2/lolcode-spec-v1.2.md
# - compiler scanning: https://craftinginterpreters.com/scanning.html
# - lexical analysis guide: https://dev.to/frederikgramkortegaard/writing-your-first-compiler-part-3-lexical-analysis-4nn2
# - python regex: https://docs.python.org/3/library/re.html

import re
from tokens import T, Token, KEYWORDS, TYPE_NAMES

# literal and identifier regexes
IDENTIFIER_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]*$")
NUMBR_PATTERN = re.compile(r"^-?[0-9]+$")
NUMBAR_PATTERN = re.compile(r"^-?[0-9]+\.[0-9]+$")

# sort keywords by length descending for greedy phrase matching
SORTED_KEYWORDS = sorted(KEYWORDS.keys(), key=len, reverse=True)

DELIMITERS = {" ", "\t", ",", "!", "+"}

def is_keyword_boundary(line: str, end_pos: int, keyword: str) -> bool:
    if end_pos >= len(line):
        return True
    next_char = line[end_pos]
    if keyword[-1].isalnum() or keyword[-1] == "_":
        return not (next_char.isalnum() or next_char == "_")
    return True

def tokenize(code: str) -> list[Token]:
    tokens: list[Token] = []
    lines = code.splitlines()
    in_multiline_comment = False

    for line_index, raw_line in enumerate(lines, start=1):
        stripped_line = raw_line.strip()

        # handle multi-line comments (obtw ... tldr)
        if in_multiline_comment:
            if "TLDR" in stripped_line:
                # check for invalid statement on tldr line
                parts = stripped_line.split("TLDR", 1)
                before_tldr = parts[0].strip()
                after_tldr = parts[1].strip()
                if before_tldr or (after_tldr and not after_tldr.startswith("BTW")):
                    tokens.append(Token(T.ERROR, raw_line, line_index))
                in_multiline_comment = False
            continue

        if stripped_line.startswith("OBTW"):
            # check for same-line tldr
            if "TLDR" in stripped_line:
                after_tldr = stripped_line.split("TLDR", 1)[1].strip()
                if after_tldr and not after_tldr.startswith("BTW"):
                    tokens.append(Token(T.ERROR, raw_line, line_index))
                continue
            in_multiline_comment = True
            continue

        # reject obtw placed after statements on the same line
        if "OBTW" in stripped_line and not stripped_line.startswith("OBTW"):
            tokens.append(Token(T.ERROR, raw_line, line_index))
            continue

        line_tokens: list[Token] = []
        pos = 0
        line_length = len(raw_line)

        while pos < line_length:
            # skip spaces and tabs
            if raw_line[pos] in " \t":
                pos += 1
                continue

            # single-line comment (btw)
            if raw_line[pos:].startswith("BTW"):
                if is_keyword_boundary(raw_line, pos + 3, "BTW"):
                    break

            # string literal (yarn)
            if raw_line[pos] in ('"', "“"):
                closing_quote = '"' if raw_line[pos] == '"' else "”"
                quote_end = raw_line.find(closing_quote, pos + 1)
                if quote_end == -1:
                    # unclosed string literal error
                    line_tokens.append(Token(T.ERROR, raw_line[pos:], line_index))
                    pos = line_length
                else:
                    raw_yarn = raw_line[pos : quote_end + 1]
                    line_tokens.append(Token(T.YARN_LIT, raw_yarn, line_index))
                    pos = quote_end + 1
                continue

            # match multi-word and punctuation keywords
            matched_keyword = None
            for keyword in SORTED_KEYWORDS:
                if raw_line[pos:].startswith(keyword):
                    end_pos = pos + len(keyword)
                    if is_keyword_boundary(raw_line, end_pos, keyword):
                        matched_keyword = keyword
                        break

            if matched_keyword:
                token_type = KEYWORDS[matched_keyword]
                line_tokens.append(Token(token_type, matched_keyword, line_index))
                pos += len(matched_keyword)
                continue

            # read next word chunk until delimiter
            start_pos = pos
            while pos < line_length and raw_line[pos] not in DELIMITERS and raw_line[pos] not in ('"', "“"):
                pos += 1
            word = raw_line[start_pos:pos]

            if not word:
                if pos < line_length and raw_line[pos] in DELIMITERS:
                    delim_char = raw_line[pos]
                    if delim_char in KEYWORDS:
                        line_tokens.append(Token(KEYWORDS[delim_char], delim_char, line_index))
                    pos += 1
                continue

            # classify word
            if word in KEYWORDS:
                line_tokens.append(Token(KEYWORDS[word], word, line_index))
            elif word in TYPE_NAMES:
                line_tokens.append(Token(T.TYPE, word, line_index))
            elif NUMBAR_PATTERN.match(word):
                line_tokens.append(Token(T.NUMBAR_LIT, word, line_index))
            elif NUMBR_PATTERN.match(word):
                line_tokens.append(Token(T.NUMBR_LIT, word, line_index))
            elif IDENTIFIER_PATTERN.match(word):
                line_tokens.append(Token(T.IDENTIFIER, word, line_index))
            else:
                line_tokens.append(Token(T.ERROR, word, line_index))

        # append newline for lines that produced tokens
        if line_tokens:
            line_tokens.append(Token(T.NEWLINE, "\n", line_index))
            tokens.extend(line_tokens)

    # append end-of-file token
    eof_line = len(lines) if lines else 1
    tokens.append(Token(T.EOF, "", eof_line))
    return tokens
