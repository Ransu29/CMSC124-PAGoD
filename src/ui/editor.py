"""Source editing and presentation for a single LOLCODE document."""

import re
import tkinter as tk
from tkinter import ttk

from core.tokens import KEYWORDS, TYPE_NAMES


MONO = ("Consolas", 10)


def set_scrollbar(bar, first, last):
    bar.set(first, last)
    if float(first) <= 0 and float(last) >= 1:
        bar.grid_remove()
    else:
        bar.grid()

_keywords = sorted((word for word in KEYWORDS.keys() | TYPE_NAMES if word[0].isalnum()),
                   key=len, reverse=True)
_patterns = {
    "comment": r'(?<!\w)BTW\b[^\n]*|(?<!\w)OBTW\b[\s\S]*?(?:\bTLDR\b|\Z)',
    "string": r'"[^"\n]*(?:"|$)|“[^”\n]*(?:”|$)',
    "number": r'(?<!\w)-?\d+(?:\.\d+)?(?!\w)',
    "keyword": r'(?<!\w)(?:' + '|'.join(map(re.escape, _keywords)) + r')(?!\w)',
}
_syntax = re.compile('|'.join(f'(?P<{name}>{pattern})' for name, pattern in _patterns.items()),
                     re.MULTILINE)


class SourceEditor(tk.Frame):
    def __init__(self, parent, content, changed, palette):
        super().__init__(parent)
        self.changed = changed
        self.redraw_job = self.color_job = None
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        self.gutter = tk.Canvas(self, width=38, highlightthickness=0)
        self.gutter.grid(row=0, column=0, sticky="ns")
        self.text = tk.Text(self, wrap="none", undo=True, font=MONO,
                            padx=6, pady=5, spacing1=1, spacing3=1, borderwidth=0,
                            highlightthickness=0, width=1, height=1)
        self.text.grid(row=0, column=1, sticky="nsew")
        self.vertical = ttk.Scrollbar(self, orient="vertical", command=self.text.yview)
        self.vertical.grid(row=0, column=2, sticky="ns")
        horizontal = ttk.Scrollbar(self, orient="horizontal", command=self.text.xview)
        horizontal.grid(row=1, column=1, sticky="ew")
        self.text.configure(yscrollcommand=self._scrolled,
                            xscrollcommand=lambda a, b: set_scrollbar(horizontal, a, b))
        self.apply_palette(palette)
        self.text.tag_raise("sel")
        self.text.insert("1.0", content)
        self.text.mark_set("insert", "1.0")
        self.text.edit_reset()
        self.text.edit_modified(False)
        self.text.bind("<<Modified>>", self._modified)
        for event in ("<Configure>", "<KeyRelease>", "<ButtonRelease-1>", "<FocusIn>"):
            self.text.bind(event, self._queue_redraw)
        self.text.bind("<Tab>", self._indent)
        self.text.bind("<Shift-Tab>", self._unindent)
        self.text.bind("<Control-y>", self._redo)
        self.text.bind("<Control-Shift-Z>", self._redo)
        self._highlight()

    def apply_palette(self, palette):
        self.palette = palette
        self.configure(bg=palette.surface)
        self.gutter.configure(bg=palette.surface)
        self.text.configure(**palette.text_options())
        self.text.tag_configure("current_line", background=palette.current_line)
        for name in _patterns:
            self.text.tag_configure(name, foreground=getattr(palette, name))
        self._queue_redraw()

    def _modified(self, _event):
        if self.text.edit_modified():
            self.text.edit_modified(False)
            self.changed()
            if self.color_job:
                self.after_cancel(self.color_job)
            self.color_job = self.after(75, self._highlight)
            self._queue_redraw()

    def _highlight(self):
        self.color_job = None
        source = self.text.get("1.0", "end-1c")
        for name in _patterns:
            self.text.tag_remove(name, "1.0", "end")
        line, offset = 1, 0
        for match in _syntax.finditer(source):
            line += source.count("\n", offset, match.start())
            start_col = match.start() - source.rfind("\n", 0, match.start()) - 1
            start = f"{line}.{start_col}"
            line += source.count("\n", match.start(), match.end())
            end_col = match.end() - source.rfind("\n", 0, match.end()) - 1
            self.text.tag_add(match.lastgroup, start, f"{line}.{end_col}")
            offset = match.end()

    def _scrolled(self, first, last):
        set_scrollbar(self.vertical, first, last)
        self._queue_redraw()

    def _queue_redraw(self, _event=None):
        if self.redraw_job is None:
            self.redraw_job = self.after_idle(self._redraw)

    def _redraw(self):
        self.redraw_job = None
        self.gutter.delete("all")
        first = int(self.text.index("@0,0").split(".")[0])
        last = int(self.text.index("end-1c").split(".")[0])
        width = max(38, 16 + len(str(last)) * 10)
        self.gutter.configure(width=width)
        current = int(self.text.index("insert").split(".")[0])
        self.text.tag_remove("current_line", "1.0", "end")
        self.text.tag_add("current_line", f"{current}.0", f"{current}.end+1c")
        for line in range(first, last + 1):
            info = self.text.dlineinfo(f"{line}.0")
            if info is None:
                break
            y, height = info[1], info[3]
            if line == current:
                self.gutter.create_rectangle(0, y, width, y + height, outline="",
                                             fill=self.palette.current_line)
            self.gutter.create_text(width - 7, y + height / 2, text=str(line),
                                    anchor="e", fill=self.palette.muted, font=MONO)

    def _indent(self, _event):
        self.text.insert("insert", "    ")
        return "break"

    def _unindent(self, _event):
        line = self.text.get("insert linestart", "insert lineend")
        count = min(4, len(line) - len(line.lstrip(" ")))
        self.text.delete("insert linestart", f"insert linestart +{count}c")
        return "break"

    def _redo(self, _event):
        self.text.event_generate("<<Redo>>")
        return "break"

    def destroy(self):
        for job in (self.redraw_job, self.color_job):
            if job:
                self.after_cancel(job)
        super().destroy()
