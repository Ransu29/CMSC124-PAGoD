# unit tests for src/controller.py and its integration with src/gui.py

import importlib
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock

base_dir = Path(__file__).resolve().parent.parent
src_dir = base_dir / "src"
examples_dir = base_dir / "examples"

if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from core.errors import LexicalError, LolRuntimeError, SemanticError, SyntaxError
from core.tokens import T
from semantics.lol_types import NOOB_VAL, LolValue
from ui.controller import InterpreterController, format_lol_value


class TestFormatLolValue(unittest.TestCase):
    def test_formats_all_types(self):
        self.assertEqual(format_lol_value(NOOB_VAL), "NOOB")
        self.assertEqual(format_lol_value(LolValue("TROOF", True)), "WIN (TROOF)")
        self.assertEqual(format_lol_value(LolValue("TROOF", False)), "FAIL (TROOF)")
        self.assertEqual(format_lol_value(LolValue("NUMBR", 42)), "42 (NUMBR)")
        self.assertEqual(format_lol_value(LolValue("NUMBAR", 3.14)), "3.14 (NUMBAR)")
        self.assertEqual(format_lol_value(LolValue("YARN", "hi")), '"hi" (YARN)')


class TestInterpreterController(unittest.TestCase):
    def _run(self, code: str, inputs: list[str] | None = None):
        tokens_seen = []
        symbol_snapshots = []
        outputs = []
        errors = []
        input_iter = iter(inputs or [])

        ctrl = InterpreterController(
            on_tokens_updated=tokens_seen.extend,
            on_symbols_updated=lambda snap: symbol_snapshots.append(snap),
            on_stdout=outputs.append,
            request_stdin=lambda: next(input_iter, ""),
            on_error=errors.append,
        )
        ok = ctrl.execute(code)
        return ok, tokens_seen, symbol_snapshots, "".join(outputs), errors

    def test_executes_program_with_io_and_symbols(self):
        code = (
            "HAI\n"
            "WAZZUP\n"
            "    I HAS A name\n"
            "    I HAS A age ITZ 20\n"
            "BUHBYE\n"
            'VISIBLE "Name: "!\n'
            "GIMMEH name\n"
            'VISIBLE SMOOSH "Hi " AN name AN " (" AN age AN ")"\n'
            "KTHXBYE\n"
        )
        ok, tokens, snapshots, stdout, errors = self._run(code, inputs=["Alice"])
        self.assertTrue(ok)
        self.assertEqual(errors, [])
        self.assertEqual(stdout, "Name: Hi Alice (20)\n")
        self.assertTrue(any(t.type == T.HAI for t in tokens))
        final_symbols = snapshots[-1]
        self.assertEqual(final_symbols["name"], LolValue("YARN", "Alice"))
        self.assertEqual(final_symbols["age"], LolValue("NUMBR", 20))

    def test_reports_lexical_syntax_semantic_and_runtime_errors(self):
        # lexical error
        ok, _, _, _, errors = self._run("HAI\n@\nKTHXBYE")
        self.assertFalse(ok)
        self.assertTrue(any(isinstance(e, LexicalError) and e.line == 2 for e in errors))

        # syntax error
        ok, _, _, _, errors = self._run('VISIBLE "no hai"')
        self.assertFalse(ok)
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], SyntaxError)
        self.assertEqual(errors[0].line, 1)

        # semantic error
        ok, _, _, _, errors = self._run("HAI\nVISIBLE missing_var\nKTHXBYE")
        self.assertFalse(ok)
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], SemanticError)
        self.assertEqual(errors[0].line, 2)

        # runtime error
        ok, _, _, _, errors = self._run("HAI\nVISIBLE QUOSHUNT OF 10 AN 0\nKTHXBYE")
        self.assertFalse(ok)
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], LolRuntimeError)
        self.assertEqual(errors[0].line, 2)

    def test_runs_all_valid_example_files(self):
        error_fixtures = {
            "errors.lol",
            "present_arity.lol",
            "present_dup.lol",
            "present_undeclared.lol",
        }
        for path in sorted(examples_dir.glob("*.lol")):
            if path.name in error_fixtures:
                continue
            code = path.read_text(encoding="utf-8")
            ok, _, snapshots, _, errors = self._run(code, inputs=["Tester"])
            self.assertTrue(ok, f"{path.name} failed with errors: {errors}")
            self.assertEqual(errors, [], f"{path.name} reported errors: {errors}")
            self.assertTrue(len(snapshots) >= 1, f"{path.name} produced no symbol table snapshot")


