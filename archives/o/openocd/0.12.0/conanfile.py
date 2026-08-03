#!/usr/bin/env python3
"""Conan recipe — openocd 0.12.0 (Autotools).

OpenOCD — Open On-Chip Debugger.  CLI tool for JTAG/SWD debugging
and flash programming.
"""
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, replace_in_file
from conan.tools.gnu import AutotoolsToolchain, Autotools
from conan.tools.env import VirtualBuildEnv
from conan.tools.layout import basic_layout
import os

required_conan_version = ">=2.0"


class OpenocdConan(ConanFile):
    name = "openocd"
    version = "0.12.0"
    package_type = "application"

    description = "OpenOCD - Open On-Chip Debugger"
    homepage = "https://openocd.org/"
    license = "GPL-2.0-or-later"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"

    exports_sources = "patches/*"

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        # SourceForge 官方 release tarball 自带预生成 configure，
        # 且打包了 jimtcl/libjaylink 子模块源码，无需 autoreconf。
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        venv = VirtualBuildEnv(self)
        venv.generate()
        tc = AutotoolsToolchain(self)
        # 最小化 CLI 构建：关掉文档与 libjaylink 内部子模块
        # （libjaylink 仅用于部分调试器适配器，核心功能不需要）
        tc.configure_args.extend([
            "--disable-werror",
            "--disable-internal-libjaylink",
            "--disable-doxygen-html",
            "--disable-doxygen-pdf",
            "--disable-doxygen-man",
            "--disable-doxygen-rst",
        ])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # OHOS 沙箱下 configure/config.status 的 mktemp -d "./confXXXXXX"
        # 会因当前目录写权限受限而失败（同 flac/ncurses 的 mktemp 修复），
        # 改为使用 build 目录下的固定可写临时目录。config.status 由
        # configure 内部生成并立即执行，因此需在 configure 前修改 configure。
        configure_path = os.path.join(self.source_folder, "configure")
        tmp_dir = os.path.join(self.build_folder, "conf-tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        if os.path.isfile(configure_path):
            # strict=False：二次构建复用缓存源码时搜索模式已不存在，
            # 静默跳过而非抛异常（同 FMILibrary 配方处理）
            replace_in_file(
                self, configure_path,
                'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
                f'tmp={tmp_dir}/conf$$-$RANDOM',
                strict=False,
            )
            replace_in_file(
                self, configure_path,
                'tmp=./conf$$-$RANDOM',
                f'tmp={tmp_dir}/conf$$-$RANDOM',
                strict=False,
            )
        autotools = Autotools(self)
        # SourceForge release tarball 自带 configure，直接 configure + make
        autotools.configure()
        autotools.make()
        # CI 门禁要求运行上游官方测试（openocd 上游无独立测试套件，
        # make check 目标仅做头文件独立编译检查，可安全执行）
        autotools.make(target="check")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]

    # package_id intentionally omitted: settings (os, arch, compiler, build_type)
    # must contribute to the Conan package ID so that different platform builds
    # produce distinct binaries.
