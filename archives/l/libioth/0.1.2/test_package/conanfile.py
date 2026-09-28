#!/usr/bin/env python3
"""Conan test_package for libioth 0.1.2.

Consumer test (TAP-style binary with 13 checks covering the native-stack
lifecycle plus the deterministic iothaddr hash/mac/eui64 vectors). The
binary output is parsed for "ok" lines; the counts feed
HMBS_TEST_PACKAGE_RESULT. The no_tests upstream result persisted by the
main recipe (res/upstream_test_result.json) is re-emitted so the evidence
survives package cache hits.
"""
import glob
import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualBuildEnv

N_CHECKS = 13


class LibiothTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _writable_tmpdir(self):
        # Mirror the main recipe: OHOS /tmp is erofs read-only; cmake
        # try_compile and clang temp files must use the HMBS-injected
        # writable tmpdir (or a build-folder fallback).
        for var in ("TMPDIR", "TMP", "TEMP", "HMBS_TMPDIR"):
            val = os.environ.get(var)
            if val and os.path.isdir(val):
                return val
        fallback = os.path.join(self.build_folder, "hmbs-tmp")
        old = os.umask(0)
        try:
            os.makedirs(fallback, exist_ok=True)
        except Exception:
            pass
        finally:
            try:
                os.umask(old)
            except Exception:
                pass
        return fallback

    def generate(self):
        # Export the writable tmpdir via conanbuild.sh so the test
        # cmake configure/compile inherits it even when conanbuild.sh
        # ordering would otherwise shadow plain os.environ.
        tmpdir = self._writable_tmpdir()
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except Exception:
            pass
        for var in ("TMPDIR", "TMP", "TEMP"):
            os.environ[var] = tmpdir
            try:
                self.buildenv_info.define(var, tmpdir)
            except Exception:
                pass
        try:
            VirtualBuildEnv(self).generate()
        except Exception as exc:
            self.output.warning("VirtualBuildEnv generate failed: {}".format(exc))
        tc = CMakeToolchain(self)
        # Same sandbox try_compile probe skip as the main recipe.
        tc.cache_variables["CMAKE_C_COMPILER_WORKS"] = "1"
        tc.cache_variables["CMAKE_C_ABI_COMPILED"] = "1"
        tc.cache_variables["CMAKE_CXX_COMPILER_WORKS"] = "1"
        tc.cache_variables["CMAKE_CXX_ABI_COMPILED"] = "1"
        tc.generate()
        # Strategy-2: repair the generated toolchain file in place (see
        # main recipe); CLI/cache pin proven ineffective.
        try:
            cc = self._discover_c_compiler()
            self._repair_toolchain_files(cc)
        except Exception as exc:
            self.output.warning("test toolchain repair failed: {!r}".format(exc))

    def _discover_c_compiler(self):
        # Same probe as the main recipe: validate the profile compiler
        # path with a real `--version` run (os.access lies on HMDFS).
        cands = []
        try:
            exes = self.conf.get("tools.build:compiler_executables", default=None)
            if isinstance(exes, dict) and exes.get("c"):
                cands.append(str(exes.get("c")))
        except Exception:
            pass
        for var in ("CC", "HMBS_CC"):
            val = os.environ.get(var)
            if val:
                cands.append(val)
        try:
            found = shutil.which("clang")
        except Exception:
            found = None
        if found:
            cands.append(found)
        for pat in ("/data/service/hnp/bin/clang",
                    "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/bin/clang"):
            try:
                cands.extend(sorted(glob.glob(pat)))
            except Exception:
                pass
        seen = set()
        for path in cands:
            if not path or path in seen or not os.path.isfile(path):
                continue
            seen.add(path)
            try:
                proc = subprocess.run(
                    [path, "--version"],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, timeout=60,
                )
                if proc.returncode == 0:
                    self.output.info("test_package compiler: {}".format(path))
                    return path
            except Exception:
                pass
        return None

    def _repair_toolchain_files(self, cc):
        # Mirror of the main recipe repair (C-only consumer project).
        if not cc:
            return 0
        broken_c = "/data/service/hnp/bin/clang"
        broken_cxx = "/data/service/hnp/bin/clang++"
        fixed = 0
        for root, _dirs, files in os.walk(self.build_folder):
            if "conan_toolchain.cmake" not in files:
                continue
            p = os.path.join(root, "conan_toolchain.cmake")
            try:
                with open(p, encoding="utf-8", errors="replace") as fh:
                    txt = fh.read()
            except Exception:
                continue
            orig = txt
            if broken_cxx in txt:
                # Consumer is C-only; map a stale cxx entry onto the good cc
                # only if no better cxx is known (harmless for a C project).
                txt = txt.replace(broken_cxx, cc + "++" if cc.endswith("/clang") else cc)
            if broken_c in txt:
                txt = txt.replace(broken_c, cc)
            force = (
                "\n# HMBS strategy-2: authoritative compiler + probe skip "
                "(FORCE beats stale cache)\n"
            )
            force += 'set(CMAKE_C_COMPILER "%s" CACHE FILEPATH "C compiler" FORCE)\n' % cc
            force += 'set(CMAKE_C_COMPILER_WORKS 1 CACHE INTERNAL "" FORCE)\n'
            force += 'set(CMAKE_C_ABI_COMPILED 1 CACHE INTERNAL "" FORCE)\n'
            force += 'set(CMAKE_CXX_COMPILER_WORKS 1 CACHE INTERNAL "" FORCE)\n'
            force += 'set(CMAKE_CXX_ABI_COMPILED 1 CACHE INTERNAL "" FORCE)\n'
            if "HMBS strategy-2" not in txt:
                txt = txt.rstrip("\n") + "\n" + force
            if txt != orig:
                try:
                    with open(p, "w", encoding="utf-8", newline="\n") as fh:
                        fh.write(txt)
                    fixed += 1
                except Exception:
                    pass
        for root, _dirs, files in os.walk(self.build_folder):
            if "CMakeCache.txt" not in files:
                continue
            p = os.path.join(root, "CMakeCache.txt")
            try:
                with open(p, encoding="utf-8", errors="replace") as fh:
                    cache = fh.read()
                if broken_c in cache:
                    os.remove(p)
            except Exception:
                pass
        return fixed

    def build(self):
        # Process-level sync before cmake configure/build.
        tmpdir = self._writable_tmpdir()
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except Exception:
            pass
        for var in ("TMPDIR", "TMP", "TEMP"):
            os.environ[var] = tmpdir
        # Re-repair before configure; no CLI pin (round-3 mechanism).
        try:
            cc = self._discover_c_compiler()
            self._repair_toolchain_files(cc)
        except Exception as exc:
            self.output.warning("test toolchain re-repair failed: {!r}".format(exc))
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return
        # Never rely on system /tmp (read-only on the true machine).
        tmpdir = self._writable_tmpdir()
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except Exception:
            pass
        for var in ("TMPDIR", "TMP", "TEMP"):
            os.environ[var] = tmpdir
        binary = os.path.join(self.cpp.build.bindir, "test_libioth")
        if not os.path.isfile(binary):
            raise RuntimeError("test binary missing: {}".format(binary))
        # L0d gate: real execution of the consumer test binary.
        self.run(binary, env="conanrun")
        env = dict(os.environ)
        dep = self.dependencies["libioth"]
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
        command = "test_libioth (13 TAP checks: native-stack lifecycle + iothaddr vectors)"
        marker = {
            "executed": True,
            "passed": proc.returncode == 0 and passed_count == N_CHECKS and not has_failure,
            "command": command,
            "discovered": N_CHECKS,
            "passedCount": passed_count,
        }
        # Re-emit the no_tests upstream result persisted by the main recipe.
        res_json = os.path.join(dep.package_folder, "res", "upstream_test_result.json")
        if not os.path.isfile(res_json):
            raise RuntimeError("upstream_test_result.json missing from package res/")
        with open(res_json, "r", encoding="utf-8") as fh:
            upstream = json.load(fh)
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream))
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream))
        if (upstream.get("status") != "no_tests"
                or int(upstream.get("discovered", -1)) != 0
                or int(upstream.get("executed", -1)) != 0
                or not str(upstream.get("reason", "")).strip()):
            raise RuntimeError("upstream result invalid: {}".format(upstream))
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))
        if not marker["passed"]:
            raise RuntimeError(
                "test_package failed: {}/{} checks passed".format(passed_count, N_CHECKS)
            )
