#!/usr/bin/env python3
"""Conan test_package — libequihash 1.0.10 (consumer view).

Compiles test_equihash.c against the packaged library and runs 4 real
API checks (solsize formula value, solve on a fixed seed, verify-accept,
verify-reject on a tampered solution) with tiny parameters (N=24/K=3) so
solve() finishes in milliseconds.

Evidence markers (parsed from the real binary output, emitted every run
so they survive Conan cache hits):
- HMBS_TEST_PACKAGE_RESULT: discovered/passedCount from the binary's
  "RESULT: N passed, M failed" trailer line.
- HMBS_UPSTREAM_TEST_RESULT: status=no_tests. Upstream ships no test
  suite (no check/test target, no tests/ directory; python/test.py is an
  assertion-free bindings demo; audit in test_package/MANIFEST.yml).
"""

import json
import os
import re
import shlex

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.files import copy
from conan.tools.layout import basic_layout


class LibequihashTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        # Copy the C test source into the build folder so it is self-contained.
        if os.path.normpath(self.source_folder) != os.path.normpath(self.build_folder):
            copy(self, "test_equihash.c", self.source_folder, self.build_folder)
        # R33: toolchain from Conan conf, never from shell env.
        # Same basename resolution as the main recipe: absolute HNP paths
        # are "inaccessible or not found" under preflight /bin/sh; hmbs
        # buildenv PATH guarantees lookup.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        _cpp = compilers.get("cpp") or "clang++"
        cxx = os.path.basename(_cpp) if "/" in _cpp else _cpp
        eq = self.dependencies["libequihash"]
        eq_inc = os.path.join(eq.package_folder, "include")
        eq_lib = os.path.join(eq.package_folder, "lib")
        src = os.path.join(self.build_folder, "test_equihash.c")
        out = os.path.join(self.build_folder, "test_equihash")
        # C++ driver: the static lib holds C++ objects (the public header
        # has no extern "C" guard; the test wraps the include itself).
        # No -lsodium: the hash (keyless BLAKE2b) is vendored inside libequihash.
        self.run(
            '"%s" -O2 -I"%s" -L"%s" "%s" -o "%s" -lequihash'
            % (cxx, eq_inc, eq_lib, src, out),
            env="conanbuild",
        )

    def test(self):
        if can_run(self):
            tmpdir = (
                os.environ.get("TMPDIR")
                or os.environ.get("TMP")
                or os.environ.get("TEMP")
                or os.path.join(self.build_folder, ".tmp")
            )
            try:
                os.makedirs(tmpdir, exist_ok=True)
            except OSError:
                tmpdir = self.build_folder
            test_bin = os.path.join(self.build_folder, "test_equihash")
            if not os.path.isfile(test_bin):
                raise ConanException("test binary missing: %s" % test_bin)
            logfile = os.path.join(self.build_folder, "test_package.log")
            # L0d: test() runs the real binary via self.run; output goes to
            # a logfile so the RESULT trailer can be parsed for evidence.
            inner = "%s %s %s %s > %s 2>&1" % (
                "TMPDIR=%s" % shlex.quote(tmpdir),
                "TMP=%s" % shlex.quote(tmpdir),
                "TEMP=%s" % shlex.quote(tmpdir),
                shlex.quote(test_bin),
                shlex.quote(logfile),
            )
            self.run(inner, env="conanrun", ignore_errors=True)

            out = ""
            if os.path.isfile(logfile):
                with open(logfile, "r", encoding="utf-8", errors="replace") as f:
                    out = f.read()
            self.output.info("test_equihash log:\n" + "\n".join(out.splitlines()[-12:]))

            m = re.search(r"RESULT: (\d+) passed, (\d+) failed", out)
            if not m:
                raise ConanException(
                    "test_equihash produced no RESULT line — harness broken"
                )
            passed = int(m.group(1))
            failed = int(m.group(2))
            discovered = passed + failed
            ok = failed == 0 and discovered > 0

            marker = {
                "executed": True,
                "passed": ok,
                "command": "./test_equihash (solsize/solve/verify consumer checks)",
                "discovered": discovered,
                "passedCount": passed,
            }
            self.output.info(
                "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
            )

            upstream_marker = {
                "status": "no_tests",
                "framework": "none",
                "command": "upstream ships no test suite (no check/test target, no tests directory)",
                "discovered": 0,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": (
                    "libequihash 1.0.10 上游无可接入的测试套件：Makefile 无 check/test 目标；"
                    "源码树无 tests/ 或 test/ 目录；python/test.py 仅为无断言的绑定用法演示；"
                    "bench.cc 为性能基准非测试（详见 test_package/MANIFEST.yml 审计）"
                ),
            }
            self.output.info(
                "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream_marker, ensure_ascii=False)
            )
            if not ok:
                raise ConanException(
                    "test_equihash failed: %d/%d cases failed" % (failed, discovered)
                )
            self.output.info("libequihash consumer test_package passed")
