#!/usr/bin/env python3
"""Conan recipe for babl-tools 0.1.126 on HarmonyOS PC.

babl is GIMP's dynamic pixel format conversion engine. babl-tools
packages the command-line verification tools shipped in babl's tools/
subdirectory (babl-fish-test, babl-fish-landscape, ...). Built from
the same babl source tarball with meson, linking the babl library
(dep: babl/0.1.126 already on main, same version).
"""
import os
import sys
import shutil

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.meson import Meson, MesonToolchain


class BablToolsConan(ConanFile):
    name = "babl-tools"
    version = "0.1.126"
    package_type = "application"
    license = "LGPL-3.0"
    homepage = "https://gegl.org/babl/"
    url = "https://gegl.org/babl/"
    description = ("GIMP pixel format conversion engine — verification "
                   "tools (babl-fish-test etc.)")
    settings = "os", "arch", "compiler", "build_type"
    # 无 generators——MesonToolchain 在 build() 手动实例化（需先 pip 装 meson）

    def requirements(self):
        self.requires("babl/0.1.126")

    def layout(self):
        # 分离 source/build 目录（meson 要求 source != build——实测报
        # 'Source and build directories must not be the same'；
        # 参考 babl 本体配方的 folders 定义，conan 2.29 无 meson_layout）
        self.folders.source = "."
        self.folders.build = "build"
        self.folders.generators = "build"

    def source(self):
        get(self, **self.conan_data["sources"][self.version],
            strip_root=True)

    def generate(self):
        # Ensure AR points to a discoverable path for meson（babl 本体配方
        # 同款：OHOS 上 llvm-ar-15/llvm-ar/ar/gar 均不在 meson 默认搜索路径
        # ——实测 'Unknown linker(s): [['llvm-ar-15'], ['llvm-ar'], ['ar'],
        # ['gar']]'）
        ar_path = shutil.which("llvm-ar") or shutil.which("ar")
        if ar_path:
            os.environ["AR"] = ar_path
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "shared"
        tc.project_options["with-docs"] = "false"
        tc.project_options["enable-gir"] = "false"
        tc.project_options["enable-vapi"] = "false"
        tc.generate()

    def build(self):
        # 参考 babl 本体配方（main 已有）：meson 工具缺失时 pip 安装
        if not shutil.which("meson"):
            self.run(f"{sys.executable} -m pip install --user meson")
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        # tools/meson.build 的 11 个命令行工具（实测清单）——全部复制
        tools_dir = os.path.join(self.build_folder, "tools")
        for tool in (
            "babl_fish_path_fitness",
            "babl-lut-verify",
            "babl-benchmark",
            "babl-html-dump",
            "babl-icc-dump",
            "babl-icc-rewrite",
            "babl-verify",
            "conversions",
            "formats",
            "introspect",
            "trc-validator",
        ):
            copy(self, tool, src=tools_dir,
                 dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.conf_info.define("user.babl-tools:exe", os.path.join(
            self.package_folder, "bin", "babl-verify"))
