#!/usr/bin/env python3
"""Conan recipe for CaDiCaL 2.1.3."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class CadicalConan(ConanFile):
    name = "cadical"
    version = "2.1.3"
    description = "Simplified Satisfiability Solver"
    license = "MIT"
    homepage = "https://github.com/arminbiere/cadical"
    url = ""
    topics = "sat-solver", "solver", "ipasir"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "CaDiCaL 2.1.3 only builds the static library libcadical.a"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # CaDiCaL has a custom configure script. It reads CXX and CXXFLAGS from
        # the Conan build environment and does not support Autotools prefixes.
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        self.run("sh ./configure", env="conanbuild", cwd=self.source_folder)
        self.run("make -j1", env="conanbuild", cwd=self.source_folder)
        self.run("make test", env="conanbuild", cwd=self.source_folder)

    def package(self):
        source_build = os.path.join(self.source_folder, "build")
        source_include = os.path.join(self.source_folder, "src")

        copy(self, "libcadical.a", src=source_build, dst=os.path.join(self.package_folder, "lib"))
        for header in ("cadical.hpp", "ccadical.h", "ipasir.h"):
            copy(self, header, src=source_include, dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["cadical"]
        self.cpp_info.set_property("cmake_file_name", "cadical")
        self.cpp_info.set_property("cmake_target_name", "cadical::cadical")
        self.cpp_info.set_property("pkg_config_name", "cadical")
