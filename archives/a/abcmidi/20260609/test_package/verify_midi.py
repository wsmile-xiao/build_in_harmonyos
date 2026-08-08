import pathlib
import sys


data = pathlib.Path(sys.argv[1]).read_bytes()
if len(data) <= 14 or data[:4] != b"MThd":
    raise SystemExit("abc2midi did not produce a valid MIDI header")
