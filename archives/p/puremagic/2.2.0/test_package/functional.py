#!/usr/bin/env python3
"""Check core puremagic behavior through the installed Conan package."""

import json
import os
import sys


def main():
    package_folder, report_path = sys.argv[1:3]
    sys.path.insert(0, os.path.join(package_folder, "lib", "python"))
    import puremagic

    assertions = 0

    png_matches = puremagic.magic_string(b"\x89PNG\r\n\x1a\n")
    assert any(match.extension == ".png" for match in png_matches)
    assertions += 1

    assert puremagic.from_string(b"%PDF-1.7") == ".pdf"
    assertions += 1

    extension_matches = puremagic.magic_extension(".png")
    assert extension_matches and all(
        match.extension == ".png" for match in extension_matches)
    assertions += 1

    image_path = os.path.join(os.path.dirname(report_path), "sample.png")
    try:
        with open(image_path, "wb") as image_file:
            image_file.write(b"\x89PNG\r\n\x1a\n")
        file_matches = puremagic.magic_file(image_path)
    finally:
        if os.path.exists(image_path):
            os.remove(image_path)
    assert any(match.extension == ".png" for match in file_matches)
    assertions += 1

    result = {
        "consumer_scenarios": 4,
        "api_calls": 4,
        "assertions": assertions,
        "passed": True,
    }
    with open(report_path, "w", encoding="utf-8") as report_file:
        json.dump(result, report_file, sort_keys=True)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
