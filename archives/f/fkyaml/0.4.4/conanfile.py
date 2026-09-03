#!/usr/bin/env python3
"""Conan recipe for fkyaml 0.4.4 (header-only C++ YAML library, CMake).

fkYAML is a C++ header-only YAML library (MIT). Upstream provides a CMake
package (fkYAML::fkYAML interface target) and a pkg-config file. Packaging
as header-library: install include/ + CMake config via upstream install rules.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class FkYamlConan(ConanFile):
    name = "fkyaml"
    version = "0.4.4"
    description = "fkYAML — header-only C++ YAML library (serialization/deserialization/order-preserving nodes)."
    license = "MIT"
    homepage = "https://github.com/fktn-k/fkYAML"
    url = "https://github.com/fktn-k/fkYAML"
    topics = ("yaml", "serialization", "header-only", "parser", "cpp17")
    package_type = "header-library"

    settings = "os", "arch", "compiler", "build_type"

    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        # Official GitHub tag archive; strip_root collapses the top dir.
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Header-only INTERFACE target — nothing to compile, only install
        # rules (include/ + CMake config + pkg-config) are generated.
        tc.variables["FK_YAML_BUILD_TEST"] = "OFF"
        tc.variables["FK_YAML_BUILD_FUZZ_TEST"] = "OFF"
        tc.variables["FK_YAML_BUILD_ALL_TEST"] = "OFF"
        tc.variables["FK_YAML_BUILD_EXAMPLES"] = "OFF"
        tc.variables["FK_YAML_RUN_BENCHMARK"] = "OFF"
        tc.variables["FK_YAML_RUN_CLANG_TIDY"] = "OFF"
        tc.variables["FK_YAML_RUN_IWYU"] = "OFF"
        tc.variables["FK_YAML_INSTALL_NATVIS"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # INTERFACE library: configure generates the CMake package files.

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "fkYAML")
        self.cpp_info.set_property("cmake_target_name", "fkYAML::fkYAML")
        self.cpp_info.set_property("pkg_config_name", "fkYAML")
        # Header-only interface target: no libs, headers under include/.
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libs = []