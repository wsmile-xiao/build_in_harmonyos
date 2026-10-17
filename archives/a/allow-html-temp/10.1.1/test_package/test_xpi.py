import hashlib
import json
import os
import sys
import zipfile


def check(condition, message):
    if not condition:
        raise AssertionError(message)
    print(f"PASS: {message}")


def main():
    package_folder = sys.argv[1]
    xpi = os.path.join(package_folder, "share", "allow-html-temp", "allow-html-temp-10.1.1.xpi")
    check(os.path.isfile(xpi), "XPI is installed")
    check(os.path.getsize(xpi) > 10000, "XPI is non-empty")

    with zipfile.ZipFile(xpi) as archive:
        names = archive.namelist()
        check(archive.testzip() is None, "ZIP CRC validation succeeds")
        check(names == sorted(names), "archive entries are deterministically ordered")
        check("manifest.json" in names, "manifest.json is packaged at archive root")
        manifest = json.loads(archive.read("manifest.json"))
        check(manifest["version"] == "10.1.1", "manifest version is 10.1.1")
        check(manifest["manifest_version"] == 2, "WebExtension manifest version is 2")
        check(manifest["applications"]["gecko"]["id"] == "{532269cf-a10e-4396-8613-b5d9a9a516d4}", "extension identifier is preserved")
        required = {
            "scripts/background.js",
            "options/options_ui.html",
            "api/allowHtmlTemp/implementation.js",
            "api/messageContentPolicy/schema.json",
            "_locales/en/messages.json",
            "icons/aht_icon.svg",
        }
        check(required.issubset(names), "runtime scripts, APIs, locale, options and icon are packaged")
        check(all(info.date_time == (1980, 1, 1, 0, 0, 0) for info in archive.infolist()), "archive timestamps are reproducible")

    digest = hashlib.sha256(open(xpi, "rb").read()).hexdigest()
    print(f"allow-html-temp 10.1.1: 10/10 checks passed; sha256={digest}")


if __name__ == "__main__":
    main()
