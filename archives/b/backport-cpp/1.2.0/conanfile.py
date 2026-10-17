#!/usr/bin/env python3
"""Conan recipe for backport-cpp 1.2.0 — header-only C++11 backport library.

BackportCpp（上游 include/bpstd/*，命名空间 bpstd）把 C++14/17/20 的
optional / variant / string_view / span / any / tuple / functional 等回移到
C++11，CMake INTERFACE 目标 ``Backport::Backport``，运行期零依赖。

适配要点（完整证据见 notes.md / reports/）：

* header-only：``package()`` 只拷 ``include/**.hpp`` + ``LICENSE``，
  ``package_id()`` 清空为单一 id（templates/conanfile-headeronly.py.tmpl 变体 A）。
* 上游单测（test/，Catch2 2.x）默认在 ``build()`` 内构建并运行：
  - ``test/CMakeLists.txt`` 调用 ``find_package(Catch2 REQUIRED)`` +
    ``include(Catch)`` + ``catch_discover_tests()``。ohpcd 制品仓的
    catch2/2.13.10 只打包头文件，不带 Catch2 v2 的 ``contrib/Catch.cmake``
    CTest 集成模块 —— 按 ``archives/c/ctpg/1.3.7`` 先例在 ``generate()`` 注入
    最小 Catch.cmake（把测试可执行注册成 1 个 ctest 用例），**不改上游源码**；
  - ``build()`` 另外直跑测试可执行并开 ``--durations yes``，让 Catch2 自报的
    用例数/断言数与逐用例耗时完整落进 conan-create.log（供 N/N′ 对账）。
* 上游 CMakeLists 给 Clang/GNU 开了 ``-Wall -Werror -Wextra -pedantic
  -pedantic-errors``；clang 15 对两处**类外析构函数定义**报 ``-Wdtor-name``
  （ISO C++ 要求 ~ 后的名字与 ~ 前在同一作用域内被找到）⇒ patches/0001 按
  clang 的 fix-it 改成「注入类名」写法：纯名字查找形式修正，零语义变化，
  用例数/断言数不变。修后 16 个公开头在 ``-pedantic-errors`` 下逐个编译探针全过。
* ``CMAKE_POLICY_VERSION_MINIMUM=3.5``：上游 ``cmake/AddSelfContainmentTest.cmake``
  声明 ``cmake_minimum_required(VERSION 3.1)``，CMake 4.x 需要该变量才不报
  兼容性错误（设备 cmake 4.1.2 实测）。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get

# 最小 Catch.cmake：Catch2 v2 的 CTest 集成模块（contrib/Catch.cmake，BSD-3-Clause）
# 未被打进 ohpcd 的 catch2 包，注入此最小实现让上游 test/CMakeLists.txt 的
# include(Catch) + catch_discover_tests(TARGET) 原样可用（不改上游源码）。
# 单个 ctest 用例 = 整个 Catch2 测试可执行；Catch2 自报口径由 build() 直跑采集。
_CATCH_CMAKE = """\
# Minimal Catch.cmake — injected by the backport-cpp recipe (see conanfile.py).
# Upstream test/CMakeLists.txt calls include(Catch) + catch_discover_tests(<target>).
# The ohpcd catch2/2.13.10 package ships headers only, so this stub registers the
# whole Catch2 test executable as one CTest case (running it executes every
# TEST_CASE registered in the binary).
function(catch_discover_tests TARGET)
    add_test(NAME ${TARGET} COMMAND ${TARGET} --durations yes)
endfunction()
"""


class BackportCppConan(ConanFile):
    name = "backport-cpp"
    version = "1.2.0"
    description = ("Modern C++ utilities (optional, variant, string_view, span, any, "
                   "tuple, functional, ...) backported to C++11 — header-only library")
    license = "MIT"
    homepage = "https://github.com/bitwizeshift/BackportCpp"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/tree/main/archives/b/backport-cpp/1.2.0"
    topics = ("backport", "header-only", "cpp11", "optional", "variant", "string_view")
    package_type = "header-library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"run_upstream_tests": [True, False]}
    default_options = {"run_upstream_tests": True}

    # CMakeDeps 提供 build() 里 find_package(Catch2)；CMakeToolchain 在 generate() 里定制
    generators = "CMakeDeps"

    def requirements(self):
        # 上游单测用 Catch2 2.x（test/CMakeLists.txt: find_package(Catch2 REQUIRED)）。
        # 仅在「能本机运行测试」且未显式关掉上游测试时引入；包本身 header-only 零依赖。
        if self.options.run_upstream_tests and can_run(self):
            self.requires("catch2/2.13.10")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.user_presets_path = False
        if self.options.run_upstream_tests and can_run(self):
            tc.cache_variables["BACKPORT_COMPILE_UNIT_TESTS"] = True
            # 上游 AddSelfContainmentTest.cmake 自带 cmake_minimum_required(3.1)，
            # CMake 4.x 默认拒绝 <3.5 的兼容声明。
            tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
            mod_dir = os.path.join(self.build_folder, "cmake-modules")
            os.makedirs(mod_dir, exist_ok=True)
            with open(os.path.join(mod_dir, "Catch.cmake"), "w", encoding="utf-8") as fh:
                fh.write(_CATCH_CMAKE)
            tc.cache_variables["CMAKE_MODULE_PATH"] = mod_dir
        else:
            # 纯 header-only 打包（交叉构建/显式关闭）：不编译任何东西
            tc.cache_variables["BACKPORT_COMPILE_UNIT_TESTS"] = False
            tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if self.options.run_upstream_tests and can_run(self):
            # ① 直跑上游 Catch2 测试可执行：--durations yes 让每个用例名与耗时、
            #    结尾的用例/断言汇总行完整落进日志（上游测试 N/N′ 对账的原始证据）
            test_bin = os.path.join(self.build_folder, "test", "Backport.test")
            self.run('"%s" --durations yes' % test_bin)
            # ② 再经 ctest 走一遍上游注册面（catch_discover_tests 注入实现）
            cmake.test()

    def package(self):
        copy(self, "*.hpp",
             src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        self.info.clear()

    def package_info(self):
        # 与上游导出名一致（cmake/templates/PackageConfig.cmake.in → Backport::Backport）
        self.cpp_info.set_property("cmake_file_name", "Backport")
        self.cpp_info.set_property("cmake_target_name", "Backport::Backport")
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
