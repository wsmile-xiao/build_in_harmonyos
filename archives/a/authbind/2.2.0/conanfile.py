#!/usr/bin/env python3
"""Conan recipe for authbind 2.2.0 — allow non-root programs to bind() low ports.

Pure Makefile build system (no configure).  Upstream Debian source tarball
authbind_2.2.0.tar.gz (root dir `work/`, strip_root=True).

Build outputs (see upstream Makefile):
  - bin/authbind                      (CLI wrapper)
  - lib/authbind/helper               (setuid helper, chmod u+s by install)
  - lib/authbind/libauthbind.so.1.0   (LD_PRELOAD interception library,
                                       soname libauthbind.so.1, link via
                                       $(LD) -shared -soname)
  - share/man/man1/authbind.1, share/man/man8/authbind-helper.8

No third-party dependencies: only system libc/libdl (Makefile LIBS=-ldl -lc;
libauthbind.c uses dlsym(RTLD_NEXT, ...)).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class AuthbindConan(ConanFile):
    name = "authbind"
    version = "2.2.0"
    description = "Allows non-root programs to bind() to low ports"
    license = "GPL-2.0-or-later"
    homepage = "https://tracker.debian.org/authbind"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"authbind supports Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)
        # authbind builds in-source (Makefile has no separate build dir)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _config_shell(self):
        return os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")

    def _compilers(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang") if compilers else "clang"
        ar = compilers.get("ar", "llvm-ar") if compilers else "llvm-ar"
        ranlib = (
            compilers.get("ranlib", "llvm-ranlib") if compilers else "llvm-ranlib"
        )
        # Makefile uses $(LD) -shared -soname ... for the .so; use clang as
        # linker driver so the OHOS sysroot/flags stay consistent (R33).
        ld = compilers.get("c", "clang") if compilers else "clang"
        return cc, ar, ranlib, ld

    def build(self):
        apply_conandata_patches(self)
        cc, ar, ranlib, ld = self._compilers()
        shell = self._config_shell()
        # R9: -j1 (never -j$(nproc))
        self.run(
            f"make CC={cc} AR={ar} RANLIB={ranlib} LD={ld} SHELL={shell} -j1",
            cwd=self.source_folder,
        )

    def package(self):
        pkg_bin = os.path.join(self.package_folder, "bin")
        pkg_lib = os.path.join(self.package_folder, "lib", "authbind")
        pkg_man1 = os.path.join(self.package_folder, "share", "man", "man1")
        pkg_man8 = os.path.join(self.package_folder, "share", "man", "man8")
        copy(self, "authbind", self.source_folder, pkg_bin)
        copy(self, "helper", self.source_folder, pkg_lib)
        copy(self, "libauthbind.so.1.0", self.source_folder, pkg_lib)
        copy(self, "authbind.1", self.source_folder, pkg_man1)
        copy(self, "authbind-helper.8", self.source_folder, pkg_man8)
        # Upstream install creates the soname symlink (ln -sf LIBTARGET LIBCANON)
        link = os.path.join(pkg_lib, "libauthbind.so.1")
        if not os.path.lexists(link):
            os.symlink("libauthbind.so.1.0", link)
        helper = os.path.join(pkg_lib, "helper")
        if os.path.exists(helper):
            # Upstream install runs chmod u+s on helper (setuid helper)
            st = os.stat(helper)
            os.chmod(helper, st.st_mode | 0o4000)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = [os.path.join("lib", "authbind")]
