#!/usr/bin/env python3
"""Conan test_package — libadwaita 1.2.0.

Verifies the packaged libadwaita recipe is consumable: builds a minimal
Adwaita program against the package, links against libadwaita-1, and runs
it to confirm the package provides a usable pkg-config / cpp_info.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class LibadwaitaTestPackage(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def generate(self):
        PkgConfigDeps(self).generate()
        # MesonToolchain doesn't write ar/ranlib from
        # tools.build:compiler_executables into the native file; meson then
        # probes bare llvm-ar which is NOT on PATH on OHOS (clang toolchain in
        # /data/service/hnp/bin) → configure aborts "Unknown linker(s)".
        # Pin the real tools by absolute path (same as the gtk4 recipe).
        for _var in ("AR", "AS", "STRIP", "NM", "RANLIB"):
            os.environ.pop(_var, None)
        tools = {name: shutil.which(name) for name in ("ar", "as", "strip", "nm", "ranlib")}
        missing = [name for name, path in tools.items() if path is None]
        if missing:
            raise ConanInvalidConfiguration(
                f"Required build tools not found in PATH: {', '.join(missing)}"
            )
        tc = MesonToolchain(self)
        tc.ar = tools["ar"]
        tc.as_ = tools["as"]
        tc.strip = tools["strip"]
        tc.binaries["nm"] = tools["nm"]
        tc.binaries["ranlib"] = tools["ranlib"]
        tc.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def test(self):
        # On OHOS (headless) the test binary links against shared gtk4/glib;
        # for cross-builds skip execution on the build host.
        from conan.tools.build import cross_building
        if cross_building(self):
            self.output.info("cross-building: skip test execution on build host")
        else:
            import os as _os
            if hasattr(_os, "uname") and _os.uname().sysname in ("OHOS", "HarmonyOS"):
                self.run("meson test -v -C \"%s\" --timeout-multiplier=16 --no-rebuild" % self.build_folder)
            else:
                Meson(self).test()
