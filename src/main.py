import sys
from pathlib import Path

# ensure src directory is on search path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.errors import LolRuntimeError, SemanticError, SyntaxError
from core.tokens import T
from frontend import lexer, parser
from runtime.interpreter import Interpreter
from semantics.semantic_analyzer import SemanticAnalyzer

# Gets the root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# change to file in examples/ to analyze
TARGET_FILE = "conditionals.lol"


def print_tokens_table(tokens):
    # filter out internal structural tokens (newlines and EOF) from the table
    display_tokens = [t for t in tokens if t.type not in (T.NEWLINE, T.EOF)]

    if not display_tokens:
        print("No tokens found.")
        return

    # calculate column widths
    max_lexeme_len = max(len("Lexeme"), max(len(t.value) for t in display_tokens))
    max_class_len = max(len("Classification"), max(len(t.classification) for t in display_tokens))

    col1_width = max(max_lexeme_len + 2, 20)
    col2_width = max(max_class_len + 2, 26)

    border = f"+{'-' * col1_width}+{'-' * col2_width}+"
    header = f"| {'Lexeme':<{col1_width - 1}}| {'Classification':<{col2_width - 1}}|"

    print(border)
    print(header)
    print(border)
    for t in display_tokens:
        print(f"| {t.value:<{col1_width - 1}}| {t.classification:<{col2_width - 1}}|")
    print(border)


def main():
    if len(sys.argv) > 1:
        arg_path = Path(sys.argv[1])
        if arg_path.exists():
            file_path = arg_path
        elif (PROJECT_ROOT / arg_path).exists():
            file_path = PROJECT_ROOT / arg_path
        else:
            file_path = arg_path
        target_name = file_path.name
    else:
        file_path = PROJECT_ROOT / "examples" / TARGET_FILE
        target_name = TARGET_FILE

    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()

    print(f"\n--- Source Code ({target_name}) ---")
    print(content)

    tokens = lexer.tokenize(content)

    print("\n--- Lexemes & Classification ---")
    print_tokens_table(tokens)

    # check for lexical errors
    errors = [t for t in tokens if t.type == T.ERROR]
    if errors:
        print(f"\n[!] {len(errors)} Lexical Error(s) Found:")
        for err in errors:
            print(f"    Line {err.line}: Unexpected or invalid lexeme '{err.value}'")
    else:
        print("\nLexical analysis completed with 0 errors.")

        # run syntax analysis, semantic analysis, and interpretation
        try:
            program = parser.parse(tokens)
            print("\n--- Parse Tree (Tuples) ---")
            for item in program.to_tuples():
                print(f"    {item}")
            print("\n--- AST Representation ---")
            print(f"    {program}")

            SemanticAnalyzer(program).analyze()
            print("\nSemantic analysis completed with 0 errors.")

            print("\n--- Program Output ---")
            final_env = Interpreter(program).run()

            print("\n--- Symbol Table ---")
            for name, lol_val in final_env.snapshot().items():
                print(f"    {name}: ({lol_val.type_name}) {lol_val.value!r}")
        except SyntaxError as e:
            print(f"\n[!] Syntax Error: {e}")
        except SemanticError as e:
            print(f"\n[!] Semantic Error: {e}")
        except LolRuntimeError as e:
            print(f"\n[!] Runtime Error: {e}")


if __name__ == "__main__":
    main()
