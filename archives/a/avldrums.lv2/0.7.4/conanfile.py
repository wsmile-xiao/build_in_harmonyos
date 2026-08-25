#!/usr/bin/env python3
"""Conan recipe for avldrums.lv2 0.7.4 — Makefile (gnu-make + pkg-config).

avldrums.lv2 is an LV2 drum sample player plugin (AVLinux Drumkits),
building with the upstream Makefile. Requires LV2 SDK and glib-2.0;
the OpenGL GUI (cairo/pango/GL) is disabled via BUILDOPENGL=no since
OHOS has no GL/X11 stack.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.env import Environment, VirtualRunEnv
from conan.tools.files import get
from conan.tools.layout import basic_layout


class AvldrumsLv2Conan(ConanFile):
    name = "avldrums.lv2"
    version = "0.7.4"
    description = "LV2 drum sample player plugin (AVLinux Drumkits)"
    license = "GPL-3.0"
    homepage = "https://x42-plugins.com/x42/x42-avldrums"
    url = "https://github.com/x42/avldrums.lv2"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    # library 类型必须声明 shared 选项（conan 2 校验；sherlock.lv2 同款先例）
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def requirements(self):
        # Makefile 经 pkg-config 检查 lv2 >= 1.6.0 与 glib-2.0
        self.requires("lv2/1.18.11-git")
        self.requires("glib/2.84.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Makefile 用 pkg-config 查 lv2/glib，需把依赖的 pkgconfig 目录
        # 注入 PKG_CONFIG_PATH（lv2 是 header-library，glib 提供 glib-2.0.pc）
        env = Environment()
        pc_paths = []
        for dep in ("lv2", "glib"):
            if dep in self.dependencies:
                pc_paths.append(
                    os.path.join(self.dependencies[dep].package_folder, "lib", "pkgconfig")
                )
        if pc_paths:
            env.append_path("PKG_CONFIG_PATH", os.pathsep.join(pc_paths))
        env.vars(self).save_script("conanbuild_env")
        # 运行测试/消费者需要 lv2/glib 共享库路径
        VirtualRunEnv(self).generate()

    def _pc_path(self):
        """返回所有依赖（含传递：glib→pcre2 等）的 pkgconfig 目录拼接串，
        供命令内 export。glib-2.0.pc Requires libpcre2-8，只注入 glib 的
        pkgconfig 仍会找不到传递依赖的 .pc。"""
        pc_paths = []
        for dep in self.dependencies.values():
            pc = os.path.join(dep.package_folder, "lib", "pkgconfig")
            if os.path.isdir(pc):
                pc_paths.append(pc)
        return os.pathsep.join(pc_paths)

    def _glib_inc_flags(self):
        """制品仓 glib 二进制包的 glib-2.0.pc prefix=/ 未修正（Cflags 输出
        -I//include/glib-2.0 根目录，glib.h 找不到——与 sord 依赖 zix 同款
        问题）。探测 glib 包真实 include 目录注入 -isystem，覆盖坏 .pc。"""
        flags = []
        for dep in self.dependencies.values():
            if dep.ref.name != "glib":
                continue
            base = dep.package_folder
            for cand in ("include/glib-2.0", "lib/glib-2.0/include"):
                full = os.path.join(base, cand)
                if os.path.isdir(full):
                    flags.append(f"-isystem{full}")
        return " ".join(flags)

    def _dep_lib_flags(self):
        """制品仓 glib/pcre2 等依赖的 .pc 未修正 prefix（-L//lib 根目录），
        链接时 -lglib-2.0/-lpcre2-8 找不到。注入依赖真实 lib 目录 -L。"""
        libs = []
        for dep in self.dependencies.values():
            libdir = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(libdir):
                libs.append(f"-L{libdir}")
        return " ".join(libs)

    def build(self):
        # tarball 无 .git，git describe 会回退 "LV2"，显式传版本号；
        # BUILDOPENGL=no 禁用 OpenGL GUI（OHOS 无 GL/X11）
        # Makefile 在源码目录（basic_layout 的 build folder 无 Makefile），
        # 用 make -C 指向 source_folder 执行；PKG_CONFIG_PATH 在命令内
        # 显式 export（conan 环境脚本不自动注入依赖 pkgconfig 路径）
        make = (
            "export PKG_CONFIG_PATH=\"{pc}:$PKG_CONFIG_PATH\"; "
            "make -C {src} -j1 CC={cc} CXX={cxx} "
            "CFLAGS=\"{glib_inc}\" LOADLIBES=\"{dep_libs}\" "
            "avldrums_VERSION=0.7.4 BUILDOPENGL=no"
        ).format(
            pc=self._pc_path(),
            src=self.source_folder,
            cc=shutil.which("clang") or "/data/service/hnp/bin/clang",
            cxx=shutil.which("clang++") or "/data/service/hnp/bin/clang++",
            glib_inc=self._glib_inc_flags(),
            dep_libs=self._dep_lib_flags(),
        )
        self.run(make, env="conanbuild")
        self.output.info("avldrums.lv2 build completed")

    def package(self):
        # 安装到 lib/lv2/avldrums.lv2（LV2 bundle 目录），遵守
        # LV2 文件系统层级规范（不用 libdir）
        self.run(
            "export PKG_CONFIG_PATH=\"{pc}:$PKG_CONFIG_PATH\"; "
            "make -C {src} install DESTDIR={dst}/ PREFIX=/usr LV2DIR=lib/lv2 "
            "CC={cc} CXX={cxx} "
            "BUILDOPENGL=no avldrums_VERSION=0.7.4".format(
                pc=self._pc_path(),
                src=self.source_folder,
                dst=self.package_folder,
                cc=shutil.which("clang") or "/data/service/hnp/bin/clang",
                cxx=shutil.which("clang++") or "/data/service/hnp/bin/clang++",
            ),
            env="conanbuild",
        )
        self.output.info(
            "avldrums.lv2 installed to {}".format(
                os.path.join(self.package_folder, "lib", "lv2", "avldrums.lv2")
            )
        )

    def package_info(self):
        # LV2 插件 bundle：头文件/库在 bundle 目录内，无导出 include/lib
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["lib/lv2"]
