#!/usr/bin/env python3
"""Conan test_package for gnustep-make 2.9.2.1.

Builds and runs the upstream GNUstep TestFramework examples (example1-9.m,
taken verbatim from gnustep/tools-make make-2_9_2 TestFramework/) against the
installed gnustep-make + the published gnustep-base/1.31.1 Foundation.

All 9 examples must exit 0. example3/example4 are intentionally written to send
a bad message to an NSString and rely on NS_DURING/NS_HANDLER to catch the
raised ObjC exception (their internal "Failed test" line is the expected
upstream behavior). With the complete GNUstep environment they are caught and
the programs exit 0 — measured 9/9 PASS on HarmonyOS PC.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class GnustepMakeTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # gnustep-base 已在制品仓发布；其运行期依赖仅 libobjc2/libffi/curl
        # （gnustep-make 是其 tool_requires，运行期无版本冲突），因此这里可以
        # 依赖 gnustep-base 真实编译运行上游 TestFramework 的 9 个 example。
        self.requires("gnustep-base/1.31.1",
                      transitive_headers=True, transitive_libs=True)

    @staticmethod
    def _sdk_cxx_lib_dir():
        """定位 OHOS SDK 的 C++ 运行时目录（含 libc++_shared.so）。

        libobjc2 的 libobjc.so 依赖 libc++_shared.so，该 .so 由 OHOS SDK 提供
        （位于 clang 真实路径的 ../lib/<triplet>/）。通过 clang 可执行文件的
        realpath 推导，CI worker 与本地路径不同也能正确解析。
        """
        clang = shutil.which("clang")
        if not clang:
            return None
        real = os.path.realpath(clang)
        llvm_root = os.path.dirname(os.path.dirname(real))
        for sub in ("aarch64-linux-ohos", "aarch64-unknown-linux-ohos",
                    "aarch64-linux-gnu"):
            cand = os.path.join(llvm_root, "lib", sub)
            if os.path.isfile(os.path.join(cand, "libc++_shared.so")):
                return cand
        return None

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info(
                "cross-building: examples linked but cannot run on this host"
            )
            return

        # 由 run_examples.sh 真实运行上游 TestFramework 9 个 example，
        # 全部要求 EXIT 0（实测 9/9 通过）。
        exe_dir = self.cpp.build.bindirs[0]
        sdk_cxx = self._sdk_cxx_lib_dir() or ""
        script = os.path.join(self.recipe_folder, "run_examples.sh")
        self.run(
            f'EXE_DIR="{exe_dir}" SDK_CXX_LIB="{sdk_cxx}" sh "{script}"',
            env="conanrun",
            shell=True,
        )
