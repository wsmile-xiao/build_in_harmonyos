#!/usr/bin/env python3
"""Conan recipe — genext2fs 1.5.0（ext2 文件系统镜像生成工具）

genext2fs 生成 ext2 文件系统镜像（无需 root），纯 C，autotools 构建。
libarchive 为可选依赖（--enable-libarchive 默认关闭），默认零第三方依赖。

Debian orig tarball 不含预生成 configure（autoreconf 产物不进版本库），
构建时须 autoreconf 自举；CI Worker 缺 automake/aclocal（E178），
通过 tool_requires 用 build profile 解析（同 afuse/duo-unix 做法）。
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class Genext2fsConan(ConanFile):
    name = "genext2fs"
    version = "1.5.0"
    description = "genext2fs — ext2 filesystem image generator（ext2 镜像生成工具）"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/bestouff/genext2fs"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def build_requirements(self):
        # 无 configure → autoreconf 自举；只用 automake+libtool（避免拉入
        # conan perl 包导致 XS 模块与系统 perl 冲突）
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # libarchive 可选，默认不启用（零硬依赖，R36 满足）
        tc.configure_args.append("--disable-libarchive")
        # pkg.m4 等在 hnp 的 aclocal 目录下，autoreconf 需找到
        env = tc.environment()
        for _d in sorted(glob.glob("/data/service/hnp/*/*/share/aclocal")):
            env.append_path("ACLOCAL_PATH", _d)
        if self.settings.os == "OHOS":
            if self.settings.arch != "armv8":
                raise ConanInvalidConfiguration(
                    "genext2fs/1.5.0 currently supports only OHOS armv8"
                )
            # config.sub 需识别 aarch64-linux-ohos triplet（同 aalib/lzop/cdecl）
            tc.configure_args.extend([
                "--build=aarch64-linux-ohos",
                "--host=aarch64-linux-ohos",
            ])
        tc.generate(env=env)

    def build(self):
        os.umask(0)
        apply_conandata_patches(self)
        # Debian orig tarball 无预生成 configure → autoreconf 自举
        self.run("autoreconf --install --verbose", cwd=self.source_folder)
        # OHOS/HMDFS: config.status 临时目录 umask 077 不可写（E114）→ 000
        self.run("sed -i 's/umask 077/umask 000/g' configure", cwd=self.source_folder)
        autotools = Autotools(self)
        autotools.configure()
        # -j1: OHOS 沙箱不支持 mkfifo（jobserver），并行编译失败
        autotools.make(args=["-j1"])

    def package(self):
        Autotools(self).install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
