#!/usr/bin/env python3
"""Conan recipe — erfa 2.0.1 (Meson)"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class ErfaConan(ConanFile):
    name = "erfa"
    version = "2.0.1"
    description = "Essential Routines for Fundamental Astronomy"
    license = "BSD-3-Clause"
    homepage = "https://github.com/liberfa/erfa"
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

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # CI worker 会把 AR/AS/STRIP/NM/RANLIB 导出为 llvm-* 裸名（llvm-ar
        # 等），meson 的 archiver 探测用裸名在 PATH 里找不到 → configure 报
        # "Unknown linker(s): llvm-ar"。弹出这些变量并锁定真实工具（绝对路径）。
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
        tc.project_options["default_library"] = "static" if not self.options.shared else "shared"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = ["erfa"]
