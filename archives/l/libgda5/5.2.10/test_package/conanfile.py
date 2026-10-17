#!/usr/bin/env python3
"""Conan test_package — libgda5 5.2.10 消费者验证（Conan L1）。

- test_libgda: 消费者功能测试（SQLite provider + 真实 SQL 往返）
- test_ohos  : HarmonyOS 专项测试（__OHOS__ 平台守卫、provider 插件动态加载、
                中文 UTF-8 往返、文件型数据库落盘/HMDFS 路径）

用 PkgConfigDeps + CMake 的 pkg_check_modules 消费被测包（libgda-5.0.pc 由
PkgConfigDeps 依据包内 cpp_info 生成，含 glib/libxml2/libxslt 的传递 Cflags/Libs）。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class Libgda5TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "PkgConfigDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()
        # 让 pkg-config 找到 PkgConfigDeps 生成的 .pc（libgda-5.0/gobject-2.0/
        # gthread-2.0/libxml-2.0/libxslt）
        env = Environment()
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        env.vars(self, scope="build").save_script("conanbuildenv-pkgconfig")
        # libgda 编译期把 provider 目录写死为 configure 时的 prefix（conan 的
        # autotools 安装走 DESTDIR，prefix=/）→ 运行期找不到 provider。libgda 支持
        # 用 GDA_TOP_BUILD_DIR 覆盖 provider 搜索目录（源码 gda-config.c:1727），
        # 这里指向包内 lib/libgda-5.0/（其下 providers/ 即 SQLite provider）。
        dep = self.dependencies[self.tested_reference_str]
        run_env = Environment()
        run_env.define("GDA_TOP_BUILD_DIR",
                       os.path.join(dep.package_folder, "lib", "libgda-5.0"))
        run_env.define("GDA_TOP_SRC_DIR",
                       os.path.join(dep.package_folder, "share", "libgda-5.0"))
        run_env.vars(self, scope="run").save_script("conanrunenv-libgda-paths")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return
        bindir = self.cpp.build.bindirs[0]
        for exe in ("test_libgda", "test_ohos"):
            self.run(os.path.join(bindir, exe), env="conanrun")
