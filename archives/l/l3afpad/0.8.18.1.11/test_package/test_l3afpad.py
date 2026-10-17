#!/usr/bin/env python3
"""Exercise the packaged l3afpad binary from a consumer's point of view.

Usage: test_l3afpad.py <path-to-l3afpad>

l3afpad is a GTK+3 GUI text editor.  Its ``parse_args()`` builds a
``GOptionContext`` that includes ``gtk_get_option_group(TRUE)``, so GTK opens
the default display *during* option parsing — meaning **every** invocation,
including ``--version``, needs a display.  (Verified on device: the binary
prints ``l3afpad: Cannot open display:`` and exits 255.)

Without a display the meaningful consumer-level assertions are therefore:

1. the packaged binary is a genuine aarch64 ELF (not a host artifact);
2. running it resolves the *entire* GTK+3 shared-library closure — a missing
   ``libgtk-3.so.0`` or an ABI/symbol mismatch would surface as
   "Error loading shared library ..." / "symbol not found" first;
3. execution proceeds all the way to GTK display initialisation and fails
   there, and only there.

The GTK closure is deliberately large (gtk3 + gdk + pango + cairo + gdk-pixbuf
+ harfbuzz + freetype + fontconfig + png/jpeg/tiff/webp ...), so (2) is a real
integration check of the packaged dependency chain.
"""
import os
import struct
import subprocess
import sys


def main():
    binary = sys.argv[1]
    assert os.path.isfile(binary), binary
    assert os.access(binary, os.X_OK), "l3afpad is not executable"

    # 1) Real aarch64 ELF, not a host build artifact.
    with open(binary, "rb") as fh:
        head = fh.read(20)
    assert head[:4] == b"\x7fELF", "not an ELF binary"
    assert head[4] == 2, "not a 64-bit ELF"
    machine = struct.unpack("<H", head[18:20])[0]
    assert machine == 0xB7, "not an aarch64 ELF (e_machine=%#x)" % machine
    print("aarch64 ELF verified")

    # 2+3) Run the editor with arguments and capture everything.
    result = subprocess.run([binary, "--tab-width", "4", "--jump", "10"],
                            capture_output=True, text=True, timeout=300)
    text = (result.stdout or "") + (result.stderr or "")

    # The whole GTK+3 closure must have resolved.
    for bad in ("Error loading shared library",
                "symbol not found",
                "undefined symbol",
                "error while loading shared libraries"):
        assert bad not in text, "dynamic link failure: %s" % text

    # And execution must reach — and stop at — display initialisation.
    assert "Cannot open display" in text, text
    print("GTK+3 closure resolved; stopped at display init as expected")
    print("L3AFPAD-CONSUMER-OK")


main()
