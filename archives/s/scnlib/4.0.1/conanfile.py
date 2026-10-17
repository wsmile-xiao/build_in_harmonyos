#!/usr/bin/env python3
"""Conan recipe — scnlib 4.0.1 (CMake, compiled library).

scnlib is a modern C++17 library for scanning values from an input string,
intended as a scanf/iostreams replacement ("scanf for modern C++").
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, rmdir, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout


class ScnlibConan(ConanFile):
    name = "scnlib"
    version = "4.0.1"
    description = "scanf for modern C++ — type-safe scanning library"
    license = "Apache-2.0"
    homepage = "https://github.com/eliaskosunen/scnlib"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        # scnlib 4.0.1 上游 bundled fast_float tag 为 v6.1.6（cmake/dependencies.cmake
        # FetchContent v6.1.6），使用仓内已发布的精确对应版本。
        # 外部 fast_float 由 patch 0001 让 find_package 与 Conan CMakeDeps 生成的
        # fast_float-config.cmake 对齐（上游写 find_package(FastFloat)）。
        self.requires("fast_float/6.1.6")
        # 上游测试依赖：SCN_USE_EXTERNAL_GTEST=ON 时上游 dependencies.cmake 走
        # find_package(GTest CONFIG REQUIRED)，由 Conan CMakeDeps 生成的
        # GTest-config.cmake + GTest::gtest_main/GTest::gmock_main targets 桥接
        # （与 fast_float 外部化同思路；上游 googletest CMake install 的导出目标名
        #  即为 GTest::gtest* / GTest::gmock*，与仓内 googletest 配方完全对齐）。
        # 用仓内已发布的 googletest/1.12.1：上游 scnlib 对 gtest 无版本约束
        # （find_package 无版本检查），本地实测 25/25 上游测试全过
        self.requires("googletest/1.12.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        # 默认静态（R26 系统同名库无冲突，静态最稳）；shared 由 Conan 管理
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        # scnlib 作为非 top-level 构建时 SCN_INSTALL 默认 OFF，显式开启
        tc.variables["SCN_INSTALL"] = True
        # 用仓内 fast_float/6.1.6（上游 bundled 版本即 v6.1.6），禁 FetchContent
        tc.variables["SCN_USE_EXTERNAL_FAST_FLOAT"] = True
        # googletest 外部化：上游 dependencies.cmake 内建 SCN_USE_EXTERNAL_GTEST
        # 开关（find_package(GTest CONFIG REQUIRED)，SCN_GTEST_LIBRARIES =
        # GTest::gtest_main + GTest::gmock_main），与仓内 googletest/1.12.1 的
        # CMakeDeps 桥接完全对齐，无需 patch 上游代码
        tc.variables["SCN_USE_EXTERNAL_GTEST"] = True
        # 上游测试补跑：SCN_TESTS=ON 构建 scn_tests/scn_impl_tests/scn_stdin_test
        # + compile-fail 测试（tests/unittests/ 全套），build() 中 ctest 执行
        tc.variables["SCN_TESTS"] = True
        tc.variables["SCN_DOCS"] = False
        # SCN_EXAMPLES=ON：注册 scn_examples_test（Python runner 验证 5 个示例
        # 输出），使 CTest 注册目标数与上游默认形态（SCN_CI=ON）完全一致（26 个）
        tc.variables["SCN_EXAMPLES"] = True
        tc.variables["SCN_BENCHMARKS"] = False
        tc.variables["SCN_BENCHMARKS_BUILDTIME"] = False
        tc.variables["SCN_BENCHMARKS_BINARYSIZE"] = False
        tc.variables["SCN_WERROR"] = False
        tc.variables["SCN_PEDANTIC"] = False
        tc.generate()
        # 物化 fast_float 的 CMakeDeps 文件（fast_float-config.cmake），
        # 供 patch 后的 find_package(fast_float) 发现
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # SCN_TESTS=ON：构建库本体 + 上游测试目标（scn_tests / scn_impl_tests /
        # scn_stdin_test / 22 个 compile-fail 测试）
        cmake.build()
        # 上游测试补跑（原 PR 因 CI 禁网拉不到 googletest 被跳过，本次回修补跑）：
        # OHOS musl ld.so 需显式 LD_LIBRARY_PATH=/system/lib64 解析
        # libc++_shared.so（test_package/conanfile.py 同一先例，glib2 亦同）；
        # compile-fail 测试经由 icm_build_failure_testing 在构建目录写临时文件，
        # /tmp 只读（E002）→ TMPDIR 指向可写构建目录
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        self.run(
            f'{bash} -c "export TMPDIR={self.build_folder} && '
            f'export LD_LIBRARY_PATH=/system/lib64 && '
            f'ctest --output-on-failure -j2"',
            env="conanbuild",
            cwd=self.build_folder,
        )

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        # CMake config 目录保留（scn-config.cmake / scn-targets.cmake 供 find_package(scn) 使用）

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "scn")
        self.cpp_info.set_property("cmake_target_name", "scn::scn")
        self.cpp_info.libs = ["scn"]
        if self.settings.os in ("Linux", "FreeBSD", "OHOS"):
            self.cpp_info.system_libs.extend(["m"])
