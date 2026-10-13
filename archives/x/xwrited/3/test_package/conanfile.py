#!/usr/bin/env python3
"""Conan test_package for xwrited 3 (L1 consumer test).

xwrited is an application; the test validates that the packaged `xwrited`
binary actually runs on the target (GLib/GApplication option handling works,
the binary is an aarch64 ELF, error paths are honoured) through a
self-contained shell script with 6 real assertions. Only code paths that do
not require a D-Bus session bus, a pty, or a notification daemon are probed,
so the test is deterministic on a headless worker.

Evidence markers:
- HMBS_TEST_PACKAGE_RESULT: discovered/passedCount parsed from the real
  "RESULT: P passed, F failed" trailer line of the script output (real counts,
  not an estimate).
- HMBS_UPSTREAM_TEST_RESULT: status=no_tests. Upstream ships no test suite
  (audited in test_package/MANIFEST.yml). The marker is re-emitted here so
  evidence survives Conan cache hits (build() may be skipped on preflight).
"""

import json
import os
import re

from conan import ConanFile
from conan.errors import ConanException


class XwritedTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Same CCI-leaf pin as the main recipe (libgsf precedent): the
        # test graph resolves libffi independently, so the ohpcd RREV
        # override must be repeated here to keep it off the CCI recipe.
        self.requires("libffi/3.4.4#ca8b0eb4102edbca48730e504e3afbdc",
                      override=True)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        bindir = dep.cpp_info.bindirs[0]
        binary = os.path.join(dep.package_folder, bindir, "xwrited")
        if not os.path.isfile(binary):
            raise ConanException("packaged binary missing: %s" % binary)

        workdir = os.path.join(self.build_folder, "xwrited-test")
        os.makedirs(workdir, exist_ok=True)
        tmpdir = (
            os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
            or workdir
        )
        os.makedirs(tmpdir, exist_ok=True)

        test_script = os.path.join(self.recipe_folder, "test_xwrited.sh")
        logfile = os.path.join(self.build_folder, "test_package.log")

        inner = (
            "TMPDIR={tmp} TMP={tmp} TEMP={tmp} "
            "sh {script} {binary} {workdir} > {log} 2>&1"
        ).format(tmp=tmpdir, script=test_script, binary=binary,
                 workdir=workdir, log=logfile)
        self.run(inner, env="conanrun", ignore_errors=True)

        out = ""
        if os.path.isfile(logfile):
            with open(logfile, "r", encoding="utf-8", errors="replace") as f:
                out = f.read()
        self.output.info(
            "test_xwrited.sh log:\n" + "\n".join(out.splitlines()[-20:])
        )

        # Machine-evidence count comes from the script's deterministic
        # "RESULT: P passed, F failed" trailer line (real assertion results).
        m = re.search(r"RESULT: (\d+) passed, (\d+) failed", out)
        if not m:
            raise ConanException(
                "test_xwrited.sh produced no RESULT line - harness broken "
                "(log: %s)" % logfile
            )
        passed = int(m.group(1))
        failed = int(m.group(2))
        discovered = passed + failed
        ok = failed == 0 and discovered > 0

        marker = {
            "executed": True,
            "passed": ok,
            "command": "sh test_xwrited.sh <pkg>/bin/xwrited <workdir>",
            "discovered": discovered,
            "passedCount": passed,
        }
        marker_msg = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker)
        print(marker_msg, flush=True)
        self.output.info(marker_msg)
        if not ok:
            raise ConanException(
                "test_xwrited.sh failed: %d/%d cases failed"
                % (failed, discovered)
            )

        # Upstream has no test suite (audited in test_package/MANIFEST.yml):
        # status=no_tests with zero counts. Re-emitted here so the evidence the
        # gate requires is present even on cache-hit rounds.
        upstream_marker = {
            "status": "no_tests",
            "framework": "make",
            "command": "make check (upstream registers no tests)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "xwrited 3 audited: hand-written Makefile defines no "
                "check/test target, the xwrited-3 tree has no tests/ "
                "directory and no test source files; make check is a no-op "
                "(see test_package/MANIFEST.yml audit)"
            ),
        }
        upstream_msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream_marker)
        print(upstream_msg, flush=True)
        self.output.info(upstream_msg)
        self.output.info("xwrited functional test_package passed")
