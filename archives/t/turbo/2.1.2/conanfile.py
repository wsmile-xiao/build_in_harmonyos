#!/usr/bin/env python3
"""Conan recipe for turbo 2.1.2 — high-performance network framework for LuaJIT.

Turbo.lua is an event-driven, non-blocking I/O framework for LuaJIT.
Build system: plain Makefile (no configure script).
SSL support is disabled (SSL=none) because OpenSSL is not yet available
as a Conan package on the ohpcd remote. Turbo functions normally without
SSL — the TURBO_NO_SSL define disables SSL-dependent code paths.

License: Apache-2.0
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain


class TurboConan(ConanFile):
    name = "turbo"
    version = "2.1.2"
    description = "A high-performance network framework for LuaJIT"
    license = "Apache-2.0"
    homepage = "https://turbo.lua.org"
    url = ""  # CI fills this

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # Build in source directory — turbo's Makefile is in the source root
        self.folders.build = "."
        self.folders.generators = "."

    def validate(self):
        # R32: Platform check must use in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"OS {self.settings.os} not supported, requires Linux or OHOS"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # AutotoolsToolchain generates CC, CFLAGS, CPPFLAGS, LDFLAGS, etc.
        # R33: All flags come from Conan toolchain, no shell env vars in build()
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # R9: Use -j1, never -j$(nproc)
        # SSL=none disables OpenSSL dependency (not available as conan package)
        # R33: CC, CFLAGS, LDFLAGS come from Conan toolchain (conanbuildenv)
        self.run("make -j1 SSL=none")

    def package(self):
        # Install using make install to the package folder
        # The Makefile's install target copies lib, bin, and Lua modules
        self.run(f'make SSL=none PREFIX="{self.package_folder}" install')
        # Also copy the http-parser shared library if it exists in build dir
        http_parser_so = os.path.join(self.build_folder, "deps", "http-parser",
                                      "libhttp_parser.so.2.1")
        if os.path.exists(http_parser_so):
            copy(self, "libhttp_parser.so*", os.path.join(self.build_folder, "deps", "http-parser"),
                 os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["tffi_wrap"]
        # turbo installs Lua modules, not C headers
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
