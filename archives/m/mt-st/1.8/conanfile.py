#!/usr/bin/env python3
"""Conan recipe for mt-st 1.8 - Linux SCSI tape driver control tools.

Builds the two upstream programs from a plain hand-written Makefile:

* ``mt``     - tape control (a Linux SCSI-tape-aware replacement for GNU mt)
* ``stinit`` - boot-time initialisation of SCSI tape drive modes

There are no third-party dependencies.  The OHOS sysroot provides every header
the sources use (``<linux/major.h>``, ``<scsi/sg.h>``, ``<sys/sysmacros.h>``,
``<sys/utsname.h>``, ``<libgen.h>``), and the sources ship their own sanitised
``mtio.h``.

The upstream ``make check`` uses shelltestrunner (``shelltest``), a Haskell
program that is not available on OHOS nor on the CI worker.  The recipe instead
runs the very same upstream ``tests/*.test`` definitions through an embedded,
dependency-free runner implementing shelltestrunner's format-1 semantics
(including the ``-DVERSION`` macro substitution).  See ``_UPSTREAM_RUNNER``.
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy, export_conandata_patches,
                               get, save)
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"

# shelltestrunner-compatible runner for the upstream tests (format 1).
_UPSTREAM_RUNNER = r'''
#!/usr/bin/env python3
"""A dependency-free runner for mt-st's upstream tests (shelltestrunner format 1).

The upstream ``make check`` target runs::

    shelltest -DVERSION=<version> tests

``shelltest`` (shelltestrunner) is a Haskell program that is not available on
OHOS and not on the CI worker, so this runner implements the exact subset of
shelltestrunner's *format 1* semantics that the upstream ``tests/*.test``
files use:

    COMMAND
    >>>  /regex/            # expected stdout (regex, unanchored) ...
    >>>2 /regex/            # expected stderr
    >>>= 0                 # expected exit status

``-D NAME=VALUE`` macros are substituted textually before parsing, exactly like
shelltestrunner's ``--defmacro`` (the upstream Makefile passes
``-DVERSION=$(VERSION)``, which is why the files contain ``/VERSION/``).
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


class Case:
    def __init__(self, cmd: str, lineno: int):
        self.cmd = cmd
        self.lineno = lineno
        self.out: list[str] = []
        self.err: list[str] = []
        self.code: str | None = None


def parse(path: Path, macros: dict[str, str]) -> list[Case]:
    text = path.read_text(encoding="utf-8", errors="replace")
    for name, value in macros.items():
        text = re.sub(r"\b" + re.escape(name) + r"\b", value, text)
    cases: list[Case] = []
    cur: Case | None = None
    mode: str | None = None
    for idx, raw in enumerate(text.splitlines(), start=1):
        line = raw.rstrip("\r")
        stripped = line.strip()
        if stripped.startswith(">>>"):
            if stripped.startswith(">>>="):
                assert cur is not None
                cur.code = stripped[len(">>>="):].strip()
                mode = None
            elif stripped.startswith(">>>2"):
                assert cur is not None
                mode = "err"
                rest = stripped[len(">>>2"):].strip()
                if rest:
                    cur.err.append(rest)
            else:
                assert cur is not None
                mode = "out"
                rest = stripped[len(">>>"):].strip()
                if rest:
                    cur.out.append(rest)
            continue
        if stripped == "" or stripped.startswith("#"):
            mode = None
            cur = None
            continue
        if mode == "out":
            cur.out.append(line)
        elif mode == "err":
            cur.err.append(line)
        else:
            cur = Case(stripped, idx)
            cases.append(cur)
            mode = None
    return cases


def _match_stream(expected: list[str], actual: str) -> bool:
    if not expected:
        return True  # not specified => ignored, per shelltestrunner
    if len(expected) == 1 and expected[0].startswith("/") and expected[0].endswith("/"):
        return re.search(expected[0][1:-1], actual) is not None
    return actual.rstrip("\n") == "\n".join(expected)


def _match_code(expected: str | None, rc: int) -> bool:
    if expected is None or expected == "":
        return True
    if expected.startswith("/") and expected.endswith("/"):
        return re.search(expected[1:-1], str(rc)) is not None
    return str(rc) == expected


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="tests", help="directory containing *.test")
    ap.add_argument("--cwd", default=".", help="working directory for the commands")
    ap.add_argument("--macro", action="append", default=[],
                    help="NAME=VALUE macro substitution (like shelltest -D)")
    args = ap.parse_args()

    macros: dict[str, str] = {}
    for m in args.macro:
        name, _, value = m.partition("=")
        macros[name] = value

    test_dir = Path(args.cwd) / args.dir
    files = sorted(test_dir.glob("*.test"))
    if not files:
        print(f"FAIL: no *.test files found under {test_dir}", file=sys.stderr)
        return 1

    total = passed = 0
    failures: list[str] = []
    for path in files:
        for case in parse(path, macros):
            total += 1
            proc = subprocess.run(case.cmd, shell=True, cwd=args.cwd,
                                  capture_output=True, text=True)
            ok = (_match_stream(case.out, proc.stdout)
                  and _match_stream(case.err, proc.stderr)
                  and _match_code(case.code, proc.returncode))
            if ok:
                passed += 1
                print(f"[OK]   {path.name}:{case.lineno}: {case.cmd}")
            else:
                failures.append(f"{path.name}:{case.lineno}: {case.cmd}")
                print(f"[FAIL] {path.name}:{case.lineno}: {case.cmd}")
                print(f"       exit={proc.returncode}")
                if case.out:
                    print(f"       stdout={proc.stdout!r}")
                if case.err:
                    print(f"       stderr={proc.stderr!r}")

    print(f"\nUPSTREAM TESTS: {passed}/{total} passed, {total - passed} failed")
    if failures:
        for f in failures:
            print(f"FAILED: {f}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''


class MtStConan(ConanFile):
    name = "mt-st"
    version = "1.8"
    description = ("Linux SCSI tape driver aware magnetic tape control "
                   "(mt + stinit)")
    license = "GPL-2.0-only"
    homepage = "https://github.com/iustin/mt-st"
    url = ""

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "mt-st OHOS adaptation is validated on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler(self, name, fallback):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        return executables.get(name) or fallback

    def build(self):
        apply_conandata_patches(self)
        cc = self._compiler("c", "clang")
        self.run('make CC="{}" CFLAGS="-Wall -O2" -j1'.format(cc),
                 cwd=self.source_folder)
        for prog in ("mt", "stinit"):
            if not os.path.isfile(os.path.join(self.source_folder, prog)):
                raise ConanInvalidConfiguration(
                    "build did not produce the '{}' program".format(prog))

        runner = os.path.join(self.build_folder, "run_upstream_tests.py")
        save(self, runner, _UPSTREAM_RUNNER)
        # Run the upstream shelltest suite (31 cases); fails the build on any
        # non-conforming case.
        self.run('"{}" "{}" --cwd "{}" --dir tests --macro VERSION={}'.format(
            sys.executable, runner, self.source_folder, self.version))

    def package(self):
        copy(self, "mt", self.source_folder,
             os.path.join(self.package_folder, "bin"))
        copy(self, "stinit", self.source_folder,
             os.path.join(self.package_folder, "bin"))
        copy(self, "mt.1", self.source_folder,
             os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "stinit.8", self.source_folder,
             os.path.join(self.package_folder, "share", "man", "man8"))
        copy(self, "stinit.def.examples", self.source_folder,
             os.path.join(self.package_folder, "share", "mt-st"))
        copy(self, "mt-st.bash_completion", self.source_folder,
             os.path.join(self.package_folder, "share", "mt-st"))
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
