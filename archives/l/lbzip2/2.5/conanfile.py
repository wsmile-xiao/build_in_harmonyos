#!/usr/bin/env python3
"""Conan recipe — lbzip2 2.5

Parallel bzip2 compression utility (CLI tool).
Build system: autotools (configure + make).
License: GPL-3.0-or-later
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class Lbzip2Conan(ConanFile):
    name = "lbzip2"
    version = "2.5"
    description = "Parallel bzip2 compression utility (multithreaded drop-in bzip2 replacement)"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/kjn/lbzip2"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static (bzip2 is a system-name tool)
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
        # lbzip2 is a CLI tool (bin/lbzip2, bin/lbunzip2, bin/lbzcat); no library
        self.cpp_info.bindirs = ["bin"]
