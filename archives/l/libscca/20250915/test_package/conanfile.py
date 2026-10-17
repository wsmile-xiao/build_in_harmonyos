#!/usr/bin/env python3
"""Conan test_package — libscca 20250915.

Runs the consumer test binary (5 real libscca API assertions) and
re-emits the upstream `make check` evidence persisted in res/.
"""

import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import replace_in_file


class LibsccaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        # Preflight 2026-09-16: conan_toolchain.cmake embeds a stale
        # CMAKE_C_COMPILER (/data/service/hnp/bin/clang) that is absent on
        # the HMBS host, so cmake.configure() dies at project(). Same
        # signature as libcli/1.10.7: resolve a usable compiler via PATH
        # fallback, repair the toolchain file entry, and pass it explicitly.
        # CMake try-compiles also spill into TMPDIR; /tmp is read-only on
        # OHOS (readonly_tmp), so wrap the configure+build in a writable
        # TMPDIR (HMBS-injected value preferred, else build_folder/tmp).
        # Only the compiler path and temp root are replaced; no test is
        # removed or skipped.
        cc = self._usable_compiler("c", ["clang", "cc"])
        cxx = self._usable_compiler("cpp", ["clang++", "c++", "g++"])
        self.output.info("test_package CC=%s CXX=%s" % (cc, cxx))
        toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        if os.path.isfile(toolchain):
            for stale in ("/data/service/hnp/bin/clang",
                          "/data/service/hnp/bin/clang++"):
                try:
                    replace_in_file(
                        self, toolchain, stale,
                        cc if "++" not in stale else cxx)
                except Exception:
                    pass
        with self._writable_tmp(cc, cxx).vars(self).apply():
            cmake = CMake(self)
            cmake.configure(variables={"CMAKE_C_COMPILER": cc,
                                       "CMAKE_CXX_COMPILER": cxx})
            cmake.build()

    def _usable_compiler(self, key, fallbacks):
        # Profile conf may point at a stale absolute clang that no longer
        # exists on this worker; prefer it only when the file exists, else
        # fall back to a PATH lookup (HMBS prepends real tool dirs to PATH).
        try:
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={},
                check_type=dict) or {}
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

    def _writable_tmp(self, cc, cxx):
        # Prefer the HMBS-injected writable TMPDIR/TMP/TEMP; fall back to a
        # build_folder private dir. Never use bare /tmp (erofs read-only).
        tmpdir = ""
        for candidate in (os.environ.get("TMPDIR"), os.environ.get("TMP"),
                          os.environ.get("TEMP")):
            if candidate and os.path.isdir(candidate):
                tmpdir = candidate
                break
        if not tmpdir:
            tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env = Environment()
        env.define_path("TMPDIR", tmpdir)
        env.define_path("TMP", tmpdir)
        env.define_path("TEMP", tmpdir)
        # Export the same usable compilers so CMake try-compiles do not
        # reuse the stale absolute path from the profile.
        if cc and os.path.isfile(cc):
            env.define("CC", cc)
            bindir = os.path.dirname(cc)
            if bindir and os.path.isdir(bindir):
                try:
                    env.prepend_path("PATH", bindir)
                except Exception:
                    pass
        if cxx and os.path.isfile(cxx):
            env.define("CXX", cxx)
        return env

    def test(self):
        if not can_run(self):
            return
        bindirs = self.cpp.build.bindirs
        if not bindirs:
            raise ConanException("No bindirs found")
        bin_path = os.path.join(bindirs[0], "test_libscca")
        if not os.path.isfile(bin_path):
            raise ConanException("Test binary not found: %s" % bin_path)
        log = os.path.join(self.build_folder, "test_package.log")
        cmd = "cd %s && %s > %s 2>&1" % (self.build_folder, bin_path, log)
        rc = self.run(cmd, env="conanrun", ignore_errors=True)
        discovered = 0
        passed_count = 0
        with open(log, encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if line.startswith("case ") and line.endswith(": PASS"):
                    discovered += 1
                    passed_count += 1
                elif line.startswith("case ") and line.endswith(": FAIL"):
                    discovered += 1
                elif line.startswith("RESULT: "):
                    parts = line[len("RESULT: "):].split("/")
                    if len(parts) == 2:
                        try:
                            passed_count = int(parts[0])
                            discovered = int(parts[1])
                        except ValueError:
                            pass
        ok = (rc == 0) and (discovered > 0) and (passed_count == discovered)
        result = {
            "executed": True,
            "passed": ok,
            "command": cmd,
            "discovered": discovered,
            "passedCount": passed_count,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(result))
        if not ok:
            raise ConanException(
                "test_package failed: rc=%s passed=%s/%s, see %s"
                % (rc, passed_count, discovered, log))
        upstream_path = os.path.join(
            self.dependencies["libscca"].package_folder,
            "res", "upstream_test_result.json")
        if not os.path.isfile(upstream_path):
            raise ConanException(
                "Packaged upstream test result missing: %s" % upstream_path)
        with open(upstream_path, encoding="utf-8") as f:
            upstream_result = json.load(f)
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream_result))
