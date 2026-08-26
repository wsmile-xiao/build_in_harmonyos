#!/usr/bin/env python3
"""Conan recipe — libbcg729 1.1.2 (native upstream CMake)"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class LibBcg729Conan(ConanFile):
    name = "libbcg729"
    version = "1.1.2"
    description = (
        "Open-source implementation of the ITU G.729 Annex A/B speech codec "
        "(concurrent encoder and decoder channels)"
    )
    license = "GPL-3.0-only"
    homepage = "https://github.com/BelledonneCommunications/bcg729"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
    }
    default_options = {
        "shared": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Upstream ENABLE_STRICT adds -Werror -Wextra; on the OHOS cross toolchain
        # this turns harmless warnings into hard failures. Disable strict so real
        # compile errors still surface without blocking on noise.
        tc.variables["ENABLE_STRICT"] = False
        # Upstream unit tests need large speech test-data files and reach into
        # private symbols; they are not suitable for the cross-compile L1 test
        # and would force -fvisibility=hidden off. Keep them off.
        tc.variables["ENABLE_UNIT_TESTS"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # Upstream target is `bcg729` (libbcg729.so / -lbcg729).
        self.cpp_info.libs = ["bcg729"]
        self.cpp_info.set_property("cmake_file_name", "libbcg729")
        self.cpp_info.set_property("cmake_target_name", "libbcg729::bcg729")
        self.cpp_info.set_property("pkg_config_name", "libbcg729")
