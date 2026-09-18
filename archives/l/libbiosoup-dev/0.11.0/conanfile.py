#!/usr/bin/env python3
"""Conan recipe for libbiosoup-dev 0.11.0 — header-only bioinformatics data
structures (NucleicAcid, Sequence, Overlap, Timer, ProgressBar).

The headers live under include/biosoup/.

Upstream ships a GoogleTest suite (test/*.cpp, 11 TEST cases across 5 files).
It is compiled and executed here, so `conan create` really runs the upstream
tests (test_requires gtest). test_package additionally exercises the public
API from a consumer.
"""
import os

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout

_TEST_SOURCES = (
    "nucleic_acid_test.cpp",
    "overlap_test.cpp",
    "progress_bar_test.cpp",
    "sequence_test.cpp",
    "timer_test.cpp",
)


class LibBiosoupConan(ConanFile):
    name = "libbiosoup-dev"
    version = "0.11.0"
    description = "C++ header-only data structures for bioinformatics (biosoup)"
    license = "MIT"
    homepage = "https://github.com/rvaser/biosoup"
    url = "https://github.com/rvaser/biosoup"

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def build_requirements(self):
        # GoogleTest, used to build and run the upstream test suite during
        # `conan create`; never propagated to consumers.
        self.test_requires("gtest/1.17.0")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()

    def _gtest_folder(self):
        for setname in ("test", "build", "host"):
            deps = getattr(self.dependencies, setname, None)
            if deps is None:
                continue
            try:
                dep = deps["gtest"]
            except Exception:
                continue
            return dep.package_folder
        raise RuntimeError("gtest test_requires not found in dependency sets")

    def build(self):
        apply_conandata_patches(self)
        gfolder = self._gtest_folder()
        ginc = os.path.join(gfolder, "include")
        glib = os.path.join(gfolder, "lib")

        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cxx = str(executables.get("cpp") or "clang++")
        opt = "-O2" if self.settings.build_type == "Release" else "-g -O0"

        src = self.source_folder
        tests = " ".join(
            f'"{os.path.join(src, "test", name)}"' for name in _TEST_SOURCES
        )
        bin_path = os.path.join(self.build_folder, "biosoup_test")
        self.run(
            f'{cxx} -std=c++17 {opt} -pthread '
            f'-I "{ginc}" -I "{os.path.join(src, "include")}" '
            f'{tests} -L "{glib}" -lgtest -lgtest_main -o "{bin_path}"'
        )
        # Run the upstream GoogleTest suite (11 cases); non-zero exit = failure.
        self.run(f'"{bin_path}"')

    def package(self):
        copy(self, "*.hpp",
             src=os.path.join(self.source_folder, "include", "biosoup"),
             dst=os.path.join(self.package_folder, "include", "biosoup"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "biosoup")
        self.cpp_info.set_property("cmake_target_name", "biosoup::biosoup")
