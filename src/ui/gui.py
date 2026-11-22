# references:
# - customtkinter window documentation: https://customtkinter.tomschimansky.com/documentation/windows/
# - customtkinter simple example: https://github.com/TomSchimansky/CustomTkinter/blob/master/examples/simple_example.py
# - python tkinter filedialog: https://docs.python.org/3/library/dialog.html
# - python tkinter ttk treeview: https://docs.python.org/3/library/tkinter.ttk.html

import os
import tkinter.filedialog as filedialog
import tkinter.messagebox as messagebox
import tkinter.ttk as ttk
import customtkinter as ctk
from core.errors import LexicalError, LolRuntimeError, SemanticError, SyntaxError
from core.tokens import T
from ui.controller import InterpreterController, format_lol_value

# main window class for lolcode interpreter gui
class InterpreterApp(ctk.CTk):
    # initalize main window and settings
    def __init__(self):
        super().__init__()
        
        # set window title bar text
        self.title("LOLTERPRETER - CMSC 124")
        
        # set initial window dimensions
        self.geometry("1200x700")
        
        # set dark theme for window appearance
        ctk.set_appearance_mode("dark")
        
        # set theme color palette for widgets
        ctk.set_default_color_theme("blue")

        # initialize tab manager state and counters
        self.tabs: list[dict] = []
        self.active_tab_id: int = 1
        self.next_tab_id: int = 1
        self.untitled_counter: int = 1

        # configure equal uniform width columns for editor, tokens, symbol table
        self.grid_columnconfigure(0, weight=1, uniform="main_cols")
        self.grid_columnconfigure(1, weight=1, uniform="main_cols")
        self.grid_columnconfigure(2, weight=1, uniform="main_cols")
        
        # configure rows for top panels, execute button, console
        self.grid_rowconfigure(0, weight=3)
        self.grid_rowconfigure(1, weight=0)
        self.grid_rowconfigure(2, weight=2)

        # functions
        self.setup_table_style() # configure dark styling for ttk tables
        self.create_editor_panel() # build top left panel for code editing
        self.create_tables_panel() # build middle and right panels for tables
        self.create_bottom_panel() # build bottom execute button and console panel

        # create initial blank editor tab
        self.create_new_tab()

    # fucntion to configure treeview dark theme colors
    def setup_table_style(self):
        style = ttk.Style()  # access ttk styling engine
        
        # set clam theme for consistent custom styling across platforms
        style.theme_use("clam")
        
        # configure main table background and text colors
        style.configure("Treeview", background="#2b2b2b", foreground="#ffffff", fieldbackground="#2b2b2b", rowheight=24, borderwidth=0)
        
        # configure header row background and text colors
        style.configure("Treeview.Heading", background="#1f1f1f", foreground="#ffffff", relief="flat")
        
        # map selection color for highlighted table rows
        style.map("Treeview", background=[("selected", "#1f6aa5")])

    # fucntion to build left editor panel widgets
    def create_editor_panel(self):
        self.editor_frame = ctk.CTkFrame(self)  # container for editor column
        self.editor_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.editor_frame.grid_columnconfigure(0, weight=1)
        self.editor_frame.grid_rowconfigure(3, weight=1)

        # container frame for file action toolbar buttons
        self.toolbar_frame = ctk.CTkFrame(self.editor_frame, fg_color="transparent")
        self.toolbar_frame.grid(row=0, column=0, sticky="ew", padx=2, pady=2)
        self.toolbar_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        # toolbar buttons for new, open, save, and save as
        self.new_btn = ctk.CTkButton(self.toolbar_frame, text="New", width=60, command=self.new_file)
        self.new_btn.grid(row=0, column=0, padx=2, pady=2, sticky="ew")

        self.open_btn = ctk.CTkButton(self.toolbar_frame, text="Open", width=60, command=self.open_file)
        self.open_btn.grid(row=0, column=1, padx=2, pady=2, sticky="ew")

        self.save_btn = ctk.CTkButton(self.toolbar_frame, text="Save", width=60, command=self.save_file)
        self.save_btn.grid(row=0, column=2, padx=2, pady=2, sticky="ew")

        self.save_as_btn = ctk.CTkButton(self.toolbar_frame, text="Save As", width=70, command=self.save_as_file)
        self.save_as_btn.grid(row=0, column=3, padx=2, pady=2, sticky="ew")

        # horizontal container for vscode style document tabs
        self.tabs_bar = ctk.CTkFrame(self.editor_frame, height=42, fg_color="#1e1e1e")
        self.tabs_bar.grid(row=1, column=0, sticky="ew", padx=2, pady=2)
        self.tabs_bar.grid_columnconfigure(0, weight=1)

        # scrollable container for open document tabs
        self.tabs_scrollable = ctk.CTkScrollableFrame(
            self.tabs_bar,
            orientation="horizontal",
            height=34,
            fg_color="transparent",
        )
        self.tabs_scrollable.grid(row=0, column=0, sticky="ew", padx=(2, 0), pady=1)

        # bind mousewheel and trackpad gestures across tabs bar for horizontal scrolling
        self.tabs_bar.bind("<MouseWheel>", self.on_tabs_mousewheel)
        self.tabs_scrollable.bind("<MouseWheel>", self.on_tabs_mousewheel)
        self.tabs_scrollable._parent_canvas.bind("<MouseWheel>", self.on_tabs_mousewheel)
        self.tabs_bar.bind("<Shift-MouseWheel>", self.on_tabs_mousewheel)
        self.tabs_scrollable.bind("<Shift-MouseWheel>", self.on_tabs_mousewheel)
        self.tabs_scrollable._parent_canvas.bind("<Shift-MouseWheel>", self.on_tabs_mousewheel)

        # add new tab plus button pinned to right
        self.add_tab_btn = ctk.CTkButton(
            self.tabs_bar,
            text="+",
            width=26,
            height=26,
            font=("Arial", 14, "bold"),
            command=self.new_file,
        )
        self.add_tab_btn.grid(row=0, column=1, padx=4, pady=2)

        # label displaying current active file path
        self.file_label = ctk.CTkLabel(self.editor_frame, text="Untitled-1.lol", font=("Arial", 11), text_color="#9e9e9e")  # file status label
        self.file_label.grid(row=2, column=0, sticky="w", padx=5, pady=1)

        # multi line text editor with native undo redo enabled
        self.editor = ctk.CTkTextbox(self.editor_frame, font=("Courier", 13), undo=True)  # code editor area
        self.editor.grid(row=3, column=0, sticky="nsew", padx=5, pady=5)

        # empty state placeholder frame when no document is open
        self.empty_state_frame = ctk.CTkFrame(self.editor_frame, fg_color="transparent")

        # center container for empty state prompt elements
        self.empty_center = ctk.CTkFrame(self.empty_state_frame, fg_color="transparent")
        self.empty_center.pack(expand=True)

        # file icon for visual empty state prompt
        self.empty_icon = ctk.CTkLabel(self.empty_center, text="📄", font=("Arial", 38), text_color="#6e6e6e")
        self.empty_icon.pack(pady=(0, 6))

        # primary prompt header
        self.empty_title = ctk.CTkLabel(self.empty_center, text="No File Open", font=("Arial", 16, "bold"), text_color="#d4d4d4")
        self.empty_title.pack(pady=(0, 4))

        # helper description with instructions
        self.empty_desc = ctk.CTkLabel(
            self.empty_center,
            text="click new file to create a file or open file to load code",
            font=("Arial", 11),
            text_color="#888888",
            wraplength=260,
        )
        self.empty_desc.pack(pady=(0, 16))

        # action button to create fresh document
        self.empty_new_btn = ctk.CTkButton(self.empty_center, text="New File (Ctrl+N)", width=170, height=32, command=self.new_file)
        self.empty_new_btn.pack(pady=4)

        # action button to open existing file from disk
        self.empty_open_btn = ctk.CTkButton(
            self.empty_center,
            text="Open File (Ctrl+O)",
            width=170,
            height=32,
            fg_color="#3a3a3a",
            hover_color="#4a4a4a",
            command=self.open_file,
        )
        self.empty_open_btn.pack(pady=4)

        # bind tab and indentation keys
        self.editor.bind("<Tab>", self.insert_tab_spaces)
        self.editor.bind("<Shift-Tab>", self.unindent_tab_spaces)

        # bind undo and redo keyboard shortcuts
        self.editor.bind("<Control-z>", self.safe_undo)
        self.editor.bind("<Control-y>", self.safe_redo)
        self.editor.bind("<Control-Z>", self.safe_redo)

        # bind text modification listener to track unsaved changes
        self.editor.bind("<KeyRelease>", self.on_text_modified)

        # bind keyboard shortcuts for file operations
        self.bind("<Control-n>", self.new_file)
        self.bind("<Control-o>", self.open_file)
        self.bind("<Control-s>", self.save_file)
        self.bind("<Control-S>", self.save_as_file)

    def insert_tab_spaces(self, event=None):
        # insert four spaces for consistent indentation
        self.editor.insert("insert", "    ")
        self.on_text_modified()
        return "break"

    def unindent_tab_spaces(self, event=None):
        # remove up to four leading spaces on current line
        cursor_pos = self.editor.index("insert")
        line_num = cursor_pos.split(".")[0]
        line_start = f"{line_num}.0"
        line_text = self.editor.get(line_start, f"{line_num}.end")
        spaces_to_remove = len(line_text) - len(line_text.lstrip(" "))
        remove_count = min(spaces_to_remove, 4)
        if remove_count > 0:
            self.editor.delete(line_start, f"{line_num}.{remove_count}")
        self.on_text_modified()
        return "break"

    def safe_undo(self, event=None):
        # handle undo action safely without crashing on empty stack
        try:
            self.editor._textbox.edit_undo()
            self.on_text_modified()
        except Exception:
            pass
        return "break"

    def safe_redo(self, event=None):
        # handle redo action safely without crashing on empty stack
        try:
            self.editor._textbox.edit_redo()
            self.on_text_modified()
        except Exception:
            pass
        return "break"

    # --- Tab Management ---

    def get_active_tab(self) -> dict | None:
        # retrieve current active tab dictionary
        for tab in self.tabs:
            if tab["id"] == self.active_tab_id:
                return tab
        return None

    def format_tab_name(self, name: str, max_chars: int = 16) -> str:
        # truncate long filenames with ellipsis to preserve tab bar width
        if len(name) <= max_chars:
            return name
        base, ext = os.path.splitext(name)
        if ext:
            ext_clean = ext.lstrip(".")
            base_limit = max(4, max_chars - len(ext_clean) - 4)
            return f"{base[:base_limit]}...{ext_clean}"
        return f"{name[:max_chars - 3]}..."

    def on_tabs_mousewheel(self, event):
        # scroll horizontal tabs using mousewheel or two finger trackpad gesture
        if event.delta:
            scroll_units = int(-1 * (event.delta / 40))
            self.tabs_scrollable._parent_canvas.xview_scroll(scroll_units, "units")
            return "break"

    def update_editor_visibility(self):
        # toggle between empty state placeholder and active editor tabs view
        if not self.tabs:
            # hide tabs bar add button file label and text editor
            self.tabs_bar.grid_remove()
            self.file_label.grid_remove()
            self.editor.grid_remove()
            # show centered empty state prompt
            self.empty_state_frame.grid(row=1, column=0, rowspan=3, sticky="nsew", padx=10, pady=10)
            # disable save buttons when no document is open
            self.save_btn.configure(state="disabled")
            self.save_as_btn.configure(state="disabled")
        else:
            # hide empty state prompt
            self.empty_state_frame.grid_remove()
            # show tabs bar with add button file label and text editor
            self.tabs_bar.grid(row=1, column=0, sticky="ew", padx=2, pady=2)
            self.file_label.grid(row=2, column=0, sticky="w", padx=5, pady=1)
            self.editor.grid(row=3, column=0, sticky="nsew", padx=5, pady=5)
            # enable save buttons
            self.save_btn.configure(state="normal")
            self.save_as_btn.configure(state="normal")

    def create_new_tab(self, name: str | None = None, path: str | None = None, content: str = ""):
        # enable editor if previously disabled
        self.editor.configure(state="normal")

        tab_id = self.next_tab_id
        self.next_tab_id += 1

        if name is None:
            name = f"Untitled-{self.untitled_counter}.lol"
            self.untitled_counter += 1

        tab_data = {
            "id": tab_id,
            "name": name,
            "path": path,
            "saved_content": content,
            "current_content": content,
            "is_dirty": False,
        }
        self.tabs.append(tab_data)
        self.switch_tab(tab_id)

    def switch_tab(self, tab_id: int):
        # enable editor
        self.editor.configure(state="normal")

        # save current editor buffer to outgoing active tab
        current_active = self.get_active_tab()
        if current_active is not None and self.editor.cget("state") == "normal":
            current_active["current_content"] = self.editor.get("1.0", "end-1c")

        # set new active tab and load content into editor
        self.active_tab_id = tab_id
        new_active = self.get_active_tab()
        if new_active is not None:
            self.editor.delete("1.0", "end")
            self.editor.insert("1.0", new_active["current_content"])
            display_path = new_active["path"] if new_active["path"] else new_active["name"]
            self.file_label.configure(text=display_path)

        self.render_tabs()

    def close_tab(self, tab_id: int, event=None):
        # close specified tab and switch to adjacent tab
        tab_to_close = None
        for tab in self.tabs:
            if tab["id"] == tab_id:
                tab_to_close = tab
                break

        if tab_to_close is None:
            return

        # check if active tab buffer has newer text
        if tab_to_close["id"] == self.active_tab_id and self.editor.cget("state") == "normal":
            current_text = self.editor.get("1.0", "end-1c")
            tab_to_close["current_content"] = current_text
            tab_to_close["is_dirty"] = (current_text != tab_to_close["saved_content"])

        # prompt user for confirmation if document has unsaved modifications
        if tab_to_close["is_dirty"]:
            self.switch_tab(tab_to_close["id"])
            choice = messagebox.askyesnocancel(
                title="Unsaved Changes",
                message=f"Do you want to save changes to '{tab_to_close['name']}' before closing?",
            )
            if choice is None:
                # cancel clicked, abort tab closing
                return
            if choice is True:
                # save clicked, write changes before closing
                saved = self.save_file()
                if not saved or tab_to_close["is_dirty"]:
                    # save was cancelled, abort tab closing
                    return

        self.tabs.remove(tab_to_close)

        # if no tabs remain open, clear editor and reset counter
        if not self.tabs:
            self.active_tab_id = 0
            self.untitled_counter = 1
            self.editor.delete("1.0", "end")
            self.render_tabs()
            return

        # if closed tab was active, switch to last open tab
        if self.active_tab_id == tab_id:
            self.switch_tab(self.tabs[-1]["id"])
        else:
            self.render_tabs()

    def render_tabs(self):
        # toggle visibility of empty state versus active tabs
        self.update_editor_visibility()

        # clear and rebuild tab pill buttons in scrollable tab bar
        for widget in self.tabs_scrollable.winfo_children():
            widget.destroy()

        if not self.tabs:
            return

        for tab in self.tabs:
            is_active = (tab["id"] == self.active_tab_id)
            pill_color = "#1f6aa5" if is_active else "#2b2b2b"

            pill = ctk.CTkFrame(self.tabs_scrollable, fg_color=pill_color, corner_radius=6)
            pill.pack(side="left", padx=2, pady=2)

            # label displaying truncated filename with unsaved circle marker if dirty
            marker = "● " if tab["is_dirty"] else ""
            display_name = self.format_tab_name(tab["name"])
            label_text = f"{marker}{display_name}"
            tab_label = ctk.CTkLabel(pill, text=label_text, font=("Arial", 11, "bold" if is_active else "normal"))
            tab_label.pack(side="left", padx=(6, 2))
            tab_label.bind("<Button-1>", lambda e, tid=tab["id"]: self.switch_tab(tid))
            pill.bind("<Button-1>", lambda e, tid=tab["id"]: self.switch_tab(tid))

            # close tab button
            close_btn = ctk.CTkButton(
                pill,
                text="✕",
                width=16,
                height=16,
                font=("Arial", 9),
                fg_color="transparent",
                hover_color="#c42b1c",
                command=lambda tid=tab["id"]: self.close_tab(tid),
            )
            close_btn.pack(side="left", padx=(0, 4))

            # bind mousewheel to tab pill and elements for smooth trackpad scrolling
            pill.bind("<MouseWheel>", self.on_tabs_mousewheel)
            tab_label.bind("<MouseWheel>", self.on_tabs_mousewheel)
            close_btn.bind("<MouseWheel>", self.on_tabs_mousewheel)

    def on_text_modified(self, event=None):
        # detect text modifications and update unsaved circle marker
        active_tab = self.get_active_tab()
        if active_tab is None:
            return

        current_text = self.editor.get("1.0", "end-1c")
        active_tab["current_content"] = current_text
        was_dirty = active_tab["is_dirty"]
        is_dirty = (current_text != active_tab["saved_content"])

        if is_dirty != was_dirty:
            active_tab["is_dirty"] = is_dirty
            self.render_tabs()

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
        active_tab["current_content"] = content
        active_tab["is_dirty"] = False
        self.file_label.configure(text=active_tab["path"])
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
        active_tab["current_content"] = content
        active_tab["is_dirty"] = False
        self.file_label.configure(text=file_path)
        self.render_tabs()
        return True

    # fucntion to build middle tokens table and right symbol table
    def create_tables_panel(self):
        # middle column frame for tokens list
        self.tokens_frame = ctk.CTkFrame(self)  # container for tokens column
        self.tokens_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self.tokens_frame.grid_columnconfigure(0, weight=1)
        self.tokens_frame.grid_rowconfigure(1, weight=1)

        # header label for tokens table
        tokens_label = ctk.CTkLabel(self.tokens_frame, text="Lexemes", font=("Arial", 14, "bold"))  # lexemes header
        tokens_label.grid(row=0, column=0, sticky="w", padx=8, pady=4)

        # table to display lexemes and their classifications
        self.tokens_table = ttk.Treeview(self.tokens_frame, columns=("lexeme", "classification"), show="headings")  # tokens table
        self.tokens_table.heading("lexeme", text="Lexeme")
        self.tokens_table.heading("classification", text="Classification")
        self.tokens_table.column("lexeme", width=120, anchor="w")
        self.tokens_table.column("classification", width=160, anchor="w")
        self.tokens_table.grid(row=1, column=0, sticky="nsew", padx=(5, 0), pady=5)

        # vertical scrollbar for tokens table
        tokens_scroll = ttk.Scrollbar(self.tokens_frame, orient="vertical", command=self.tokens_table.yview)  # tokens scrollbar
        tokens_scroll.grid(row=1, column=1, sticky="ns", pady=5)
        self.tokens_table.configure(yscrollcommand=tokens_scroll.set)

        # right column frame for symbol table
        self.symbol_frame = ctk.CTkFrame(self)  # container for symbol column
        self.symbol_frame.grid(row=0, column=2, sticky="nsew", padx=5, pady=5)
        self.symbol_frame.grid_columnconfigure(0, weight=1)
        self.symbol_frame.grid_rowconfigure(1, weight=1)

        # header label for symbol table
        symbol_label = ctk.CTkLabel(self.symbol_frame, text="SYMBOL TABLE", font=("Arial", 14, "bold"))  # symbol header
        symbol_label.grid(row=0, column=0, sticky="w", padx=8, pady=4)

        # table to display variable identifiers, types, and runtime values in three dedicated columns
        self.symbol_table = ttk.Treeview(self.symbol_frame, columns=("identifier", "type", "value"), show="headings")  # symbol table
        self.symbol_table.heading("identifier", text="Identifier")
        self.symbol_table.heading("type", text="Type")
        self.symbol_table.heading("value", text="Value")
        self.symbol_table.column("identifier", width=100, anchor="w")
        self.symbol_table.column("type", width=80, anchor="center")
        self.symbol_table.column("value", width=130, anchor="w")
        self.symbol_table.grid(row=1, column=0, sticky="nsew", padx=(5, 0), pady=5)

        # vertical scrollbar for symbol table
        symbol_scroll = ttk.Scrollbar(self.symbol_frame, orient="vertical", command=self.symbol_table.yview)  # symbol scrollbar
        symbol_scroll.grid(row=1, column=1, sticky="ns", pady=5)
        self.symbol_table.configure(yscrollcommand=symbol_scroll.set)

    # fucntion to build execute button and console output area
    def create_bottom_panel(self):
        # full width execute button spanning all columns
        self.execute_button = ctk.CTkButton(self, text="EXECUTE", font=("Arial", 14, "bold"), command=self.execute_code)  # execute button
        self.execute_button.grid(row=1, column=0, columnspan=3, sticky="ew", padx=5, pady=5)

        # multi line console output area spanning all columns
        self.console = ctk.CTkTextbox(self, font=("Courier", 12))  # console text area
        self.console.grid(row=2, column=0, columnspan=3, sticky="nsew", padx=5, pady=5)

    # function to execute code from editor and update lexemes, symbol table, and console
    def execute_code(self):
        # check if any file tab is open
        if not self.tabs or self.get_active_tab() is None:
            self.console.delete("1.0", "end")
            self.console.insert("end", "no file open to execute\n")
            return

        code = self.editor.get("1.0", "end-1c")  # get current text from editor

        # clear existing rows from lexemes table
        for item in self.tokens_table.get_children():
            self.tokens_table.delete(item)

        # clear existing rows from symbol table
        for item in self.symbol_table.get_children():
            self.symbol_table.delete(item)

        # clear console display area
        self.console.delete("1.0", "end")

        # check if editor has content, stop if empty
        if not code.strip():
            self.console.insert("end", "no code to execute\n")
            return

        controller = InterpreterController(
            on_tokens_updated=self.update_tokens_table,
            on_symbols_updated=self.update_symbol_table,
            on_stdout=self.append_console,
            request_stdin=self.prompt_input,
            on_error=self.report_error,
        )
        controller.execute(code)

    # populate lexemes table from token stream
    def update_tokens_table(self, tokens):
        for tok in tokens:
            # skip structural tokens from table display
            if tok.type not in (T.NEWLINE, T.EOF):
                self.tokens_table.insert("", "end", values=(tok.value, tok.classification))

    # refresh symbol table with identifier, type, and value columns
    def update_symbol_table(self, symbols):
        for item in self.symbol_table.get_children():
            self.symbol_table.delete(item)
        for name, lol_val in symbols.items():
            type_str = lol_val.type_name
            if lol_val.type_name == "NOOB":
                val_str = "NOOB"
            elif lol_val.type_name == "TROOF":
                val_str = "WIN" if lol_val.value else "FAIL"
            elif lol_val.type_name == "YARN":
                val_str = f'"{lol_val.value}"'
            else:
                val_str = str(lol_val.value)
            self.symbol_table.insert("", "end", values=(name, type_str, val_str))
        self.update_idletasks()

    # append interpreter output to console and refresh display immediately
    def append_console(self, text):
        self.console.insert("end", text)
        self.console.see("end")
        self.update_idletasks()

    # prompt user for GIMMEH input via modal dialog and echo it to console
    def prompt_input(self):
        dialog = ctk.CTkInputDialog(text="Enter input for GIMMEH:", title="Program Input")
        user_input = dialog.get_input()
        if user_input is None:
            user_input = ""
        self.append_console(f"{user_input}\n")
        return user_input

    # format and display lexical, syntax, semantic, or runtime errors in console
    def report_error(self, err):
        if isinstance(err, LexicalError):
            phase = "Lexical Error"
        elif isinstance(err, SyntaxError):
            phase = "Syntax Error"
        elif isinstance(err, SemanticError):
            phase = "Semantic Error"
        elif isinstance(err, LolRuntimeError):
            phase = "Runtime Error"
        else:
            phase = "Error"

        if err.line > 0:
            self.append_console(f"\n[{phase}] Line {err.line}: {err.message}\n")
        else:
            self.append_console(f"\n[{phase}] {err.message}\n")

# entry point fucntion to start gui
def main():
    app = InterpreterApp()  # create window instance
    
    # run window event loop
    app.mainloop()

if __name__ == "__main__":
    main()