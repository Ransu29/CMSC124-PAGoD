"""Colors and the saved appearance preference for the desktop workspace."""

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import sys
from tempfile import NamedTemporaryFile


@dataclass(frozen=True)
class Palette:
    surface: str
    chrome: str
    edge: str
    ink: str
    muted: str
    play: str
    stop: str
    dirty: str
    hover: str
    focus: str
    current_line: str
    selection: str
    table_selection: str
    tooltip_bg: str
    tooltip_fg: str
    scroll_thumb: str
    keyword: str
    string: str
    number: str
    comment: str

    def text_options(self):
        return dict(bg=self.surface, fg=self.ink, insertbackground=self.ink,
                    selectbackground=self.selection, selectforeground=self.ink)


LIGHT = Palette(
    surface="#fdfdfe", chrome="#e8edf4", edge="#d5dce6", ink="#182d47", muted="#52647b",
    play="#007d68", stop="#c73434", dirty="#2968db", hover="#dbe3ed", focus="#1760a5",
    current_line="#f3f4f6", selection="#caddfa", table_selection="#d9e8fa",
    tooltip_bg="#182d47", tooltip_fg="#ffffff", scroll_thumb="#8d9bac",
    keyword="#183f86", string="#007478", number="#a04328", comment="#687981",
)

dark_colors = {name: f"#{0xffffff - int(color[1:], 16):06x}"
               for name, color in asdict(LIGHT).items()}
dark_colors["stop"] = LIGHT.stop
DARK = Palette(**dark_colors)

PALETTES = {"light": LIGHT, "dark": DARK}


def preferences_path():
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "LOLTERPRETER" / "preferences.json"


def load_theme(path):
    try:
        settings = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(settings, dict) and settings.get("theme") == "dark":
            return "dark"
    except (OSError, ValueError):
        pass
    return "light"


def save_theme(path, mode):
    draft = None
    try:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                    delete=False) as temporary:
                draft = Path(temporary.name)
                json.dump({"theme": mode}, temporary)
            draft.replace(path)
        finally:
            if draft is not None:
                draft.unlink(missing_ok=True)
    except OSError:
        # The in-memory preference still applies when settings cannot be written.
        pass
