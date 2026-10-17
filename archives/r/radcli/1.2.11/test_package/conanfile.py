#!/usr/bin/env python3
"""Conan test_package for radcli 1.2.11.

Consumer test (test.c, 19 CHECKs distilled from upstream avpair.c plus
dictionary-buffer coverage) runs on the OHOS target and counts the real
"ok <line>:" lines for the HMBS_TEST_PACKAGE_RESULT machine-evidence
marker (exit-0-alone is not proof).

Upstream evidence (N=14 single harness): the 13 shell integration tests need a live RADIUS
server (SERVER_IP) and SKIP without one. The main recipe build() really
runs `make check`, parses the automake summary into
res/upstream_test_summary.json; this test() re-emits it as
HMBS_UPSTREAM_TEST_RESULT (the HMBS gate only scans test_package stdout
and build() is skipped on conan cache hits, so the marker must appear
here; counts come from the live make-check log, never fabricated).
"""
import json
import os
import re

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout

# test.c performs exactly 19 CHECK() invocations, each printing one
# "ok <line>: <msg>" line on success.
CONSUMER_CHECK_COUNT = 19


class RadcliTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # DRAFT-6487: OHOS system bash (/data/service/hnp/bin/bash) fails
        # getcwd() on HMDFS dirs; test binary must run under getcwd-safe
        # /bin/sh (toybox ash, same as HMBS SHELL injection).
        bash = os.environ.get("SHELL", "/bin/sh")
        if "hnp" in bash or "bash" in os.path.basename(bash):
            bash = "/bin/sh"
        log_path = os.path.join(self.build_folder, "hmbs_test_package.log")
        cmd = "%s -c './test_radcli'" % bash
        rc = 0
        try:
            self.run("%s > \"%s\" 2>&1" % (cmd, log_path), env="conanrun")
        except Exception:
            rc = 1
        output = ""
        try:
            with open(log_path, "r", encoding="utf-8",
                      errors="replace") as f:
                output = f.read()
        except OSError:
            output = ""
        tail = "\n".join(output.splitlines()[-15:])
        if tail:
            self.output.info("test_radcli output tail:\n%s" % tail)
        ok_count = len(re.findall(r"^ok \d+: ", output, re.MULTILINE))
        all_passed = "ALL CHECKS PASSED" in output
        tp_passed = (rc == 0 and all_passed
                     and ok_count == CONSUMER_CHECK_COUNT)
        tp_marker = {
            "executed": True,
            "passed": tp_passed,
            "command": "./test_radcli",
            "discovered": CONSUMER_CHECK_COUNT,
            "passedCount": ok_count,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT="
                         + json.dumps(tp_marker, ensure_ascii=False))

        # Upstream evidence: re-emit the live make-check summary shipped
        # by the main recipe (res/upstream_test_summary.json).
        try:
            pkg = self.dependencies[self.tested_reference_str]
            summary_path = os.path.join(str(pkg.package_folder), "res",
                                        "upstream_test_summary.json")
        except Exception:
            summary_path = ""
        upstream = None
        if summary_path and os.path.isfile(summary_path):
            try:
                with open(summary_path, "r", encoding="utf-8") as f:
                    upstream = json.load(f)
            except (OSError, ValueError) as exc:
                self.output.warning(
                    "radcli: could not read upstream summary: %s" % exc)
                upstream = None
        if upstream is not None:
            self.output.info("HMBS_UPSTREAM_TEST_RESULT="
                             + json.dumps(upstream, ensure_ascii=False))
        else:
            self.output.warning(
                "radcli: upstream test summary missing; emitting failed "
                "marker (no fabricated pass)")
            ut = {
                "status": "failed",
                "framework": "autotools-make-check",
                "command": "make check (run in main recipe build())",
                "discovered": 0,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": "upstream_test_summary.json missing in package; "
                          "build() upstream make-check evidence unavailable",
            }
            self.output.info("HMBS_UPSTREAM_TEST_RESULT="
                             + json.dumps(ut, ensure_ascii=False))
            raise ConanException(
                "radcli: upstream test summary missing; cannot pass gate")

        if not tp_passed:
            raise ConanException(
                "radcli consumer test failed: rc=%s ok=%s/%s all_passed=%s"
                % (rc, ok_count, CONSUMER_CHECK_COUNT, all_passed))
        self.output.info("radcli consumer test_package passed")
