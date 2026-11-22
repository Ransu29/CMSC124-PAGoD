"""Editable input at the end of a read-only program transcript."""

import tkinter as tk


INPUT_START = "input_start"


class OutputConsole(tk.Text):
    def __init__(self, parent, **options):
        super().__init__(parent, **options)
        # Tk's keyboard, clipboard, and mouse bindings all call the widget command.
        self._text_command = self._w + "_text"
        edit_filter = self.register(self._filter_edit)
        self.tk.call("rename", self._w, self._text_command)
        self.tk.call("proc", self._w, "args", f"""
            if {{[lindex $args 0] in {{insert delete replace}} && [llength $args] > 1}} {{
                set args [{edit_filter} {{*}}$args]
                if {{![llength $args]}} {{ return }}
            }}
            tailcall {self._text_command} {{*}}$args
        """)

    def _filter_edit(self, command, *args):
        if INPUT_START not in self.mark_names():
            return ()

        try:
            if command == "delete":
                editable = self._editable_ranges(args)
                return (command, *editable) if editable else ()
            if self.compare(args[0], ">=", INPUT_START):
                return (command, *args)
            if command == "replace" and self.compare(args[1], ">", INPUT_START):
                return (command, INPUT_START, *args[1:])
        except tk.TclError:
            # Paste can try to delete the selection when there isn't one.
            pass
        return ()

    def _editable_ranges(self, indices):
        editable = []
        for first, last in zip(indices[::2], indices[1::2]):
            if self.compare(last, ">", INPUT_START):
                start = INPUT_START if self.compare(first, "<", INPUT_START) else first
                editable.extend((start, last))
        if len(indices) % 2 and self.compare(indices[-1], ">=", INPUT_START):
            editable.append(indices[-1])
        return editable

    def clear_transcript(self):
        self.tk.call(self._text_command, "delete", "1.0", "end")

    def append_transcript(self, text):
        if INPUT_START not in self.mark_names():
            self.tk.call(self._text_command, "insert", "end", text)
            return
        # Keep program messages outside the pending user input.
        self.mark_gravity(INPUT_START, "right")
        try:
            self.tk.call(self._text_command, "insert", INPUT_START, text)
        finally:
            self.mark_gravity(INPUT_START, "left")

    def destroy(self):
        super().destroy()
        self.tk.call("rename", self._w, "")
