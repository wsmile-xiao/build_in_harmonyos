#!/usr/bin/env python3
"""Conan test_package for libcello 2.1.0 — L1 consumer-side test.

Exercises real Cello objects/containers/lifecycle with actual value + lifetime
assertions (not a compile-only stub). Links against libCello.a + system
pthread + libm, matching the upstream Makefile link line.

OHOS lld runtime: the same lld/libxml2.so.16 issue that affects the main
build also affects CMake try_compile / link here. This test_package reuses
the proven minised/1.16 pattern verbatim: compiler from Conan conf
`tools.build:compiler_executables`, SDK llvm/lib derived dynamically from
realpath(cc), Conan-native Environment().prepend_path so LD_LIBRARY_PATH
propagates to every CMake-spawned clang -> lld subprocess, and a pre-build
lld probe that fails loudly before configure. No hardcoded paths; kept
identical in logic to the main recipe so there is one implementation, not two.
"""
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class CelloTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    # ── Compiler & OHOS SDK runtime (same as main recipe) ─────────────
    def _get_cc(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        )
        return compilers.get("c") or "clang"

    def _get_cxx(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        )
        return compilers.get("cpp") or compilers.get("c") or "clang++"

    def _sdk_llvm_libdir(self):
        if str(self.settings.os) != "OHOS":
            return ""
        cc = self._get_cc()
        try:
            real_cc = os.path.realpath(cc)
        except OSError:
            return ""
        llvm_lib = os.path.join(
            os.path.dirname(os.path.dirname(real_cc)), "lib"
        )
        if os.path.isfile(os.path.join(llvm_lib, "libxml2.so.16")):
            return llvm_lib
        return ""

    def _probe_lld(self, sdk_lib):
        cc = self._get_cc()
        try:
            real_cc = os.path.realpath(cc)
        except OSError as e:
            raise ConanException(
                f"OHOS lld probe: cannot resolve compiler path {cc}: {e}"
            )
        bin_dir = os.path.dirname(real_cc)
        lld = None
        for cand in ("lld", "ld.lld"):
            p = os.path.join(bin_dir, cand)
            if os.path.isfile(p):
                lld = p
                break
        if not lld:
            raise ConanException(
                f"OHOS lld probe: lld not found in {bin_dir} "
                "(SDK layout unexpected)"
            )
        probe_env = dict(os.environ)
        existing = probe_env.get("LD_LIBRARY_PATH", "")
        probe_env["LD_LIBRARY_PATH"] = (
            sdk_lib + (os.pathsep + existing if existing else "")
        )
        try:
            res = subprocess.run(
                [lld, "-flavor", "gnu", "--version"],
                capture_output=True, text=True, env=probe_env,
            )
        except (OSError, subprocess.SubprocessError) as e:
            raise ConanException(
                f"OHOS lld probe: failed to run {lld}: {e}"
            )
        if res.returncode != 0:
            raise ConanException(
                f"OHOS lld probe: `{lld} -flavor gnu --version` exited "
                f"rc={res.returncode} — libxml2.so.16 not loadable from "
                f"{sdk_lib}; stderr:\n{res.stderr.strip()}"
            )
        first = res.stdout.splitlines()[0].strip() if res.stdout.strip() else "ok"
        self.output.info(f"OHOS lld probe OK: {lld} -> {first}")

    def _build_env(self):
        # Build the Conan-native Environment once; used for configure/build
        # and test so LD_LIBRARY_PATH survives every CMake-spawned
        # clang -> lld subprocess (try_compile, the link step, and the test
        # binary run).
        env = Environment()
        sdk_lib = self._sdk_llvm_libdir()
        if sdk_lib:
            self.output.info(
                f"Prepending OHOS SDK linker runtime path: {sdk_lib}"
            )
            env.prepend_path("LD_LIBRARY_PATH", sdk_lib)
            self._probe_lld(sdk_lib)
        return env

    def build(self):
        cmake = CMake(self)
        with self._build_env().vars(self).apply():
            cmake.configure()
            cmake.build()

    def test(self):
        cmake = CMake(self)
        with self._build_env().vars(self).apply():
            cmake.test()
            test_bin = os.path.join(self.cpp.build.bindirs[0], "test_cello")
            self.run(test_bin, env="conanrun")
