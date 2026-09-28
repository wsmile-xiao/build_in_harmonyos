#!/usr/bin/env python3
"""Conan test_package — 消费者视角验证 libsavitar 真实 API。

构造最小 3MF 模型 → 调用 Savitar::ThreeMFParser::parse / sceneToString，
解析失败或序列化缺 <model 即判失败（非空壳测试，R34）。
test() 显式 self.run() 运行二进制（L0d 要求）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibsavitarTestConan(ConanFile):
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
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_libsavitar")
        # libSavitar.so.0 运行时 NEEDED libc++_shared.so（OHOS SDK llvm lib，
        # profile [buildenv] 提供），conanrun 环境不带该目录，需显式注入。
        run_dirs = self._runtime_lib_dirs()
        self.run(f'LD_LIBRARY_PATH="{":".join(run_dirs)}" "{test_bin}"', ignore_errors=False)
        # HarmonyOS 专项测试入口：平台数据模型/目标确认 + 3MF 解析/序列化往返
        ohos_test_bin = os.path.join(self.cpp.build.bindirs[0], "harmonyos_specific_test")
        self.run(
            f'LD_LIBRARY_PATH="{":".join(run_dirs)}" "{ohos_test_bin}"',
            ignore_errors=False,
        )

    def _runtime_lib_dirs(self):
        """libSavitar.so.0 运行期需要的库目录：SDK libc++_shared + 被测包 + 环境已有。"""
        run_dirs = []
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = compilers.get("cpp") or compilers.get("cxx")
        if compiler:
            sdk_lib = os.path.join(
                os.path.dirname(os.path.realpath(compiler)),
                "..", "lib", "aarch64-linux-ohos", "c++",
            )
            if os.path.isdir(sdk_lib):
                run_dirs.append(sdk_lib)
        for d in self.dependencies.values():
            pkg_lib = os.path.join(d.package_folder, d.cpp_info.libdirs[0])
            if os.path.isdir(pkg_lib):
                run_dirs.append(pkg_lib)
        existing_ld = os.environ.get("LD_LIBRARY_PATH")
        if existing_ld:
            run_dirs.append(existing_ld)
        return run_dirs