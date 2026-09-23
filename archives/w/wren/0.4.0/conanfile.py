#!/usr/bin/env python3
"""Conan recipe — wren 0.4.0

Wren is a small, fast, class-based concurrent scripting language (C library).

Build system: premake-generated GNU Makefiles under projects/make/
  make -C projects/make config=release_64bit   # builds lib/libwren.a + lib/libwren.so + bin/wren_test
  (no `make install` target; package() copies libs and headers manually)
License: MIT
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import GnuToolchain
from conan.tools.layout import basic_layout


class WrenConan(ConanFile):
    name = "wren"
    version = "0.4.0"
    description = "Wren is a small, fast, class-based concurrent scripting language"
    license = "MIT"
    homepage = "https://wren.io/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = GnuToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # R33: get compiler/flags from Conan conf, never bare shell env vars
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"
        cflags = self.conf.get("tools.build:cflags", default=[], check_type=list)
        self.run(
            f'make -C projects/make config=release_64bit -j1 CC="{cc}" CFLAGS="{" ".join(cflags)}"',
            cwd=self.source_folder,
        )

    def package(self):
        # No upstream `make install`; copy libs + public headers manually.
        src = self.source_folder
        copy(self, "libwren.a", src=os.path.join(src, "lib"),
             dst=os.path.join(self.package_folder, "lib"))
        if self.options.shared:
            copy(self, "libwren.so", src=os.path.join(src, "lib"),
                 dst=os.path.join(self.package_folder, "lib"))
        copy(self, "wren.h", src=os.path.join(src, "src", "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "wren.hpp", src=os.path.join(src, "src", "include"),
             dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = ["wren"]
        # wren links against libm (system library, not a Conan component)
        self.cpp_info.system_libs = ["m"]
