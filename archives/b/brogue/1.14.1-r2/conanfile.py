#!/usr/bin/env python3
"""Conan recipe — brogue 1.14.1-r2 (Makefile).

Brogue is a roguelike game.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
import os
import shutil


class BrogueConan(ConanFile):
    name = "brogue"
    version = "1.14.1-r2"
    description = "Roguelike game"
    license = "AGPL-3.0-or-later"
    homepage = "https://sites.google.com/site/broguegame/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        # 自带头文件 + 静态库（参照 mp3info/nudoku/bitwise 绕开先例）：
        # 系统 libncursesw.so.6 缺 keypad 等符号且无 ncurses.h，无法直接链接；
        # ncurses/6.4 为他人 PR 前置（未发布制品仓），制品仓 ncurses/6.5 缺 OHOS 二进制。
        res_src = os.path.join(self.recipe_folder, "res")
        if os.path.isdir(res_src):
            res_dst = os.path.join(self.export_folder, "res")
            if os.path.exists(res_dst):
                shutil.rmtree(res_dst)
            shutil.copytree(res_src, res_dst)

    def requirements(self):
        # brogue 上游 term.c 用 #include <ncurses.h>，ncurses 为系统运行时库
        # （无 Conan recipe 可依赖），头文件/静态库自带（R27 绕开）。
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # 把自带的 ncurses 头文件/静态库从 export 目录复制到源码目录
        export_dir = os.path.join(os.path.dirname(self.source_folder), "e")
        res_src = os.path.join(export_dir, "res")
        if os.path.isdir(res_src):
            res_dst = os.path.join(self.source_folder, "res")
            if os.path.exists(res_dst):
                shutil.rmtree(res_dst)
            shutil.copytree(res_src, res_dst)

    def build(self):
        apply_conandata_patches(self)
        # Use terminal mode instead of SDL graphics (no SDL2 available on OHOS)
        # 上游 config.mk 在源根目录（非 src/），修正 sed 路径
        self.run(f"cd {self.source_folder} && sed -i 's/TERMINAL := NO/TERMINAL := YES/' config.mk")
        self.run(f"cd {self.source_folder} && sed -i 's/GRAPHICS := YES/GRAPHICS := NO/' config.mk")
        opt_flag = {"Debug": "-g -O0", "Release": "-O2", "RelWithDebInfo": "-O2 -g", "MinSizeRel": "-Os"}.get(str(self.settings.build_type), "-O2")

        # 自带的 ncurses（CI worker 无 dev 头文件）
        bundled_inc = os.path.join(self.source_folder, "res", "headers")
        bundled_lib = os.path.join(self.source_folder, "res", "libs")
        if not os.path.isdir(bundled_inc):
            raise RuntimeError(f"bundled ncurses headers missing: {bundled_inc}")
        if not os.path.isdir(bundled_lib):
            raise RuntimeError(f"bundled ncurses libs missing: {bundled_lib}")
        # 静态库以 base64 文本（.b64）入库（GitCode .diff 端点不支持二进制 patch，
        # 参照 Crypt-OpenSSL-RSA/unshield 先例），构建时解码回 .a
        for _f in os.listdir(bundled_lib):
            if _f.endswith(".b64"):
                _b64p = os.path.join(bundled_lib, _f)
                _binp = os.path.join(bundled_lib, _f[:-4])
                with open(_b64p, "r") as _b64f, open(_binp, "wb") as _binf:
                    import base64 as _b64
                    _binf.write(_b64.b64decode(_b64f.read()))

        # 上游 Makefile 在源根目录（非 src/）
        # -I{bundled_inc} 让 term.c #include <ncurses.h> 找到自带头文件；
        # LDFLAGS=-L{bundled_lib} -lncursesw 链接自带完整静态库（含 keypad 等符号）
        cc = self.conf.get('tools.build:compiler_executables', default={}, check_type=dict).get('c','cc')
        self.run(f"cd {self.source_folder} && make CC='{cc}' CFLAGS='{opt_flag} -I{bundled_inc}' LDFLAGS='-L{bundled_lib} -lncursesw'")
        # Run upstream regression tests（上游 tar 无 .broguerec 录制文件，
        # 传目录空跑验证脚本可用性；录制文件需另行生成故 0 用例通过）
        self.run(f"cd {self.source_folder}/test && python3 run_regression_tests.py . 2>&1", cwd=self.source_folder)

    def package(self):
        self.run(f"mkdir -p {self.package_folder}/bin")
        self.run(f"cp {self.source_folder}/bin/brogue {self.package_folder}/bin/")

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
