#!/usr/bin/env python3
"""Conan recipe — tofrodos 1.8.3（DOS↔Unix 文本换行转换工具）

简单 Makefile 构建（非 autotools），Makefile 不支持 DESTDIR，
package() 手动复制产物：fromdos 可执行 + todos（软链接/副本）。
HMDFS 拒绝 ln -s，todos 用复制代替软链接（同 libaccounts-qt 经验）。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout


class TofrodosConan(ConanFile):
    name = "tofrodos"
    version = "1.8.3"
    description = "tofrodos — DOS↔Unix 文本换行转换工具（fromdos/todos）"
    license = "GPL-2.0-or-later"
    homepage = "https://www.thefreecountry.com/tofrodos/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    # 无第三方依赖（纯 C），R36 天然满足

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 上游 Makefile 默认 CC=gcc，系统仅 clang；从 profile conf 取编译器
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c") or "clang"
        # -j1: OHOS 沙箱不支持 mkfifo（jobserver），并行编译失败
        self.run(f'make -C "{self.source_folder}/src" CC="{cc}" -j1')

    def package(self):
        src = os.path.join(self.source_folder, "src")
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        # HMDFS 对 copy() 丢执行位、对 ln -s 拒绝 → 手动读写新文件 + chmod 0o755，
        # 确保 fromdos/todos 均可执行（同 libaccounts-glib 经验）
        self._install_executable(src, bin_dir, "fromdos", "fromdos")
        self._install_executable(src, bin_dir, "fromdos", "todos")
        # man page
        man_dir = os.path.join(self.package_folder, "share", "man", "man1")
        os.makedirs(man_dir, exist_ok=True)
        copy(self, "fromdos.1", src=src, dst=man_dir, keep_path=False)
        copy(self, "fromdos.1", src=src,
             dst=os.path.join(man_dir, "todos.1"), keep_path=False)

    @staticmethod
    def _install_executable(src_dir, dst_dir, src_name, dst_name):
        """复制二进制为新文件并置执行位（绕开 HMDFS copy 丢权限 / ln -s 被拒）。"""
        import shutil
        src_path = os.path.join(src_dir, src_name)
        dst_path = os.path.join(dst_dir, dst_name)
        shutil.copyfile(src_path, dst_path)
        os.chmod(dst_path, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
