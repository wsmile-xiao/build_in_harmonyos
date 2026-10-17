#!/usr/bin/env python3
"""Bundle-layout smoke test for Affiche."""

import os
import sys


def find_entry(root, needle):
    for dirpath, dirnames, filenames in os.walk(root):
        for entry in dirnames + filenames:
            if needle in entry:
                return os.path.join(dirpath, entry)
    return ""


def main():
    bundle = sys.argv[1]
    assert os.path.isdir(bundle), f"Affiche.app bundle missing: {bundle}"
    package_root = os.path.dirname(os.path.dirname(os.path.dirname(bundle)))
    launcher = os.path.join(package_root, "bin", "Affiche")
    assert os.path.isfile(launcher), f"Affiche launcher missing: {launcher}"
    assert os.access(launcher, os.X_OK), f"Affiche launcher is not executable: {launcher}"

    executable = os.path.join(bundle, "Affiche")
    assert os.path.isfile(executable), f"Affiche executable missing: {executable}"
    assert os.access(executable, os.X_OK), f"Affiche executable is not executable: {executable}"

    expected = {
        "bundle plist": ("AfficheInfo.plist", "Info-gnustep.plist"),
        "desktop entry": ("Affiche.desktop",),
        "localization": ("Localizable.strings", "InfoPlist.strings"),
        "image": (".tiff",),
    }
    for label, needles in expected.items():
        found = ""
        for needle in needles:
            found = find_entry(bundle, needle)
            if found:
                break
        assert found, f"{label} not found under {bundle}"
        print(f"{label}: {found}")

    print("affiche bundle smoke test passed")


if __name__ == "__main__":
    main()
