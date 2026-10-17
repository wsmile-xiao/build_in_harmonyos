#!/usr/bin/env python3
import os
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import can_run


class Log4cplusTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        # OHOS 上 socket helper 符号为外部引用，使用 --warn-unresolved-symbols
        # 允许链接，核心 API 测试仍可正常编译运行
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _check_library_exists(self):
        """验证库文件存在于 package 中"""
        libdirs = self.dependencies["log4cplus"].cpp_info.libdirs
        if not libdirs:
            raise FileNotFoundError("libdirs is empty — log4cplus library not packaged")
        lib_dir = libdirs[0]
        for lib_name in ["liblog4cplusS.a", "liblog4cplus.so"]:
            lib_path = os.path.join(lib_dir, lib_name)
            if os.path.isfile(lib_path):
                self.output.info(f"Library found: {lib_path}")
                return True
        raise FileNotFoundError(f"Library not found in {lib_dir}")

    def test(self):
        self._check_library_exists()

        if can_run(self):
            test_bin = os.path.join(self.cpp.build.bindir, "test_log4cplus")
            if not os.path.isfile(test_bin):
                raise FileNotFoundError(f"test_log4cplus binary not found at {test_bin}")

            # OHOS 上 socket helper 符号缺失导致动态链接失败，test_package 明确失败
            #（R9/R34：不吞没二进制执行失败，测试状态如实反映 OHOS 运行时限制）
            try:
                self.run(test_bin, env="conanrun")
            except Exception as e:
                msg = str(e)
                if self.settings.os == "OHOS" and "symbol not found" in msg:
                    msg += "\n[OHOS] socket helper symbols unresolved — log4cplus core API cannot run on this OHOS build environment"
                raise RuntimeError(msg)
