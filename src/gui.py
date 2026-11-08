# references:
# - customtkinter tutorial grid system: https://customtkinter.tomschimansky.com/tutorial/grid-system
# - customtkinter window documentation: https://customtkinter.tomschimansky.com/documentation/windows/
# - customtkinter simple example: https://github.com/TomSchimansky/CustomTkinter/blob/master/examples/simple_example.py

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

# entry point fucntion to start gui
def main():
    app = InterpreterApp()  # create window instance
    
    # run window event loop
    app.mainloop()

if __name__ == "__main__":
    main()