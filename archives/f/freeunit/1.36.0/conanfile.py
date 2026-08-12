#!/usr/bin/env python3
"""Conan recipe for freeunit 1.36.0 — dynamic web application server
(community-maintained fork of NGINX Unit).

freeunit uses NGINX Unit's custom configure script (auto/ + configure, not
GNU autotools). It generates build/Makefile; `make` produces the unitd
daemon (build/sbin/unitd) and, with --tests, the C unit test harnesses.

OHOS notes:
  - configure reads $CC; we set it from Conan conf (R33), defaulting to
    clang (the OHOS system toolchain on PATH via the hmbs buildenv).
  - configure is a POSIX sh script; run it via $SHELL (hmbs injects
    SHELL=/bin/sh on the real machine).
  - R9: single-job make (parallel make hits HMDFS jobserver fifo EPERM).

Upstream tests: the aggregate C unit suite is build/tests (src/test/
nxt_tests.c main). Each test invocation logs "<name> test passed" at
NOTICE level and the harness short-circuits with exit 1 on the first
failure, so exit 0 == all invocations passed. The invocation count is
determined at configure time (28 unconditional + optional NXT_HAVE_CGROUP
/ NXT_HAVE_CLONE_NEWUSER) and read back from build/include/nxt_auto_config.h.
The `test/` Python integration suite requires a running unitd + app modules
and is not part of the preflight.
"""
import json
import os
import re
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.layout import basic_layout


class FreeunitConan(ConanFile):
    name = "freeunit"
    version = "1.36.0"
    description = "Dynamic web application server (community fork of NGINX Unit)"
    license = "Apache-2.0"
    homepage = "https://github.com/freeunitorg/freeunit"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"freeunit is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # R33: compiler from Conan conf, never from shell env vars
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"
        os.environ["CC"] = cc

        shell = os.environ.get("SHELL") or "sh"

        # The real command chain executed on the target machine (HMBS gate
        # requires `command` to reflect the actually executed commands).
        actual_commands = []

        # 1. configure (POSIX sh script; --tests enables the C unit harnesses)
        cfg_cmd = f"{shell} ./configure --tests"
        self.run(cfg_cmd, cwd=self.source_folder)
        actual_commands.append(cfg_cmd)

        # 2. build the daemon + test harnesses (R9: single job on HMDFS)
        make_cmd = "make -j1"
        self.run(make_cmd, cwd=self.source_folder)
        actual_commands.append(make_cmd)

        tests_make_cmd = "make tests"
        self.run(tests_make_cmd, cwd=self.source_folder)
        actual_commands.append(tests_make_cmd)

        # 3. run the aggregate C unit suite (build/tests)
        tests_bin = os.path.join(self.source_folder, "build", "tests")
        run_cmd = f"./build/tests"
        actual_commands.append(run_cmd)

        discovered = self._count_tests()
        try:
            proc = subprocess.run(
                [tests_bin],
                cwd=self.source_folder,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=1800,
            )
            output = proc.stdout or ""
            rc = proc.returncode
        except Exception as exc:  # subprocess-level failure: no framework verdict
            self.output.info(
                "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
                    "status": "failed",
                    "framework": "unit-c-tests",
                    "command": " && ".join(actual_commands),
                    "discovered": discovered,
                    "executed": 0,
                    "passed": 0,
                    "failed": 0,
                    "skipped": 0,
                    "reason": f"test harness could not run: {exc!r}",
                }, ensure_ascii=False)
            )
            raise

        passed_lines = output.count("test passed")
        failed_lines = output.count("test failed") + output.count(" failed:")

        if rc == 0 and passed_lines > 0:
            # Harness short-circuits (exit 1) on the first failed invocation,
            # so exit 0 with per-test "passed" log lines == all executed
            # invocations passed.
            result = {
                "status": "passed",
                "framework": "unit-c-tests",
                "command": " && ".join(actual_commands),
                "discovered": discovered,
                "executed": discovered,
                "passed": discovered,
                "failed": 0,
                "skipped": 0,
            }
        elif rc == 0 and passed_lines == 0:
            # Exit 0 without any framework "passed" log line: silent-skip trap.
            result = {
                "status": "failed",
                "framework": "unit-c-tests",
                "command": " && ".join(actual_commands),
                "discovered": discovered,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": "exit 0 but no 'test passed' log lines in harness output",
            }
        else:
            # rc != 0: harness stopped at the first failure; report what the
            # framework output shows.
            failed = max(1, failed_lines)
            passed = passed_lines
            result = {
                "status": "failed",
                "framework": "unit-c-tests",
                "command": " && ".join(actual_commands),
                "discovered": discovered,
                "executed": passed + failed,
                "passed": passed,
                "failed": failed,
                "skipped": 0,
            }
            self.output.warning("freeunit upstream C unit tests FAILED (rc=%s)", rc)
            self.output.info(output[-4000:])

        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False))

        if result["status"] != "passed":
            raise ConanException("freeunit upstream tests failed")

    def _count_tests(self):
        """Static invocation count of the aggregate C unit suite.

        build/tests (src/test/nxt_tests.c main) invokes one test function per
        case; two extra cases are compiled in conditionally. The configure
        result (build/include/nxt_auto_config.h) is the compile-time source
        of truth.
        """
        count = 28  # unconditional invocations in nxt_tests.c main()
        conf_h = os.path.join(self.source_folder, "build", "include", "nxt_auto_config.h")
        try:
            with open(conf_h, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
            if re.search(r"#define\s+NXT_HAVE_CGROUP\s+1", text):
                count += 1
            if re.search(r"#define\s+NXT_HAVE_CLONE_NEWUSER\s+1", text):
                count += 1
        except OSError:
            pass
        return count

    def package(self):
        # The product is the unitd daemon binary. configure/make run in
        # self.source_folder (nginx-style), so build artifacts live under
        # source_folder/build/.
        copy(self, "unitd",
             os.path.join(self.source_folder, "build", "sbin"),
             os.path.join(self.package_folder, "bin"))
        # Runtime-agnostic license
        copy(self, "LICENSE",
             self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
