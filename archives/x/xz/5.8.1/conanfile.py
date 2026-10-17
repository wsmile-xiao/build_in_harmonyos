#!/usr/bin/env python3
"""Conan recipe for xz 5.8.1 — Autotools build system (configure + make).

XZ Utils provide liblzma (LZMA2 compression library) and xz/xzdec command-line tools.
Build: ./configure && make && make check && make install
No external dependencies. Not a system same-name library (no /lib/liblzma.so),
so default (shared) linking is acceptable.

Adapted for HarmonyOS PC (OHOS aarch64 + musl libc). Platform task #7343,
branch feat/xz-5.8.1.
"""
import os
import stat
from pathlib import Path

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class XzConan(ConanFile):
    name = "xz"
    version = "5.8.1"
    description = "XZ Utils — general-purpose data compression with high ratio (LZMA2)"
    license = "0BSD"
    homepage = "https://tukaani.org/xz/"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # HarmonyOS: mktemp -d creates dirs with drwx--S--- (broken group perms),
        # causing config.status to fail. Create a mktemp wrapper that fixes perms.
        wrapper_dir = Path(self.build_folder) / ".hmos_fix"
        wrapper_dir.mkdir(exist_ok=True, parents=True)
        wrapper = wrapper_dir / "mktemp"
        wrapper.write_text(
            '#!/bin/sh\n'
            '# HarmonyOS: mktemp -d creates dirs with broken perms (hmmac MAC).\n'
            '# Return failure to force autoconf AS_TMPDIR to use mkdir fallback.\n'
            'exit 1\n'
        )
        wrapper.chmod(wrapper.stat().st_mode | stat.S_IEXEC)

        tc = AutotoolsToolchain(self)
        # OHOS: scripts (xzdiff, xzgrep, etc.) use /bin/sh which doesn't exist.
        # Disable scripts to skip test_scripts.sh and avoid installing broken scripts.
        tc.configure_args.append("--disable-scripts")
        # Link binaries (xz, lzmadec, lzmainfo) statically against liblzma.a
        # so they don't need LD_LIBRARY_PATH at runtime (L2 smoke test).
        # liblzma.so is still built for consumers who need shared linking.
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # 交叉编译（本机 x86-64 → OHOS aarch64）时把程序静态链接。
        # 原因：OHOS SDK 不随附设备端动态加载器 ld-musl-aarch64.so.1，
        # 动态产物在本机 QEMU/binfmt 下无法执行 —— 上游 tests/ 的 18 个测试
        # 二进制会全部报 "Could not open '/lib/ld-musl-aarch64.so.1'"，
        # make check 整体失败。静态链接后上游测试套件可在本地真实跑完。
        # ★ 必须用 "-all-static" 而不是 "-static"：上游 tests/ 与 CLI 都由
        #   libtool 驱动链接，libtool 会把裸 "-static" 当作自己的参数消费掉、
        #   不转发给编译器（实测：程序仍是动态，readelf 可见
        #   INTERP = /lib/ld-musl-aarch64.so.1）。
        # 设备端原生构建（官方 CI aarch64 worker）cross_building 为 False，
        # 不加此标志，配置与已发布的 xz/5.8.3 保持一致。
        if cross_building(self):
            tc.extra_ldflags.append("-all-static")
        tc.generate()

        # OHOS: No /bin/sh — propagate CONFIG_SHELL and mktemp wrapper
        env = Environment()
        config_shell = os.environ.get("CONFIG_SHELL")
        if config_shell:
            env.define("CONFIG_SHELL", config_shell)
        env.prepend_path("PATH", str(wrapper_dir))
        # Set LD_LIBRARY_PATH for make check (test programs need liblzma.so
        # from build tree, but rpath points to install prefix /lib)
        lib_build_dir = os.path.join(self.build_folder, "src", "liblzma", ".libs")
        env.prepend_path("LD_LIBRARY_PATH", lib_build_dir)
        env.vars(self).save_script("ohos_env")

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # L1: Run upstream official test suite (make check)
        autotools.make(target="check")

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["lzma"]
        # 本包同时安装命令行工具到 bin/（xz / xzdec / lzmadec / lzmainfo）。
        # 显式声明 bindirs，让配方自描述为「库 + 工具」包：按 R38，产物含可执行文件
        # 的软件必须在软件级目录提供 commands.json（archives/x/xz/commands.json
        # 已存在，本版本已补齐对应条目）。
        self.cpp_info.bindirs = ["bin"]
