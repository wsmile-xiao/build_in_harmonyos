#!/usr/bin/env python3
"""Conan test_package — check 0.15.2.

L1 official test: builds a CMake consumer that links against
libcheck and runs a simple unit test suite.
"""
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
import os


class CheckTestConan(ConanFile):
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

    def test(self):
        if can_run(self):
            bindirs = self.cpp.build.bindirs
            if not bindirs:
                raise Exception("No bindirs found — test binary was not built")
            bin_path = os.path.join(bindirs[0], "test_check")
            if not os.path.isfile(bin_path):
                raise Exception(f"Test binary not found: {bin_path}")
            self.run(f"\"{bin_path}\"", env="conanrun")

            # Shared-library link test: compile test.c against libcheck.so
            pkg_folder = self.dependencies[self.tested_reference_str].package_folder
            shared_lib = os.path.join(pkg_folder, "lib", "libcheck.so")
            if os.path.isfile(shared_lib):
                # Use Conan's configured compiler instead of raw $CC (R33)
                compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
                cc = compilers.get("c")
                if not cc:
                    # 无 Conan 配置编译器时不回退到裸 shell 环境变量（R33），直接失败
                    raise Exception("No C compiler configured in tools.build:compiler_executables")
                src = os.path.join(self.source_folder, "test.c")
                shared_bin = os.path.join(bindirs[0], "test_check_shared")
                self.run(
                    f"\"{cc}\" \"{src}\" -o \"{shared_bin}\""
                    f" -I\"{pkg_folder}/include\" -L\"{pkg_folder}/lib\" -lcheck -lm -lrt -lpthread",
                    env="conanrun",
                )
                # 运行 shared 二进制时需将 libcheck.so 所在目录加入
                # LD_LIBRARY_PATH，否则动态加载器找不到符号
                lib_dir = os.path.join(pkg_folder, "lib")
                self.run(
                    f"LD_LIBRARY_PATH=\"{lib_dir}:$LD_LIBRARY_PATH\" \"{shared_bin}\"",
                    env="conanrun",
                )
                self.output.info("shared library test PASS")
