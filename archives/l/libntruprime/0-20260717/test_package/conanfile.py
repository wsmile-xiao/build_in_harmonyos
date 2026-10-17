#!/usr/bin/env python3
"""Conan test_package for libntruprime/0-20260717.

Consumer test (TAP-style binary, 8 checks: 6 sntrup KEM roundtrips +
encapsulation randomization + double decapsulation). The binary output is
parsed for "ok" lines; the counts feed HMBS_TEST_PACKAGE_RESULT. The
upstream ntruprime-test result persisted by the main recipe
(res/upstream_test_result.json) is re-emitted so the evidence survives
package cache hits (libcanard pattern).
"""

import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.files import replace_in_file

N_CHECKS = 8


class LibntruprimeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps"
    exports_sources = "CMakeLists.txt", "test_ntruprime.c"

    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _usable_compiler(self, key, fallbacks):
        # The generated conan_toolchain.cmake may embed a stale
        # /data/service/hnp/bin/clang; HMBS prepends the real tool dirs to
        # PATH, so prefer an absolute conf path only when it exists.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cand = compilers.get(key)
        if cand and os.path.isabs(str(cand)) and os.path.isfile(str(cand)):
            return str(cand)
        for name in fallbacks:
            found = shutil.which(name)
            if found and os.path.isfile(found):
                return found
        if cand and os.path.isfile(str(cand)):
            return str(cand)
        return fallbacks[0]

    def build(self):
        cc = self._usable_compiler("c", ["clang", "cc"])
        self.output.info("test_package CC=%s" % cc)
        toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        if os.path.isfile(toolchain):
            for stale in ("/data/service/hnp/bin/clang",
                          "/data/service/hnp/bin/clang++"):
                try:
                    replace_in_file(self, toolchain, stale, cc)
                except Exception:
                    pass
        cmake = CMake(self)
        cmake.configure(variables={"CMAKE_C_COMPILER": cc})
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: build verified, runtime test skipped")
            return
        # Never rely on system /tmp (read-only on the true machine). Prefer
        # injected TMPDIR/TMP/TEMP, else use a dir under the build folder.
        tmpdir = os.environ.get("TMPDIR") or os.environ.get("TMP") or os.environ.get("TEMP")
        if not (tmpdir and os.path.isdir(tmpdir) and os.access(tmpdir, os.W_OK)):
            tmpdir = os.path.join(self.build_folder, ".hmbs-tmp")
            try:
                os.makedirs(tmpdir, exist_ok=True)
            except Exception:
                pass
            for var in ("TMPDIR", "TMP", "TEMP"):
                os.environ[var] = tmpdir
        binary = os.path.join(self.cpp.build.bindir, "test_ntruprime")
        if not os.path.isfile(binary):
            raise RuntimeError("test binary missing: %s" % binary)
        # L0d/R34 gate: real execution of the consumer test binary.
        self.run(binary, env="conanrun")
        env = dict(os.environ)
        dep = self.dependencies["libntruprime"]
        libdir = os.path.join(dep.package_folder, "lib")
        if os.path.isdir(libdir):
            prev = env.get("LD_LIBRARY_PATH")
            env["LD_LIBRARY_PATH"] = libdir + (os.pathsep + prev if prev else "")
        proc = subprocess.run(
            [binary],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=300,
            env=env,
        )
        output = proc.stdout or ""
        self.output.info(output)
        passed_count = sum(
            1 for line in output.splitlines() if line.startswith("ok ")
        )
        has_failure = any(
            line.startswith("not ok ") for line in output.splitlines()
        )
        command = "test_ntruprime (8 TAP checks: 6 KEM roundtrips + randomization + double decapsulation)"
        marker = {
            "executed": True,
            "passed": proc.returncode == 0 and passed_count == N_CHECKS and not has_failure,
            "command": command,
            "discovered": N_CHECKS,
            "passedCount": passed_count,
        }
        # Re-emit the upstream suite result persisted by the main recipe.
        res_json = os.path.join(dep.package_folder, "res", "upstream_test_result.json")
        if not os.path.isfile(res_json):
            raise RuntimeError("upstream_test_result.json missing from package res/")
        with open(res_json, "r", encoding="utf-8") as fh:
            upstream = json.load(fh)
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream))
        if (upstream.get("status") != "passed"
                or int(upstream.get("discovered", 0)) <= 0
                or int(upstream.get("executed", 0)) != int(upstream.get("discovered", 0))
                or int(upstream.get("passed", 0)) != int(upstream.get("discovered", 0))):
            raise RuntimeError("upstream result invalid: %r" % (upstream,))
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))
        if not marker["passed"]:
            raise RuntimeError(
                "test_package failed: %d/%d checks passed" % (passed_count, N_CHECKS)
            )
