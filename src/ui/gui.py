"""Desktop workspace for editing and running LOLCODE programs."""

import os
from queue import Empty
from subprocess import TimeoutExpired
from time import monotonic
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk
from tkinter_icons import MaterialIcon

from ui.editor import MONO, SourceEditor, set_scrollbar
from ui.runner import ProgramRun
from ui.tables import ResultsTable
from ui.tabs import FileTabStrip
from ui.theme import PALETTES, load_theme, preferences_path, save_theme


UI_FONT = ("Segoe UI", 9)
FILE_GLYPHS = {
    "New": "file-plus-outline",
    "Open": "folder-open-outline",
    "Save": "content-save-outline",
    "Save As": "content-save-edit-outline",
}


def tooltip(widget, text):
    """Show the action/shortcut or full document path after a short hover."""
    window = None
    timer = None

    def show():
        nonlocal window, timer
        timer = None
        window = tk.Toplevel(widget)
        window.wm_overrideredirect(True)
        window.geometry(f"+{widget.winfo_rootx() + 12}+{widget.winfo_rooty() + widget.winfo_height()}")
        content = {"textvariable": text} if isinstance(text, tk.Variable) else {"text": text}
        ttk.Label(window, style="Hint.TLabel", **content).pack()

    def hide(_event):
        nonlocal timer, window
        if timer:
            widget.after_cancel(timer)
            timer = None
        if window:
            window.destroy()
            window = None

    def schedule(event):
        nonlocal timer
        hide(event)
        timer = widget.after(450, show)

    widget.bind("<Enter>", schedule, add="+")
    widget.bind("<ButtonRelease-1>", schedule, add="+")
    for event in ("<Leave>", "<ButtonPress>", "<Destroy>"):
        widget.bind(event, hide, add="+")


def flat_button(parent, command, **options):
    return tk.Button(parent, command=command, relief="flat", overrelief="flat", bd=0,
                     highlightthickness=0, cursor="hand2", font=UI_FONT, **options)


