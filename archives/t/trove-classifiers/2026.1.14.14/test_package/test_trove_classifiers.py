#!/usr/bin/env python3
"""Deterministic consumer checks for the packaged public API and CLI."""

import os
from pathlib import Path
import subprocess
import sys

import trove_classifiers


checks = 0


def check(condition, message):
    global checks
    if not condition:
        raise AssertionError(message)
    checks += 1


sorted_classifiers = trove_classifiers.sorted_classifiers
classifiers = trove_classifiers.classifiers
deprecated = trove_classifiers.deprecated_classifiers
all_classifiers = trove_classifiers.all_classifiers

check(len(sorted_classifiers) == 887, "sorted classifier count mismatch")
check(len(classifiers) == 887, "classifier set count mismatch")
check(len(deprecated) == 8, "deprecated classifier count mismatch")
check(len(all_classifiers) == 895, "all classifier count mismatch")
check(
    sorted_classifiers.index("Programming Language :: Python :: 3.9")
    < sorted_classifiers.index("Programming Language :: Python :: 3.10"),
    "natural version ordering mismatch",
)
check(len(set(sorted_classifiers)) == 887, "classifier list has duplicates")
check(classifiers == set(sorted_classifiers), "set and list differ")
check(
    sorted_classifiers[0] == "Development Status :: 1 - Planning",
    "first classifier mismatch",
)
check(sorted_classifiers[-1] == "Typing :: Typed", "last classifier mismatch")
check(
    "License :: OSI Approved :: Apache Software License" in classifiers,
    "Apache license classifier missing",
)
check(
    "Programming Language :: Python :: 3" in classifiers,
    "Python 3 classifier missing",
)
check("Typing :: Typed" in classifiers, "typing classifier missing")
check(
    "Fuzzy :: Wuzzy :: Was :: A :: Bear" not in classifiers,
    "invalid classifier unexpectedly present",
)
check(
    "Natural Language :: Ukranian" in deprecated,
    "known deprecated classifier missing",
)
check(
    deprecated["Natural Language :: Ukranian"]
    == ["Natural Language :: Ukrainian"],
    "deprecated replacement mismatch",
)
check(
    "Natural Language :: Ukranian" in all_classifiers,
    "deprecated classifier missing from all_classifiers",
)
check(
    set(all_classifiers) == set(sorted_classifiers) | set(deprecated),
    "all_classifiers does not match active and deprecated classifiers",
)

module_run = subprocess.run(
    [sys.executable, "-m", "trove_classifiers"],
    capture_output=True,
    text=True,
    check=False,
)
check(module_run.returncode == 0, "module CLI failed")
module_lines = module_run.stdout.splitlines()
check(module_lines == sorted_classifiers, "module CLI output mismatch")
check(module_run.stderr == "", "module CLI wrote to stderr")

command = None
for path_entry in os.environ.get("PATH", "").split(os.pathsep):
    candidate = Path(path_entry) / "trove-classifiers"
    if candidate.is_file():
        command = candidate
        break

check(command is not None, "packaged console entry point not found")
entry_run = subprocess.run(
    [sys.executable, str(command)],
    capture_output=True,
    text=True,
    check=False,
)
check(entry_run.returncode == 0, "packaged console entry point failed")
check(entry_run.stdout == module_run.stdout, "entry point output mismatch")
check(entry_run.stderr == "", "entry point wrote to stderr")

expected_checks = 24
if checks != expected_checks:
    raise AssertionError(
        f"consumer assertion count mismatch: expected {expected_checks}, got {checks}"
    )

print(
    "PASS: trove-classifiers packaged API and CLI consumer test "
    f"({checks}/{expected_checks} assertions)"
)
