#!/usr/bin/env python3
"""Conan recipe for zxcc — CP/M 2/3 emulator for cross-development (John Elliott).

zxcc builds five command-line tools (zxcc/zxc/zxas/zxlink/zxlibr) plus two
static helper libraries (libcpmio, libcpmredir). Runtime CP/M data (bios.bin
etc.) is installed under <prefix>/lib/cpm/ and the tools locate it relative
to their compiled-in prefix (BINDIR80), so the package is self-contained.

Adaptation notes (HarmonyOS PC, aarch64-linux-ohos):
- GNU autotools shipped config.guess/config.sub do not know HarmonyOS →
  patch adds HarmonyOS detection (E007 pattern, no platform macro injection).
- configure's `umask 077 && mktemp` breaks on HMDFS (owner bits lost) →
  patch drops the private umask.
- ncurses: cpmio needs ncurses headers/lib; uses conan ncurses dependency.
"""
import os
import stat

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class ZxccConan(ConanFile):
    name = "zxcc"
    version = "0.5.7"
    description = "CP/M 2/3 emulator for cross-development (wrapper for Hi-Tech C CP/M compiler and DResearch assembler/linker tools)"
    license = ("GPL-2.0-or-later", "LGPL-2.0-or-later")
    homepage = "https://www.seasip.info/Unix/Zxcc/"
    url = "https://www.seasip.info/Unix/Zxcc/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # cpmio console emulation needs ncurses headers and libncursesw
        self.requires("ncurses/6.5")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # cpmio/configure 硬编码探测 -lncurses/-lcurses，而包内仅有
        # libncursesw.a → 建立兼容符号链接目录供探测/链接使用
        nc_libdir = self.dependencies["ncurses"].cpp_info.libdirs[0]
        compat = os.path.join(self.build_folder, "compat-lib")
        os.makedirs(compat, exist_ok=True)
        dst = os.path.join(compat, "libncurses.a")
        if not os.path.exists(dst):
            os.symlink(os.path.join(nc_libdir, "libncursesw.a"), dst)
        nc = self.dependencies["ncurses"].cpp_info
        tc = AutotoolsToolchain(self)
        # ncurses 包 cpp_info.libs 为空，conan 不会自动注入其头/库路径，手动补充
        tc.extra_cflags = [f"-I{nc.includedirs[0]}"]
        tc.extra_ldflags = [f"-L{compat}", f"-L{nc.libdirs[0]}"]
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # E490: HMDFS/部分适配路径会丢失 autotools 脚本可执行位，恢复之
        script_names = {"configure", "config.guess", "config.sub", "install-sh",
                        "missing", "mkinstalldirs", "depcomp", "compile"}

        for root, _, files in os.walk(self.source_folder):
            for f in files:
                if f in script_names:
                    p = os.path.join(root, f)
                    st = os.stat(p)
                    os.chmod(p, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        autotools = Autotools(self)
        import shutil
        from conan.tools.env import Environment
        bash = shutil.which("bash")
        # OHOS 的 /bin/sh 是 mksh：configure 在 mksh 下探测出 korn-shell 能力，
        # 生成的 libtool 含 bash 无法解析的引号 → 全程用 bash 执行
        shell_env = Environment()
        if bash:
            shell_env.define("SHELL", bash)
        with shell_env.vars(self).apply():
            autotools.configure()
            if bash:
                for root, _, files in os.walk(self.build_folder):
                    if "libtool" in files:
                        lp = os.path.join(root, "libtool")
                        s = open(lp).read()
                        fixed = s.replace("#! /bin/sh\n", f"#!{bash}\n", 1).replace("#!/bin/sh\n", f"#!{bash}\n", 1)
                        # mksh 环境下生成的 archive_expsym_cmds 引号嵌套破损：
                        # 整块重建为单引号字面量（包含 $CC/$LD 两种变体）
                        marker = 'archive_expsym_cmds="echo "{ global:"'
                        pos = 0
                        parts = []
                        while True:
                            i = fixed.find(marker, pos)
                            if i < 0:
                                parts.append(fixed[pos:])
                                break
                            end = fixed.find(' -o $lib"\n', i)
                            end += len(' -o $lib"\n')
                            block = fixed[i:end]
                            nb = block.replace(
                                marker, 'archive_expsym_cmds=\'echo "{ global:" >', 1)
                            nb = nb[:nb.rfind(' -o $lib"\n')] + " -o $lib'\n"
                            parts.append(fixed[pos:i])
                            parts.append(nb)
                            pos = end
                        fixed = "".join(parts)
                        # ksh 内建 print 在 bash 下不存在；libtool 自身回退值
                        # 形式为 printf %s\n（可安全经受无引号变量展开）
                        fixed = fixed.replace("print -r --", "printf %s\\n")
                        if fixed != s:
                            open(lp, "w").write(fixed)
            autotools.make(args=("-j2", f"SHELL={bash}") if bash else ("-j2",))

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["cpmio", "cpmredir"]
