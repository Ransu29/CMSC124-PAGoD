#lightweight trace logger; prints to stderr so it never mixes with program output
import os
import sys

DEBUG = os.environ.get('LOLDEBUG', '0') == '1'


def set_debug(enabled: bool) -> None:
    global DEBUG
    DEBUG = enabled
    os.environ['LOLDEBUG'] = '1' if enabled else '0'


def log(stage: str, message: str, depth: int = 0) -> None:
    if not DEBUG:
        return
    print(f'[{stage:<8}] {" " * depth}{message}', file=sys.stderr)
