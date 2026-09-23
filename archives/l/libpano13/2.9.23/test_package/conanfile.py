#!/usr/bin/env python3
"""Conan test_package — libpano13 消费者测试。

用裸 clang 编译（绕开 CMakeToolchain 在 os=OHOS 下把 CMAKE_SYSTEM_NAME 映射成
cmake 不认的值），直接链接 libpano13.so 并调用公开 API（panorama.h/filter.h）。
与 libtiff/libtiff 系同法。
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building


class Libpano13TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # 头闭包自检要用「所有依赖」的 include（如 tiff 相关头 #include <tiffio.h> 等）
        incs = []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
        inc = " ".join(incs)
        libdir = self.dependencies["libpano13"].cpp_info.libdirs[0]
        libs = " ".join("-l" + l for l in self.dependencies["libpano13"].cpp_info.libs)
        cc = os.environ.get("CC", "clang")
        self.run(f"{cc} test.c -o test_libpano13 {inc} -L{libdir} {libs}")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        # libpano13 的 SONAME 为 libpano13.so.3，运行期需把被测包及全部传递依赖
        # 的 lib 目录注入 LD_LIBRARY_PATH（conanrun 聚合 env 未必覆盖被测包自身）。
        ld_paths = []
        for _ref, _d in self.dependencies.items():
            ld_paths += list(_d.cpp_info.libdirs)
        _ld = ":".join(ld_paths)
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c 'LD_LIBRARY_PATH=\"{_ld}:$LD_LIBRARY_PATH\" ./test_libpano13'",
                 env="conanrun")
