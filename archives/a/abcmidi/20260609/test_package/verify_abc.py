import pathlib
import sys


text = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
if "X:" not in text or "K:" not in text:
    raise SystemExit("midi2abc output is missing required ABC fields")
