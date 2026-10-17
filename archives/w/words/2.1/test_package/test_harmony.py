#!/usr/bin/env python3
"""HarmonyOS PC integration check using an attached HDC target."""

import argparse
import os
import shutil
import subprocess
from pathlib import Path


REMOTE_DIR = "/data/local/tmp/words-2.1"
FILES = (
    "american-english",
    "british-english",
    "catala",
    "finnish",
    "french",
    "italian",
    "ngerman",
    "ogerman",
    "spanish",
    "british",
    "catalan",
    "german",
    "usa",
)


def run(command, *, check=True):
    return subprocess.run(
        command,
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    ).stdout.strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("package_folder", type=Path)
    parser.add_argument("--hdc", default=os.environ.get("HDC") or shutil.which("hdc"))
    parser.add_argument("--native-consumer", type=Path)
    args = parser.parse_args()
    if not args.hdc:
        raise SystemExit("HDC unavailable: set HDC to the HarmonyOS SDK hdc executable")

    targets = run([args.hdc, "list", "targets"]).splitlines()
    targets = [line.strip() for line in targets if line.strip() and line.strip() != "[Empty]"]
    if not targets:
        raise SystemExit("no HDC target is connected; attach the HarmonyOS PC emulator")
    if len(targets) != 1:
        raise SystemExit(f"expected one HDC target, found {len(targets)}: {targets}")
    target = targets[0]

    api_level = run([args.hdc, "-t", target, "shell", "param", "get", "const.ohos.apiversion"])
    if not api_level.isdigit() or int(api_level) <= 0:
        raise SystemExit(f"target has no valid OpenHarmony API level: {api_level!r}")

    dictionary_dir = args.package_folder / "share" / "dict"
    run([args.hdc, "-t", target, "shell", "mkdir", "-p", REMOTE_DIR + "/share/dict"])
    for name in FILES:
        local_file = dictionary_dir / name
        run([args.hdc, "-t", target, "file", "send", str(local_file), REMOTE_DIR + "/share/dict/" + name])

    remote = REMOTE_DIR + "/share/dict"
    for name in FILES:
        run([args.hdc, "-t", target, "shell", "test", "-s", remote + "/" + name])
    if args.native_consumer:
        if not args.native_consumer.is_file():
            raise SystemExit(f"native consumer binary does not exist: {args.native_consumer}")
        remote_consumer = REMOTE_DIR + "/test_words_native"
        run([args.hdc, "-t", target, "file", "send", str(args.native_consumer), remote_consumer])
        run([args.hdc, "-t", target, "shell", "chmod", "755", remote_consumer])
        lookups = (
            ("american-english", "color"),
            ("british-english", "colour"),
            ("spanish", "hola"),
        )
        for filename, word in lookups:
            run([args.hdc, "-t", target, "shell", remote_consumer, remote + "/" + filename, word])
    else:
        run([args.hdc, "-t", target, "shell", "grep", "-Fx", "color", remote + "/american-english"])
        run([args.hdc, "-t", target, "shell", "grep", "-Fx", "colour", remote + "/british-english"])
        run([args.hdc, "-t", target, "shell", "grep", "-Fx", "hola", remote + "/spanish"])
    print(f"HarmonyOS PC (OpenHarmony API {api_level}) accepted the packaged dictionaries and language lookups")


if __name__ == "__main__":
    main()
