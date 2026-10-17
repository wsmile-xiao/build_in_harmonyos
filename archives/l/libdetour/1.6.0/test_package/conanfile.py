#!/usr/bin/env python3
"""Conan test_package — libdetour 1.6.0.

Builds the Detour consumer test, runs it, parses the real CHECK-OK
counts for the HMBS_TEST_PACKAGE_RESULT marker, and re-emits the
upstream Catch2 evidence persisted by the main recipe package.
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
from conan.tools.env import Environment, VirtualRunEnv


class LibdetourTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # Same OHOS preflight hardening as the main recipe: this
        # test_package is an independent consumer recipe, so the main
        # recipe's hmbs_fix script does not propagate here. Resolve the
        # compiler the same way and forward the writable TMPDIR plus the
        # lld host runtime into this recipe's conanbuild environment.
        CMakeDeps(self).generate()
        VirtualRunEnv(self).generate()
        cc_conf = cxx_conf = ""
        try:
            exes = self.conf.get("tools.build:compiler_executables") or {}
            if isinstance(exes, dict):
                cc_conf = exes.get("c") or ""
                cxx_conf = exes.get("cpp") or ""
        except Exception:
            pass
        cc = cc_conf if (cc_conf and os.path.isfile(cc_conf)) else ""
        cxx = cxx_conf if (cxx_conf and os.path.isfile(cxx_conf)) else ""
        cc_fallback = cxx_fallback = False
        if not cc:
            cc = shutil.which("clang") or shutil.which("cc") or ""
            cc_fallback = bool(cc)
        if not cxx:
            cxx = shutil.which("clang++") or shutil.which("c++") or ""
            cxx_fallback = bool(cxx)
        tc = CMakeToolchain(self)
        if cc_fallback and cc:
            tc.variables["CMAKE_C_COMPILER"] = cc
        if cxx_fallback and cxx:
            tc.variables["CMAKE_CXX_COMPILER"] = cxx
        tc.generate()
        env = Environment()
        for _k in ("TMPDIR", "TMP", "TEMP"):
            _v = os.environ.get(_k)
            if _v:
                env.define(_k, _v)
        if cc_fallback and cc:
            env.define("CC", cc)
        if cxx_fallback and cxx:
            env.define("CXX", cxx)
        llvm_lib = self._llvm_lib_for_lld(cc or cxx)
        if llvm_lib:
            env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
        env.vars(self).save_script("hmbs_fix")

    def _llvm_lib_for_lld(self, cc_hint=""):
        cc = cc_hint or ""
        if not cc:
            try:
                exes = self.conf.get("tools.build:compiler_executables") or {}
                if isinstance(exes, dict):
                    cc = exes.get("c") or ""
            except Exception:
                cc = ""
        if not cc:
            cc = shutil.which("clang") or ""
        if not cc:
            return ""
        try:
            proc = subprocess.run([cc, "-print-search-dirs"], capture_output=True,
                                  text=True, timeout=60)
        except Exception:
            return ""
        out = (proc.stdout or "") + (proc.stderr or "")
        for line in out.splitlines():
            if not line.startswith("libraries:"):
                continue
            paths = line.split("=", 1)[1] if "=" in line else ""
            for p in paths.replace(";", ":").split(":"):
                p = p.strip().lstrip("=")
                if not p:
                    continue
                for cand in (p, os.path.dirname(p.rstrip("/"))):
                    try:
                        if os.path.isfile(os.path.join(cand, "libxml2.so.16")):
                            return cand
                    except OSError:
                        pass
        return ""

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _emit_upstream_result(self):
        dep = self.dependencies["libdetour"]
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
                and int(result.get("discovered", 0)) > 0
                and int(result.get("executed", 0)) == int(result.get("discovered", 0))
                and int(result.get("passed", 0)) == int(result.get("discovered", 0))
                and int(result.get("failed", 0)) == 0
                and int(result.get("skipped", 0)) == 0
            )
            self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False))
            if not ok_shape:
                raise ConanException("upstream test evidence invalid: %s" % result)
            return
        raise ConanException("upstream_test_result.json not found in libdetour package")

    def test(self):
        if not can_run(self):
            raise ConanException("test_package requires a runnable host")
        test_bin = None
        for root, _, files in os.walk(self.build_folder):
            if "libdetour_test" in files:
                test_bin = os.path.join(root, "libdetour_test")
                break
        if test_bin is None or not os.path.isfile(test_bin):
            raise ConanException("libdetour_test binary not found")
        self.run(test_bin, env="conanrun")
        proc = subprocess.run([test_bin], capture_output=True, text=True, timeout=60)
        out = (proc.stdout or "") + (proc.stderr or "")
        self.output.info("consumer test output:\n" + out)
        passed_count = len(re.findall(r"^CHECK-OK:", out, re.MULTILINE))
        discovered = 3
        marker = {
            "executed": True,
            "passed": proc.returncode == 0 and passed_count == discovered,
            "command": "./libdetour_test (navmesh lifecycle, convex poly sample, query/vector helpers)",
            "discovered": discovered,
            "passedCount": passed_count,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))
        self._emit_upstream_result()
        if not marker["passed"]:
            raise ConanException("test_package failed: %d/%d checks passed" % (passed_count, discovered))
