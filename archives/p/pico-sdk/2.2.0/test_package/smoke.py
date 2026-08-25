#!/usr/bin/env python3
"""Consumer smoke test for pico-sdk's packaged pioasm tool."""
import os
import pathlib
import subprocess
import sys


def main() -> int:
    if len(sys.argv) != 4:
        print("usage: smoke.py <pioasm> <input.pio> <output.h>", file=sys.stderr)
        return 2

    pioasm = pathlib.Path(sys.argv[1])
    pio_source = pathlib.Path(sys.argv[2])
    header = pathlib.Path(sys.argv[3])
    if not pioasm.is_file():
        raise RuntimeError(f"pioasm executable missing: {pioasm}")
    sdk_path = os.environ.get("PICO_SDK_PATH")
    if not sdk_path:
        raise RuntimeError("PICO_SDK_PATH missing")

    version_file = pathlib.Path(sdk_path) / "pico_sdk_version.cmake"
    if not version_file.is_file():
        raise RuntimeError(f"pico_sdk_version.cmake missing under {sdk_path}")

    subprocess.run([str(pioasm), "--version"], check=True)
    subprocess.run([str(pioasm), "-o", "c-sdk", "-v", "0", str(pio_source), str(header)], check=True)

    generated = header.read_text(encoding="utf-8")
    for marker in ("conandata_smoke_program", "conandata_smoke_wrap_target"):
        if marker not in generated:
            raise RuntimeError(f"pioasm generated header is missing {marker}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())