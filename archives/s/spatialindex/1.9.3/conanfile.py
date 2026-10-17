#!/usr/bin/env python3
"""Conan recipe for spatialindex 1.9.3 — R-tree/MVR-tree/TPR-tree library.

libspatialindex (OSGeo) is a C++ spatial index library.  CMake build,
no external dependencies.

Platform notes:
- Nothing is stripped on install (llvm-strip output is refused by the
  platform's exec policy — yices 2.7.0 evidence + knowledge draft).
- Upstream sets BUILD_SHARED_LIBS ON unconditionally; both flavours are
  produced by the toolchain defaults.
"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class SpatialindexConan(ConanFile):
    name = "spatialindex"
    version = "1.9.3"
    description = ("libspatialindex - C++ implementation of R*-tree, "
                   "MVR-tree and TPR-tree spatial indexes")
    license = "MIT"
    homepage = "https://github.com/libspatialindex/libspatialindex"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        # url may arrive as a candidate list (the CI pre-download step
        # rewrites conandata's url into [mirror, official]) — conan's
        # get() handles both shapes natively.
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        # build upstream gtest suites too — the gates job runs the resulting
        # test-* executables for R51 evidence
        tc.variables["SIDX_BUILD_TESTS"] = True
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "spatialindex")
        self.cpp_info.set_property("cmake_target_name", "spatialindex::spatialindex")
        self.cpp_info.libs = ["spatialindex"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]
