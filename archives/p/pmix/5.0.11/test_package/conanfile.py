#!/usr/bin/env python3
"""Conan test_package — pmix 5.0.11 (R34 substantive test).

Consumer-side verification:
1. Build & run test_pmix.c against the packaged library — end-to-end
   PMIx server/client handshake (PMIx_server_init/setup_fork +
   forked client PMIx_Init/PMIx_Finalize), 8 C-level assertions.
2. Run the packaged pmix_info binary and assert it reports "PMIX: 5.0.11".
3. Assert package layout (include/pmix.h, lib/libpmix.so, bin/pmix_info).

Results are aggregated into a single HMBS_TEST_PACKAGE_RESULT line.
Commands execute through self.run(env="conanrun") — the OHOS-adapted
conan 2.29.1 run() takes no timeout and returns only the exit code, so
output is captured by passing an open file as stdout (stderr merged via
subprocess.STDOUT); temp files live in a mkdtemp() dir removed in a
try/finally block.
"""
import os
import shlex
import shutil
import subprocess
import tempfile

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class PmixTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _run_capture(self, cmd, out_file):
        """Run cmd under the conanrun environment, capture combined output.

        Returns the exit code; output (stdout+stderr) lands in out_file.
        """
        with open(out_file, "w") as f:
            rc = self.run(shlex.quote(cmd), env="conanrun", stdout=f,
                          stderr=subprocess.STDOUT, ignore_errors=True)
        try:
            with open(out_file, "r") as f:
                return rc, f.read()
        except OSError:
            return rc, ""

    def test(self):
        total = 0
        passed = 0

        def record(ok, desc):
            nonlocal total, passed
            total += 1
            if ok:
                passed += 1
                self.output.info("ASSERT OK: %s" % desc)
            else:
                self.output.error("ASSERT FAIL: %s" % desc)

        # NOTE: self.cpp.package in a test_package refers to the test
        # package's own (nonexistent) package scope. The tested package's
        # artifacts must be located through the dependency object.
        tested = self.dependencies[self.tested_reference_str]
        pkg_folder = tested.package_folder

        tmpdir = tempfile.mkdtemp(prefix="pmix-test-")
        try:
            # --- 1. end-to-end API test (C program, 8 assertions) ---
            test_bin = os.path.join(self.cpp.build.bindirs[0], "test_pmix")
            rc, out = self._run_capture(test_bin,
                                        os.path.join(tmpdir, "test_pmix.out"))
            c_total = c_passed = 0
            for line in out.splitlines():
                if line.startswith("PMIX_TEST_ASSERTIONS:"):
                    parts = dict(p.split("=") for p in line.split()[1:])
                    c_total = int(parts.get("total", 0))
                    c_passed = int(parts.get("passed", 0))
            record(rc == 0 and c_total > 0 and c_total == c_passed,
                   "test_pmix end-to-end API handshake (%d/%d C assertions, rc=%d)"
                   % (c_passed, c_total, rc))

            # --- 2. packaged pmix_info smoke (version assertion) ---
            info_bin = os.path.join(pkg_folder, "bin", "pmix_info")
            irc, iout = self._run_capture(info_bin,
                                          os.path.join(tmpdir, "pmix_info.out"))
            record(irc == 0 and "PMIX: 5.0.11" in iout,
                   "pmix_info reports version 5.0.11 (rc=%d)" % irc)
            ver_line = next((ln for ln in iout.splitlines() if "PMIX:" in ln), "")
            self.output.info("pmix_info version line: %s" % ver_line.strip())

            # --- 3. package layout assertions ---
            record(os.path.isfile(os.path.join(pkg_folder, "include", "pmix.h")),
                   "package layout: include/pmix.h exists")
            record(any(os.path.isfile(os.path.join(pkg_folder, d, "libpmix.so"))
                       for d in ("lib", "lib64")),
                   "package layout: lib/libpmix.so exists")
            record(os.path.isfile(info_bin),
                   "package layout: bin/pmix_info exists")
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

        self.output.info("HMBS_TEST_PACKAGE_RESULT: total=%d passed=%d" % (total, passed))
        if total == 0 or total != passed:
            raise Exception(
                "test_package failed: %d/%d assertions passed" % (passed, total)
            )
