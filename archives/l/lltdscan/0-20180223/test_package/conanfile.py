#!/usr/bin/env python3
"""Conan test_package — lltdscan 0-20180223.

lltdscan is a layer-2 LLTD scanner, so the L1 test runs the real binary (R34).
Only the command-line paths that return before any socket is opened are
exercised — `-h`, an unknown option, a missing option argument, a malformed
trailing MAC and two trailing MACs. A bare `lltdscan` must never be run here:
it calls pcap_lookupdev(), sends a broadcast frame via libnet and then blocks
in pcap_dispatch() for the -t timeout, needing root and a real NIC.
"""

import json
import os

from conan import ConanFile
from conan.errors import ConanException


class LltdscanTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # Point test.sh at the packaged binary explicitly instead of relying on
        # PATH resolution, so the assertions always hit this package's copy.
        dep = self.dependencies[self.tested_reference_str]
        os.environ["LLTDSCAN_BIN"] = os.path.join(dep.package_folder, "bin", "lltdscan")

    def test(self):
        # OHOS /system/bin/sh (mksh) cannot execute ELF binaries; use bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # test.sh runs 5 test cases / 20 real assertions against the packaged
        # binary (8 in case 1: exit code + non-empty output + program name +
        # 5 banner greps; 2 each in cases 2-4; 6 in case 5: exit code +
        # 5 banner greps).
        discovered = 5
        passed = 0
        try:
            self.run("%s test.sh" % bash, env="conanrun")
            passed = discovered
        except Exception as exc:
            self.output.error("test.sh failed: %s" % exc)

        # HMBS machine-evidence markers, printed on the Conan output stream
        # (same channel as cdpr/2.4, which passed the full gate).
        tp_result = {
            "executed": True,
            "passed": passed == discovered,
            "command": "%s test.sh" % bash,
            "discovered": discovered,
            "passedCount": passed,
        }
        print("HMBS_TEST_PACKAGE_RESULT=%s" % json.dumps(tp_result))

        # Upstream lltdscan has no test suite (audited tarball, see
        # test_package/MANIFEST.yml upstream_tests_exist: false): the Makefile
        # defines only all/lltdscan/clean/doc/install/dist, so make check has no
        # rule to execute. The honest result is no_tests/0.
        ut_result = {
            "status": "no_tests",
            "framework": "make",
            "command": "make check",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "lltdscan tarball at upstream master HEAD "
                "258dbb1c7f8672c09a4a578fc17dada524c3eabb (sha256 "
                "678b4813d8ad0d33059797ce16614e8065bcd6ecd7658221967a8aee866f4108) "
                "audited: no tests/ directory and no test source files anywhere in "
                "the tree (no TEST(/TEST_F, no def test_); the Makefile defines only "
                "the all/lltdscan/clean/doc/install/dist targets with no "
                "check/test/TESTS target, so make check has no rule to execute"
            ),
        }
        print("HMBS_UPSTREAM_TEST_RESULT=%s" % json.dumps(ut_result))

        if passed != discovered:
            raise ConanException("test_package smoke tests failed")