from pathlib import Path
import lexer
from tokens import T

# Gets the root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Change this to whichever file in examples/ you want to analyze
TARGET_FILE = "hello.lol"


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
    file_path = PROJECT_ROOT / "examples" / TARGET_FILE

    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()

    print(f"\n--- Source Code ({TARGET_FILE}) ---")
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


if __name__ == "__main__":
    main()
