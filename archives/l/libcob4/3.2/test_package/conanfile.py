#!/usr/bin/env python3
"""Conan test_package for libcob4 (L1 official test).

CI runs this automatically via `conan create`.

File location: archives/l/libcob4/3.2/test_package/conanfile.py

两层：
  1. `ctest` 跑 test_libcob.c 的 api 模式 —— 链接真实 libcob.so.4，跑运行时
     初始化状态机、内存 API、字段→字符串边界截断、运行时 getpid 绑定。
  2. `test_libcob.sh` 以 TAP 形式补包布局与临时目录解析行为断言。
     临时目录那几条必须**换进程**才能测（libcob 的 TMPDIR 解析结果是进程内
     静态缓存），所以放在 shell 驱动里而不是 ctest 里。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout


class Libcob4TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _find_binary(self):
        exact = os.path.join(self.build_folder, "test_libcob")
        if os.path.isfile(exact):
            return exact
        for root, _dirs, files in os.walk(self.build_folder):
            if "test_libcob" in files:
                return os.path.join(root, "test_libcob")
        return None

    def test(self):
        cmake = CMake(self)
        cmake.test()

        binary = self._find_binary()
        if binary is None:
            raise ConanException("built test_libcob executable was not found")

        dep = self.dependencies["libcob4"]
        driver = os.path.join(self.source_folder, "test_libcob.sh")
        self.run(
            'sh "{driver}" "{binary}" "{pkg}"'.format(
                driver=driver, binary=binary, pkg=dep.package_folder),
            env="conanrun",
        )
