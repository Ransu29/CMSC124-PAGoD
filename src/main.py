from pathlib import Path
import lexer

# Gets the root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Builds the path
file_path = PROJECT_ROOT / "examples" / "hello.lol"

with open(file_path, "r", encoding="utf-8") as file:
    content = file.read()

print(content)
print("\nTokenized: ")
tokens = lexer.tokenize(content)
print(tokens)