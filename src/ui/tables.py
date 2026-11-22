"""Results table with individually colored cells on Tk 8.6."""

import tkinter as tk
from tkinter import ttk

from ui.editor import set_scrollbar


class ResultsTable(tk.Frame):
    def __init__(self, parent, columns):
        super().__init__(parent)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.panes = tk.PanedWindow(self, orient="horizontal", bd=0, sashwidth=3,
                                    sashrelief="flat", opaqueresize=True)
        self.panes.grid(row=0, column=0, sticky="nsew")
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.scroll)
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.columns = []
        for index, (heading, width) in enumerate(columns):
            tree = ttk.Treeview(self.panes, columns=("value",), show="headings", takefocus=index == 0)
            tree.heading("value", text=heading, anchor="w")
            tree.column("value", width=width, minwidth=45, anchor="w")
            self.panes.add(tree, width=width, minsize=45, stretch="always", sticky="nsew")
            tree.bind("<<TreeviewSelect>>", self.sync_selection)
            tree.configure(yscrollcommand=lambda _first, _last, source=tree: self.sync_scroll(source))
            self.columns.append(tree)

    def apply_palette(self, palette):
        self.configure(bg=palette.surface)
        self.panes.configure(bg=palette.edge)
        for tree in self.columns:
            for role in ("ink", "keyword", "string", "number", "comment"):
                tree.tag_configure(role, foreground=getattr(palette, role))

    def extend(self, rows):
        for values, roles in rows:
            item = None
            for tree, value, role in zip(self.columns, values, roles):
                item = tree.insert("", "end", iid=item, values=(value,), tags=(role,))

    def clear(self):
        items = self.columns[0].get_children()
        for tree in self.columns:
            tree.delete(*items)

    def scroll(self, *args):
        first_column = self.columns[0]
        first_column.yview(*args)
        self.sync_scroll(first_column)

    def sync_scroll(self, source):
        first, last = source.yview()
        for tree in self.columns:
            if tree is not source and tree.yview()[0] != first:
                tree.yview_moveto(first)
        set_scrollbar(self.scrollbar, first, last)

    def sync_selection(self, event):
        source = event.widget
        selected = source.selection()
        focused = source.focus()
        for tree in self.columns:
            if tree is source:
                continue
            if tree.focus() != focused:
                tree.focus(focused)
            if tree.selection() != selected:
                tree.selection_set(selected)
