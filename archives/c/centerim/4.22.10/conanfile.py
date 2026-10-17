#!/usr/bin/env python3
"""Conan recipe — centerim 4.22.10 (Autotools, C/C++).

HarmonyOS PC adaptation of CenterIM, a text-mode multi-protocol instant
messenger (ICQ/Jabber/GG/MSN/Yahoo!/IRC/RSS/LJ). Autotools configure+make.

Dependencies (Conan): ncurses (TUI), curl (fetch), openssl (SSL), libiconv.
libgadu / intl (gettext) / libicq2000 / libjabber / libmsn / libyahoo2 are
BUNDLED inside the upstream tarball, so no separate conan deps are needed.

OHOS specifics:
- 2009-era config.guess/config.sub do not know aarch64 / linux-ohos;
  0001-config.sub-ohos.patch (E007) teaches config.sub to accept the
  aarch64-linux-ohos triplet, passed as --build/--host.
- configure defaults to gcc; CC/CXX are exported as clang/clang++.
- pre-C++11 codebase: force -std=gnu++11 (libc++ cannot build C++03).
- fribidi / libjpeg (optional extras) default off.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches, export_conandata_patches, get, copy,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class CenterimConan(ConanFile):
    name = "centerim"
    version = "4.22.10"
    description = "Text-mode multi-protocol instant messenger (CenterIM)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/petrpavlu/centerim5"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("ncurses/6.4")
        self.requires("curl/8.15.0")
        self.requires("libiconv/1.17")

    def validate(self):
        # R32: settings.os must be Linux/OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "centerim is only supported on Linux/OHOS, not "
                + str(self.settings.os))

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        if self.settings.os == "OHOS":
            if self.settings.arch != "armv8":
                raise ConanInvalidConfiguration(
                    "centerim currently supports only OHOS armv8")
            tc.configure_args.extend([
                "--build=aarch64-linux-ohos",
                "--host=aarch64-linux-ohos",
                "--with-ssl=no",
                "--with-fribidi=no",
                "--without-libjpeg",
                "--disable-yahoo",   # Yahoo hard-requires libcurl with SSL
                "--disable-msn",     # MSN hard-requires libcurl with SSL
                "--disable-jabber",  # libjabber/jconn.c old C errors on clang
            ])
            # pre-C++11 codebase; libc++ requires at least C++11
            tc.extra_cxxflags.append("-std=gnu++11")
            tc.extra_cxxflags.append("-fpermissive")  # old C++ -> warnings
            # bundled gettext generates intl/libintl.h in the BUILD dir (not
            # the source copy); expose it so `#include <libintl.h>` resolves
            # and `::gettext()` is declared.
            tc.extra_cflags.append("-I" + os.path.join(self.build_folder, "intl"))
            tc.extra_cxxflags.append("-I" + os.path.join(self.build_folder, "intl"))
        # wire conan deps' include/lib dirs into configure
        inc_dirs = []
        lib_dirs = []
        for dep in self.dependencies.values():
            pf = dep.package_folder
            if not pf:
                continue  # build/tool or skipped binary deps have no folder
            cpp = dep.cpp_info
            inc_dirs.extend(
                os.path.join(pf, p) for p in cpp.includedirs if p)
            lib_dirs.extend(
                os.path.join(pf, p) for p in cpp.libdirs if p)
        for d in sorted(set(inc_dirs)):
            tc.extra_cflags.append("-I" + d)
            tc.extra_cxxflags.append("-I" + d)
        for d in sorted(set(lib_dirs)):
            tc.extra_ldflags.append("-L" + d)
        tc.generate()

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        src = self.source_folder
        pkg = self.package_folder
        bin_dir = os.path.join(pkg, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        # centerim binary (upstream Makefile install needs /usr/bin/install
        # which the OHOS sysroot lacks — copy manually instead). The binary
        # is produced in the BUILD folder (out-of-tree autotools build).
        bin_src = os.path.join(self.build_folder, "src", "centerim")
        if os.path.isfile(bin_src):
            shutil.copy(bin_src, os.path.join(bin_dir, "centerim"))
            shutil.copymode(bin_src, os.path.join(bin_dir, "centerim"))
        # share data (icons, sounds, translations)
        share_src = os.path.join(src, "share")
        if os.path.isdir(share_src):
            copy(self, "*", share_src, os.path.join(pkg, "share"))
        copy(self, "LICENSE*", src, os.path.join(pkg, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin"))
