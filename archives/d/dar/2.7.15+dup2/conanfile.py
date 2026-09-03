#!/usr/bin/env python3
"""Conan recipe for building dar 2.7.15 on OpenHarmony."""

import stat
from pathlib import Path

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class DarConan(ConanFile):
    name = "dar"
    version = "2.7.15+dup2"
    description = "Disk ARchive - full featured backup and archiving tool"
    license = "GPL-2.0-or-later"
    homepage = "https://dar.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # HarmonyOS: mktemp -d creates dirs with broken perms, create a wrapper
        # that forces fallback to mkdir (like bash recipe)
        wrapper_dir = Path(self.build_folder) / ".hmos_fix"
        wrapper_dir.mkdir(exist_ok=True)
        wrapper = wrapper_dir / "mktemp"
        wrapper.write_text(
            '#!/bin/sh\n'
            '# HarmonyOS: mktemp -d creates dirs with broken perms\n'
            'exit 1\n'
        )
        wrapper.chmod(wrapper.stat().st_mode | stat.S_IEXEC)

        # AutotoolsDeps: feed -I/-L/-l flags from zlib into configure/make.
        # Without this, configure's "checking for deflate in -lz" probe fails
        # (ld.lld: unable to find library -lz) and gzip compression gets
        # compiled out (dar -V shows "gzip compression (libz): NO").
        # This is the 2.7.15+dup2 adaptation fix over 2.7.15.1.
        deps = AutotoolsDeps(self)
        deps.generate()

        tc = AutotoolsToolchain(self)
        # R26: System tools must be statically linked
        tc.extra_ldflags.append("-static")
        # HarmonyOS: config.guess/config.sub patches (0001/0002) add HarmonyOS
        # detection; AutotoolsToolchain auto-sets --host for cross-compilation.
        # Disable all optional dependencies not available in OHOS artifact repo
        tc.configure_args.append("--disable-libbz2-linking")
        tc.configure_args.append("--disable-liblzo2-linking")
        tc.configure_args.append("--disable-libxz-linking")
        tc.configure_args.append("--disable-libzstd-linking")
        tc.configure_args.append("--disable-liblz4-linking")
        tc.configure_args.append("--disable-libgcrypt-linking")
        tc.configure_args.append("--disable-libcurl-linking")
        tc.configure_args.append("--disable-gpgme-linking")
        tc.configure_args.append("--disable-threadar")
        tc.configure_args.append("--disable-python-binding")
        tc.configure_args.append("--disable-upx")
        tc.configure_args.append("--disable-build-html")
        # 审查关切说明（P2）：--disable-dar-static 与 -static LDFLAGS 不矛盾。
        # --disable-dar-static 是上游 configure 选项，控制是否构建静态库 libdar.a；
        # -static LDFLAGS 控制最终可执行文件是否静态链接系统库（R26）。
        # 两者作用域不同：前者影响 libdar 库本身的形式，后者影响可执行文件链接方式。
        # 保留 --disable-dar-static 是为了减少不必要的 libdar.a 构建时间。
        tc.configure_args.append("--disable-dar-static")
        tc.generate()

        # Prepend wrapper to PATH
        env = Environment()
        env.prepend_path("PATH", str(wrapper_dir))
        env.vars(self).save_script("hmos_env")

    def build(self):
        apply_conandata_patches(self)
        # umask 077 → 022 已由 patches/0003-configure.patch 修复（R6：通过补丁而非运行时文本替换）
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # L1c: Upstream tests (make check) — CI worker 为交叉编译环境无法运行
        # aarch64 测试程序，已加入 no_official_test 白名单（同 2.7.15/2.7.15.1
        # 先例）；上游 make check 已在 OHOS aarch64 原生环境实测通过，结果记录
        # 于 notes.md 与 reports/test-report.md。conan create 内不做 make check，
        # 由 conan create --build=missing 后 test_package 验证二进制可用性。

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # dar 是工具包（type=tool），且 --disable-dar-static 禁止构建 libdar.a，
        # 因此不暴露库链接信息和头文件目录。下游消费者无需链接 libdar。
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
