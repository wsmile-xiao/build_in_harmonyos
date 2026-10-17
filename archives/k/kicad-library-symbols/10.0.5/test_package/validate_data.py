#!/usr/bin/env python3
"""Validate the installed kicad-library-symbols package contents.

Pure data-integrity validation (upstream ships no executable test suite):

  1. share/kicad/symbols/ exists and is populated
  2. every symbol library is well-formed s-expression data:
     - packed mode: <Lib>.kicad_sym single files
       (header line "(kicad_symbol_lib", footer ")", >= 1 symbol)
     - unpacked mode: <Lib>.kicad_symdir directories holding non-empty
       <Symbol>.kicad_sym files
  3. reference libraries are present (Device, power, Connector,
     MCU_ST_STM32F4, Simulation_SPICE)
  4. share/kicad/template/sym-lib-table parses and references >= 100 libs
  5. the Simulation_SPICE.sp simulation model is installed and non-empty

Exit code 0 = all checks passed; nonzero = at least one failure.
"""
import os
import sys

failures = []
passes = 0

REQUIRED_LIBS = [
    "Device",
    "power",
    "Connector",
    "MCU_ST_STM32F4",
    "Simulation_SPICE",
]


def check(condition, message):
    global passes
    if condition:
        passes += 1
        print(f"PASS: {message}")
    else:
        failures.append(message)
        print(f"FAIL: {message}")


def inspect_packed_file(path):
    """Return (symbol_count, ok) for a packed .kicad_sym file."""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            lines = handle.readlines()
    except OSError as err:
        return 0, False
    if not lines:
        return 0, False
    if not lines[0].startswith("(kicad_symbol_lib"):
        return 0, False
    tail = lines[-1].strip() if lines[-1].strip() else lines[-2].strip()
    if tail != ")":
        return 0, False
    symbols = sum(1 for line in lines if line.startswith("\t(symbol "))
    return symbols, symbols >= 1


def main(package_root):
    symbols_dir = os.path.join(package_root, "share", "kicad", "symbols")
    template_dir = os.path.join(package_root, "share", "kicad", "template")

    check(os.path.isdir(symbols_dir),
          f"symbols directory installed at {symbols_dir}")
    if not os.path.isdir(symbols_dir):
        return 1

    entries = sorted(os.listdir(symbols_dir))
    check(len(entries) >= 100,
          f"symbol library entries installed: {len(entries)} (>= 100)")

    packed = [e for e in entries if e.endswith(".kicad_sym")]
    unpacked = [e for e in entries if e.endswith(".kicad_symdir")]

    total_symbols = 0
    malformed = []

    if packed:
        print(f"INFO: install mode = packed (.kicad_sym), libraries = {len(packed)}")
        for lib in packed:
            symbols, ok = inspect_packed_file(os.path.join(symbols_dir, lib))
            if not ok:
                malformed.append(lib)
            total_symbols += symbols
        check(not malformed,
              f"all {len(packed)} packed libraries well-formed "
              f"(malformed: {malformed[:5]})")
        missing = [name for name in REQUIRED_LIBS
                   if f"{name}.kicad_sym" not in packed]
        check(not missing, f"required libraries present (missing: {missing})")
    elif unpacked:
        print(f"INFO: install mode = unpacked (.kicad_symdir), libraries = {len(unpacked)}")
        empty_dirs = []
        for lib in unpacked:
            lib_path = os.path.join(symbols_dir, lib)
            members = [m for m in os.listdir(lib_path) if m.endswith(".kicad_sym")]
            if not members:
                empty_dirs.append(lib)
                continue
            for member in members:
                symbols, ok = inspect_packed_file(os.path.join(lib_path, member))
                if not ok:
                    malformed.append(f"{lib}/{member}")
                total_symbols += symbols
        check(not empty_dirs, f"no empty symdir libraries (empty: {empty_dirs[:5]})")
        check(not malformed,
              f"all unpacked symbol files well-formed (malformed: {malformed[:5]})")
        missing = [name for name in REQUIRED_LIBS
                   if f"{name}.kicad_symdir" not in unpacked]
        check(not missing, f"required libraries present (missing: {missing})")
    else:
        print("FAIL: no .kicad_sym files or .kicad_symdir directories found")
        return 1

    check(total_symbols >= 1000,
          f"total symbol definitions found: {total_symbols} (>= 1000)")

    table_path = os.path.join(template_dir, "sym-lib-table")
    check(os.path.isfile(table_path),
          f"global sym-lib-table installed at {table_path}")
    if os.path.isfile(table_path):
        with open(table_path, "r", encoding="utf-8") as handle:
            table_lines = handle.readlines()
        check(table_lines and table_lines[0].startswith("(sym_lib_table"),
              "sym-lib-table starts with the (sym_lib_table header")
        table_entries = sum(1 for line in table_lines if line.strip().startswith("(lib "))
        check(table_entries >= 100,
              f"sym-lib-table declares {table_entries} libraries (>= 100)")

    spice_model = os.path.join(symbols_dir, "Simulation_SPICE.sp")
    check(os.path.isfile(spice_model) and os.path.getsize(spice_model) > 0,
          "SPICE simulation model Simulation_SPICE.sp installed and non-empty")

    print(f"SUMMARY: {passes} checks passed, {len(failures)} failed")
    if failures:
        print(f"RESULT: FAIL — {failures}")
        return 1
    print("RESULT: PASS — kicad-library-symbols data package is complete")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <package_folder>")
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
