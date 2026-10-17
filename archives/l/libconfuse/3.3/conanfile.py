#!/usr/bin/env python3
"""Conan recipe — libconfuse 3.3 (martinh/libconfuse).

Small C library for parsing configuration files (autotools configure+make).

OHOS/HMDFS adaptations:
  - config.guess cannot identify HarmonyOS ("cannot guess build type") and
    the bundled 2018 config.sub does not know `*-linux-ohos`; pass the GNU
    triplet explicitly so configure never runs the config.guess probe
    (abiword-plugin / libfstrm precedent).
  - configure's config.status temp-dir creation uses mktemp, which HMDFS
    projects to an unwritable drwx--S--- dir (E114/E046); the bundled patch
    replaces mktemp with plain mkdir.
  - make runs with -j1 (E074: HMDFS jobserver fifo EPERM).
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, collect_libs, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibconfuseConan(ConanFile):
    name = "libconfuse"
    version = "3.3"
    description = "libconfuse 3.3 - small configuration file parser library (C)"
    license = "ISC"
    homepage = "https://github.com/libconfuse/libconfuse"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libconfuse is only supported on Linux/OHOS, not " +
                str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: system-name library — default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # config.guess cannot identify HarmonyOS; bundled 2018 config.sub has
        # no *-linux-ohos either — pass GNU triplet explicitly (verified
        # config.sub accepts aarch64-unknown-linux-gnu).
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # E074: parallel make hits HMDFS jobserver fifo EPERM
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # libtool builds libconfuse.so / libconfuse.a from confuse.c
        self.cpp_info.libs = collect_libs(self) or ["confuse"]
        self.cpp_info.set_property("cmake_file_name", "libconfuse")
        self.cpp_info.set_property("cmake_target_name", "libconfuse::libconfuse")