class _FakeTextbox:
    def __init__(self, initial: str = ""):
        self.content = initial

    def get(self, *_args):
        return self.content

    def delete(self, *_args):
        self.content = ""

    def insert(self, _index, text: str):
        self.content += text

    def see(self, *_args):
        pass


class _FakeTreeview:
    def __init__(self):
        self._items = {}
        self._next_id = 0

    @property
    def rows(self):
        return list(self._items.values())

    def get_children(self):
        return list(self._items.keys())

    def delete(self, item):
        self._items.pop(item, None)

    def insert(self, _parent, _index, values=()):
        item_id = f"I{self._next_id}"
        self._next_id += 1
        self._items[item_id] = values


class TestGuiIntegration(unittest.TestCase):
    def _load_gui_module_headless(self, dialog_reply: str | None = "PagodUser"):
        # stub tkinter/customtkinter so gui.py can be tested without a display server
        fake_tk = types.ModuleType("tkinter")
        fake_fd = types.ModuleType("tkinter.filedialog")
        fake_ttk = types.ModuleType("tkinter.ttk")
        fake_ctk = types.ModuleType("customtkinter")

        class _FakeCTk:
            pass

        class _FakeInputDialog:
            def __init__(self, **_kwargs):
                pass

            def get_input(self):
                return dialog_reply

        fake_ctk.CTk = _FakeCTk
        fake_ctk.CTkInputDialog = _FakeInputDialog
        fake_tk.filedialog = fake_fd
        fake_tk.ttk = fake_ttk

        saved = {
            name: sys.modules.get(name)
            for name in ("tkinter", "tkinter.filedialog", "tkinter.ttk", "customtkinter", "ui.gui", "gui")
        }
        sys.modules["tkinter"] = fake_tk
        sys.modules["tkinter.filedialog"] = fake_fd
        sys.modules["tkinter.ttk"] = fake_ttk
        sys.modules["customtkinter"] = fake_ctk
        sys.modules.pop("ui.gui", None)
        sys.modules.pop("gui", None)

        gui_mod = importlib.import_module("ui.gui")
        return gui_mod, saved

    def _restore_modules(self, saved):
        for name, mod in saved.items():
            if mod is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = mod

    def test_gui_execute_code_populates_tokens_symbols_and_console(self):
        gui_mod, saved = self._load_gui_module_headless(dialog_reply="Garfield")
        try:
            app = gui_mod.InterpreterApp.__new__(gui_mod.InterpreterApp)
            app.editor = _FakeTextbox(
                "HAI\n"
                "WAZZUP\n"
                "    I HAS A name\n"
                "    I HAS A count ITZ 3\n"
                "BUHBYE\n"
                'VISIBLE "Who? "!\n'
                "GIMMEH name\n"
                'VISIBLE SMOOSH "Hello " AN name\n'
                "KTHXBYE\n"
            )
            app.tokens_table = _FakeTreeview()
            app.symbol_table = _FakeTreeview()
            app.console = _FakeTextbox()
            app.update_idletasks = MagicMock()

            app.execute_code()

            self.assertEqual(app.console.content, "Who? Garfield\nHello Garfield\n")
            self.assertTrue(len(app.tokens_table.rows) > 0)
            self.assertIn(("name", '"Garfield" (YARN)'), app.symbol_table.rows)
            self.assertIn(("count", "3 (NUMBR)"), app.symbol_table.rows)
            self.assertIn(("IT", "NOOB"), app.symbol_table.rows)
        finally:
            self._restore_modules(saved)

    def test_gui_execute_code_reports_errors_and_empty_editor(self):
        gui_mod, saved = self._load_gui_module_headless()
        try:
            app = gui_mod.InterpreterApp.__new__(gui_mod.InterpreterApp)
            app.tokens_table = _FakeTreeview()
            app.symbol_table = _FakeTreeview()
            app.console = _FakeTextbox()
            app.update_idletasks = MagicMock()

            # empty editor case
            app.editor = _FakeTextbox("   \n")
            app.execute_code()
            self.assertEqual(app.console.content, "no code to execute\n")

            # runtime error case clears old symbol rows and displays error line
            app.symbol_table.insert("", "end", values=("stale", "1 (NUMBR)"))
            app.editor = _FakeTextbox("HAI\nVISIBLE QUOSHUNT OF 5 AN 0\nKTHXBYE\n")
            app.execute_code()
            self.assertIn("[Runtime Error] Line 2: Division by zero", app.console.content)
        finally:
            self._restore_modules(saved)


if __name__ == "__main__":
    unittest.main()
