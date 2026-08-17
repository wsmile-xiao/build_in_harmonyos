#!/usr/bin/env python3
"""Conan recipe for numactl 2.0.18 (Autotools) — NUMA policy control library and utilities.

numactl provides libnuma (a library for NUMA policy control) and several
command-line utilities (numactl, numastat, numademo, migratepages, migspeed,
memhog) for managing NUMA policy on Linux/HarmonyOS systems.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class NumactlConan(ConanFile):
    name = "numactl"
    version = "2.0.18"
    description = "NUMA policy control library (libnuma) and utilities"
    license = "LGPL-2.1"
    homepage = "https://github.com/numactl/numactl"

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
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Fix umask 077 -> 022 for HMDFS filesystem compatibility
        replace_in_file(self, os.path.join(self.source_folder, "configure"),
                        "umask 077", "umask 022")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["numa"]
        self.cpp_info.bindirs = ["bin"]
