# root entry point for lolcode gui application

import sys
from pathlib import Path

# ensure src directory is on search path
sys.path.insert(0, str(Path(__file__).resolve().parent))

if '--debug' in sys.argv:
    from core.debug import set_debug
    set_debug(True)

from ui.gui import InterpreterApp, main

if __name__ == "__main__":
    main()