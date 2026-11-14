# reference: lolcode 1.2 specification - https://github.com/justinmeza/lolcode-spec/blob/master/v1.2/lolcode-spec-v1.2.md
# reference: uplb cmsc 124 project specification

import unittest
import sys
from pathlib import Path

# ensure src is in python search path
base_dir = Path(__file__).resolve().parent.parent
src_dir = base_dir / "src"
cases_dir = base_dir / "tests" / "test_cases"
examples_dir = base_dir / "examples"

if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from tokens import T
from lexer import tokenize

def read_source_file(file_path: Path) -> str:
    # read lolcode file using utf-8 encoding
    return file_path.read_text(encoding="utf-8")

class TestLexer(unittest.TestCase):

    def test_empty_source(self):
        source_code = read_source_file(cases_dir / "empty.lol")
        tokens = tokenize(source_code)
        self.assertEqual(len(tokens), 1)
        self.assertEqual(tokens[0].type, T.EOF)

    def test_single_line_comments(self):
        source_code = read_source_file(cases_dir / "comments_single.lol")
        tokens = tokenize(source_code)
        token_types = [tok.type for tok in tokens]

        self.assertNotIn(T.BTW, token_types)
        self.assertNotIn(T.COMMENT_TEXT, token_types)
        self.assertEqual(token_types[0], T.HAI)
        self.assertEqual(token_types[2], T.VISIBLE)
        self.assertEqual(token_types[3], T.STRING_DELIMITER)
        self.assertEqual(token_types[4], T.YARN_LIT)
        self.assertEqual(token_types[-3], T.KTHXBYE)
        self.assertEqual(token_types[-1], T.EOF)

    def test_multi_line_comments(self):
        source_code = read_source_file(cases_dir / "comments_multi.lol")
        tokens = tokenize(source_code)
        clean_types = [tok.type for tok in tokens if tok.type != T.NEWLINE]
        self.assertEqual(clean_types, [T.HAI, T.KTHXBYE, T.EOF])

    def test_literals(self):
        source_code = read_source_file(cases_dir / "literals.lol")
        tokens = tokenize(source_code)
        values_by_type = {tok.type: [] for tok in tokens}
        for tok in tokens:
            values_by_type[tok.type].append(tok.value)

        self.assertIn("42", values_by_type[T.NUMBR_LIT])
        self.assertIn("-99", values_by_type[T.NUMBR_LIT])
        self.assertIn("3.14", values_by_type[T.NUMBAR_LIT])
        self.assertIn("-0.5", values_by_type[T.NUMBAR_LIT])
        self.assertIn("Spaces          between", values_by_type[T.YARN_LIT])
        self.assertIn("WIN", values_by_type[T.WIN])
        self.assertIn("FAIL", values_by_type[T.FAIL])

    def test_keywords_and_types(self):
        source_code = read_source_file(cases_dir / "keywords.lol")
        tokens = tokenize(source_code)
        token_types = [tok.type for tok in tokens]

        expected_sequence = [
            T.HAI, T.NEWLINE,
            T.ADD, T.SUB, T.MUL, T.DIV, T.NEWLINE,
            T.EQUAL, T.NOT_EQUAL, T.AND, T.OR, T.XOR, T.NEWLINE,
            T.ALL, T.ANY, T.IF, T.THEN, T.ELSE, T.IS_NOW_A, T.NEWLINE,
            T.LOOP_START, T.LOOP_END, T.FUNCTION_START, T.FUNCTION_END, T.RETURN, T.FUNCTION_CALL, T.NEWLINE,
            T.TYPE, T.TYPE, T.TYPE, T.TYPE, T.TYPE, T.NEWLINE,
            T.KTHXBYE, T.NEWLINE,
            T.EOF
        ]
        self.assertEqual(token_types, expected_sequence)

    def test_delimiters(self):
        source_code = read_source_file(cases_dir / "delimiters.lol")
        tokens = tokenize(source_code)
        meaningful_types = [tok.type for tok in tokens if tok.type not in (T.NEWLINE, T.EOF, T.HAI, T.KTHXBYE)]

        # line 1: VISIBLE "msg" + "extra" !
        # line 2: VISIBLE "part1", VISIBLE "part2"
        self.assertIn(T.PLUS, meaningful_types)
        self.assertIn(T.BANG, meaningful_types)
        self.assertIn(T.COMMA, meaningful_types)

    def test_line_numbers(self):
        source_code = read_source_file(cases_dir / "line_numbers.lol")
        tokens = tokenize(source_code)
        line_lookup = {tok.value: tok.line for tok in tokens}

        self.assertEqual(line_lookup["HAI"], 1)
        self.assertEqual(line_lookup["VISIBLE"], 3)
        self.assertEqual(line_lookup["1"], 3)
        self.assertEqual(line_lookup["KTHXBYE"], 5)

    def test_error_unclosed_string(self):
        source_code = read_source_file(cases_dir / "error_unclosed_string.lol")
        tokens = tokenize(source_code)
        error_tokens = [tok for tok in tokens if tok.type == T.ERROR]
        self.assertEqual(len(error_tokens), 1)

    def test_error_invalid_obtw_placement(self):
        source_code = read_source_file(cases_dir / "error_invalid_obtw.lol")
        tokens = tokenize(source_code)
        error_tokens = [tok for tok in tokens if tok.type == T.ERROR]
        self.assertEqual(len(error_tokens), 1)

    def test_example_hello(self):
        source_code = read_source_file(examples_dir / "hello.lol")
        tokens = tokenize(source_code)
        token_types = [tok.type for tok in tokens if tok.type != T.NEWLINE]
        self.assertEqual(token_types, [T.HAI, T.VISIBLE, T.STRING_DELIMITER, T.YARN_LIT, T.STRING_DELIMITER, T.KTHXBYE, T.EOF])

    def test_example_variables(self):
        source_code = read_source_file(examples_dir / "variables.lol")
        tokens = tokenize(source_code)
        error_tokens = [tok for tok in tokens if tok.type == T.ERROR]
        self.assertEqual(len(error_tokens), 0)
        identifiers = [tok.value for tok in tokens if tok.type == T.IDENTIFIER]
        self.assertIn("name", identifiers)
        self.assertIn("age", identifiers)
        self.assertIn("isCat", identifiers)

    def test_example_conditionals(self):
        source_code = read_source_file(examples_dir / "conditionals.lol")
        tokens = tokenize(source_code)
        error_tokens = [tok for tok in tokens if tok.type == T.ERROR]
        self.assertEqual(len(error_tokens), 0)
        types = [tok.type for tok in tokens]
        self.assertIn(T.IF, types)
        self.assertIn(T.THEN, types)
        self.assertIn(T.ELIF, types)
        self.assertIn(T.ELSE, types)
        self.assertIn(T.ENDIF, types)

    def test_example_loops(self):
        source_code = read_source_file(examples_dir / "loops.lol")
        tokens = tokenize(source_code)
        error_tokens = [tok for tok in tokens if tok.type == T.ERROR]
        self.assertEqual(len(error_tokens), 0)
        types = [tok.type for tok in tokens]
        self.assertIn(T.LOOP_START, types)
        self.assertIn(T.INC, types)
        self.assertIn(T.YR, types)
        self.assertIn(T.UNTIL, types)
        self.assertIn(T.LOOP_END, types)

if __name__ == "__main__":
    unittest.main()
