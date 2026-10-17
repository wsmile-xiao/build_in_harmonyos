#!/usr/bin/env python3
"""Conan test_package — codemadness-frontends 0.8.

codemadness-frontends is a CLI/CGI/Gopher toolset (application). The L1
test runs the real packaged binaries offline (R34, no network):

1. `youtube-cli` with no args prints `usage:` to stderr and exits 1
   (argument-parsing path, no network touched).
2. `youtube-cli -o bogus` prints `usage:` and exits non-zero (option
   validation path, no network touched).
3. `youtube-cgi` with an empty QUERY_STRING renders the search page
   offline (output contains `</html>`).
4. `youtube-gopher` with an empty environment answers the Gopher menu
   offline (output contains `7Search`).
"""
import json
import os

from conan import ConanFile
from conan.errors import ConanException


class CodemadnessFrontendsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS /system/bin/sh (mksh) cannot execute ELF binaries; use bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        if not os.path.isfile(bash):
            bash = "bash"
        # test_frontends.sh runs 4 real assertions against the packaged
        # binaries (see the script header for the assertion list).
        discovered = 4
        passed = 0
        try:
            self.run(f"{bash} test_frontends.sh", env="conanrun")
            passed = discovered
        except Exception as exc:
            self.output.error(f"test_frontends.sh failed: {exc}")

        # HMBS machine-evidence markers on the Conan output stream.
        tp_result = {
            "executed": True,
            "passed": passed == discovered,
            "command": f"{bash} test_frontends.sh",
            "discovered": discovered,
            "passedCount": passed,
        }
        print(f"HMBS_TEST_PACKAGE_RESULT={json.dumps(tp_result)}")

        # Upstream frontends 0.8 ships no test suite (audited tarball, see
        # test_package/MANIFEST.yml upstream_tests_exist: false): no tests/
        # directory, no `check`/`test` make target, `make -n check` is a
        # no-op, so the honest result is no_tests/0.
        ut_result = {
            "status": "no_tests",
            "framework": "makefile",
            "command": "make check",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "frontends-0.8.tar.gz audited (sha256 "
                "b59b264eba2e2927e06b5b035a0f1b68fe743635b37b26e8c3dfad67a03928e0): "
                "no tests/ or test/ directory and no test source files in the "
                "tree; Makefile defines only all/youtube/clean targets with no "
                "check/test target, so `make check` is a no-op executing zero "
                "test cases. Offline behavior is covered by test_package "
                "running the real packaged binaries (cli usage paths, cgi/gopher "
                "empty-query rendering)."
            ),
        }
        print(f"HMBS_UPSTREAM_TEST_RESULT={json.dumps(ut_result)}")

        if passed != discovered:
            raise ConanException("test_package frontend smoke tests failed")
