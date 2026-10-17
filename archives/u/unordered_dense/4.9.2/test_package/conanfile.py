#!/usr/bin/env python3
"""Conan test_package for unordered_dense — Conan L1 official test.

Compiles test_unordered_dense.cpp against the unordered_dense header-only
library and runs it. Uses Conan's CMakeToolchain for proper cross-compilation
support.
"""
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class UnorderedDenseTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    # ── OHOS SDK lld runtime helper (CI #17494 workaround) ──
    # On OHOS CI workers, the SDK lld depends on libxml2.so.16 at runtime and
    # the dynamic linker fails to resolve lld's RUNPATH ($ORIGIN/../lib),
    # so we prepend the SDK's llvm/lib to LD_LIBRARY_PATH before CMake.

    def _sdk_llvm_libdir(self):
        if str(self.settings.os) != "OHOS":
            return ""

        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cxx = compilers.get("cpp") or compilers.get("c")
        candidates = []
        if cxx:
            compiler = os.path.realpath(cxx)
            try:
                resource_dir = subprocess.check_output(
                    [cxx, "-print-resource-dir"],
                    stderr=subprocess.DEVNULL,
                    text=True,
                ).strip()
                candidates.append(os.path.dirname(os.path.dirname(resource_dir)))
            except (OSError, subprocess.CalledProcessError):
                pass
            candidates.append(
                os.path.join(os.path.dirname(os.path.dirname(compiler)), "lib")
            )

        for candidate in dict.fromkeys(candidates):
            if os.path.isfile(os.path.join(candidate, "libxml2.so.16")):
                return candidate
        return ""

    def _usable_sdk_llvm_libdir(self):
        if str(self.settings.os) != "OHOS":
            return ""

        cached = getattr(self, "_checked_sdk_llvm_libdir", None)
        if cached is not None:
            return cached

        sdk_llvm_lib = self._sdk_llvm_libdir()
        if sdk_llvm_lib:
            lld = os.path.join(os.path.dirname(sdk_llvm_lib), "bin", "ld.lld")
            probe_env = os.environ.copy()
            old_ld_path = probe_env.get("LD_LIBRARY_PATH", "")
            probe_env["LD_LIBRARY_PATH"] = os.pathsep.join(
                part for part in (sdk_llvm_lib, old_ld_path) if part
            )
            try:
                probe = subprocess.run(
                    [lld, "--version"],
                    env=probe_env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=10,
                    check=False,
                )
            except (OSError, subprocess.SubprocessError) as error:
                raise ConanException(
                    f"Cannot execute the active OHOS SDK linker {lld}: {error}"
                ) from error
            if probe is not None and probe.returncode == 0:
                self._checked_sdk_llvm_libdir = sdk_llvm_lib
                return sdk_llvm_lib
            raise ConanException(
                f"The active OHOS SDK linker failed its version probe: {lld}; "
                f"stderr={probe.stderr.strip()!r}"
            )

        raise ConanException(
            "Cannot locate the active OHOS SDK llvm/lib containing "
            "libxml2.so.16"
        )

    def _build_environment(self):
        environment = Environment()
        sdk_llvm_lib = self._usable_sdk_llvm_libdir()
        if sdk_llvm_lib:
            self.output.info(
                f"Prepending OHOS SDK linker runtime path: {sdk_llvm_lib}"
            )
            environment.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
        return environment

    def build(self):
        cmake = CMake(self)
        with self._build_environment().vars(self).apply():
            cmake.configure()
            cmake.build()

    def test(self):
        test_bin = os.path.join(self.build_folder, "test_unordered_dense")
        self.run(test_bin, env="conanrun")