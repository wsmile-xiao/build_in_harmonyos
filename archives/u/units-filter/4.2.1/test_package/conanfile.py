#!/usr/bin/env python3
"""Conan test_package for units-filter 4.2.1 (L1 consumer test).

Runs test_units_filter.sh against the packaged bin/units-filter binary:
6 real conversions through stdin plus a negative control (an invalid
expression must be rejected, proving the harness observes real failures).
The script prints a deterministic "RESULT: P passed, F failed" trailer;
this recipe parses that trailer line for HMBS_TEST_PACKAGE_RESULT.
The upstream 77-case perl harness runs in the main recipe build() and its
HMBS_UPSTREAM_TEST_RESULT marker is emitted there.
"""

import json
import os
import re
import shlex

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building


class UnitsFilterTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: build only, skip run")
            return
        dep = self.dependencies[self.tested_reference_str]
        bindir = dep.cpp_info.bindirs[0]
        binary = os.path.join(dep.package_folder, bindir, "units-filter")
        if not os.path.isfile(binary):
            raise ConanException("packaged binary missing: %s" % binary)

        workdir = os.path.join(self.build_folder, "units-filter-test")
        os.makedirs(workdir, exist_ok=True)
        tmpdir = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                  or os.environ.get("TEMP") or workdir)
        os.makedirs(tmpdir, exist_ok=True)

        test_script = os.path.join(self.recipe_folder, "test_units_filter.sh")
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
        self.output.info("test_units_filter.sh log:\n"
                         + "\n".join(out.splitlines()[-25:]))

        m = re.search(r"RESULT: (\d+) passed, (\d+) failed", out)
        if not m:
            raise ConanException(
                "test_units_filter.sh produced no RESULT line - harness broken "
                "(log: %s)" % logfile)
        passed = int(m.group(1))
        failed = int(m.group(2))
        discovered = passed + failed
        ok = failed == 0 and discovered > 0

        marker = {
            "executed": True,
            "passed": ok,
            "command": "sh test_units_filter.sh <pkg>/bin/units-filter <workdir>",
            "discovered": discovered,
            "passedCount": passed,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT="
                         + json.dumps(marker, ensure_ascii=False))
        if not ok:
            raise ConanException(
                "test_units_filter.sh failed: %d/%d cases failed"
                % (failed, discovered))
        self.output.info("units-filter functional test_package passed")
