#!/usr/bin/env python3
"""Conan test_package for lib25519 0-20260614 — exercises the real C API.

Builds test_lib25519.c (X25519 keypair/agreement + Ed25519 sign/open
roundtrips and reject-cases) with CMake and runs it via ctest. Parses the
real assertion counts from the test output and emits the
HMBS_TEST_PACKAGE_RESULT evidence marker. Also re-emits the upstream
lib25519-test evidence persisted by the main recipe (cache-hit safe); any
count mismatch or missing evidence fails the test.
"""
import json
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.files import replace_in_file


class Lib25519TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _usable_compiler(self, key, fallbacks):
        # Profile conf may point at a stale /data/service/hnp/bin/clang
        # that no longer exists on preflight; HMBS prepends the real tool
        # dirs to PATH, so prefer an absolute conf path only when it
        # exists, else fall back to PATH lookup.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
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
        # The generated conan_toolchain.cmake can embed a stale
        # CMAKE_C_COMPILER (/data/service/hnp/bin/clang). Override it with
        # a usable compiler resolved via PATH so test_package configures.
        cc = self._usable_compiler("c", ["clang", "cc"])
        cxx = self._usable_compiler("cpp", ["clang++", "c++", "g++"])
        self.output.info("test_package CC={} CXX={}".format(cc, cxx))
        toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        if os.path.isfile(toolchain):
            for stale in ("/data/service/hnp/bin/clang",
                          "/data/service/hnp/bin/clang++"):
                try:
                    replace_in_file(self, toolchain, stale, cc if "++" not in stale else cxx)
                except Exception:
                    pass
        cmake = CMake(self)
        cmake.configure(variables={"CMAKE_C_COMPILER": cc,
                                   "CMAKE_CXX_COMPILER": cxx})
        cmake.build()

    def _emit_upstream_result(self, dep):
        """Re-emit the 13-split lib25519-test evidence from package()."""
        candidates = (
            os.path.join(dep.package_folder, "res", "upstream_test_result.json"),
            os.path.join(dep.package_folder, "upstream_test_result.json"),
        )
        for path in candidates:
            if not os.path.isfile(path):
                continue
            with open(path, "r", encoding="utf-8") as f:
                result = json.load(f)
            ok_shape = (
                isinstance(result, dict)
                and result.get("status") == "passed"
                and int(result.get("discovered", 0)) == 13
                and int(result.get("executed", 0)) == 13
                and int(result.get("passed", 0)) == 13
                and int(result.get("failed", 0)) == 0
                and int(result.get("skipped", 0)) == 0
            )
            self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False))
            if not ok_shape:
                raise ConanException(f"upstream test evidence invalid: {result}")
            return
        raise ConanException("upstream_test_result.json not found in package")

    def test(self):
        # readonly_tmp (HarmonyOS workers mount /tmp read-only): the
        # previous `bash -c "ctest ..." > log 2>&1` nesting needs shell
        # temp files under /tmp (mksh: /tmp/shf*.tmp) and a bash binary
        # that may not exist (CONFIG_SHELL fallback). Run ctest directly
        # with no bash wrapper, no pipes, no command substitution and no
        # shell redirection; ctest writes its own log via --output-log
        # (pure file write, no /tmp temp). TMPDIR/TMP/TEMP point at a
        # writable build_folder dir so ctest/cmake never touch /tmp.
        # NOTE (round 6): --output-on-failure hides passing-test stdout, and
        # --output-log only records what ctest prints, so a PASSING test left
        # an empty-of-markers log (discovered=0). -V forces ctest to always
        # emit the test stdout, which --output-log then captures for parsing.
        tmpdir = os.path.join(self.build_folder, "hmbs_tmp")
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except Exception:
            pass
        for var in ("TMPDIR", "TMP", "TEMP"):
            try:
                os.environ[var] = tmpdir
            except Exception:
                pass
        try:
            os.makedirs(self.build_folder, exist_ok=True)
        except Exception:
            pass
        log_path = os.path.join(self.build_folder, "test_lib25519.log")
        try:
            self.run(
                'ctest -V -R test_lib25519 '
                f'--output-log "{log_path}"',
                cwd=self.build_folder,
                env="conanrun",
            )
        except Exception:
            pass
        out = ""
        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                out = f.read()
        except OSError:
            out = ""
        self.output.info("test output:\n" + out)

        match = re.search(r"LIB25519_TEST_RESULT\s+passed=(\d+)\s+total=(\d+)", out)
        if match:
            passed_count, discovered = int(match.group(1)), int(match.group(2))
        else:
            discovered = len(re.findall(r"\[(PASS|FAIL)\]", out))
            passed_count = len(re.findall(r"\[PASS\]", out))
        marker = {
            "executed": True,
            "passed": discovered > 0 and passed_count == discovered,
            "command": "ctest -V -R test_lib25519",
            "discovered": discovered,
            "passedCount": passed_count,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))

        # Upstream suite evidence (13 lib25519-test operation splits).
        dep = self.dependencies["lib25519"]
        self._emit_upstream_result(dep)

        if not marker["passed"]:
            raise ConanException(
                f"test_package failed: {passed_count}/{discovered} assertions passed"
            )
