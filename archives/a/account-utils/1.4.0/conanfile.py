#!/usr/bin/env python3
"""Conan recipe — account-utils 1.4.0（账户/用户管理命令行工具）

account-utils 提供 chage/chfn/chsh/newuidmap/newgidmap 等命令
（C，Meson 构建，meson.build），依赖仅标准库/PAM（可选）。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout


class AccountUtilsConan(ConanFile):
    name = "account-utils"
    version = "1.4.0"
    description = "account-utils — account/user management utilities (chage/chfn/chsh 等)"
    license = "GPL-2.0-or-later"
    homepage = "https://accountsservice.org/" if False else "https://github.com/OpenSourceKakaxi/account-utils"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # stubs/ 随 recipe 导出，source() 后复制到源码目录（补丁后 meson 引用）
    exports_sources = "stubs/*"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        pass

    def build_requirements(self):
        self.tool_requires("meson/1.11.0")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.generate()

    def build(self):
        # 应用 0001-ohos-stub-deps.patch（stub systemd/PAM 依赖）
        apply_conandata_patches(self)
        # meson 检测 compiler/archiver 需 PATH 含 clang/llvm-ar
        # （/data/service/hnp/bin）；Meson 工具类不加载自定义 env →
        # 手动执行 meson（PATH + CC/AR 环境变量）
        self.run(
            "PATH=/data/service/hnp/bin:$PATH "
            "CC=/data/service/hnp/bin/clang "
            "AR=/data/service/hnp/bin/llvm-ar "
            f"meson setup {self.build_folder} {self.source_folder} "
            "--buildtype=release -Dman=disabled",
            cwd=self.build_folder,
            env="conanbuild",
        )
        self.run(
            f"PATH=/data/service/hnp/bin:$PATH meson compile -C {self.build_folder}",
            env="conanbuild",
        )

    def package(self):
        # 手动复制可执行程序（绕开 meson install 的 HMDFS 符号链接坑）
        bin_dst = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dst, exist_ok=True)
        build_dir = self.build_folder
        for name in ("chage", "chfn", "chsh", "newuidmap", "newgidmap",
                     "pwupdd", "pwaccessd", "newidmapd"):
            copy(self, name, src=build_dir, dst=bin_dst, keep_path=False) if os.path.exists(
                os.path.join(build_dir, name)
            ) else None
        copy(self, "LICENSE.GPL2", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        bin_path = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bin_path):
            self.runenv_info.append_path("PATH", bin_path)
            self.buildenv_info.append_path("PATH", bin_path)
