#!/usr/bin/env python3
"""Conan recipe — lexbor 3.0.0 (HTML/CSS parser library, pure C, CMake).

lexbor is a pure-C library with zero external dependencies, using CMake.
Official source: https://github.com/lexbor/lexbor (tag v3.0.0).

Build notes:
- Builds both shared (lexbor) and static (lexbor_static) libraries by
  default upstream; we let the `shared` option control the artifact type
  (R26: only system-name libs are forced static; lexbor is not a system lib).
- No `make check` target; upstream tests are built with
  LEXBOR_BUILD_TESTS=ON and run via ctest (see MANIFEST.yml).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LexborConan(ConanFile):
    name = "lexbor"
    version = "3.0.0"
    description = "Open source HTML Renderer library - fast, lightweight HTML/CSS parser"
    license = "Apache-2.0"
    homepage = "https://lexbor.com"
    url = "https://github.com/lexbor/lexbor"  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # pure C library, no external dependencies
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # lexbor upstream builds both shared and static; honor the option.
        tc.variables["LEXBOR_BUILD_SHARED"] = "ON" if self.options.shared else "OFF"
        tc.variables["LEXBOR_BUILD_STATIC"] = "OFF" if self.options.shared else "ON"
        # No tests/examples/utils in the package build (keep CI fast and clean)
        tc.variables["LEXBOR_BUILD_TESTS"] = "OFF"
        tc.variables["LEXBOR_BUILD_EXAMPLES"] = "OFF"
        tc.variables["LEXBOR_BUILD_UTILS"] = "OFF"
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
        if self.options.shared:
            self.cpp_info.libs = ["lexbor"]
        else:
            self.cpp_info.libs = ["lexbor_static"]
        self.cpp_info.set_property("cmake_file_name", "lexbor")
        self.cpp_info.set_property("cmake_target_name", "lexbor::lexbor")