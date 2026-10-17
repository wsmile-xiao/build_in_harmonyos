#!/usr/bin/env python3
"""Conan recipe for NetBSD bozohttpd 20260503."""

import os
import shutil

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class BozohttpdConan(ConanFile):
    name = "bozohttpd"
    version = "20260503"
    description = "Small and secure HTTP/1.1 server from NetBSD"
    license = "BSD-2-Clause"
    homepage = "https://github.com/NetBSD/src/tree/trunk/libexec/httpd"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"with_ssl": [True, False]}
    default_options = {"with_ssl": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        if self.options.with_ssl:
            self.requires("openssl/3.0.21", options={"shared": False})

    def layout(self):
        basic_layout(self)
        # The portable Makefile.boot builds in the source tree.
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        # Select the profile's native or OHOS cross compiler and flags for
        # this handwritten Makefile, which otherwise defaults to host cc.
        AutotoolsToolchain(self).generate()

    def build(self):
        cppflags = [
            "$CPPFLAGS",
            "-D_LARGEFILE_SOURCE",
            "-D_FILE_OFFSET_BITS=64",
            "-D_GNU_SOURCE",
            "-D_DEFAULT_SOURCE",
            "-DNO_LUA_SUPPORT",
            "-DNO_BLOCKLIST_SUPPORT",
        ]
        cryptolibs = ""
        extralibs = ""
        if self.options.with_ssl:
            openssl = self.dependencies["openssl"].cpp_info
            cppflags.extend(f"-I{path}" for path in openssl.includedirs)
            linker_flags = [f"-L{path}" for path in openssl.libdirs]
            linker_flags.extend(f"-l{name}" for name in openssl.libs)
            linker_flags.extend(f"-l{name}" for name in openssl.system_libs)
            # Makefile.boot's built-in list names host libraries; pass the
            # Conan dependency paths and library order explicitly instead.
            extralibs = " ".join(linker_flags)
        else:
            cppflags.append("-DNO_SSL_SUPPORT")

        self.run(
            'make -f Makefile.boot -j1 '
            'CC="$CC" '
            f'CPPFLAGS="{" ".join(cppflags)}" '
            'CFLAGS="$CFLAGS" LDFLAGS="$LDFLAGS" '
            f'CRYPTOLIBS="{cryptolibs}" EXTRALIBS="{extralibs}"',
            cwd=self.source_folder,
            env="conanbuild",
        )

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        copy(self, "bozohttpd", src=self.source_folder, dst=bindir, keep_path=False)
        shutil.copy2(os.path.join(bindir, "bozohttpd"), os.path.join(bindir, "httpd"))

        mandir = os.path.join(self.package_folder, "share", "man", "man8")
        os.makedirs(mandir, exist_ok=True)
        copy(self, "bozohttpd.8", src=self.source_folder, dst=mandir, keep_path=False)
        shutil.copy2(os.path.join(mandir, "bozohttpd.8"), os.path.join(mandir, "httpd.8"))
        copy(self, "COPYING*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