class InterpreterApp(ctk.CTk):
    def __init__(self):
        self.preferences_path = preferences_path()
        self.mode = load_theme(self.preferences_path)
        self.palette = PALETTES[self.mode]
        ctk.set_appearance_mode(self.mode)
        super().__init__()
        self.title("LOLTERPRETER - CMSC 124")
        self.geometry("1200x700")
        self.tabs = []
        self.active_tab_id = None
        self.next_tab_id = self.untitled_counter = 1
        self.icons = {}
        self.run = self.run_job = self.input_dialog = None
        self.input_label = None
        self.run_eof = False
        self.style = ttk.Style(self)
        self.style.theme_use("clam")

        self.workspace = tk.Frame(self)
        self.workspace.pack(fill="both", expand=True)
        self.create_toolbar(self.workspace)
        self.split = tk.PanedWindow(self.workspace, orient="horizontal", bd=0,
                                    sashwidth=5, sashrelief="flat", opaqueresize=True)
        self.split.pack(side="left", fill="both", expand=True)
        self.editor_frame = tk.Frame(self.split)
        self.results_frame = tk.Frame(self.split)
        self.split.add(self.editor_frame, width=690, minsize=220, stretch="always")
        self.split.add(self.results_frame, width=460, stretch="always")
        self.create_editor_panel()
        self.create_results_panel()
        self.create_new_tab()
        self.apply_palette()
        self.update_idletasks()
        min_results = self.result_header.winfo_reqwidth() + 4
        self.split.paneconfigure(self.results_frame, minsize=min_results)
        self.minsize(220 + min_results + self.toolbar_frame.winfo_reqwidth() + 10, 310)

        for shortcut, action in (("<Control-n>", self.new_file), ("<Control-o>", self.open_file),
                                 ("<Control-s>", self.save_file), ("<Control-Shift-S>", self.save_as_file)):
            self.bind(shortcut, action)

    def icon(self, glyph, color):
        key = (glyph, color)
        if key not in self.icons:
            self.icons[key] = MaterialIcon(glyph, size=18, color=color)
        return self.icons[key].image

    def create_toolbar(self, parent):
        self.toolbar_frame = tk.Frame(parent)
        self.toolbar_frame.pack(side="left", fill="y", padx=(0, 1))
        self.file_buttons = {}
        actions = (
            ("New", "Ctrl+N", self.new_file),
            ("Open", "Ctrl+O", self.open_file),
            ("Save", "Ctrl+S", self.save_file),
            ("Save As", "Ctrl+Shift+S", self.save_as_file),
        )
        for name, shortcut, action in actions:
            button = flat_button(self.toolbar_frame, action, image=self.icon(FILE_GLYPHS[name], self.palette.muted),
                                 width=38, height=34, padx=0, pady=0)
            button.pack()
            tooltip(button, f"{name} ({shortcut})")
            self.file_buttons[name] = button
        self.theme_button_border = tk.Frame(self.toolbar_frame)
        self.theme_button_border.pack()
        glyph = "white-balance-sunny" if self.mode == "dark" else "weather-night"
        self.theme_button = flat_button(self.theme_button_border, self.toggle_theme,
                                        image=self.icon(glyph, self.palette.muted),
                                        width=34, height=30, padx=0, pady=0, takefocus=True)
        self.theme_button.pack(padx=2, pady=2)
        self.theme_hint = tk.StringVar(self)
        tooltip(self.theme_button, self.theme_hint)
        self.theme_button.bind("<Return>", self.toggle_theme)
        self.theme_button.bind("<space>", self.toggle_theme)
        self.theme_button.bind("<FocusIn>", lambda _event: self.style_theme_focus(True))
        self.theme_button.bind("<FocusOut>", lambda _event: self.style_theme_focus(False))

    def style_theme_focus(self, focused):
        self.theme_button_border.configure(bg=self.palette.focus if focused else self.palette.chrome)

    def toggle_theme(self, _event=None):
        self.mode = "light" if self.mode == "dark" else "dark"
        self.palette = PALETTES[self.mode]
        ctk.set_appearance_mode(self.mode)
        self.apply_palette()
        save_theme(self.preferences_path, self.mode)
        return "break"

    def style_button(self, button, *, bg=None, fg=None):
        palette = self.palette
        background = bg or palette.chrome
        foreground = fg or palette.ink
        button.configure(bg=background, fg=foreground, activebackground=palette.hover,
                         activeforeground=foreground, highlightbackground=background,
                         highlightcolor=palette.focus)

    def apply_palette(self):
        palette = self.palette
        self.configure(fg_color=palette.surface)
        for widget in (self.workspace, self.split):
            widget.configure(bg=palette.edge)
        for widget in (self.toolbar_frame, self.editor_header, self.result_header):
            widget.configure(bg=palette.chrome)
        for widget in (self.editor_frame, self.results_frame, *self.views.values()):
            widget.configure(bg=palette.surface)
        self.empty_label.configure(bg=palette.surface, fg=palette.muted)
        self.console.configure(**palette.text_options())
        self.file_tabs.apply_palette(palette)

        for name, button in self.file_buttons.items():
            self.style_button(button)
            button.configure(image=self.icon(FILE_GLYPHS[name], palette.muted))
        self.style_button(self.theme_button)
        self.style_theme_focus(self.focus_get() == self.theme_button)
        dark = self.mode == "dark"
        glyph = "white-balance-sunny" if dark else "weather-night"
        self.theme_button.configure(image=self.icon(glyph, palette.muted))
        self.theme_hint.set("Switch to light mode" if dark else "Switch to dark mode")
        self.style_button(self.execute_button)
        self.refresh_execution_button()
        self.apply_result_tabs_palette()
        self.apply_document_tabs_palette()
        for tab in self.tabs:
            tab["view"].apply_palette(palette)
        self.configure_ttk_styles()
        for table in (self.tokens_table, self.symbol_table):
            table.apply_palette(palette)
        if self.input_dialog is not None:
            self.style_input_dialog()

    def create_editor_panel(self):
        self.editor_frame.columnconfigure(0, weight=1)
        self.editor_frame.rowconfigure(1, weight=1)
        self.editor_header = tk.Frame(self.editor_frame)
        self.editor_header.grid(row=0, column=0, sticky="ew")
        self.editor_header.columnconfigure(0, weight=1)
        self.file_tabs = FileTabStrip(self.editor_header)
        self.file_tabs.grid(row=0, column=0, sticky="ew")
        self.execute_button = flat_button(self.editor_header, self.execute_code,
                                          image=self.icon("play", self.palette.play), width=34,
                                          height=34, padx=0, pady=0)
        self.execute_button.grid(row=0, column=1, sticky="ns")
        self.execution_hint = tk.StringVar(self, "Execute active file")
        tooltip(self.execute_button, self.execution_hint)
        self.empty_label = tk.Label(self.editor_frame, text="No file open", font=UI_FONT)

    def refresh_execution_button(self):
        if self.run is None:
            self.execute_button.configure(image=self.icon("play", self.palette.play))
            self.execution_hint.set("Execute active file")
        else:
            self.execute_button.configure(image=self.icon("stop", self.palette.stop))
            self.execution_hint.set("Terminate running program (Ctrl+C in Output)")

    def create_results_panel(self):
        self.results_frame.columnconfigure(0, weight=1)
        self.results_frame.rowconfigure(1, weight=1)
        self.result_header = tk.Frame(self.results_frame)
        self.result_header.grid(row=0, column=0, sticky="ew")
        self.result_header.rowconfigure(0, minsize=32)
        self.result_header.columnconfigure(3, weight=1)
        self.views = {}
        self.result_tabs = {}
        for column, name in enumerate(("Output", "Lexemes", "Symbol Table")):
            button = flat_button(self.result_header, lambda view=name: self.show_result(view),
                                 text=name.upper(), padx=8, pady=4)
            button.grid(row=0, column=column, sticky="ns")
            underline = tk.Frame(self.result_header, height=2)
            underline.grid(row=1, column=column, sticky="ew")
            self.result_tabs[name] = (button, underline)
            page = tk.Frame(self.results_frame)
            page.grid(row=1, column=0, sticky="nsew")
            page.rowconfigure(0, weight=1)
            page.columnconfigure(0, weight=1)
            self.views[name] = page
        output = self.views["Output"]
        self.console = tk.Text(output, font=MONO, bd=0, highlightthickness=0,
                               width=1, height=1, padx=12, pady=10, wrap="word")
        self.console.grid(row=0, column=0, sticky="nsew")
        self.console.bind("<Control-c>", self.stop_run)
        self.add_scrollbar(output, self.console)
        self.tokens_table = self.create_table("Lexemes", (("Lexeme", 130), ("Classification", 130)))
        self.symbol_table = self.create_table("Symbol Table",
                                              (("Identifier", 130), ("Type", 85), ("Value", 130)))
        self.show_result("Output")

    def configure_ttk_styles(self):
        palette, style = self.palette, self.style
        style.configure("Treeview", background=palette.surface, fieldbackground=palette.surface,
                        foreground=palette.ink, font=MONO, rowheight=25, borderwidth=0,
                        bordercolor=palette.edge, lightcolor=palette.edge, darkcolor=palette.edge)
        style.map("Treeview", background=[("selected", palette.table_selection)],
                  foreground=[("selected", palette.ink)])
        style.configure("Treeview.Heading", background=palette.chrome, foreground=palette.ink,
                        relief="flat", padding=(6, 4), font=UI_FONT, bordercolor=palette.edge,
                        lightcolor=palette.chrome, darkcolor=palette.chrome)
        style.map("Treeview.Heading", background=[("active", palette.hover)])

        style.configure("TScrollbar", background=palette.scroll_thumb, troughcolor=palette.chrome,
                        bordercolor=palette.chrome, lightcolor=palette.scroll_thumb,
                        darkcolor=palette.scroll_thumb, arrowcolor=palette.surface)
        style.map("TScrollbar", background=[("active", palette.muted)])
        style.configure("Hint.TLabel", background=palette.tooltip_bg, foreground=palette.tooltip_fg,
                        font=UI_FONT, padding=(8, 3))
        style.configure("TEntry", fieldbackground=palette.surface, foreground=palette.ink,
                        bordercolor=palette.edge, insertcolor=palette.ink,
                        lightcolor=palette.surface, darkcolor=palette.surface,
                        selectbackground=palette.selection, selectforeground=palette.ink)
        style.map("TEntry", bordercolor=[("focus", palette.focus)],
                  lightcolor=[("focus", palette.surface)], darkcolor=[("focus", palette.surface)])
        style.configure("TButton", background=palette.chrome, foreground=palette.ink,
                        bordercolor=palette.edge, lightcolor=palette.chrome, darkcolor=palette.chrome,
                        focuscolor=palette.focus)
        style.map("TButton", background=[("pressed", palette.selection), ("active", palette.hover)],
                  bordercolor=[("focus", palette.focus)])

    @staticmethod
    def add_scrollbar(page, widget):
        bar = ttk.Scrollbar(page, orient="vertical", command=widget.yview)
        bar.grid(row=0, column=1, sticky="ns")
        widget.configure(yscrollcommand=lambda a, b: set_scrollbar(bar, a, b))

    def create_table(self, view, columns):
        table = ResultsTable(self.views[view], columns)
        table.grid(row=0, column=0, sticky="nsew")
        return table

    def show_result(self, name):
        self.active_result = name
        self.views[name].tkraise()
        self.apply_result_tabs_palette()

    def apply_result_tabs_palette(self):
        palette = self.palette
        for view, (button, underline) in self.result_tabs.items():
            active = view == self.active_result
            self.style_button(button, fg=palette.ink if active else palette.muted)
            underline.configure(bg=palette.play if active else palette.chrome)

    def get_active_tab(self):
        return next((tab for tab in self.tabs if tab["id"] == self.active_tab_id), None)

    def create_new_tab(self, name=None, path=None, content=""):
        if name is None:
            name = f"Untitled-{self.untitled_counter}.lol"
            self.untitled_counter += 1
        tab = dict(id=self.next_tab_id, name=name, path=path, saved_content=content, is_dirty=False)
        self.next_tab_id += 1
        tab["view"] = SourceEditor(self.editor_frame, content, lambda: self.on_text_modified(tab),
                                   self.palette)
        self.tabs.append(tab)
        self.switch_tab(tab["id"])

    def switch_tab(self, tab_id):
        current = self.get_active_tab()
        if current:
            current["view"].grid_remove()
        self.active_tab_id = tab_id
        tab = self.get_active_tab()
        self.empty_label.grid_remove()
        tab["view"].grid(row=1, column=0, sticky="nsew")
        self.editor = tab["view"].text
        self.editor.focus_set()
        self.render_tabs(reveal_active=True)

    def close_tab(self, tab_id):
        tab = next(tab for tab in self.tabs if tab["id"] == tab_id)
        self.on_text_modified(tab)
        if tab["is_dirty"]:
            self.switch_tab(tab_id)
            choice = messagebox.askyesnocancel("Unsaved Changes",
                f"Do you want to save changes to '{tab['name']}' before closing?", parent=self)
            if choice is None or (choice and not self.save_file()):
                return
        self.tabs.remove(tab)
        tab["view"].destroy()
        if self.tabs and self.active_tab_id == tab_id:
            self.switch_tab(self.tabs[-1]["id"])
        else:
            if not self.tabs:
                self.active_tab_id = self.editor = None
                self.untitled_counter = 1
                self.empty_label.grid(row=1, column=0)
            self.render_tabs()

    def on_text_modified(self, tab):
        content = tab["view"].text.get("1.0", "end-1c")
        dirty = content != tab["saved_content"]
        if dirty != tab["is_dirty"]:
            tab["is_dirty"] = dirty
            self.render_tabs()

    def render_tabs(self, reveal_active=False):
        for widget in self.file_tabs.items.winfo_children():
            widget.destroy()
        self.tab_widgets = []
        for name in ("Save", "Save As"):
            self.file_buttons[name].configure(state="normal" if self.tabs else "disabled")
        for tab in self.tabs:
            tab_id = tab["id"]
            active = tab_id == self.active_tab_id
            item = tk.Frame(self.file_tabs.items)
            item.pack(side="left", fill="y", padx=(0, 1))
            select = lambda tid=tab_id: self.switch_tab(tid)
            dot = None
            if tab["is_dirty"]:
                dot = tk.Canvas(item, width=12, height=12, highlightthickness=0)
                dot.create_oval(3, 3, 10, 10, outline="")
                dot.pack(side="left", padx=(5, 0))
                dot.bind("<Button-1>", lambda e, action=select: action())
            name = tab["name"]
            label = flat_button(item, select, text=name if len(name) <= 24 else name[:20] + "…",
                                padx=7, pady=5)
            label.pack(side="left")
            tooltip(label, tab["path"] or name)
            close = flat_button(item, lambda tid=tab_id: self.close_tab(tid),
                                text="×", padx=4, pady=2)
            close.pack(side="left", padx=(0, 3))
            self.tab_widgets.append((active, item, label, close, dot))
            for widget in (item, *item.winfo_children()):
                self.file_tabs.bind_scrolling(widget)
            if active and reveal_active:
                item.bind("<Map>", self.file_tabs.reveal)
        self.apply_document_tabs_palette()

    def apply_document_tabs_palette(self):
        palette = self.palette
        for active, item, label, close, dot in self.tab_widgets:
            background = palette.surface if active else palette.chrome
            item.configure(bg=background)
            self.style_button(label, bg=background)
            self.style_button(close, bg=background, fg=palette.muted)
            if dot is not None:
                dot.configure(bg=background)
                dot.itemconfigure("all", fill=palette.dirty)

    # --- File Operations ---

    def new_file(self, event=None):
        # create new document tab
        self.create_new_tab()
        return "break"

    def open_file(self, event=None):
        # prompt user to select lolcode file from disk
        file_path = filedialog.askopenfilename(filetypes=[("LOLCode files", "*.lol")])
        if not file_path:
            return "break"

        # restrict opened files strictly to lol extension
        if not file_path.lower().endswith(".lol"):
            messagebox.showerror(
                title="Invalid File Type",
                message="Only LOLCode files (.lol) are supported by LOLTERPRETER.",
            )
            return "break"

        # if file is already open in a tab, switch directly to that tab
        for tab in self.tabs:
            if tab["path"] == file_path:
                self.switch_tab(tab["id"])
                return "break"

        # read content from selected file and open in new tab
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()

        file_name = os.path.basename(file_path)
        self.create_new_tab(name=file_name, path=file_path, content=content)
        return "break"

    def save_file(self, event=None):
        # save active tab to disk or prompt save as if untitled
        active_tab = self.get_active_tab()
        if active_tab is None:
            return False

        if active_tab["path"] is None:
            return self.save_as_file()

        content = self.editor.get("1.0", "end-1c")
        with open(active_tab["path"], "w", encoding="utf-8") as file:
            file.write(content)

        active_tab["saved_content"] = content
        active_tab["is_dirty"] = False
        self.render_tabs()
        return True

    def save_as_file(self, event=None):
        # prompt user for target file path and save editor text
        active_tab = self.get_active_tab()
        if active_tab is None:
            return False

        file_path = filedialog.asksaveasfilename(
            defaultextension=".lol",
            filetypes=[("LOLCode files", "*.lol")],
        )
        if not file_path:
            return False

        # sanitize extension to strictly lol
        base, ext = os.path.splitext(file_path)
        if ext.lower() != ".lol":
            file_path = f"{base}.lol"

        content = self.editor.get("1.0", "end-1c")
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(content)

        file_name = os.path.basename(file_path)
        active_tab["path"] = file_path
        active_tab["name"] = file_name
        active_tab["saved_content"] = content
        active_tab["is_dirty"] = False
        self.render_tabs()
        return True

    def execute_code(self):
        if self.run is not None:
            self.stop_run()
            return

        self.show_result("Output")
        self.console.delete("1.0", "end")
        for table in (self.tokens_table, self.symbol_table):
            table.clear()

        if self.get_active_tab() is None:
            self.append_console("no file open to execute\n")
            return
        source = self.editor.get("1.0", "end-1c")
        if not source.strip():
            self.append_console("no code to execute\n")
            return

        try:
            self.run = ProgramRun(source)
        except OSError as error:
            self.append_console(f"[Execution Error] {error}\n")
            return

        self.run_eof = False
        self.refresh_execution_button()
        self.run_job = self.after(15, self.poll_run)

    def stop_run(self, _event=None):
        if self.run is None:
            return None
        if not self.run.cancelled.is_set():
            self.run.stop()
            self.close_input_dialog()
        return "break"

    def poll_run(self):
        self.run_job = None
        run = self.run
        if run.cancelled.is_set() or self.run_eof:
            exit_code = run.process.poll()
            if exit_code is not None:
                self.finish_run(exit_code)
                return
        else:
            self.drain_run_events()
        self.run_job = self.after(15, self.poll_run)

    def drain_run_events(self):
        output = []
        deadline = monotonic() + 0.008
        for _ in range(64):
            try:
                kind, value = self.run.events.get_nowait()
            except Empty:
                break
            if kind == "output":
                output.append(value)
            elif kind == "input":
                self.append_console("".join(output))
                output.clear()
                self.show_input_dialog()
            elif kind == "eof":
                self.run_eof = True
                break
            elif kind == "clear_symbols":
                self.symbol_table.clear()
            else:
                table = self.tokens_table if kind == "lexemes" else self.symbol_table
                table.extend(value)
            if monotonic() >= deadline:
                break
        self.append_console("".join(output))

    def finish_run(self, exit_code):
        if self.run.cancelled.is_set():
            newline = "" if self.console.index("end-1c").endswith(".0") else "\n"
            self.append_console(f"{newline}Program terminated by user.\n")
        elif exit_code:
            self.append_console(f"\n[Execution Error] Interpreter exited with status {exit_code}.\n")
        self.close_input_dialog()
        self.run = None
        self.refresh_execution_button()

    def append_console(self, text):
        if text:
            self.console.insert("end", text)
            self.console.see("end")

    def show_input_dialog(self):
        run = self.run
        dialog = tk.Toplevel(self)
        self.input_dialog = dialog
        dialog.title("Program Input")
        dialog.transient(self)
        dialog.resizable(False, False)
        width = 300
        x = self.winfo_rootx() + (self.winfo_width() - width) // 2
        y = self.winfo_rooty() + 90
        dialog.geometry(f"{width}x106+{x}+{y}")

        def reply(value):
            if self.run is run and self.input_dialog is dialog and not run.cancelled.is_set():
                self.close_input_dialog()
                self.append_console(f"{value}\n")
                run.replies.put(value)

        self.input_label = tk.Label(dialog, text="Enter input for GIMMEH:", font=UI_FONT)
        self.input_label.pack(anchor="w", padx=12, pady=(8, 3))
        self.style_input_dialog()
        entry = ttk.Entry(dialog)
        entry.pack(fill="x", padx=12)
        ttk.Button(dialog, text="Submit", command=lambda: reply(entry.get())
                   ).pack(anchor="e", padx=12, pady=7)
        dialog.bind("<Return>", lambda _event: reply(entry.get()))
        dialog.bind("<Escape>", lambda _event: reply(""))
        dialog.protocol("WM_DELETE_WINDOW", lambda: reply(""))
        entry.focus_set()

    def style_input_dialog(self):
        self.input_dialog.configure(bg=self.palette.surface)
        self.input_label.configure(bg=self.palette.surface, fg=self.palette.ink)

    def close_input_dialog(self):
        if self.input_dialog is not None:
            dialog, self.input_dialog = self.input_dialog, None
            self.input_label = None
            dialog.destroy()

    def destroy(self):
        if self.run_job is not None:
            self.after_cancel(self.run_job)
        if self.run is not None:
            self.run.stop()
            try:
                self.run.process.wait(timeout=0.5)
            except TimeoutExpired:
                pass
        self.close_input_dialog()
        super().destroy()


# entry point fucntion to start gui
def main():
    app = InterpreterApp()  # create window instance
    
    # run window event loop
    app.mainloop()

if __name__ == "__main__":
    main()
