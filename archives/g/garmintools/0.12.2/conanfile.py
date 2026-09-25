#!/usr/bin/env python3
"""Conan recipe — garmintools 0.12.2（Garmin USB 协议库与命令行工具）

garmintools 提供 libgarmintools.so.6.2.0（C，Meson 构建）及
garmin_dump/garmin_get_info/garmin_gmap/garmin_gchart/garmin_gpx/
garmin_tcx/garmin_save_runs 7 个 CLI 工具，依赖 libusb-1.0。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import PkgConfigDeps
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout


class GarmintoolsConan(ConanFile):
    name = "garmintools"
    version = "0.12.2"
    description = "garmintools — Library and CLI tools implementing the Garmin USB protocol"
    license = "MIT"
    homepage = "https://github.com/phako/garmintools"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires("libusb/1.0.27")

    def build_requirements(self):
        self.tool_requires("meson/1.11.0")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = PkgConfigDeps(self)
        deps.generate()
        tc = MesonToolchain(self)
        tc.project_options["python-module"] = "false"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        native = os.path.join(self.generators_folder, "conan_meson_native.ini")
        self.run(
            "PATH=/data/service/hnp/bin:$PATH "
            "CC=/data/service/hnp/bin/clang "
            "AR=/data/service/hnp/bin/llvm-ar "
            f"meson setup {self.build_folder} {self.source_folder} "
            f"--native-file \"{native}\" "
            "--buildtype=release --prefix=/ -Dpython-module=false "
            "-Ddefault_library=static",
            cwd=self.build_folder,
            env="conanbuild",
        )
        self.run(
            f"PATH=/data/service/hnp/bin:$PATH meson compile -C {self.build_folder}",
            env="conanbuild",
        )

    def package(self):
        # meson install 写入 DESTDIR 前缀（staging 隔离）
        self.run(
            f"PATH=/data/service/hnp/bin:$PATH DESTDIR={self.package_folder} "
            f"meson install -C {self.build_folder}",
            env="conanbuild",
        )
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        # meson install_headers('garmin.h', subdir: 'garmintools') 安装到
        # include/garmintools/garmin.h，consumer 以 <garmintools/garmin.h> 引用，
        # 因此 includedirs 必须是 ["include"]（包根 include 目录）。
        # 注意：package_type=application 时 cpp_info 默认 includedirs 为空，
        # 必须显式声明，否则 CMakeDeps 生成空 INCLUDE_DIRS。
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libs = ["garmintools"]
