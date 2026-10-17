#!/usr/bin/env python3
"""Conan recipe for qqwing 1.3.4 — Sudoku generator/solver library and CLI tool."""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout

# OHOS 链接器（GNU ld 2.45，E266：绕过 lld 的 libxml2 依赖问题）
_OHOS_LD = "/data/service/hnp/bin/ld"


class QqwingConan(ConanFile):
    name = "qqwing"
    version = "1.3.4"
    description = "Sudoku puzzle generator and solver library with a command-line tool"
    license = "GPL-2.0-or-later"
    homepage = "https://qqwing.com/"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def _toolchain_prefix(self):
        # libtool 在 PATH 里搜不到 OHOS 的 ld/ar/ranlib，显式 export（E266/E012）。
        # 在命令内 export 而非 Environment.save_script，避免与 AutotoolsToolchain
        # 的聚合 env 文件产生递归 source（导致 printenv Argument list too long）。
        if self.settings.os == "OHOS":
            return (
                f'export LD={_OHOS_LD}; '
                f'export AR=/data/service/hnp/bin/ar; '
                f'export RANLIB=/data/service/hnp/bin/ranlib; '
            )
        return ""

    def _patch_configure_mktemp(self):
        # OHOS HMDFS 下 mktemp -d 创建的临时目录被剥夺 group 权限（2700），导致
        # config.status 写 subs1.awk 时 Permission denied（E112/E011）。
        # 把 umask 077 改为 022，让 mkdir 得到可写的 2710。必须在 configure 之前修补。
        targets = [
            os.path.join(self.source_folder, "configure"),
            os.path.join(self.source_folder, "config.guess"),
            os.path.join(self.source_folder, "config.sub"),
        ]
        for tgt in targets:
            if not os.path.isfile(tgt):
                continue
            with open(tgt, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            if "(umask 077 && " in content:
                content = content.replace("(umask 077 && ", "(umask 022 && ")
                with open(tgt, "w", encoding="utf-8") as f:
                    f.write(content)
                self.output.info(f"Patched {os.path.basename(tgt)}: umask 077 -> 022")

    def build(self):
        apply_conandata_patches(self)
        self._patch_configure_mktemp()
        # HMDFS 上源码解压后的 configure 无执行权限（owner 非当前用户，chmod 不生效，E087），
        # 需用 CONFIG_SHELL 显式执行 configure，而不是直接执行脚本路径。
        config_shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        prefix = self.package_folder
        args = ["--disable-shared", "--enable-static"]
        if self.settings.os == "OHOS":
            # 上游 config.sub (2014) 不识别 linux-ohos，配合 0001-config.sub-ohos.patch
            args += ["--build=aarch64-linux-ohos", "--host=aarch64-linux-ohos"]
        configure = os.path.join(self.source_folder, "configure")
        ld = self._toolchain_prefix()
        self.run(
            f'{ld}{config_shell} {configure} ' + " ".join(args) +
            f' --prefix="{prefix}" --bindir="{prefix}/bin" --sbindir="{prefix}/bin" ' +
            f'--libdir="{prefix}/lib" --includedir="{prefix}/include" ' +
            f'--oldincludedir="{prefix}/include"',
            env="conanbuild",
            cwd=self.source_folder,
        )
        self.run(f'{ld}make -j1', env="conanbuild", cwd=self.source_folder)

    def package(self):
        self.run(f'{self._toolchain_prefix()}make install', env="conanbuild", cwd=self.source_folder)

    def package_info(self):
        self.cpp_info.libs = ["qqwing"]
        self.cpp_info.bindirs = ["bin"]
