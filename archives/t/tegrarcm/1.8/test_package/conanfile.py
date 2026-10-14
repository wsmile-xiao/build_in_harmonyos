#!/usr/bin/env python3
"""Conan test_package for tegrarcm 1.8 (L1 consumer test).

Runs test_tegrarcm.sh against the packaged bin/tegrarcm and parses its
deterministic "RESULT: P passed, F failed" trailer into
HMBS_TEST_PACKAGE_RESULT. Re-emits HMBS_UPSTREAM_TEST_RESULT (no_tests:
upstream ships no suite, audited in MANIFEST.yml) so evidence survives
Conan cache hits.
"""
import json
import os
import re
import shlex

from conan import ConanFile
from conan.errors import ConanException


class TegrarcmTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        bindir = dep.cpp_info.bindirs[0]
        binary = os.path.join(dep.package_folder, bindir, "tegrarcm")
        if not os.path.isfile(binary):
            self.output.error("tegrarcm binary not found at: %s" % binary)
            raise Exception("packaged binary missing: %s" % binary)

        workdir = os.path.join(self.build_folder, "tegrarcm-test")
        os.makedirs(workdir, exist_ok=True)
        tmpdir = (
            os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
            or workdir
        )
        os.makedirs(tmpdir, exist_ok=True)

        test_script = os.path.join(self.recipe_folder, "test_tegrarcm.sh")
        logfile = os.path.join(self.build_folder, "test_package.log")

        inner = "%s %s %s %s %s %s %s > %s 2>&1" % (
            "TMPDIR=%s" % shlex.quote(tmpdir),
            "TMP=%s" % shlex.quote(tmpdir),
            "TEMP=%s" % shlex.quote(tmpdir),
            shlex.quote("sh"),
            shlex.quote(test_script),
            shlex.quote(binary),
            shlex.quote(workdir),
            shlex.quote(logfile),
        )
        self.run(inner, env="conanrun", ignore_errors=True)

        out = ""
        if os.path.isfile(logfile):
            with open(logfile, "r", encoding="utf-8", errors="replace") as f:
                out = f.read()
        self.output.info(
            "test_tegrarcm.sh log:\n" + "\n".join(out.splitlines()[-20:])
        )

        m = re.search(r"RESULT: (\d+) passed, (\d+) failed", out)
        if not m:
            raise ConanException(
                "test_tegrarcm.sh produced no RESULT line - harness broken "
                "(log: %s)" % logfile
            )
        passed = int(m.group(1))
        failed = int(m.group(2))
        discovered = passed + failed
        ok = failed == 0 and discovered > 0

        marker = {
            "executed": True,
            "passed": ok,
            "command": "sh test_tegrarcm.sh <pkg>/bin/tegrarcm <workdir>",
            "discovered": discovered,
            "passedCount": passed,
        }
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
        )
        if not ok:
            raise ConanException(
                "test_tegrarcm.sh failed: %d/%d cases failed" % (failed, discovered)
            )

        upstream_marker = {
            "status": "no_tests",
            "framework": "autotools",
            "command": "make check (upstream registers no tests)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "tegrarcm 1.8 ships no automated tests: no tests/ directory, "
                "no TESTS/check_PROGRAMS in Makefile.am or src/Makefile.am, "
                "configure.ac has no test probe; make check is the empty "
                "automake default. See test_package/MANIFEST.yml audit."
            ),
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT="
            + json.dumps(upstream_marker, ensure_ascii=False)
        )
        self.output.info("tegrarcm functional test_package passed")
