#!/usr/bin/env python3
"""Conan test_package template — Conan L1 official test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/{letter}/hdrhistogram/{version}/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class HdrhistogramTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()


    def _lib_env(self):
        """显式给出依赖的 libdir 供运行期加载。

        为什么不能只靠 env="conanrun"：这些包按 shared=False 发布（package_type 视其为静态），
        conan 的 VirtualRunEnv 因而不会把 libdirs 写进 LD_LIBRARY_PATH——
        实测生成的 conanrunenv-*.sh 里是空的 `for v in`，即什么都没设。
        而包里确实装了 .so，且本次修复把它的 DT_SONAME 补成了裸名
        （修复前无 SONAME，链接器会把绝对路径烤进 DT_NEEDED，所以"碰巧"能跑）。
        裸名 + 无搜索路径 = 运行期找不到，故这里显式补上。
        """
        import os
        dirs = []
        for _ref, dep in self.dependencies.items():
            for d in (dep.cpp_info.libdirs or []):
                if d not in dirs:
                    dirs.append(d)
        old = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(dirs + ([old] if old else []))
        self.output.info("测试期 LD_LIBRARY_PATH=%s" % os.environ["LD_LIBRARY_PATH"][:200])

    def test(self):
        self._lib_env()
        cmake = CMake(self)
        cmake.test()
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_hdrhistogram")
        self.run(bin_path, env="conanrun")