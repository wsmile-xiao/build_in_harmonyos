#!/usr/bin/env python3
"""Conan recipe for libXau (libxau) 1.0.12.

X.Org libXau — parses the ~/.Xauthority file for X authentication records.
Pure autotools library; the official tarball ships pre-generated
configure + Makefile.in so no autoreconf/automake is needed at build time.

OHOS adaptation (patches declared in conandata.yml):
  - config.guess:  __OHOS__ LIBC detection + *:HarmonyOS:* identification (E205)
  - config.sub:    ohos-linux triplet + ohos* OS list + linux-ohos* kernel
                   validation (E205)
  - configure:     umask 077 -> 022 for HMDFS temp-dir exec (E002)
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibxauConan(ConanFile):
    name = "libxau"
    version = "1.0.12"
    description = "X.Org Xauthority library — X authentication record parsing"
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/xorg/lib/libxau"
    url = "https://gitlab.freedesktop.org/xorg/lib/libxau"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
    }

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libXau supports Linux and OHOS, not {self.settings.os}"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # X11/Xauth.h transitively pulls in <X11/Xfuncproto.h> from xorgproto.
        self.requires("xorgproto/2025.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # No autoreconf — official tarball ships pre-generated configure.
        tc = AutotoolsToolchain(self)
        # config.guess/sub patched (E205) — do NOT pass --build/--host.
        # Disable DocBook/man-page toolchain pulls (not present on OHOS).
        tc.configure_args.append("--disable-docs")
        tc.configure_args.append("--without-xmlto")
        tc.configure_args.append("--without-fop")
        tc.configure_args.append("--without-xsltproc")
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--disable-shared")
            tc.configure_args.append("--enable-static")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # ── 上游官方测试 ──
        # libXau ships one Automake check_PROGRAM: Autest (upstream
        # Makefile.am: `check_PROGRAMS=Autest` / `TESTS=Autest`). Autest
        # exercises XauWriteAuth() round-trip on a tmpfile.
        autotools.make(target="check")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        self._patch_libtool_libdir()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def _patch_libtool_libdir(self):
        import re

        lib_dir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(lib_dir):
            return
        for entry in os.listdir(lib_dir):
            if not entry.endswith(".la"):
                continue
            la_path = os.path.join(lib_dir, entry)
            with open(la_path, "r", encoding="utf-8") as handle:
                content = handle.read()
            new_content = re.sub(
                r"^libdir='.*'$",
                f"libdir='{lib_dir}'",
                content,
                flags=re.MULTILINE,
            )
            if new_content != content:
                with open(la_path, "w", encoding="utf-8") as handle:
                    handle.write(new_content)

    def package_info(self):
        self.cpp_info.libs = ["Xau"]
        # Propagate xorgproto headers transitively so consumers that link
        # libxau::libxau automatically get <X11/Xfuncproto.h>.
        self.cpp_info.requires = ["xorgproto::xorgproto"]
        self.cpp_info.set_property("cmake_file_name", "libxau")
        self.cpp_info.set_property("cmake_target_name", "libxau::libxau")
        self.cpp_info.set_property("cmake_target_aliases", ["libxau::Xau"])
        self.cpp_info.set_property("pkg_config_name", "xau")
