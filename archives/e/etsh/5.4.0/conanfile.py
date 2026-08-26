#!/usr/bin/env python3
"""Conan recipe — etsh 5.4.0

etsh is an enhanced, backward-compatible port of the V6 Thompson shell
(/bin/sh from 1975 Sixth Edition UNIX).  It produces CLI executables:
etsh, tsh, glob, fd2, goto, if.

Build system: hand-written ./configure + make (NOT autotools — there is
no config.sub/config.guess, no --enable-static/--disable-shared support).
The configure script runs ./mkconfig which probes `uname -s` to generate
config.h.  A patch makes mkconfig recognise HarmonyOS as Linux-compatible
(musl libc needs the same _XOPEN_SOURCE/_DEFAULT_SOURCE feature macros).

License: BSD-2-Clause / BSD-3-Clause / BSD-4-Clause / public_domain
Homepage: https://etsh.dev/
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class EtshConan(ConanFile):
    name = "etsh"
    version = "5.4.0"
    description = "Enhanced backward-compatible port of the V6 Thompson shell (1975 /bin/sh)"
    license = "BSD-2-Clause"  # etsh is multi-licensed: BSD-2/3/4-Clause + public_domain
    homepage = "https://etsh.dev/"
    url = ""  # CI fills this

    # etsh produces executables, not a library
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # R32: restrict to Linux/OHOS — etsh's mkconfig probes uname -s and the
    # patch only adds HarmonyOS recognition to the Linux-compatible branch.
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"etsh supports only Linux/OHOS, got os={self.settings.os}"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # etsh has no third-party dependencies
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # etsh's hand-written configure/make does not use autotools,
        # so we do not generate an AutotoolsToolchain.
        # The compiler is passed directly in build() via Conan conf (R33).
        pass

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf — NEVER use bare ${CC}.
        comp_execs = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = comp_execs.get("c") or "clang"

        # Run the hand-written configure in the source folder.
        # etsh's configure calls ./mkconfig which generates config.h.
        # Prefer CONFIG_SHELL (profile buildenv), else PATH search for bash/sh.
        config_shell = (
            os.environ.get("CONFIG_SHELL")
            or shutil.which("bash")
            or "sh"
        )
        self.run(f'"{config_shell}" ./configure', cwd=self.source_folder)

        # OHOS SDK's lld depends on libxml2.so.16, which the CI conan
        # subprocess can't find (Error loading libxml2.so.16 -> clang:
        # unable to execute command). Prepend SDK llvm/lib to
        # LD_LIBRARY_PATH so lld loads it (same fix as abuild/babeld).
        # Do NOT switch to -fuse-ld=GNU ld: its output is not executable
        # in the OHOS sandbox (exit 126, needs ELF signature).
        ld_library_path = ""
        if self.settings.os == "OHOS":
            ld_library_path = (
                "LD_LIBRARY_PATH="
                "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
                ":$LD_LIBRARY_PATH "
            )

        # Build with the OHOS cross-compiler (R9: -j1).
        self.run(f'{ld_library_path}make CC="{cc}" -j1', cwd=self.source_folder)

    def package(self):
        # Install into the package folder via DESTDIR staging.
        comp_execs = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = comp_execs.get("c") or "clang"
        # Portable install lookup: prefer env override, else PATH search.
        # OHOS ships install at /system/bin/install (toybox); Linux CI hosts
        # have it at /usr/bin/install — hardcoding either breaks the other.
        install = os.environ.get("INSTALL") or shutil.which("install") or "install"
        destdir = self.package_folder
        # OHOS lld needs libxml2.so.16 from SDK llvm/lib (see build()).
        ld_library_path = ""
        if self.settings.os == "OHOS":
            ld_library_path = (
                "LD_LIBRARY_PATH="
                "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
                ":$LD_LIBRARY_PATH "
            )
        self.run(
            f'{ld_library_path}make install CC="{cc}" INSTALL="{install}" '
            f'DESTDIR="{destdir}" PREFIX=/usr/local',
            cwd=self.source_folder,
        )

    def package_info(self):
        # Command-line tool — no libraries, headers, or libdirs.
        # Binaries install to usr/local/bin/ (PREFIX=/usr/local).
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["usr/local/bin"]
