#!/usr/bin/env python3
"""Conan test_package for libgdf 0.1.3 — consumer test of the public C++ API.

Builds and runs test_libgdf.cpp: creates an empty GDF file with Writer,
verifies the 264-byte header, checks GDF_VERSION, and reopens the file with
Reader. The consumer program prints its own assertion count, which is reported
through HMBS_TEST_PACKAGE_RESULT.
"""
import json
import os
import re
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class LibgdfTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # HMBS readonly_tmp: /tmp is erofs read-only on device runners.
        # Pass through the HMBS-injected writable TMPDIR/TMP/TEMP into both
        # build and run scopes so cmake build and the consumer test binary
        # avoid /tmp. Only the temp root is replaced; test scope unchanged.
        tmp_env = Environment()
        for _var in ("TMPDIR", "TMP", "TEMP"):
            _val = os.environ.get(_var)
            if _val:
                tmp_env.define(_var, _val)
        tmp_env.vars(self, scope="build").save_script("hmbs_tmpdir_build")
        tmp_env.vars(self, scope="run").save_script("hmbs_tmpdir_run")
        # HMBS low-memory convergence (main package hit Signal 9/SIGKILL in
        # preflight compile): keep the single-TU consumer build minimal
        # (-O0 -g0, no inline/vectorize) and single-jobbed. Test scope and
        # assertions unchanged; scoped to this test package only.
        lowmem_env = Environment()
        lowmem_env.define("CFLAGS", "-O0 -g0 -fno-inline -fno-vectorize -fno-slp-vectorize")
        lowmem_env.define("CXXFLAGS", "-O0 -g0 -fno-inline -fno-vectorize -fno-slp-vectorize")
        lowmem_env.define("CMAKE_BUILD_PARALLEL_LEVEL", "1")
        lowmem_env.define("MAKEFLAGS", "-j1")
        lowmem_env.define("MALLOC_ARENA_MAX", "2")
        lowmem_env.vars(self, scope="build").save_script("hmbs_lowmem")

    def build(self):
        cmake = CMake(self)
        # Consumer side of the compiler fallback: the toolchain file baked
        # from the profile may reference compiler paths that do not exist on
        # this runner. Patch runs here (not in generate()) so the attribute
        # generators have already written conan_toolchain.cmake.
        fallback = self._compiler_fallback()
        if fallback:
            self._patch_toolchain_compiler(fallback)
            cmake.configure(variables={"CMAKE_C_COMPILER": fallback["c"], "CMAKE_CXX_COMPILER": fallback["cpp"]})
        else:
            cmake.configure()
        cmake.build()

    @staticmethod
    def _probe_compiler(path):
        if not path or not os.path.isfile(path):
            return False
        try:
            proc = subprocess.run(
                [path, "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=30,
                stdin=subprocess.DEVNULL,
            )
        except Exception:
            return False
        return proc.returncode == 0

    def _compiler_fallback(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        pinned_c = compilers.get("c")
        pinned_cpp = compilers.get("cpp")
        ok_c = self._probe_compiler(pinned_c)
        ok_cpp = self._probe_compiler(pinned_cpp)
        if ok_c and ok_cpp:
            return None
        self.output.info(f"hmbs compiler fallback: pinned compiler unusable (c={pinned_c} cpp={pinned_cpp})")
        cand_c = shutil.which("clang")
        cand_cpp = shutil.which("clang++")
        if cand_cpp and not cand_c:
            sib = os.path.join(os.path.dirname(cand_cpp), "clang")
            if self._probe_compiler(sib):
                cand_c = sib
        if cand_c and not cand_cpp:
            sib = os.path.join(os.path.dirname(cand_c), "clang++")
            if self._probe_compiler(sib):
                cand_cpp = sib
        final_c = pinned_c if ok_c else cand_c
        final_cpp = pinned_cpp if ok_cpp else cand_cpp
        if not self._probe_compiler(final_c) or not self._probe_compiler(final_cpp):
            raise ConanException(
                "OHOS preflight environment has no usable C/C++ compiler: "
                f"profile-pinned c={pinned_c} cpp={pinned_cpp} failed probing "
                "and no working clang/clang++ was found via PATH. This is an "
                "environment fault, not a recipe bug."
            )
        self.output.info(f"hmbs compiler fallback: using CC={final_c} CXX={final_cpp}")
        os.environ["CC"] = final_c
        os.environ["CXX"] = final_cpp
        cc_env = Environment()
        cc_env.define("CC", final_c)
        cc_env.define("CXX", final_cpp)
        cc_env.vars(self, scope="build").save_script("hmbs_cc_fallback")
        pairs = []
        if not ok_c and pinned_c:
            pairs.append((pinned_c, final_c))
        if not ok_cpp and pinned_cpp:
            pairs.append((pinned_cpp, final_cpp))
        return {"c": final_c, "cpp": final_cpp, "pairs": pairs}

    def _patch_toolchain_compiler(self, fallback):
        tc_path = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        if not os.path.isfile(tc_path):
            return
        with open(tc_path, "r", encoding="utf-8", errors="replace") as handle:
            text = handle.read()
        patched = text
        for old, new in fallback["pairs"]:
            if old and new:
                patched = patched.replace(old, new)
        if patched != text:
            with open(tc_path, "w", encoding="utf-8") as handle:
                handle.write(patched)
            self.output.info("hmbs compiler fallback: patched conan_toolchain.cmake compiler paths")

    def _read(self, path):
        if not os.path.isfile(path):
            return ""
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            return handle.read()

    def test(self):
        test_pkg = {
            "executed": False,
            "passed": False,
            "command": "./test_libgdf",
            "discovered": 0,
            "passedCount": 0,
        }
        if not can_run(self):
            test_pkg["command"] = "CMake build (compile+link) only: cannot run on build host"
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False))
            print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False), flush=True)
            return
        bash = os.environ.get("SHELL") or os.environ.get("CONFIG_SHELL") or "/bin/sh"
        out_file = os.path.join(os.getcwd(), "test_libgdf-console.log")
        passed = True
        try:
            self.run(f"{bash} -c {shlex.quote('./test_libgdf > ' + shlex.quote(out_file) + ' 2>&1')}", env="conanrun")
        except Exception:
            passed = False
        output = self._read(out_file)
        self.output.info(output)
        checks = re.search(r"test_libgdf: (\d+) checks passed", output)
        if checks:
            test_pkg["discovered"] = int(checks.group(1))
        test_pkg["executed"] = True
        test_pkg["passed"] = passed
        test_pkg["passedCount"] = test_pkg["discovered"] if passed else 0
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False))
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False), flush=True)
        if not passed:
            raise ConanException("consumer test failed:\n" + output[-2000:])
