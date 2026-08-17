#!/usr/bin/env python3
"""Conan recipe for premake 5.0.0-beta8 — build script generator (C + Lua).

HarmonyOS PC adaptation:
- Bootstrap.mak builds a self-contained premake (bundled Lua, no external deps).
- Bootstrap.sh dispatches by uname (HarmonyOS → "Unsupported platform"), so
  call `make -f Bootstrap.mak linux` directly.
- linux target links -luuid: OHOS has no libuuid, so drop it from LIBS
  (premake uses it only for hostname lookup fallback).
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, copy
from conan.tools.layout import basic_layout


class PremakeConan(ConanFile):
    name = "premake"
    version = "5.0.0-beta8"
    description = "Build script generator (Premake 5 beta8)"
    license = "BSD-3-Clause"
    homepage = "https://premake.github.io/"
    url = "https://github.com/premake/premake-core"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    exports_sources = "patches/*"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        if not os.path.isfile(os.path.join(self.source_folder, "Bootstrap.mak")):
            raise ConanException("premake Bootstrap.mak not found in source")
        # OHOS uname="HarmonyOS" → Bootstrap.sh would bail; build linux target
        # directly. -luuid is absent on OHOS; the 0001 patch removes it.
        self.run(
            'sh -c "make -f Bootstrap.mak linux CONFIG=release"',
            cwd=self.source_folder,
        )

    def package(self):
        bin_path = os.path.join(self.source_folder, "bin", "release", "premake5")
        if not os.path.isfile(bin_path):
            raise ConanException(f"premake5 binary not found: {bin_path}")
        copy(self, "premake5", src=os.path.dirname(bin_path),
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
