#!/usr/bin/env python3
"""Conan recipe for opencore-amr 0.1.6 (Autotools).

opencore-amr provides AMR-NB and AMR-WB speech codec libraries
derived from the OpenCore codec implementation.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.env import Environment
from conan.tools.layout import basic_layout


class OpencoreAmrConan(ConanFile):
    name = "opencore-amr"
    version = "0.1.6"
    description = "AMR-NB and AMR-WB speech codec library from OpenCore implementation"
    license = "Apache-2.0"
    homepage = "https://sourceforge.net/projects/opencore-amr/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

        # opencore-amr is C-only but uses CXXLINK; the CI profile sets
        # -stdlib=libc++ -std=c++17 in CXXFLAGS which fails the C++ compiler
        # check on workers without libc++. Override to simple -O2.
        env = Environment()
        env.define("CXXFLAGS", "-O2")
        env.vars(self, scope="build").save_script("conanbuildcxx")

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # Both components share the same include root
        # Headers are at include/opencore-amrnb/ and include/opencore-amrwb/
        self.cpp_info.components["amrnb"].libs = ["opencore-amrnb"]
        self.cpp_info.components["amrwb"].libs = ["opencore-amrwb"]
