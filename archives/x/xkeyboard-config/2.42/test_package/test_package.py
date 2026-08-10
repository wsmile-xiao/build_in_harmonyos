#!/usr/bin/env python3
"""Consumer validation for xkeyboard-config 2.42.

Verifies that installed XKB data is complete and discoverable:
  - rules/base.xml, rules/evdev.xml exist
  - rules/base.lst, rules/evdev.lst exist
  - symbols/, keycodes/, compat/, types/, geometry/ directories exist
  - pkg-config file (xkeyboard-config.pc) is installed and resolvable
"""
import os
import sys


def main():
    pkg_folder = sys.argv[1] if len(sys.argv) > 1 else ""

    errors = []

    # XKB base directory
    xkb_base = os.path.join(pkg_folder, "share", "X11", "xkb")
    if not os.path.isdir(xkb_base):
        errors.append(f"XKB base directory not found: {xkb_base}")
        print(f"FAIL: {errors[-1]}")
        sys.exit(1)

    # Check rules directory
    rules_dir = os.path.join(xkb_base, "rules")
    expected_rules_files = [
        "base.xml", "base.lst", "base.extras.xml",
        "evdev.xml", "evdev.lst", "evdev.extras.xml",
    ]
    for f in expected_rules_files:
        path = os.path.join(rules_dir, f)
        if not os.path.isfile(path):
            errors.append(f"Missing rules file: {f}")
        else:
            print(f"OK: rules/{f}")

    # Check XKB data directories
    expected_dirs = ["symbols", "keycodes", "compat", "types", "geometry"]
    for d in expected_dirs:
        path = os.path.join(xkb_base, d)
        if not os.path.isdir(path):
            errors.append(f"Missing XKB directory: {d}")
        else:
            file_count = sum(1 for _ in os.scandir(path) if _.is_file())
            print(f"OK: {d}/ ({file_count} files)")
            if file_count == 0:
                errors.append(f"Empty XKB directory: {d}")

    # Check pkg-config file
    pc_path = os.path.join(pkg_folder, "share", "pkgconfig", "xkeyboard-config.pc")
    if not os.path.isfile(pc_path):
        errors.append(f"Missing pkg-config file: xkeyboard-config.pc")
    else:
        print("OK: pkgconfig/xkeyboard-config.pc")
        # Verify pkg-config file content
        with open(pc_path) as f:
            content = f.read()
        if "xkb_base" not in content:
            errors.append("pkg-config file missing xkb_base variable")

    # Check man page
    man_path = os.path.join(pkg_folder, "share", "man", "man7", "xkeyboard-config.7")
    if not os.path.isfile(man_path):
        print("WARN: man page not found (xsltproc may not have been available)")
    else:
        print("OK: man/man7/xkeyboard-config.7")

    if errors:
        print(f"\nFAILED with {len(errors)} error(s):")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("\nAll checks passed.")
        sys.exit(0)


if __name__ == "__main__":
    main()
