#!/usr/bin/env python3
"""Conan recipe for d11amp 0.61 (Oldskool mp3 player, GTK4 GUI).

Build system: bare Makefile (mark4/software/Makefile).
Main target: mark4 (the current generation; mark1..mark3 are historical).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class D11AmpConan(ConanFile):
    name = "d11amp"
    version = "0.61"
    description = "Oldskool mp3 player (GTK4)"
    license = "BSD-2-Clause"
    homepage = "https://github.com/dettus/d11amp"
    url = "https://github.com/dettus/d11amp"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        # R32: os 判断必须 in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # d11amp mark4/software/Makefile 的 LIBRARIES 依赖：
        #   gdk-pixbuf-2.0 gtk4 libmpg123 portaudio-2.0 libzip
        # gtk4/4.22.4 配方 override glib/2.84.0.1.1(shared=True)，使全图 glib 锁定
        # 2.84.0.1.1 → harfbuzz 需匹配 glib/2.84.Z 动态链的二进制。制品仓
        # harfbuzz/14.2.0.1 只有锁定 glib/2.84.0.1 的 3009fa3b（不匹配，CI
        # 干净环境回退源码构建且 meson.test 失败 165 项）；修复版 14.2.0.1.1.1
        # (2026-08-23, requires glib/2.84.Z 动态) 与依赖图完全匹配。
        # E538/gtkmm 先例：消费者 override 统一版本（不得改依赖库配方）。
        self.requires("harfbuzz/14.2.0.1.1.1", override=True)
        self.requires("gtk4/4.22.4", transitive_headers=True, transitive_libs=True)
        self.requires("gdk-pixbuf/2.44.6", transitive_headers=True, transitive_libs=True)
        self.requires("mpg123/1.33.5", transitive_headers=True, transitive_libs=True)
        self.requires("portaudio/19.7.0", transitive_headers=True, transitive_libs=True)
        self.requires("libzip/1.11.4", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Makefile 用 pkg-config 探测依赖，PkgConfigDeps 生成 .pc 文件
        PkgConfigDeps(self).generate()
        # audiowmark 先例：make 通过 `pkg-config libmpg123` 引用，而 conan
        # mpg123 包导出 mpg123.pc，补 libmpg123.pc 别名
        mpg123_pc = os.path.join(self.generators_folder, "mpg123.pc")
        libmpg123_pc = os.path.join(self.generators_folder, "libmpg123.pc")
        if os.path.isfile(mpg123_pc) and not os.path.exists(libmpg123_pc):
            shutil.copyfile(mpg123_pc, libmpg123_pc)
        # libzip 包 pkg_config_name 动态探测；若未生成 libzip.pc 补别名
        libzip_pcs = [f for f in os.listdir(self.generators_folder)
                      if f.endswith(".pc") and os.path.isfile(os.path.join(self.generators_folder, f))]
        if "libzip.pc" not in libzip_pcs:
            cand = [f for f in libzip_pcs if f.startswith("libzip")]
            if cand and not os.path.exists(os.path.join(self.generators_folder, "libzip.pc")):
                shutil.copyfile(os.path.join(self.generators_folder, cand[0]),
                                os.path.join(self.generators_folder, "libzip.pc"))

    def _compilers(self):
        """R33: 编译器从 Conan conf（tools.build:compiler_executables）获取，
        不依赖未定义的 shell 环境变量。OHOS profile 已配置 clang 路径。"""
        cc = cxx = ""
        execs = self.conf.get("tools.build:compiler_executables", default={})
        if execs:
            cc = execs.get("c", "")
            cxx = execs.get("cpp", "")
        cc = cc or "clang"
        cxx = cxx or "clang++"
        return cc, cxx

    def _run_make(self, src: str, extra: str = ""):
        cc, cxx = self._compilers()
        self.run(
            f"cd '{src}' && CC={cc} CXX={cxx} "
            f"PKG_CONFIG_PATH={self.generators_folder} make -j1 {extra}",
            env="conanbuild",
        )

    def build(self):
        apply_conandata_patches(self)
        # 主构建目标在 mark4/software（当前版本；mark1..mark3 为历史代）
        src = os.path.join(self.source_folder, "mark4", "software")
        self._run_make(src)

    def package(self):
        src = os.path.join(self.source_folder, "mark4", "software")
        # Makefile install 目标：PREFIX?=/usr/local，DESTDIR 指向 package_folder。
        # install(1) 不创建父目录：先建好 bin/ 与 man1/；PREFIX= 空串使
        # MYPREFIX=$(DESTDIR)$(PREFIX) = package_folder → 产物落到
        # <package>/bin/d11amp 与 <package>/share/man/man1/d11amp.1（与
        # package_info.bindirs 对齐）。
        os.makedirs(os.path.join(self.package_folder, "bin"), exist_ok=True)
        os.makedirs(
            os.path.join(self.package_folder, "share", "man", "man1"),
            exist_ok=True,
        )
        cc, cxx = self._compilers()
        self.run(
            f"cd '{src}' && CC={cc} CXX={cxx} "
            f"PKG_CONFIG_PATH={self.generators_folder} "
            f"make install DESTDIR={self.package_folder} PREFIX=",
            env="conanbuild",
        )

    def package_info(self):
        # 应用型产物：bin/ 下是可执行文件
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []