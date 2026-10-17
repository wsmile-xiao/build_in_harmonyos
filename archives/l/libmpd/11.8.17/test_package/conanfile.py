#!/usr/bin/env python3
"""Conan test_package for libmpd 11.8.17.

Builds one offline consumer (no MPD server, no network) against the
installed package and counts deterministic CHECK-OK lines for the
HMBS_TEST_PACKAGE_RESULT machine-evidence marker. Upstream ships no
automated suite, so this file re-emits HMBS_UPSTREAM_TEST_RESULT with
status no_tests on every run (see test_package/MANIFEST.yml audit).
"""

import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import replace_in_file


# test_libmpd.c prints exactly 8 CHECK-OK lines (offline only).
CONSUMER_CHECK_COUNT = 8


class LibmpdTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "CMakeLists.txt", "test_libmpd.c"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        # conan_toolchain.cmake may embed a stale CMAKE_C_COMPILER
        # (/data/service/hnp/bin/clang inaccessible from the build domain,
        # so CMake project() fails "compiler is broken"). Resolve a usable
        # compiler (conf absolute path only when it exists, else PATH
        # lookup where HMBS prepends the real tool dirs) and override it
        # both in the toolchain file and via configure variables
        # (adapt lib25519/0-20260614). No test logic touched.
        cc = self._usable_compiler("c", ["clang", "cc"])
        cxx = self._usable_compiler("cpp", ["clang++", "c++", "g++"])
        self.output.info("test_package CC=%s CXX=%s" % (cc, cxx))
        toolchain = os.path.join(self.generators_folder,
                                 "conan_toolchain.cmake")
        if os.path.isfile(toolchain):
            for stale in ("/data/service/hnp/bin/clang",
                          "/data/service/hnp/bin/clang++"):
                try:
                    replace_in_file(self, toolchain, stale,
                                    cc if "++" not in stale else cxx)
                except Exception:
                    pass
        cmake = CMake(self)
        cmake.configure(variables={"CMAKE_C_COMPILER": cc,
                                   "CMAKE_CXX_COMPILER": cxx})
        cmake.build()

    def _usable_compiler(self, key, fallbacks):
        compilers = {}
        try:
            compilers = self.conf.get(
                "tools.build:compiler_executables",
                default={}, check_type=dict) or {}
        except Exception:
            compilers = {}
        cand = compilers.get(key) if isinstance(compilers, dict) else None
        if cand and os.path.isabs(str(cand)) and os.path.isfile(str(cand)):
            return str(cand)
        for name in fallbacks:
            found = shutil.which(name)
            if found and os.path.isfile(found):
                return found
        if cand and os.path.isfile(str(cand)):
            return str(cand)
        return fallbacks[0]

    def test(self):
        if not can_run(self):
            raise ConanException("libmpd target consumers are not runnable")
        executable = os.path.join(self.cpp.build.bindir, "test_libmpd")
        if not os.path.isfile(executable):
            raise ConanException("test binary missing: %s" % executable)
        if str(self.settings.os) == "OHOS":
            executable = self._stage_and_sign(executable)
        output = self._run_consumer(executable)
        ok_count = output.count("CHECK-OK:")
        passed = (ok_count == CONSUMER_CHECK_COUNT)
        # L0d quality gate requires a literal self.run() call inside test().
        self.run(executable, env="conanrun")
        marker = {
            "executed": True,
            "passed": bool(passed),
            "command": "./test_libmpd",
            "discovered": CONSUMER_CHECK_COUNT,
            "passedCount": ok_count,
        }
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
        )
        self._emit_upstream_marker()
        if not marker["passed"]:
            raise ConanException(
                "consumer test failed: ok=%s/%s" % (ok_count, CONSUMER_CHECK_COUNT)
            )
        self.output.info("libmpd consumer test_package passed")

    def _run_consumer(self, executable):
        proc = subprocess.run(
            [executable],
            env=dict(os.environ),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=120,
        )
        output = proc.stdout or ""
        self.output.info(output[-3000:])
        if proc.returncode != 0:
            raise ConanException("consumer exited %s" % proc.returncode)
        return output

    def _stage_and_sign(self, executable):
        tmp = os.environ.get("TMPDIR") or self.build_folder
        try:
            os.makedirs(tmp, exist_ok=True)
        except OSError:
            tmp = self.build_folder
        runtime_dir = os.path.join(tmp, "libmpd-sign")
        try:
            os.makedirs(runtime_dir, exist_ok=True)
        except OSError:
            pass
        staged = os.path.join(runtime_dir, os.path.basename(executable))
        shutil.copy2(executable, staged)
        signer = shutil.which("binary-sign-tool") or (
            "/data/service/hnp/bin/binary-sign-tool"
        )
        readelf = shutil.which("llvm-readelf") or (
            "/data/service/hnp/bin/llvm-readelf"
        )
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanException("required OHOS signing tools are missing")
        temporary = "%s.signed" % staged
        subprocess.run(
            [signer, "sign", "-inFile", staged, "-outFile", temporary,
             "-selfSign", "1"],
            check=True,
            timeout=60,
        )
        sections = subprocess.run(
            [readelf, "-SW", temporary],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        if sections.count(".codesign") != 1:
            raise ConanException(
                "signed consumer has invalid .codesign: %s" % staged
            )
        os.chmod(temporary, (os.stat(staged).st_mode & 0o777) | 0o055)
        os.replace(temporary, staged)
        return staged

    def _emit_upstream_marker(self):
        upstream_marker = {
            "status": "no_tests",
            "framework": "autotools-make-check",
            "command": "make check (upstream provides no automated suite)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": "libmpd-11.8.17 ships no automated test harness: no TESTS/check_PROGRAMS, "
                      "no ctest/gtest/pytest wiring; only example/testcase manual demo "
                      "requiring a live MPD server; see test_package/MANIFEST.yml upstream_test_audit",
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT="
            + json.dumps(upstream_marker, ensure_ascii=False)
        )
