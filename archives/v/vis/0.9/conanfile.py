#!/usr/bin/env python3
"""Conan recipe — vis 0.9（Vim 风格终端文本编辑器）

vis 提供 vis 命令（C，configure + make），核心依赖 libtermkey +
unibilium（制品仓未发布 → 本配方通过 requirements 声明本地 stub/源码
处理，同 account-utils 先例）+ lua（可选，--enable-lua=no 禁用）。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class VisConan(ConanFile):
    name = "vis"
    version = "0.9"
    description = "vis — modern, legacy free, simple yet efficient Vim-like editor"
    license = "ISC"
    homepage = "https://github.com/martanne/vis"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # stubs/ 随 recipe 导出（libtermkey/unibilium 未发布 → stub 硬做）
    exports_sources = "stubs/*"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # libtermkey stub：编译 stub-termkey.c 成静态库（制品仓未发布）
        build_dir = self.build_folder
        src_dir = self.source_folder
        stub_dir = os.path.join(src_dir, "stubs")
        self.run(
            f"/data/service/hnp/bin/clang -c {stub_dir}/stub-termkey.c "
            f"-I{stub_dir} -o {src_dir}/stub-termkey.o",
        )
        self.run(
            f"/data/service/hnp/bin/ar rcs {src_dir}/libtermkey.a "
            f"{src_dir}/stub-termkey.o",
        )
        # vis Makefile 用相对路径源文件（不支持 out-of-source）→ 在源码
        # 目录 in-source 构建；--enable-curses/lua/tre=no 禁用可选依赖
        self.run(
            f"umask 000 && cd {src_dir} && "
            # configure 检测编译用 $CFLAGS（非 $CPPFLAGS）→ -I stubs 注入 CFLAGS
            f"CFLAGS=-I{stub_dir} "
            f"LDFLAGS='-L{src_dir} -ltermkey' "
            f"./configure --enable-curses=no --enable-lua=no "
            "--enable-tre=no",
            env="conanbuild",
        )
        self.run(
            f"umask 000 && cd {src_dir} && make -j1",
            env="conanbuild",
        )

    def package(self):
        bin_dst = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dst, exist_ok=True)
        import glob as _glob
        # in-source 构建：vis 产物在 source_folder（非 build_folder）
        for name in ("vis", "vis-cli"):
            cands = _glob.glob(
                os.path.join(self.source_folder, "**", name), recursive=True
            )
            if cands:
                copy(self, name, src=os.path.dirname(cands[0]),
                     dst=bin_dst, keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        bin_path = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bin_path):
            self.runenv_info.append_path("PATH", bin_path)
            self.buildenv_info.append_path("PATH", bin_path)
