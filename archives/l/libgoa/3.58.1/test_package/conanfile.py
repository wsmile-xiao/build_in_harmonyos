#!/usr/bin/env python3
"""Conan test_package — libgoa 3.58.1 消费者契约测试（L1）。

两层验证（都针对"安装后的包"，不是源码树）：
  1. CMakeDeps + CMakeToolchain 构建并运行 test_goa_consumer：实际调用
     libgoa-1.0.so.0 的导出符号（版本全局量、goa_check_version、
     goa_error_quark、GObject/GDBus 类型注册、goa_client_new_sync）。
  2. PkgConfig 校验 goa-1.0.pc 这一"包身份面"：modversion / includedirs /
     libs 必须来自本包，而不是同名的系统库。

文件位置: archives/l/libgoa/3.58.1/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.gnu import PkgConfig, PkgConfigDeps


class LibgoaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    exports_sources = "CMakeLists.txt", "*.c"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()
        PkgConfigDeps(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            raise ConanException("libgoa 消费者程序只能在 OHOS/Linux 上运行")

        # 1. 链接 + 运行：调用库导出的真实符号
        executable = os.path.join(self.cpp.build.bindirs[0], "test_goa_consumer")
        self.run('"%s"' % executable, env="conanrun")

        # 2. 包身份面：conan 生成的 goa-1.0.pc
        pkg_config = PkgConfig(self, "goa-1.0", pkg_config_path=self.generators_folder)
        self.output.info("goa-1.0.pc modversion = %s" % pkg_config.version)
        self.output.info("goa-1.0.pc includedirs = %s" % pkg_config.includedirs)
        self.output.info("goa-1.0.pc libs = %s" % pkg_config.libs)
        if pkg_config.version.split(".")[:2] != ["3", "58"]:
            raise ConanException("goa-1.0.pc 版本异常: %s" % pkg_config.version)
        if not any("goa-1.0" in include for include in pkg_config.includedirs):
            raise ConanException("goa-1.0.pc 缺少 goa-1.0 头文件目录: %s"
                                 % pkg_config.includedirs)
        if "goa-1.0" not in pkg_config.libs:
            raise ConanException("goa-1.0.pc 缺少 -lgoa-1.0: %s" % pkg_config.libs)
