#!/usr/bin/env python3
"""Consumer test for qtbase without a display server."""

import os
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class QtbaseTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    # ── CI #31406/#31646: OHOS SDK lld needs libxml2.so.16 at runtime ──
    # lld is a dynamic ELF with NEEDED libxml2.so.16 and RUNPATH
    # $ORIGIN/../lib. On CI workers the musl dynamic linker fails to
    # resolve lld's RUNPATH, so try-compile (cmake→clang++→lld) dies
    # with "Error loading shared library libxml2.so.16". The main
    # recipe already injects the SDK's llvm/lib into LD_LIBRARY_PATH
    # for the package build; the test_package must do the same so its
    # own cmake.configure() try-compile passes. This mirrors the
    # argagg/0.4.7 test_package precedent (CI #17494 workaround).

    def _sdk_llvm_libdir(self):
        if str(self.settings.os) != "OHOS":
            return ""
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cxx = compilers.get("cpp") or compilers.get("c")
        candidates = []
        if cxx:
            try:
                resource_dir = subprocess.check_output(
                    [cxx, "-print-resource-dir"],
                    stderr=subprocess.DEVNULL,
                    text=True,
                ).strip()
                # resource_dir = .../llvm/lib/clang/15.0.4
                candidates.append(
                    os.path.dirname(os.path.dirname(resource_dir))
                )
            except (OSError, subprocess.CalledProcessError):
                pass
            compiler = os.path.realpath(cxx)
            # Fallback: .../llvm/bin/clang++ -> .../llvm/lib
            candidates.append(
                os.path.join(os.path.dirname(os.path.dirname(compiler)), "lib")
            )
        for candidate in dict.fromkeys(candidates):
            if os.path.isfile(os.path.join(candidate, "libxml2.so.16")):
                return candidate
        return ""

    def generate(self):
        tc = CMakeToolchain(self)
        package_prefix = self.dependencies["qtbase"].package_folder
        tc.cache_variables["CMAKE_PREFIX_PATH"] = package_prefix
        tc.generate()

        # Inject the OHOS SDK's world-readable llvm/lib (containing
        # libxml2.so.16 with full symbols) into LD_LIBRARY_PATH, so the
        # cmake→clang→lld subprocess chain in build() can load it.
        sdk_llvm_lib = self._sdk_llvm_libdir()
        if sdk_llvm_lib:
            build_env = Environment()
            build_env.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
            build_env.vars(self).save_script("qtbase_test_ohos_sdk_libxml2")
            self.output.info(
                f"Injected OHOS SDK llvm/lib into LD_LIBRARY_PATH: "
                f"{sdk_llvm_lib}"
            )

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            bindirs = self.cpp.build.bindirs
            if not bindirs:
                raise ConanInvalidConfiguration(
                    "qtbase test package has no build bindir"
                )
            executable = os.path.join(bindirs[0], "test_qtbase")
            self.run(
                executable,
                env="conanrun",
                ignore_errors=False,
            )
