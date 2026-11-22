"""Run one editor snapshot in a child process and stream its results."""

import json
import os
from pathlib import Path
from queue import Empty, Full, Queue
import subprocess
import sys
from threading import Event, Thread
from time import monotonic

from core.errors import LexicalError, LolRuntimeError, SemanticError, SyntaxError
from core.tokens import KEYWORDS, T
from ui.controller import InterpreterController


TOKEN_COLORS = {
    **{kind: "keyword" for word, kind in KEYWORDS.items() if word[0].isalnum()},
    T.TYPE: "keyword",
    T.YARN_LIT: "string",
    T.STRING_DELIMITER: "string",
    T.NUMBR_LIT: "number",
    T.NUMBAR_LIT: "number",
    T.BTW: "comment",
    T.OBTW: "comment",
    T.TLDR: "comment",
    T.COMMENT_TEXT: "comment",
}

VALUE_COLORS = {
    "YARN": "string",
    "NUMBR": "number",
    "NUMBAR": "number",
    "TROOF": "keyword",
}


class ProgramRun:
    """Own the subprocess and keep blocking pipe operations off the Tk thread."""

    def __init__(self, source):
        self.events = Queue(maxsize=128)
        self.replies = Queue()
        self.cancelled = Event()
        self.process = subprocess.Popen(
            [sys.executable, "-B", "-m", "ui.runner"],
            cwd=Path(__file__).resolve().parents[1],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            encoding="utf-8",
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        Thread(target=self._exchange, args=(source,), daemon=True).start()

    def _enqueue(self, message):
        while not self.cancelled.is_set():
            try:
                self.events.put(message, timeout=0.1)
                return
            except Full:
                continue

    def _exchange(self, source):
        try:
            with self.process.stdin as stdin, self.process.stdout as stdout:
                _write(stdin, source)
                for line in stdout:
                    if self.cancelled.is_set():
                        break
                    kind, value = json.loads(line)
                    self._enqueue((kind, value))
                    if kind == "input":
                        reply = self._wait_for_reply()
                        if reply is None:
                            break
                        _write(stdin, reply)
        except (OSError, ValueError) as error:
            self._enqueue(("output", f"\n[Execution Error] {error}\n"))
        finally:
            self._enqueue(("eof", None))

    def _wait_for_reply(self):
        while not self.cancelled.is_set() and self.process.poll() is None:
            try:
                return self.replies.get(timeout=0.1)
            except Empty:
                continue
        return None

    def stop(self):
        self.cancelled.set()
        self.replies.put(None)
        try:
            self.process.kill()
        except ProcessLookupError:
            pass


def _write(stream, value):
    stream.write(json.dumps(value) + "\n")
    stream.flush()


def _worker():
    pending_symbols = None
    last_symbol_update = 0.0

    def send(kind, value=None):
        _write(sys.stdout, (kind, value))

    def send_output(value):
        for start in range(0, len(value), 4096):
            send("output", value[start:start + 4096])

    def send_rows(kind, rows):
        batch = []
        for row in rows:
            batch.append(row)
            if len(batch) == 64:
                send(kind, batch)
                batch = []
        if batch:
            send(kind, batch)

    def request_input():
        flush_symbols()
        send("input")
        return json.loads(sys.stdin.readline())

    def report_error(error):
        phases = {
            LexicalError: "Lexical Error",
            SyntaxError: "Syntax Error",
            SemanticError: "Semantic Error",
            LolRuntimeError: "Runtime Error",
        }
        phase = phases.get(type(error), "Error")
        location = f"Line {error.line}: " if error.line > 0 else ""
        send_output(f"\n[{phase}] {location}{error.message}\n")

    def send_tokens(tokens):
        rows = (((tok.value, tok.classification), (TOKEN_COLORS.get(tok.type, "ink"), "ink"))
                for tok in tokens if tok.type not in (T.NEWLINE, T.EOF))
        send_rows("lexemes", rows)

    def send_symbols(symbols):
        nonlocal pending_symbols
        pending_symbols = symbols
        if monotonic() - last_symbol_update >= 0.05:
            flush_symbols()

    def flush_symbols():
        nonlocal pending_symbols, last_symbol_update
        if pending_symbols is None:
            return

        def rows():
            for name, value in pending_symbols.items():
                if value.type_name == "NOOB":
                    display = "None"
                elif value.type_name == "TROOF":
                    display = "WIN" if value.value else "FAIL"
                elif value.type_name == "YARN":
                    display = f'"{value.value}"'
                else:
                    display = str(value.value)
                role = VALUE_COLORS.get(value.type_name, "ink")
                yield (name, value.type_name, display), ("ink", "keyword", role)

        send("clear_symbols")
        send_rows("symbols", rows())
        pending_symbols = None
        last_symbol_update = monotonic()

    try:
        source = json.loads(sys.stdin.readline())
        InterpreterController(on_tokens_updated=send_tokens, on_symbols_updated=send_symbols,
                              on_stdout=send_output, request_stdin=request_input,
                              on_error=report_error).execute(source)
        flush_symbols()
    except BrokenPipeError:
        return
    except Exception as error:
        send_output(f"\n[Execution Error] {error}\n")


if __name__ == "__main__":
    _worker()
