#!/usr/bin/env python3
"""Conan recipe for dev86 (Linux-8086 Development Environment).

dev86 is a C compiler / assembler / linker toolchain for 8086-family targets
(used by the ELKS project). We build and package the HOST toolchain
(bcc, ncc, as86, ar86, ld86, objdump86) on HarmonyOS PC (aarch64). The
8086 target libraries (libc etc.) are not built: they require ncc to be
invoked with host clang CFLAGS, which ncc rejects.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches, chdir
from conan.tools.gnu import GnuToolchain
from conan.tools.layout import basic_layout


class Dev86Conan(ConanFile):
    name = "dev86"
    version = "0.16.21"
    description = "Linux-8086 Development Environment - 8086 C compiler, assembler and linker toolchain"
    license = "GPL-2.0-only"
    homepage = "https://github.com/jbruchon/dev86"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # Old (K&R style) C code that clang rejects under its default diagnostics
    _cflags = (
        "-O2 -Wno-return-type -Wno-implicit-function-declaration "
        "-Wno-implicit-int -Wno-int-conversion -Wno-deprecated-non-prototype "
        "-Wno-unused-parameter -Wno-parentheses -Wno-missing-prototypes"
    )

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    # R32: settings.os must be Linux or OHOS
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def source(self):
        # Mirror archive: top dir is build_in_harmonyos-dev86-src-raw/; strip_root
        # leaves the branch root, which contains a single src/ subdir.
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R33: CC/CFLAGS injected from the Conan profile via GnuToolchain
        tc = GnuToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        src = os.path.join(self.source_folder, "src")
        if not os.path.isdir(src):
            src = self.source_folder  # fallback: non-mirror source layout
        with chdir(self, src):
            # Two-phase GNU make: generate make.fil first, then build only the
            # host toolchain targets (bcc86/cpp/unproto/copt/as86/ar86/ld86/
            # objdump86). CFLAGS must be passed on the command line so the
            # make.fil generation substitutes it into all sub-makes.
            self.run(
                'make -f Makefile IFDEFFLAGS=-DGNUMAKE IFDEFNAME=ifdefg '
                'CC="${{CC}}" CFLAGS="{cf}" make.fil'.format(cf=self._cflags),
                env="conanbuild",
            )
            self.run(
                'make -f make.fil bcc86 cpp unproto copt as86 ar86 ld86 objdump86 '
                'VERSION={v} TOPDIR="." CC="${{CC}}" CFLAGS="{cf}"'.format(
                    v=self.version, cf=self._cflags
                ),
                env="conanbuild",
            )

    def package(self):
        src = os.path.join(self.source_folder, "src")
        if not os.path.isdir(src):
            src = self.source_folder

        bin_src = os.path.join(src, "bin")
        lib_src = os.path.join(src, "lib")
        libc_src = os.path.join(src, "libc")
        pkg_bin = os.path.join(self.package_folder, "bin")
        pkg_lib_bcc = os.path.join(self.package_folder, "lib", "bcc")

        # Host tools. The tarball ships the bcc driver as bin/Bcc; install name
        # is bcc. nm86/size86 are objdump86 aliases.
        for tool in ("ncc", "as86", "ar86", "ld86", "objdump86"):
            copy(self, tool, bin_src, pkg_bin, keep_path=False)
        copy(self, "Bcc", bin_src, pkg_bin, keep_path=False)
        os.replace(os.path.join(pkg_bin, "Bcc"), os.path.join(pkg_bin, "bcc"))
        # nm86/size86 are copies of the packaged objdump86 (HMDFS forbids
        # renaming over an existing file, so do not reuse the objdump86 copy)
        for alias in ("nm86", "size86"):
            shutil.copyfile(
                os.path.join(pkg_bin, "objdump86"),
                os.path.join(pkg_bin, alias),
            )

        # Components that bcc locates under $BCC_PREFIX/lib/bcc (see bcc.c)
        for comp in ("bcc-cpp", "bcc-cc1", "unproto", "copt"):
            copy(self, comp, lib_src, pkg_lib_bcc, keep_path=False)
        copy(self, "rules.*", lib_src, pkg_lib_bcc, keep_path=False)
        copy(self, "rules.*", os.path.join(lib_src, "i386"),
             os.path.join(pkg_lib_bcc, "i386"), keep_path=False)
        # C headers so bcc can find them via $BCC_PREFIX/lib/bcc/include
        copy(self, "*", os.path.join(libc_src, "include"),
             os.path.join(pkg_lib_bcc, "include"))

        copy(self, "COPYING", src, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
