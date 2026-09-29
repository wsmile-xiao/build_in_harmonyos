#!/usr/bin/env python3
"""Conan test_package — kyua 0.13-git20240311-0a43bb8d89e3 consumer verification.

Runs the real consumer script test_kyua.py (3 checks: `kyua about version`,
`kyua help`, and a genuine `kyua test` smoke session over a minimal
Kyuafile + plain test program). Counts the deterministic per-check
`SMOKE-PASS` evidence lines for the HMBS_TEST_PACKAGE_RESULT marker, then
re-emits the upstream suite result persisted by the main recipe so evidence
survives Conan cache hits.
"""

import json
import os
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run

CONSUMER_CHECK_COUNT = 3


class KyuaTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("Cross-building: skip runtime execution")
            return
        dep = self.dependencies["kyua"]
        bin_dir = os.path.join(dep.package_folder, "bin")
        kyua_bin = os.path.join(bin_dir, "kyua")
        if not os.path.isfile(kyua_bin):
            raise ConanException("kyua binary missing: %s" % kyua_bin)
        python = os.environ.get("HMBS_PYTHON3") or sys.executable or "python3"
        script = os.path.join(self.source_folder, "test_kyua.py")
        # L0d: real execution through Conan (non-zero exit fails the package).
        self.run('"%s" "%s" "%s"' % (python, script, bin_dir), env="conanrun")
        # Capture run for the evidence marker (one SMOKE-PASS line per check).
        # Round 51: the capture subprocess does NOT inherit conanrun, so the
        # runenv KYUA_STOREDIR (package_info) would be missing and `kyua
        # test` would fail on the schema path while the real run above
        # passed. Export it explicitly for a deterministic identical env.
        capture_env = dict(os.environ)
        capture_env["KYUA_STOREDIR"] = os.path.join(
            dep.package_folder, "share", "kyua", "store")
        self.output.info("kyua: capture KYUA_STOREDIR=%s"
                         % capture_env["KYUA_STOREDIR"])
        proc = subprocess.run(
            [python, script, bin_dir],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=600,
            env=capture_env,
        )
        output = proc.stdout or ""
        self.output.info(output[-3000:])
        ok_count = 0
        for line in output.splitlines():
            if line.startswith("SMOKE-PASS "):
                ok_count += 1
        marker = {
            "executed": True,
            "passed": proc.returncode == 0 and ok_count == CONSUMER_CHECK_COUNT,
            "command": "python3 test_kyua.py <bindir> (kyua about version + kyua help + kyua test smoke)",
            "discovered": CONSUMER_CHECK_COUNT,
            "passedCount": ok_count,
        }
        marker_msg = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker)
        self.output.info(marker_msg)
        print(marker_msg, flush=True)
        if not marker["passed"]:
            raise ConanException(
                "consumer test failed: rc=%s ok=%s/%s"
                % (proc.returncode, ok_count, CONSUMER_CHECK_COUNT)
            )
        # Re-emit the upstream evidence persisted by build() into
        # <package>/res/upstream_test_result.json (runs every round, even on
        # cached build() which skips the main marker).
        result_path = os.path.join(
            dep.package_folder, "res", "upstream_test_result.json"
        )
        if not os.path.isfile(result_path):
            raise ConanException(
                "upstream_test_result.json not found in package (%s) — "
                "upstream tests did not run during build(); refusing to pass "
                "silently" % result_path
            )
        with open(result_path, "r", encoding="utf-8") as handle:
            upstream = json.load(handle)
        for key in ("status", "framework", "command", "discovered",
                    "executed", "passed", "failed", "skipped"):
            if key not in upstream:
                raise ConanException(
                    "upstream_test_result.json missing key %r" % key
                )
        if not isinstance(upstream["discovered"], int) or upstream["discovered"] <= 0:
            raise ConanException(
                "upstream_test_result.json has invalid discovered=%r"
                % (upstream.get("discovered"),)
            )
        # Re-emit the compact marker line (standard keys + gaps/reason;
        # breakdown stays in the persisted file only, see build()).
        reemit = {key: upstream[key] for key in (
            "status", "framework", "command", "discovered",
            "executed", "passed", "failed", "skipped")}
        for extra in ("gaps", "reason"):
            if extra in upstream:
                reemit[extra] = upstream[extra]
        line = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(reemit, ensure_ascii=False)
        print(line, flush=True)
        self.output.info(line)
