# references:
# - customtkinter window documentation: https://customtkinter.tomschimansky.com/documentation/windows/
# - customtkinter simple example: https://github.com/TomSchimansky/CustomTkinter/blob/master/examples/simple_example.py
# - python tkinter filedialog: https://docs.python.org/3/library/dialog.html

# references:
# - customtkinter tutorial grid system: https://customtkinter.tomschimansky.com/tutorial/grid-system
# - customtkinter window documentation: https://customtkinter.tomschimansky.com/documentation/windows/
# - customtkinter textbox documentation: https://customtkinter.tomschimansky.com/documentation/widgets/textbox
# - python tkinter filedialog: https://docs.python.org/3/library/dialog.html

import tkinter.filedialog as filedialog
import customtkinter as ctk

# main window class for lolcode interpreter gui
class InterpreterApp(ctk.CTk):
    # initalize main window and settings
    def __init__(self):
        super().__init__()
        
        # set window title bar text
        self.title("LOLTERPRETER - CMSC 124")
        
        # set initial window dimensions
        self.geometry("1100x700")
        
        # set dark theme for window appearance
        ctk.set_appearance_mode("dark")
        
        # set theme color palette for widgets
        ctk.set_default_color_theme("blue")

        # configure window root grid layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # build left panel for code editing
        self.create_left_panel()

    # fucntion to build left panel widgets
    def create_left_panel(self):
        self.left_frame = ctk.CTkFrame(self)  # container for left controls
        self.left_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.left_frame.grid_columnconfigure(0, weight=1)
        self.left_frame.grid_rowconfigure(2, weight=1)

        # button to trigger file dialog
        self.file_button = ctk.CTkButton(self.left_frame, text="Open File", command=self.open_file)  # file picker button
        self.file_button.grid(row=0, column=0, sticky="ew", padx=10, pady=5)

        # label displaying current opened file name
        self.file_label = ctk.CTkLabel(self.left_frame, text="No file selected")  # file status label
        self.file_label.grid(row=1, column=0, sticky="w", padx=10, pady=2)

        # multi line text editor for lolcode source code
        self.editor = ctk.CTkTextbox(self.left_frame, font=("Courier", 13))  # code editor area
        self.editor.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)

    # handler to open and load lolcode file into editor
    def open_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("LOLCode files", "*.lol"), ("All files", "*.*")])  # get file path
        
        # check if user cancelled file selection, return if empty
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