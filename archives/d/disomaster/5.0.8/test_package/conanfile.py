#!/usr/bin/env python3
"""Conan test_package for disomaster 5.0.8.

非破坏性消费者测试：使用 fake_xorriso 模拟 xorriso 命令行行为，
验证 DISOMaster 公开 API 的所有方法（34 个断言）。
"""

import os
import shlex

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class DisomasterTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)

        # 手动传递 Qt5 路径（CMakeDeps 组件级 includedirs/libdirs 在此环境未正确传递）
        qt5 = self.dependencies["qt5-qtbase"]
        tc.cache_variables["QT5_INCLUDE_DIR"] = os.path.join(qt5.package_folder, "include")
        tc.cache_variables["QT5_CORE_INCLUDE_DIR"] = os.path.join(qt5.package_folder, "include", "QtCore")
        tc.cache_variables["QT5_LIB_DIR"] = os.path.join(qt5.package_folder, "lib")

        # OHOS 平台：从编译器路径推断 C++ 运行时库目录
        if str(self.settings.os) == "OHOS":
            import shutil
            compiler = shutil.which("CC") or shutil.which("clang++")
            if compiler:
                compiler_dir = os.path.dirname(os.path.realpath(compiler))
                runtime_dir = os.path.join(
                    compiler_dir, "..", "lib", "aarch64-linux-ohos"
                )
                tc.cache_variables["OHOS_CXX_RUNTIME_DIR"] = runtime_dir

        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("Cross-building: consumer linked but cannot run")
            return

        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_disomaster")
        fake_bin = os.path.join(self.cpp.build.bindirs[0], "fake_xorriso")

        # 检查 xorriso 是否在包中可用
        pkg_name = self.tested_reference_str.split("/")[0]
        pkg = self.dependencies[pkg_name]
        xorriso_path = os.path.join(pkg.package_folder, "bin", "xorriso")
        lib_path = os.path.join(pkg.package_folder, "lib")

        is_ohos = str(self.settings.os) == "OHOS"
        bash = "/data/service/hnp/bin/bash" if is_ohos else "/bin/bash"

        # 运行 xorriso -version（如果可用）
        if os.path.isfile(xorriso_path):
            version_cmd = f"{shlex.quote(xorriso_path)} -version"
            if is_ohos:
                version_cmd = f"{shlex.quote(bash)} -c {shlex.quote(version_cmd)}"
            self.run(version_cmd, env="conanrun")

        # 运行主测试：test_disomaster fake_xorriso
        # 设置 LD_LIBRARY_PATH 以便找到 libdisomaster.so 和 libQt5Core.so
        qt5_lib_path = os.path.join(self.dependencies["qt5-qtbase"].package_folder, "lib")
        ld_path = f"{lib_path}:{qt5_lib_path}"
        # 直接设置环境变量，确保 conanrun 环境不会覆盖
        current_ld = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = f"{ld_path}:{current_ld}" if current_ld else ld_path
        test_cmd = f"{shlex.quote(test_bin)} {shlex.quote(fake_bin)}"
        if is_ohos:
            test_cmd = f"{shlex.quote(bash)} -c {shlex.quote(test_cmd)}"
        self.run(test_cmd, env="conanrun")
