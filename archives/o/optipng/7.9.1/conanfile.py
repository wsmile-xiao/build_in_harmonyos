#!/usr/bin/env python3
"""Conan recipe for optipng 7.9.1 — PNG image optimizer CLI tool.

optipng is a command-line tool that optimizes PNG files to reduce file size
without losing quality. It uses bundled static copies of zlib and libpng
(third_party/ directory), so no external dependencies are required.

OHOS adaptations:
  - LIBM="" : HarmonyOS libc already includes libm symbols, -lm causes link error
  - unset LD: Let configure use $(CC) as linker instead of ld.lld directly
  - in-tree build: optipng's custom configure does not support out-of-tree builds
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class OptipngConan(ConanFile):
    name = "optipng"
    version = "7.9.1"
    description = "PNG image optimizer that reduces file size without losing quality"
    license = "Zlib"
    homepage = "https://optipng.sourceforge.net/"
    url = ""  # CI fills this

    # CLI tool, not a library (R38: commands.json declared at software level)
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"optipng is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        # OHOS: libm is part of libc; setting LIBM="" prevents -lm link error.
        # Also unset LD so configure uses $(CC) as the linker.
        env = Environment()
        env.define("LIBM", "")
        env.unset("LD")
        env.vars(self, scope="build").save_script("ohos_optipng_env")

    def build(self):
        # optipng's configure is custom (not standard autotools) and does not
        # support out-of-tree builds or --sbindir/--libdir/--includedir options.
        # Run configure and make directly from the source directory.
        self.run(f"./configure --prefix={self.package_folder}")

        # R9: single job — parallel make may hit HMDFS jobserver fifo EPERM
        self.run("make -j1")

    def package(self):
        self.run("make install")

    def package_info(self):
        # Standalone binary, no library info
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
