#!/usr/bin/env python3
"""Conan recipe for jinja2cpp 0.9 — Jinja2 模板引擎的 C++ 实现（静态库）。

jinja2cpp 0.9 上游结构：
- CMake 构建（cmake_minimum_required 3.0，已在补丁中现代化为 3.5...4.1）
- 库本体 libjinja2cpp.a（header-only 依赖：expected-lite vendored + boost headers）
- 上游 test/ 为 gtest 参数化测试套（jinja2cpp_tests 单目标，78 个注册用例，
  其中 8 个 perf 用例上游默认 DISABLED）

依赖说明：
- boost（W0 核实制品仓 boost/1.85.0 已发布，静态包实测可装）：上游
  target_link_libraries 仅链接 Boost::boost（头文件目标），运行时无 boost 符号；
  上游测试额外链接 boost_filesystem/system。
- expected-lite：上游 vendored（thirdparty/nonstd/expected-light 子模块），
  tarball 不含子模块内容；source() 按上游 .gitmodules 指针从官方源补齐
  expected-lite 0.9.0 头文件（conandata.yml expected_lite 条目），
  符合"vendored 优先用上游自带"原则。
- gtest（仅上游测试需要）：制品仓 gtest/1.17.0 已发布（W0 核实）。

适配补丁（详见 notes.md）：
- 0001: CMake 现代化 + HarmonyOS 非 UNIX 误判修复 + conan Boost target 命名空间
        + unique 过滤器 stable_sort 确定性修复 + gtest 集成改造
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class Jinja2CppConan(ConanFile):
    name = "jinja2cpp"
    version = "0.9"
    description = "Jinja2 template engine implementation in C++ (0.9)"
    license = "MIT"
    homepage = "https://github.com/jinja2cpp/Jinja2Cpp"
    url = "https://github.com/jinja2cpp/Jinja2Cpp"
    topics = ("jinja2", "template-engine", "template")

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "with_tests": [True, False],
    }
    default_options = {
        "with_tests": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 上游 target_link_libraries(jinja2cpp PUBLIC boost::boost)——仅头文件依赖；
        # boost/1.85.0 已在制品仓发布（W0 conan download 实测）
        self.requires("boost/1.85.0")
        if self.options.with_tests:
            # 上游测试套链接 gtest + gtest_main（host context，CMakeDeps 生成
            # gtest-config.cmake；gtest/1.17.0 已发布，W0 核实）
            self.requires("gtest/1.17.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # 上游 v0.9 tarball 不含 .gitmodules 子模块内容（thirdparty/nonstd/
        # expected-light 为空目录），而库本体与公共头依赖 <nonstd/expected.hpp>。
        # 按上游 .gitmodules 指针对应版本（expected-lite v0.9.0）从官方源补齐
        # vendored 头文件，与上游 thirdparty/nonstd/CMakeLists.txt 的 INTERFACE
        # include 路径对齐。
        import os
        from conan.tools.files import copy
        exp_src = self.folders.base_source
        exp_dir = os.path.join(exp_src, "expected-lite-0.9.0")
        if not os.path.isdir(exp_dir):
            get(self, **self.conan_data["expected_lite"], destination=exp_src)
        copy(self, "expected.hpp",
             src=os.path.join(exp_dir, "include", "nonstd"),
             dst=os.path.join(exp_src, "thirdparty", "nonstd", "expected-light", "include", "nonstd"))

    def generate(self):
        tc = CMakeToolchain(self)
        # 上游 CMAKE_CXX_STANDARD=14；gtest 1.17 要求 C++17（测试编译期）
        if self.options.with_tests:
            tc.variables["CMAKE_CXX_STANDARD"] = 17
        else:
            tc.variables["CMAKE_CXX_STANDARD"] = 14
        tc.variables["WITH_TESTS"] = self.options.with_tests
        if self.options.with_tests:
            # 上游 GTEST_ROOT 为空时会尝试内嵌构建 vendored gtest 子模块
            #（tarball 缺失必失败）；改用 conan CMakeDeps 的 gtest
            tc.variables["JINJA2CPP_USE_CONAN_GTEST"] = True
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if self.options.with_tests:
            # 上游测试：add_test(jinja2cpp_tests jinja2cpp_tests) 注册目标；
            # GoogleTestVerification.UninstantiatedParameterizedTestSuite<LogicalExprTest>
            # 为 gtest 1.17 对上游 0.9 遗留未实例化 TEST_P（LogicalExprTest 声明后
            # 上游未 INSTANTIATE）的框架级校验，非库缺陷，排除之。
            from conan.tools.env import Environment
            env = Environment()
            sdk_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos"
            sdk_lib2 = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
            if os.path.isdir(sdk_lib):
                env.prepend_path("LD_LIBRARY_PATH", sdk_lib)
            if os.path.isdir(sdk_lib2):
                env.prepend_path("LD_LIBRARY_PATH", sdk_lib2)
            with env.vars(self).apply():
                # 上游 add_test(jinja2cpp_tests jinja2cpp_tests) 注册单测试项；
                # gtest 内部用例 GoogleTestVerification.UninstantiatedParameterized
                # TestSuite<LogicalExprTest> 为 gtest 1.17 对上游 0.9 遗留未实例化
                # TEST_P（LogicalExprTest 声明后上游未 INSTANTIATE）的框架级校验，
                # 非库缺陷——以 --gtest_filter 排除后全量运行
                self.run(
                    "./jinja2cpp_tests --gtest_filter=-GoogleTestVerification.*",
                    cwd=self.build_folder,
                )

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["jinja2cpp"]
        # 上游安装 ARCHIVE DESTINATION lib/static
        self.cpp_info.libdirs = ["lib", "lib/static"]
        self.cpp_info.includedirs = ["include"]
        # 上游公共头依赖 nonstd/expected.hpp（随包安装到 include/nonstd/）
        # 与 boost headers（通过 requires 传递）
