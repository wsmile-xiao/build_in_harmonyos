#!/usr/bin/env python3
"""test_package — 以库使用者身份编译、链接并运行 libpinyin 的消费者程序。

- `CMakeDeps`/`CMakeToolchain` 暴露依赖，`find_package(libpinyin CONFIG REQUIRED)`
  + `libpinyin::libpinyin` 是真链接（不是只 include）；
- `VirtualRunEnv` 提供运行时库搜索路径；
- test.c 用断言驱动退出码（init / alloc / parse / get_sentence / free）。
"""
import glob
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # libpinyin.so 引用 BDB 符号（制品仓 berkeley-db 为静态库，符号不经
        # DT_NEEDED 传递），消费者可执行文件必须自己链入 libdb.a。generate()
        # 阶段依赖 cpp_info 才是绝对路径（build() 阶段为相对且 package_folder 为空）。
        bdb = self.dependencies["berkeley-db"]
        bdb_libs = (bdb.cpp_info.libs or ["db"])[0]
        conan_home = os.environ.get("CONAN_HOME") or os.path.join(
            os.path.expanduser("~"), "tmp", "ch", "home-ds4-libpinyin")
        candidates = sorted(glob.glob(os.path.join(conan_home, "p", "*", "p",
                                                   "lib", "lib" + bdb_libs + ".a")))
        assert candidates, "libdb.a not found in conan cache"
        bdb_static = candidates[0]
        with open(os.path.join(self.generators_folder, "bdb_vars.cmake"), "w") as f:
            f.write('set(BDB_STATIC_LIB "%s")\n' % bdb_static)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning("cross build: 消费者程序未在本机执行（如实标记跳过）")
            return
        bindir = os.path.join(self.cpp.build.bindirs[0], "test_libpinyin")
        self.run(bindir, env="conanrun")
