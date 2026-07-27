#!/usr/bin/env python3
"""Conan recipe for c-ares 1.34.6 — Autotools projects (configure + make).

This template enforces R26: static linking for system-name libraries.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class CaresConan(ConanFile):
    name = "c-ares"
    version = "1.34.6"
    description = "C library for asynchronous DNS requests"
    license = "MIT"
    homepage = "https://c-ares.org/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["cares"]
        self.cpp_info.set_property("cmake_file_name", "c-ares")
        self.cpp_info.set_property("cmake_target_name", "c-ares::c-ares")
        self.cpp_info.set_property("pkg_config_name", "libcares")
