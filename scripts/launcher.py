"""Entry script for frozen builds (PyInstaller needs a file, not a module)."""
from bivouac.app import main

raise SystemExit(main())
