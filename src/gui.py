# references:
# - customtkinter window documentation: https://customtkinter.tomschimansky.com/documentation/windows/
# - customtkinter simple example: https://github.com/TomSchimansky/CustomTkinter/blob/master/examples/simple_example.py
# - python tkinter filedialog: https://docs.python.org/3/library/dialog.html
# - python tkinter ttk treeview: https://docs.python.org/3/library/tkinter.ttk.html

import tkinter.filedialog as filedialog
import tkinter.ttk as ttk
import customtkinter as ctk

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

        # configure three columns for editor, tokens, symbol table
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)
        
        # configure rows for top panels, execute button, console
        self.grid_rowconfigure(0, weight=3)
        self.grid_rowconfigure(1, weight=0)
        self.grid_rowconfigure(2, weight=2)

        # functions
        self.setup_table_style() # configure dark styling for ttk tables
        self.create_editor_panel() # build top left panel for code editing        
        self.create_tables_panel()# build middle and right panels for tables
        self.create_bottom_panel() # build bottom execute button and console panel

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
        self.editor_frame.grid_rowconfigure(2, weight=1)

        # button to trigger file dialog
        self.file_button = ctk.CTkButton(self.editor_frame, text="Open File", command=self.open_file)  # file picker button
        self.file_button.grid(row=0, column=0, sticky="ew", padx=5, pady=5)

        # label displaying current opened file name
        self.file_label = ctk.CTkLabel(self.editor_frame, text="No file selected")  # file status label
        self.file_label.grid(row=1, column=0, sticky="w", padx=5, pady=2)

        # multi line text editor for lolcode source code
        self.editor = ctk.CTkTextbox(self.editor_frame, font=("Courier", 13))  # code editor area
        self.editor.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)

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

        # table to display variable identifiers and runtime values
        self.symbol_table = ttk.Treeview(self.symbol_frame, columns=("identifier", "value"), show="headings")  # symbol table
        self.symbol_table.heading("identifier", text="Identifier")
        self.symbol_table.heading("value", text="Value")
        self.symbol_table.column("identifier", width=120, anchor="w")
        self.symbol_table.column("value", width=160, anchor="w")
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

    # placeholder fucntion for execute button action
    def execute_code(self):
        pass

    # handler to open and load lolcode file into editor
    def open_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("LOLCode files", "*.lol"), ("All files", "*.*")])  # get file path
        
        # check if file selection was cancelled, return if empty
        if not file_path:
            return

        # read content from selected file
        with open(file_path, "r") as file:
            content = file.read()  # read full text

        # update editor text area with file content
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", content)
        
        # display opened file path on label
        self.file_label.configure(text=file_path)

# entry point fucntion to start gui
def main():
    app = InterpreterApp()  # create window instance
    
    # run window event loop
    app.mainloop()

if __name__ == "__main__":
    main()