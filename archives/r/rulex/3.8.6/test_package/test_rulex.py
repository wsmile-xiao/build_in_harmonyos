#!/usr/bin/env python3
"""Run packaged RuLex CLI, locale fallback, and full upstream data tests."""

import os
from pathlib import Path
import subprocess
import sys


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def run(command, environment):
    return subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=environment,
        check=False,
    )


def main():
    if len(sys.argv) != 6:
        raise RuntimeError("expected lexholder, databases, fixture and output path")

    lexholder, _consumer_db, installed_db, upstream_data, output_dir = sys.argv[1:]
    environment = os.environ.copy()
    environment.update({"LANG": "C", "LC_ALL": "C"})

    help_result = run([lexholder, "-h"], environment)
    help_text = help_result.stdout + help_result.stderr
    require(help_result.returncode == 0, "lexholder help failed without KOI8-R locale")
    require(b"Lexical database holding utility" in help_text, "help text missing")

    uppercase_word = b"\xE1\xE1\xF2\xEF\xEE\xE1".decode(
        sys.getfilesystemencoding(), "surrogateescape"
    )
    query_result = run(
        [lexholder, "-s", uppercase_word, installed_db], environment
    )
    require(query_result.returncode == 0, "KOI8-R uppercase query failed")
    require(
        query_result.stdout == b"\xC1\xC1\xD2\xCF+\xCE\xC1\n",
        "KOI8-R case folding mismatch",
    )

    mismatch_dump = Path(output_dir) / "packaged-lexicon.dump"
    suite_result = run(
        [
            lexholder,
            "-v",
            "-f",
            str(mismatch_dump),
            "-t",
            upstream_data,
            installed_db,
        ],
        environment,
    )
    suite_text = suite_result.stdout + suite_result.stderr
    require(suite_result.returncode == 0, "packaged upstream suite failed")
    require(b"430015 words have been checked" in suite_text, "upstream count mismatch")
    require(b"No mismatches found" in suite_text, "upstream mismatch reported")
    require(
        mismatch_dump.exists() and mismatch_dump.stat().st_size == 0,
        "upstream mismatch dump is not empty",
    )

    print("rulex packaged upstream tests: 430015/430015 passed")
    print("rulex HarmonyOS locale fallback checks: 4/4 passed")


if __name__ == "__main__":
    main()
