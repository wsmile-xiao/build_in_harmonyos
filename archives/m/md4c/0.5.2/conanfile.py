#!/usr/bin/env python3
"""Conan recipe for md4c 0.5.2.

md4c is a fast C Markdown parser with a SAX-like callback interface.
Upstream provides a standard CMake build (src/CMakeLists.txt) that
builds two libraries: `md4c` (the core parser) and `md4c-html`
(the HTML renderer built on top of md4c).

This recipe uses the upstream CMake build unmodified, only disabling the
`md2html` command-line executable (not needed for the library package) and
forcing a static library (BUILD_SHARED_LIBS=OFF) for OHOS cross-compilation.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class Md4cConan(ConanFile):
    name = "md4c"
    version = "0.5.2"
    description = "Fast C Markdown parser with a SAX-like callback interface"
    license = "MIT"
    homepage = "https://github.com/mity/md4c"
    url = "https://github.com/mity/md4c"
    topics = ("markdown", "parser", "commonmark")

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
    }
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: system same-name library must be static for OHOS cross-compilation
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        # Disable the md2html executable; we package only the libraries
        tc.variables["BUILD_MD2HTML_EXECUTABLE"] = False
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
        self.cpp_info.set_property("cmake_file_name", "md4c")
        self.cpp_info.set_property("pkg_config_name", "md4c")

        # Core parser library
        md4c = self.cpp_info.components["md4c"]
        md4c.set_property("cmake_target_name", "md4c::md4c")
        md4c.libs = ["md4c"]

        # HTML renderer library (links against the core parser)
        md4c_html = self.cpp_info.components["md4c-html"]
        md4c_html.set_property("cmake_target_name", "md4c::md4c-html")
        md4c_html.set_property("pkg_config_name", "md4c-html")
        md4c_html.libs = ["md4c-html"]
        md4c_html.requires = ["md4c"]