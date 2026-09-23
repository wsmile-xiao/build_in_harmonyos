#!/usr/bin/env python3
"""Conan test_package for libosmpbf 1.6.1 — real API consumer (R34).

Builds test.cpp against the installed libosmpbf via CMake and runs it.
test.cpp performs 7 real assertions (version macro, namespace constants,
BlobHeader/Blob/PrimitiveBlock/HeaderBlock protobuf round-trips).

Evidence markers (hmbs preflight hard gates):
- HMBS_TEST_PACKAGE_RESULT: discovered/passedCount parsed from the real
  "RESULT: P passed, F failed" trailer line; only emitted after the
  binary exits 0 with 7/7.
- HMBS_UPSTREAM_TEST_RESULT: status=no_tests. Upstream C++ ships no test
  suite (no enable_testing()/add_test(), no tests/ directory; audit in
  MANIFEST.yml). Re-emitted here because the main-recipe build() output
  may be skipped on cache-hit preflight rounds (c10t precedent).
"""

import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import replace_in_file


class LibosmpbfTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _usable_compiler(self, key, fallbacks):
        # Mirror the main recipe: conf absolute path only when it exists and
        # passes a --version probe, else PATH lookup (HMBS prepends tool dirs).
        try:
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict) or {}
        except Exception:
            compilers = {}
        cand = compilers.get(key)
        if cand and os.path.isabs(str(cand)) and os.path.isfile(str(cand)):
            try:
                p = subprocess.run([str(cand), "--version"],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   timeout=15)
                if p.returncode == 0:
                    return str(cand)
            except Exception:
                pass
            self.output.warning(
                "conf compiler '{}' unusable; falling back to PATH".format(cand))
        for name in fallbacks:
            found = shutil.which(name)
            if found and os.path.isfile(found):
                return found
        if cand and os.path.isfile(str(cand)):
            return str(cand)
        return fallbacks[0]

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        # Match the main recipe: device cmake has no HarmonyOS platform
        # module, force the Linux branches for the consumer build too.
        if str(self.settings.os) == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        # Registry protobuf exports cmake_find_mode=none: CMakeDeps
        # generates no config for it, so point the consumer's own
        # find_package(Protobuf CONFIG) at the installed upstream configs
        # (grpc/brpc test_package wiring). Available transitively via the
        # tested libosmpbf requirement.
        try:
            _protobuf = self.dependencies["protobuf"]
            _protobuf_pkg = _protobuf.package_folder.replace("\\", "/")
            tc.variables["Protobuf_DIR"] = os.path.join(
                _protobuf_pkg, "lib", "cmake", "protobuf")
            tc.variables["protobuf_DIR"] = os.path.join(
                _protobuf_pkg, "lib", "cmake", "protobuf")
            tc.variables["utf8_range_DIR"] = os.path.join(
                _protobuf_pkg, "lib", "cmake", "utf8_range")
            tc.variables["PROTOBUF_PREFIX"] = _protobuf_pkg
        except Exception:
            self.output.warning("protobuf not in test graph; skipping Protobuf_DIR")
        try:
            _abseil_pkg = self.dependencies["abseil-cpp"].package_folder.replace("\\", "/")
            tc.variables["absl_DIR"] = os.path.join(_abseil_pkg, "lib", "cmake", "absl")
        except Exception:
            pass
        _cc = self._usable_compiler("c", ["clang", "cc"])
        _cxx = self._usable_compiler("cpp", ["clang++", "c++", "g++"])
        self.output.info("test_package CC={} CXX={}".format(_cc, _cxx))
        tc.variables["CMAKE_C_COMPILER"] = _cc
        tc.variables["CMAKE_CXX_COMPILER"] = _cxx
        tc.generate()

    def build(self):
        # E002/readonly_tmp: same writable-tmp guard as the main recipe —
        # consumer configure on OHOS must not fall back to readonly /tmp.
        _tmp = os.environ.get("TMPDIR") or os.environ.get("TMP") or os.environ.get("TEMP")
        if not (_tmp and os.path.isdir(_tmp)):
            _tmp = os.path.join(self.build_folder, "hmbs-tmp")
            try:
                os.makedirs(_tmp, exist_ok=True)
            except Exception:
                pass
            os.environ["TMPDIR"] = _tmp
            os.environ["TMP"] = _tmp
            os.environ["TEMP"] = _tmp
        # Consumer-side stale-path patch (libcli precedent): replace only
        # confirmed-unusable absolute paths, then pass compilers explicitly.
        cc = self._usable_compiler("c", ["clang", "cc"])
        cxx = self._usable_compiler("cpp", ["clang++", "c++", "g++"])
        self.output.info("test_package CC={} CXX={}".format(cc, cxx))
        try:
            toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
            if os.path.isfile(toolchain):
                for stale, good in (("/data/service/hnp/bin/clang++", cxx),
                                    ("/data/service/hnp/bin/clang", cc)):
                    try:
                        replace_in_file(self, toolchain, stale, good)
                    except Exception:
                        pass
        except Exception:
            pass
        os.environ["CC"] = cc
        os.environ["CXX"] = cxx
        cmake = CMake(self)
        cmake.configure(variables={"CMAKE_C_COMPILER": cc,
                                   "CMAKE_CXX_COMPILER": cxx})
        cmake.build()

    def test(self):
        if not can_run(self):
            tp = {
                "executed": False,
                "passed": False,
                "command": "test_libosmpbf (can_run=false)",
                "discovered": 7,
                "passedCount": 0,
            }
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(tp, ensure_ascii=False))
            ut = {
                "status": "skipped",
                "framework": "ctest",
                "command": "ctest (can_run=false)",
                "discovered": 0,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": "can_run is False for this configuration",
            }
            self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(ut, ensure_ascii=False))
            return

        build_bindir = os.path.join(self.build_folder, "build")
        candidates = [
            os.path.join(self.build_folder, "test_libosmpbf"),
            os.path.join(build_bindir, "test_libosmpbf"),
        ]
        binary = next((c for c in candidates if os.path.isfile(c)), candidates[0])
        if not os.path.isfile(binary):
            # Fall back to a recursive search inside the build folder.
            found = None
            for root, _dirs, files in os.walk(self.build_folder):
                if "test_libosmpbf" in files or "test_libosmpbf.exe" in files:
                    name = "test_libosmpbf.exe" if "test_libosmpbf.exe" in files else "test_libosmpbf"
                    found = os.path.join(root, name)
                    break
            if found is None:
                raise ConanException("test binary not found under {}".format(self.build_folder))
            binary = found
        if os.path.getsize(binary) < 1024:
            raise ConanException("test binary suspiciously small: {}".format(binary))

        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries reliably;
        # wrap execution in bash like the zlib test_package precedent.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        logfile = os.path.join(self.build_folder, "test_package.log")
        self.run(
            '{} -c \'"{}" > "{}" 2>&1\''.format(bash, binary, logfile),
            env="conanrun",
            ignore_errors=True,
        )

        out = ""
        if os.path.isfile(logfile):
            with open(logfile, "r", encoding="utf-8", errors="replace") as f:
                out = f.read()
        for line in out.splitlines()[-12:]:
            self.output.info("test_libosmpbf | {}".format(line))

        # Falsification guard: a harness that cannot catch failure is
        # worthless (toybox tar-B precedent). Require the real trailer.
        m = re.search(r"RESULT:\s*(\d+)\s*passed,\s*(\d+)\s*failed", out)
        if not m:
            raise ConanException("test binary produced no RESULT line — harness broken")
        passed = int(m.group(1))
        failed = int(m.group(2))
        discovered = passed + failed
        ok = failed == 0 and discovered == 7 and "ALL CHECKS PASSED (7/7)" in out

        marker = {
            "executed": True,
            "passed": ok,
            "command": "test_libosmpbf (7 osmpbf API checks)",
            "discovered": discovered,
            "passedCount": passed,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False), flush=True)
        if not ok:
            raise ConanException("test_libosmpbf failed: {}/{} passed".format(passed, discovered))

        upstream_marker = {
            "status": "no_tests",
            "framework": "ctest",
            "command": "upstream audit (libosmpbf 1.6.1 C++ has no test suite)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "libosmpbf 1.6.1 上游 C++ 无可接入的测试套件：顶层与 osmpbf/tools 的 "
                "CMakeLists.txt 从未调用 enable_testing()/add_test()，源码树无 tests/ 或 "
                "test/ 目录，无 make check/ctest 入口；唯一的 ReadFileTest.java 系 Java 侧 "
                "Maven 测试，与本 C++ Conan 包无关（详见 test_package/MANIFEST.yml 审计）"
            ),
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream_marker, ensure_ascii=False)
        )
        print(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream_marker, ensure_ascii=False),
            flush=True,
        )
        self.output.info("libosmpbf test_package passed (7/7)")
