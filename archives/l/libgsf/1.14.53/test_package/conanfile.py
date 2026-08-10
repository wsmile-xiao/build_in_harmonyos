#!/usr/bin/env python3
"""Conan test_package — libgsf 1.14.53

L1 test: build test.c (links libgsf-1 via pkg-config) and run it.
Uses self.run() so the CI L0d gate sees a real command execution.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake
from conan.tools.gnu import PkgConfigDeps
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv


class LibgsfTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # gsf.h 需要 glib 的头 (版本与本体配方对齐,避免 graph 冲突)
        self.requires("glib/2.84.0")
        # libgsf 头文件 gsf-libxml.h 依赖 <libxml/parser.h>,
        # PkgConfigDeps 需生成 libxml-2.0.pc 供 pkg_check_modules 发现
        self.requires("libxml2/2.15.3")

    def generate(self):
        VirtualBuildEnv(self).generate()
        PkgConfigDeps(self).generate()
        # glib 2.84.0 是 R26 static 包(仅 .a 无 .so),PkgConfigDeps 生成的
        # glib-2.0.pc 的 Libs 是动态 "-lxxx" 形式,链接 test_libgsf 会动态
        # NEEDED libgobject-2.0.so.0(不存在)导致运行时 symbol not found;
        # 且 glib 无 components,PkgConfigDeps 不生成 gobject-2.0.pc/
        # gio-2.0.pc(CMakeLists 的 pkg_check_modules 需要)→ 缺失则创建
        # 完整 .pc(指向 .a 绝对路径),已存在则 patch 为 .a 绝对路径。
        # 用 dependencies 的 package_folder 定位(CI 干净环境 glib 从 ohpcd
        # 下载,缓存路径无 b/ 前缀,硬编码 glob 匹配不到 → 曾漏建 gobject-2.0.pc)。
        _gl = None
        if "glib" in self.dependencies:
            _gl = self.dependencies["glib"].package_folder
        if _gl and os.path.exists(os.path.join(_gl, "lib", "libgobject-2.0.a")):
            _inc = os.path.join(_gl, "include", "glib-2.0")
            _inc2 = os.path.join(_gl, "lib", "glib-2.0", "include")
            for _pcname, _libname in (("glib-2.0.pc", "glib-2.0"),
                                      ("gobject-2.0.pc", "gobject-2.0"),
                                      ("gio-2.0.pc", "gio-2.0")):
                _pf = os.path.join(self.generators_folder, _pcname)
                if os.path.exists(_pf):
                    with open(_pf, "r", encoding="utf-8") as _f:
                        _pc = _f.read()
                    if ".a" not in _pc:
                        for _libn in ("glib-2.0", "gobject-2.0", "gio-2.0",
                                      "gmodule-2.0", "gthread-2.0"):
                            _pc = _pc.replace(
                                "-l{}".format(_libn),
                                "{}/lib/lib{}.a".format(_gl, _libn))
                        _pc = _pc.replace("-l:ld-musl-aarch64.so.1",
                                          "/lib/ld-musl-aarch64.so.1")
                        with open(_pf, "w", encoding="utf-8") as _f:
                            _f.write(_pc)
                else:
                    # PkgConfigDeps 未生成(glib 无 components)→ 创建完整 .pc
                    _pc = (
                        "prefix={}\n"
                        "libdir=${{prefix}}/lib\n"
                        "includedir=${{prefix}}/include/glib-2.0\n"
                        "includedir1=${{prefix}}/lib/glib-2.0/include\n"
                        "\n"
                        "Name: {}\n"
                        "Description: Conan package: {}\n"
                        "Version: 2.84.0\n"
                        "Libs: -L${{libdir}} {}/lib/lib{}.a\n"
                        "Cflags: -I${{includedir}} -I${{includedir1}}\n"
                        "Requires: glib-2.0\n"
                    ).format(_gl, _pcname.replace(".pc", ""),
                             _pcname.replace(".pc", ""), _gl, _libname)
                    with open(_pf, "w", encoding="utf-8") as _f:
                        _f.write(_pc)
        # P2 review: 与全仓库其他 test_package 一致, VirtualRunEnv 默认 scope
        # 即生成 conanrun 环境(含 host-context 依赖运行时路径),
        # 匹配 test() 中 env="conanrun" 运行测试二进制。
        VirtualRunEnv(self).generate()

    def test(self):
        # Build the test executable via CMake; test.c links libgsf-1 through
        # pkg-config (PkgConfigDeps above emits libgsf-1.pc into the env).
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        # Run the compiled test executable — self.run() satisfies L0d gate
        test_exe = os.path.join(self.build_folder, "test_libgsf")
        self.run(test_exe, env="conanrun")
