#!/usr/bin/env python3
"""Conan recipe for abduco 0.6 (upstream Makefile build)."""

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class AbducoConan(ConanFile):
    name = "abduco"
    version = "0.6"
    description = "Session management tool for detachable terminal programs."
    license = "ISC"
    homepage = "https://github.com/martanne/abduco"
    url = "https://github.com/martanne/abduco"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"][0], strip_root=True)

    def build(self):
        if self.settings.os not in ("Linux", "OHOS"):
            self.fail("abduco requires a POSIX host (Linux or OHOS)")
        apply_conandata_patches(self)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang") if compilers else "clang"
        strip = "true"  # OHOS MAC rejects llvm-strip on the produced binary
        # The upstream Makefile's default target performs a clean build.
        self.run(
            "make -j1 CC={} STRIP={} PREFIX=/usr MANPREFIX=/usr/share/man".format(
                cc, strip
            )
        )

    def package(self):
        # Empty PREFIX installs directly under the Conan package root.
        # Pass STRIP=true again: upstream `make install` strips the installed
        # binary by default, and on OpenHarmony the kernel MAC rejects stripped
        # binaries (Operation not permitted) — keep it unstripped (see build()).
        self.run(
            "make install PREFIX= MANPREFIX=share/man STRIP=true DESTDIR={}".format(
                self.package_folder
            )
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
