#!/usr/bin/env python3
"""Conan test_package — liblockfile 1.17.1

L1 test: build a small consumer that exercises the lockfile_create /
lockfile_remove / lockfile_check API through the installed static library.
"""
import os
from pathlib import Path

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout


class LiblockfileTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def configure(self):
        # Override profile's compiler_executables if the path doesn't exist.
        # Profile may point to /data/service/hnp/bin/clang which doesn't exist
        # on all environments. Use PATH-resolved compiler instead.
        cc = os.environ.get("CC", "clang")
        cxx = os.environ.get("CXX", "clang++")
        self.conf_info.define("tools.build:compiler_executables",
                              {"c": cc, "cpp": cxx})

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: CMake doesn't recognize HarmonyOS as a platform
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()
        # Generate CMake dependency files so find_package(liblockfile) works
        CMakeDeps(self).generate()
        # Fix compiler paths: profile may point to non-existent /data/service/hnp/bin/clang
        tc_file = Path(self.generators_folder) / "conan_toolchain.cmake"
        if tc_file.exists():
            content = tc_file.read_text(encoding="utf-8")
            content = content.replace("/data/service/hnp/bin/clang", "clang")
            content = content.replace("/data/service/hnp/bin/clang++", "clang++")
            tc_file.write_text(content, encoding="utf-8")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Execute the built consumer binary that calls the real library API
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries directly.
        bash = os.environ.get("CONFIG_SHELL", "bash")
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_liblockfile")
        self.run(f"{bash} -c '\"{bin_path}\"'", env="conanrun")