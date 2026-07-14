#!/usr/bin/env python3
"""Conan recipe — mad (libmad) 0.16.4 — CMake build system.

libmad is a high-quality MPEG audio decoder library.
Source: https://codeberg.org/tenacityteam/libmad
"""
import os
from pathlib import Path

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class MadConan(ConanFile):
    name = "mad"
    version = "0.16.4"
    description = "MAD is a high-quality MPEG audio decoder library"
    license = "GPL-2.0-or-later"
    homepage = "https://codeberg.org/tenacityteam/libmad"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # No runtime dependencies
        pass

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

    def source(self):
        sources = self.conan_data["sources"]
        try:
            get(self, **{k: v for k, v in sources.items() if k != "backup_urls"},
                strip_root=True)
        except Exception:
            backup_urls = sources.get("backup_urls", [])
            if backup_urls:
                self.output.warning(f"Primary URL failed, trying backup: {backup_urls[0]}")
                get(self, url=backup_urls[0], sha256=sources["sha256"],
                    strip_root=True)
            else:
                raise

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: System same-name library — build static to avoid polluting /lib, /lib64
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        # CMake 4.x removed compat with < 3.5; project declares 3.1.0
        # Must be a cache variable so it's passed as -D on the command line,
        # before cmake_minimum_required() is processed.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # Optimize for accuracy (matching upstream packaging)
        tc.variables["OPTIMIZE"] = "ACCURACY"
        # E092: CMake doesn't recognize HarmonyOS as a platform;
        # override to Linux so CMake can configure properly.
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()
        # Fix compiler paths in generated toolchain: profile may point to
        # /data/service/hnp/bin/clang which doesn't exist on all environments.
        # Replace with PATH-resolved compiler from CC/CXX env vars.
        tc_file = Path(self.generators_folder) / "conan_toolchain.cmake"
        if tc_file.exists():
            content = tc_file.read_text(encoding="utf-8")
            content = content.replace(
                "/data/service/hnp/bin/clang", "clang")
            content = content.replace(
                "/data/service/hnp/bin/clang++", "clang++")
            tc_file.write_text(content, encoding="utf-8")

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["mad"]
s = ["mad"]
