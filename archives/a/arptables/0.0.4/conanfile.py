#!/usr/bin/env python3
"""Conan recipe for arptables 0.0.4 — Makefile-based ARP firewall tool.

arptables is a command-line tool for managing ARP packet filtering rules.
It uses a plain Makefile (not autotools/CMake) and produces an executable.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class ArptablesConan(ConanFile):
    name = "arptables"
    version = "0.0.4"
    description = "Userspace ARP packet filtering tool for Linux/HarmonyOS"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/KVM-COLO/arptables"
    url = ""  # CI fills this

    # R38: arptables is a command-line tool, not a library
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    # No options/shared — application type does not need shared option

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # arptables has no external dependencies (only libc)
        pass

    def validate(self):
        # R32: settings.os check must use in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"arptables only supports Linux and OHOS, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        # R39: Use Conan get(), no verify=False
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf, NEVER from shell env vars.
        cc_executables = self.conf.get("tools.build:compiler_executables", default={})
        if isinstance(cc_executables, dict):
            cc = cc_executables.get("c", "clang")
        else:
            cc = "clang"

        # Clear environment variables that could interfere with Makefile.
        for var in ("CC", "CXX", "CFLAGS", "CXXFLAGS", "LDFLAGS", "CPPFLAGS"):
            os.environ.pop(var, None)

        # arptables uses a plain Makefile with COPT_FLAGS for extra CFLAGS.
        # Pass env=None to skip Conan's conanbuild.sh wrapper which can cause
        # issues on OHOS (e.g., environment variable conflicts).
        self.run(f'make CC={cc} COPT_FLAGS="-fPIC -O2" -j1',
                 cwd=self.source_folder, env=None)

    def package(self):
        for var in ("CC", "CXX", "CFLAGS", "CXXFLAGS", "LDFLAGS", "CPPFLAGS"):
            os.environ.pop(var, None)

        dest = self.package_folder
        self.run(f'make install DESTDIR="{dest}" PREFIX="" -j1',
                 cwd=self.source_folder, env=None)

        # Ensure binary is also in bin/ for standard bindir lookup
        sbin = os.path.join(dest, "sbin")
        bin_dir = os.path.join(dest, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        copy(self, "arptables", sbin, bin_dir)

    def package_info(self):
        # Application type: no libs, but bindirs for executables
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["sbin", "bin"]
