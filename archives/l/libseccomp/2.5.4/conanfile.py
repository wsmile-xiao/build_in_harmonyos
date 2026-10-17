#!/usr/bin/env python3
"""Conan recipe — libseccomp 2.5.4 (autotools, OHOS/arm64).

libseccomp is an enhanced seccomp library (LGPL-2.1), standalone C library,
no external dependencies beyond libc + linux kernel headers.

OHOS adaptation:
- config.guess/config.sub: add aarch64-unknown-linux-ohos triplet (E007)
- configure/config.status: bypass HMDFS mktemp-d tempdir restriction (E112)
- tests/tools scripts shebang: /bin/bash missing on OHOS, use bundled bash (E087)
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibseccompConan(ConanFile):
    name = "libseccomp"
    version = "2.5.4"
    description = "The enhanced seccomp (syscall filtering) library"
    license = "LGPL-2.1"
    homepage = "https://github.com/seccomp/libseccomp"
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
        self.cpp_info.libs = ["seccomp"]
        self.cpp_info.set_property("pkg_config_name", "libseccomp")
