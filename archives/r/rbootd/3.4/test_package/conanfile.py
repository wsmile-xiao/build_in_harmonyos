#!/usr/bin/env python3
"""Conan test_package — rbootd 3.4.

rbootd is a privileged network daemon shipped as a command-line binary, so
the L1 test runs the real binary (R34): `rbootd -d -Z` exercises the getopt
option parser and the startup path in the foreground without daemonizing and
without touching the network (a bare `rbootd` would `daemon(0,0)` and need a
live capture interface + root). Two of the three assertions are OHOS-specific
(OHOS/musl aarch64 ELF identity + static libpcap linkage).
"""

import json
import os

from conan import ConanFile
from conan.errors import ConanException


class RbootdTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS /system/bin/sh (mksh) cannot execute ELF binaries; use bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # test.sh runs 3 real assertions against the packaged binary:
        #   1. `rbootd -d -Z` runs and getopt reports the invalid option
        #   2. OHOS-specific: packaged ELF is aarch64 + /lib/ld-musl-aarch64.so.1
        #   3. OHOS-specific: libpcap is linked statically (no libpcap.so dep)
        discovered = 3
        passed = 0
        try:
            self.run("%s test.sh" % bash, env="conanrun")
            passed = discovered
        except Exception as exc:
            self.output.error("test.sh failed: %s" % exc)

        # HMBS machine-evidence markers, printed on the Conan output stream.
        tp_result = {
            "executed": True,
            "passed": passed == discovered,
            "command": "%s test.sh" % bash,
            "discovered": discovered,
            "passedCount": passed,
        }
        print("HMBS_TEST_PACKAGE_RESULT=%s" % json.dumps(tp_result))

        # Upstream rbootd 3.4 has no test suite (audited tarball, see
        # test_package/MANIFEST.yml upstream_tests_exist: false): the Makefile
        # defines only the rbootd/clean/all/install/rbootd.8.gz targets, so
        # `make check` has no rule and the honest result is no_tests/0.
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
                "rbootd_3.4.tar.xz audited (sha256 "
                "8a6543af25237f6553e40c47bcc42edf8d743e6d37516611e4a06973c5913225): "
                "no tests/ directory and no test source files anywhere in the "
                "tree (no TEST(/TEST_F, no def test_); the Makefile defines only "
                "the rbootd, clean, all, install and rbootd.8.gz targets with no "
                "check/test/TESTS target, so `make check` has no rule to execute"
            ),
        }
        print("HMBS_UPSTREAM_TEST_RESULT=%s" % json.dumps(ut_result))

        if passed != discovered:
            raise ConanException("test_package smoke tests failed")
