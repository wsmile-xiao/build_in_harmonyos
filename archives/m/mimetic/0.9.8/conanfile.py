#!/usr/bin/env python3
"""Conan recipe for mimetic 0.9.8 — a free MIME (email) library written in C++.

HarmonyOS PC (aarch64) adaptation notes:
- the bundled config.guess/config.sub (2007) predate aarch64/OHOS: config.guess gains
  a HarmonyOS case reporting aarch64-unknown-linux-ohos (the device reports
  uname -s as HarmonyOS) and config.sub learns the aarch64 machine name and the
  linux-ohos OS triplets, so configure runs the native path without
  --build/--host overrides (E007, R13);
- configure is patched from `umask 077` to `umask 022` (HMDFS permission trap) and
  gains a CONFIG_SHELL capability probe: the CI profile exports the hnp bash as
  CONFIG_SHELL, and that launcher cannot getcwd on HMDFS build trees, so configure
  now falls back to /bin/sh before its own re-exec (E386);
- libconfig.h gains the `uint` typedef for the CONFIG_UNIX branch (OHOS libc does
  not provide it, unlike the historical glibc the upstream tree relied on);
- source fixes required by modern clang: the base64 decode table becomes
  `signed char` (on aarch64 `char` is unsigned, so the -1 sentinel could never
  match) and string literals in test/cutee.cxx get a separating space before the
  RUNTEST_NAME macro (C++11 user-defined-literal lexing).
- the upstream cutee suite runs inside `make` (test/all-local): 65 test functions
  and 2740 checks execute on the target during every conan create.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, rm
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class MimeticConan(ConanFile):
    name = "mimetic"
    version = "0.9.8"
    description = "mimetic - a free MIME (email) library written in C++"
    license = "MIT"
    homepage = "https://www.codesink.org/mimetic_mime_library.html"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("mimetic is supported only on Linux/OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("mimetic on OHOS requires armv8/aarch64")

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
        # test/all-local builds and runs the upstream cutee suite inside make.
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # libtool *.la wrappers are development leftovers, drop them.
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["mimetic"]
