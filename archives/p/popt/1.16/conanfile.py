#!/usr/bin/env python3
"""
Conan recipe for popt v1.16 — OHOS (OpenHarmony) aarch64 adaptation.

Build system: autotools (configure + make).
Portability patches: config.guess/config.sub replacement for OHOS detection (E007),
HMDFS umask/mktemp fix (E097).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class PoptConan(ConanFile):
    name = "popt"
    version = "1.16"
    description = "C library for parsing command line parameters"
    license = "MIT"
    homepage = "https://github.com/rpm-software-management/popt"
    url = "https://github.com/rpm-software-management/popt"

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
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["popt"]
