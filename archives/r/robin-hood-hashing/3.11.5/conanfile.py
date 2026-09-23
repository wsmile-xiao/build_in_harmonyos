#!/usr/bin/env python3
"""Conan recipe — robin-hood-hashing 3.11.5 (C++14 header-only hash map/set).

robin-hood-hashing is a fast C++14 header-only robin-hood hash map/set
implementation by martinus. Nothing is compiled: the single public header
src/include/robin_hood.h is installed together with the upstream CMake
config (INTERFACE library target robin_hood::robin_hood).

R32 note: no settings.os branch is needed — the OHOS-adapted conan maps
os=OHOS to CMAKE_SYSTEM_NAME=HarmonyOS via CMakeToolchain.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class RobinHoodHashingConan(ConanFile):
    name = "robin-hood-hashing"
    version = "3.11.5"
    description = "Fast & memory efficient hashtable based on robin hood hashing (header-only)"
    license = "MIT"
    homepage = "https://github.com/martinus/robin-hood-hashing"
    url = "https://github.com/martinus/robin-hood-hashing"  # 官方上游仓库

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)  # apply patches/0001 after source extraction

    # header-only: no build() — nothing to compile (R34: test_package still
    # exercises the real API, no fake compile logs)

    def build(self):
        # header-only library: nothing to compile; kept explicit so the
        # recipe is complete and CI has no build step to run
        pass

    def package(self):
        copy(self, "robin_hood.h",
             src=os.path.join(self.source_folder, "src", "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_id(self):
        self.info.clear()  # header-only: single package_id for all configurations

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []  # header-only：无链接库
        self.cpp_info.set_property("cmake_file_name", "robin_hood")
        self.cpp_info.set_property("cmake_target_name", "robin_hood::robin_hood")
