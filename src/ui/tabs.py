"""Horizontal viewport for the editor's open-file tabs."""

import tkinter as tk

class FileTabStrip(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.viewport = tk.Canvas(self, height=29, width=1, bd=0,
                                  highlightthickness=0, xscrollincrement=1)
        self.viewport.pack(fill="x")
        self.items = tk.Frame(self.viewport)
        self.viewport.create_window(0, 0, anchor="nw", height=29, window=self.items)
        self.track = tk.Canvas(self, height=5, bd=0, highlightthickness=0)
        self.track.pack(fill="x")
        self.thumb = self.track.create_rectangle(0, 1, 0, 5, outline="", state="hidden")
        self.range = (0.0, 1.0)
        self.thumb_left = self.thumb_width = 0
        self.drag_offset = self.hide_job = None
        self.visible = False

        self.items.bind("<Configure>", self.resize)
        self.viewport.bind("<Configure>", self.resize)
        self.track.bind("<Configure>", self.draw_thumb)
        self.viewport.configure(xscrollcommand=self.update_range)
        self.track.bind("<Button-1>", self.start_drag)
        self.track.bind("<B1-Motion>", self.drag)
        self.track.bind("<ButtonRelease-1>", self.end_drag)
        for widget in (self, self.viewport, self.track, self.items):
            self.bind_scrolling(widget)

    def apply_palette(self, palette):
        for widget in (self, self.viewport, self.track, self.items):
            widget.configure(bg=palette.chrome)
        self.track.itemconfigure(self.thumb, fill=palette.muted)

    def bind_scrolling(self, widget):
        for event in ("<MouseWheel>", "<Shift-MouseWheel>", "<Button-4>", "<Button-5>",
                      "<Shift-Button-4>", "<Shift-Button-5>"):
            widget.bind(event, self.scroll)
        widget.bind("<Enter>", self.show_thumb)
        widget.bind("<Leave>", self.schedule_hide)

    def resize(self, _event=None):
        width = max(self.items.winfo_reqwidth(), self.viewport.winfo_width())
        self.viewport.configure(scrollregion=(0, 0, width, 29))

    def update_range(self, first, last):
        self.range = float(first), float(last)
        self.draw_thumb()

    def draw_thumb(self, _event=None):
        first, last = self.range
        if not self.visible or last - first >= 1:
            self.track.itemconfigure(self.thumb, state="hidden")
            return
        width = self.track.winfo_width()
        visible_fraction = last - first
        self.thumb_width = min(width, max(22, round(width * visible_fraction)))
        self.thumb_left = round((width - self.thumb_width) * first / (1 - visible_fraction))
        self.track.coords(self.thumb, self.thumb_left, 1, self.thumb_left + self.thumb_width, 5)
        self.track.itemconfigure(self.thumb, state="normal")

    def show_thumb(self, _event=None):
        self.visible = True
        self.draw_thumb()

    def schedule_hide(self, _event=None):
        if self.hide_job is not None:
            self.after_cancel(self.hide_job)
        self.hide_job = self.after(650, self.hide_thumb)

    def hide_thumb(self):
        self.hide_job = None
        x, y = self.winfo_pointerxy()
        inside = (0 <= x - self.winfo_rootx() < self.winfo_width()
                  and 0 <= y - self.winfo_rooty() < self.winfo_height())
        if self.drag_offset is None and not inside:
            self.visible = False
            self.draw_thumb()

    def scroll(self, event):
        if event.num in (4, 5):
            pixels = -50 if event.num == 4 else 50
        else:
            pixels = round(-event.delta * 50 / 120)
            if not pixels and event.delta:
                pixels = -1 if event.delta > 0 else 1
        self.viewport.xview_scroll(pixels, "units")
        self.show_thumb()
        self.schedule_hide()
        return "break"

    def start_drag(self, event):
        self.show_thumb()
        first, last = self.range
        if last - first < 1:
            self.drag_offset = event.x - self.thumb_left
            if not 0 <= self.drag_offset <= self.thumb_width:
                self.drag_offset = self.thumb_width / 2
                self.drag(event)

    def drag(self, event):
        travel = self.track.winfo_width() - self.thumb_width
        if self.drag_offset is not None and travel > 0:
            position = min(1, max(0, (event.x - self.drag_offset) / travel))
            first, last = self.range
            self.viewport.xview_moveto(position * (1 - (last - first)))

    def end_drag(self, _event):
        self.drag_offset = None
        self.schedule_hide()

    def reveal(self, event):
        item = event.widget
        item.unbind("<Map>")
        self.resize()
        left = self.viewport.canvasx(0)
        width = self.viewport.winfo_width()
        x = item.winfo_x()
        end = x + item.winfo_width()
        if x < left or end > left + width:
            target = x if x < left else end - width
            self.viewport.xview_moveto(target / max(1, self.items.winfo_reqwidth()))
            self.show_thumb()
            self.schedule_hide()

    def destroy(self):
        if self.hide_job is not None:
            self.after_cancel(self.hide_job)
        super().destroy()
