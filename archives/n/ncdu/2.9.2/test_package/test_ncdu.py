#!/usr/bin/env python3
"""Exercise the installed ncdu binary in non-interactive export mode."""

import json
import pathlib
import shutil
import subprocess
import sys


def run_checked(command):
    result = subprocess.run(
        command,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"command failed ({result.returncode}): {command!r}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result.stdout


def collect_entries(value, entries):
    if isinstance(value, dict):
        name = value.get("name")
        if isinstance(name, str):
            entries[name] = value
        for child in value.values():
            collect_entries(child, entries)
    elif isinstance(value, list):
        for child in value:
            collect_entries(child, entries)


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: test_ncdu.py <ncdu> <workdir>")

    executable = pathlib.Path(sys.argv[1]).resolve()
    workdir = pathlib.Path(sys.argv[2]).resolve()
    assert executable.is_file(), f"missing ncdu executable: {executable}"

    version = run_checked([str(executable), "--version"]).strip()
    assert version == "ncdu 2.9.2", version

    help_text = run_checked([str(executable), "--help"])
    assert "-o FILE" in help_text, help_text
    assert "Export scanned directory" in help_text, help_text

    fixture = workdir / "ncdu-fixture"
    export_file = workdir / "ncdu-export.json"
    if fixture.exists():
        shutil.rmtree(fixture)
    if export_file.exists():
        export_file.unlink()
    (fixture / "nested").mkdir(parents=True)
    (fixture / "alpha.txt").write_bytes(b"A" * 17)
    (fixture / "nested" / "beta.bin").write_bytes(b"B" * 31)

    run_checked(
        [
            str(executable),
            "--ignore-config",
            "--apparent-size",
            "-0",
            "-o",
            str(export_file),
            str(fixture),
        ]
    )
    assert export_file.is_file() and export_file.stat().st_size > 0

    exported = json.loads(export_file.read_text(encoding="utf-8"))
    assert exported[0:2] == [1, 2], exported[0:2]
    entries = {}
    collect_entries(exported, entries)
    assert "alpha.txt" in entries, sorted(entries)
    assert "beta.bin" in entries, sorted(entries)
    assert entries["alpha.txt"].get("asize") == 17, entries["alpha.txt"]
    assert entries["beta.bin"].get("asize") == 31, entries["beta.bin"]

    print("ncdu consumer test passed: version, help, scan, and JSON export")


if __name__ == "__main__":
    main()
