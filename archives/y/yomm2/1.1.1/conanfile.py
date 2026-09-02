#!/usr/bin/env python3
"""Conan recipe for yomm2 1.1.1 (CMake).

Fast, orthogonal, open multi-methods for C++17 — solve the Expression Problem.
Homepage: https://github.com/jll63/yomm2
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class Yomm2Conan(ConanFile):
    name = "yomm2"
    version = "1.1.1"
    description = "Fast, orthogonal, open multi-methods for C++17."
    license = "BSL-1.0"
    homepage = "https://github.com/jll63/yomm2"
    url = "https://github.com/jll63/yomm2"
    topics = ("open-methods", "multi-methods", "multiple-dispatch", "expression-problem", "cpp17")
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        # R32: settings.os checks must use `in ("Linux", "OHOS")`.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"yomm2 is validated only for Linux and OHOS, not {self.settings.os}"
            )

    def requirements(self):
        # yomm2 needs Boost headers (preprocessor/type_traits/dynamic_bitset)
        # both to build and for its CMake `find_package(Boost REQUIRED)`.
        self.requires("boost/1.90.0", transitive_headers=True, transitive_libs=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        # The GitHub archive extracts to `yomm2-1.1.1/`; strip_root collapses it.
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # CMakeDeps: make conan's boost/1.90.0 visible to the upstream
        # `find_package(Boost 1.53 REQUIRED)` (cmake_file_name "Boost").
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        # Upstream CMakeLists.txt/srowse uses the FindBoost-style uppercase
        # `${Boost_INCLUDE_DIR}` while CMakeDeps only exports the lowercase
        # `boost_INCLUDE_DIR`, so inject the include dir explicitly.
        boost = self.dependencies["boost"]
        boost_incs = [os.path.join(boost.package_folder, d) for d in boost.cpp_info.includedirs]
        tc.variables["Boost_INCLUDE_DIR"] = ";".join(boost_incs)
        tc.variables["Boost_INCLUDE_DIRS"] = ";".join(boost_incs)
        # Upstream CMakeLists.txt requires cmake_minimum_required(3.0); modern
        # CMake (>=3.5) dropped compatibility with < 3.5, so pin the policy
        # version minimum to let it configure on current CMake 4.x.
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # Library-only package: disable examples/tests/benchmarks (they are not
        # shipped with the package and require extra deps like google benchmark).
        tc.variables["YOMM2_ENABLE_EXAMPLES"] = "OFF"
        tc.variables["YOMM2_ENABLE_TESTS"] = "OFF"
        tc.variables["YOMM2_ENABLE_BENCHMARKS"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # CMAKE_POLICY_VERSION_MINIMUM must be a configure-time cache variable
        # (-D) to be visible before cmake_minimum_required(3.0) runs; a
        # toolchain set() is too late.
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "YOMM2")
        self.cpp_info.set_property("cmake_target_name", "YOMM2::yomm2")
        self.cpp_info.libs = ["yomm2"]
        self.cpp_info.set_property("cmake_build_modules", [])
        # Keep the upstream CMake package layout: headers live in include/yorel
        # and the exported target is YOMM2::yomm2.
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
