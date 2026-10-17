#!/usr/bin/env python3
"""Conan recipe — swig 4.4.1

Simplified Wrapper and Interface Generator (SWIG) — connects C/C++
code to scripting languages (Python, Ruby, PHP, etc.).

Build system: Autotools (configure + make).
Product: command-line tool (swig + ccache-swig), not a library.
License: GPL-3.0
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain


class SwigConan(ConanFile):
    name = "swig"
    version = "4.4.1"
    description = "Simplified Wrapper and Interface Generator for connecting C/C++ to scripting languages"
    license = "GPL-3.0"
    homepage = "https://www.swig.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        # R32: OHOS platform compatibility
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("pcre2/10.45")

    def layout(self):
        self.folders.build = "."
        self.folders.generators = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)

        # Provide pcre2 paths to configure via standard autotools variable assignment.
        # SWIG's configure uses pcre2-config to find pcre2, but the conan pcre2 package's
        # pcre2-config has prefix=/ (built with --prefix=/), so we bypass it by setting
        # PCRE2_CFLAGS and PCRE2_LIBS directly.
        # R33: Paths come from Conan dependency, not undefined shell variables.
        pcre2 = self.dependencies["pcre2"]
        pcre2_include = os.path.join(pcre2.package_folder, "include")
        pcre2_lib = os.path.join(pcre2.package_folder, "lib")

        autotools.configure(args=[
            f"PCRE2_CONFIG=",
            f"PCRE2_CFLAGS=-I{pcre2_include} -DPCRE2_STATIC",
            f"PCRE2_LIBS=-L{pcre2_lib} -lpcre2-8 -lpcre2-posix",
        ])
        autotools.make(args=["-j2"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # swig is a command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        # SWIG embeds the install prefix in the binary to locate its .swg library files.
        # With conan's --prefix=/ + DESTDIR, the compiled-in path is wrong (/share/swig/...).
        # Set SWIG_LIB env var so consumers (and test_package) can find the library files.
        swig_lib = os.path.join(self.package_folder, "share", "swig", self.version)
        self.buildenv_info.define("SWIG_LIB", swig_lib)
        self.runenv_info.define("SWIG_LIB", swig_lib)
