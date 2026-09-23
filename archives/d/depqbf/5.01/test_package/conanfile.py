#!/usr/bin/env python3
"""Consumer test for the packaged DepQBF library and CLI binary."""

import json
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout


class DepqbfTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        # run=True: VirtualRunEnv only injects bindirs to PATH for run deps;
        # depqbf is a library package type (default run=False), otherwise
        # test_bin.sh cannot find the depqbf command.
        self.requires(self.tested_reference_str, run=True)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # 1) C API test: links against libqdpll.a, exercises create /
        #    prefix setup / add / solve / model query / prefix inspection
        #    (19 CHECK points in test_qdpll.c).
        # 2) CLI binary test: --version/--help plus SAT(10)/UNSAT(20)
        #    exit-code checks over minimal QDIMACS fixtures
        #    (6 checks in test_bin.sh).
        # Total test_package assertions: 25.
        discovered = 25
        passed = 0
        bin_ok = False
        api_ok = False
        try:
            test_exe = os.path.join(self.cpp.build.bindirs[0], "test_qdpll")
            self.run(test_exe, env="conanrun")
            api_ok = True
            # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries, so wrap
            # the shell script with bash like other tool packages do.
            bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
            script = os.path.join(self.source_folder, "test_bin.sh")
            self.run(f'"{bash}" "{script}" "{self.source_folder}"', env="conanrun")
            bin_ok = True
            if api_ok and bin_ok:
                passed = discovered
        except Exception as exc:
            self.output.error(f"test_package failed: {exc}")

        # HMBS machine-evidence markers, printed on the Conan output stream.
        # test_package count = 19 libqdpll C API CHECKs + 6 CLI checks.
        bash_cmd = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        tp_result = {
            "executed": True,
            "passed": passed == discovered,
            "command": f"test_qdpll + {bash_cmd} test_bin.sh <source-folder>",
            "discovered": discovered,
            "passedCount": passed,
        }
        tp_line = f"HMBS_TEST_PACKAGE_RESULT={json.dumps(tp_result)}"
        print(tp_line)
        self.output.info(tp_line)

        # Upstream depqbf 5.01 provides no automated test suite (audited,
        # see test_package/MANIFEST.yml upstream_tests_exist: false):
        # root makefile has only build/clean targets, no check/test target;
        # the source archive has no tests/ or test harness; examples/ holds
        # only hand-built API demos with no assertions. Honest result is
        # no_tests/0. Re-emitted here every run because the main-recipe
        # build() output may be skipped on cache-hit preflight rounds.
        ut_result = {
            "status": "no_tests",
            "framework": "make",
            "command": "make check (upstream provides no check/test target)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "depqbf 5.01 upstream tarball audited: root makefile defines "
                "only depqbf/libqdpll.a/libqdpll.so/clean targets with no "
                "check/test entry; archive has no tests/ or test harness; "
                "examples/makefile builds six hand-run API demos with gcc "
                "and no assertions or expected-output comparison"
            ),
        }
        ut_line = f"HMBS_UPSTREAM_TEST_RESULT={json.dumps(ut_result)}"
        print(ut_line)
        self.output.info(ut_line)

        if passed != discovered:
            raise ConanException("depqbf test_package checks failed")
