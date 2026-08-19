#!/usr/bin/env python3
"""Integration tests for installed Transmission 4.1.3 command-line utilities."""

import os
import subprocess
import sys
import tempfile


def run(command):
    result = subprocess.run(command, check=True, text=True, capture_output=True)
    return result.stdout + result.stderr


def check(condition, message):
    if not condition:
        raise AssertionError(message)
    print(f"PASS: {message}")


def main():
    package = sys.argv[1]
    bindir = os.path.join(package, "bin")
    create = os.path.join(bindir, "transmission-create")
    edit = os.path.join(bindir, "transmission-edit")
    show = os.path.join(bindir, "transmission-show")

    for executable in (create, edit, show):
        check(os.path.isfile(executable), f"{os.path.basename(executable)} is installed")

    installed_tools = sorted(
        name for name in os.listdir(bindir) if os.path.isfile(os.path.join(bindir, name))
    )
    check(
        installed_tools
        == ["transmission-create", "transmission-edit", "transmission-show"],
        "bin contains exactly the three requested Transmission utilities",
    )
    for directory in ("include", "lib", "share"):
        check(
            not os.path.exists(os.path.join(package, directory)),
            f"application package does not contain a {directory} directory",
        )

    version_outputs = [run([tool, "--version"]) for tool in (create, edit, show)]
    check(all("4.1.3" in output for output in version_outputs), "all utilities report version 4.1.3")

    with tempfile.TemporaryDirectory(prefix="transmission-extra-") as work:
        payload = os.path.join(work, "payload.txt")
        torrent = os.path.join(work, "payload.torrent")
        with open(payload, "w", encoding="utf-8") as stream:
            stream.write("HarmonyOS PC transmission-extra consumer test\n" * 16)

        run([create, "-o", torrent, "-c", "OHOS consumer test", payload])
        check(os.path.isfile(torrent) and os.path.getsize(torrent) > 0, "transmission-create produces a torrent")

        initial = run([show, torrent])
        check("payload.txt" in initial, "transmission-show reports the payload name")
        check("OHOS consumer test" in initial, "transmission-show reports the comment")

        tracker = "https://tracker.example.invalid/announce"
        run([edit, "-a", tracker, torrent])
        updated = run([show, torrent])
        check(tracker in updated, "transmission-edit adds a tracker visible to transmission-show")

    print("transmission-extra 4.1.3: 12/12 consumer checks passed")


if __name__ == "__main__":
    main()
