#!/usr/bin/env python3
"""Conan recipe — limonp 1.0.2 (yanyiwu/limonp) on OpenHarmony PC.

limonp 是 cppjieba 作者 yanyiwu 抽出来的 C++ 基础设施头文件库（MIT）：字符串
工具（Split/Join/StringFormat/Trim/Utf8<->Unicode/GBK<->Unicode）、Logging
（XLOG/XCHECK）、Config（key=value 配置解析）、LocalVector（栈上内联缓冲的
小向量）、Closure（函数/成员函数绑定）、ArgvContext（命令行解析）、Colors。
纯 header-only：上游 `add_library(limonp INTERFACE)`，运行时零依赖。

OHOS 适配要点（两个上游缺陷，见 patches/）：
- **上游 unit test 的 CMake 在 configure 期联网**：`test/unittest/CMakeLists.txt`
  用 `FetchContent_Declare(googletest GIT_REPOSITORY ... GIT_TAG release-1.12.1)`
  + `FetchContent_MakeAvailable(googletest)`，在 configure 期 git clone
  googletest。CI worker 不可联网。patch 0002 换成 `find_package(GTest REQUIRED)`
  + `GTest::gtest`（Conan 的 gtest/1.17.0.1 由 CMakeDeps 生成 GTestConfig.cmake）。
  注意 `test.run` 自己带了 main（`test/unittest/gtest_main.cpp`），所以只链
  `GTest::gtest`，**不能**链 `GTest::gtest_main`（会 duplicate main）。
- **上游测试的 fixture 路径只在"build 目录恰好是源码根的直接子目录"时成立**：
  `TConfig.cpp` / `TStdExtension.cpp` / `TStringUtil.cpp` 用相对路径
  `"../test/testdata/..."` 打开 fixture，而上游 `ADD_TEST(... COMMAND
  ./test/demo)` 用相对路径 + 默认 WORKING_DIRECTORY（= build 目录）。上游 CI
  里 build 就是 `<repo>/build`，`<build>/../test/testdata` 正好命中源码里的
  fixture —— 但在 Conan 里 build 目录在本地缓存里、与 source 目录是兄弟节点，
  于是 4 个用 fixture 的用例（TConfig.Test1 / TStdExtension.Test1 /
  TStringUtil.Test2 / TStringUtil.Test3）会因为 fixture 打不开而失败
  （本地实跑复现：`50% tests passed, 1 tests failed out of 2`）。
  patch 0001 给两个 ADD_TEST 补上
  `WORKING_DIRECTORY ${PROJECT_SOURCE_DIR}/test` 并把 COMMAND 换成
  `$<TARGET_FILE:...>`（只有 cwd 是源码根的直接子目录时 `../test/testdata`
  才解析得到），这样任何 out-of-tree 构建目录都能跑。

上游测试：`ADD_TEST(./test/demo)` + `ADD_TEST(./test/test.run)` 共 2 个 ctest
用例；其中 `test.run` 由 `test/unittest/*.cpp` 里的 **25 个 gtest TEST 宏**
（`TCastFloat.cpp` 没有被 ADD_EXECUTABLE 收录）组成，aarch64/OHOS 上全部注册、
全部执行。
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)

# 上游在顶层 CMakeLists.txt 注册的 ctest 用例数：
#   ADD_TEST(NAME ./test/demo COMMAND ...) + ADD_TEST(NAME ./test/test.run ...)
CTEST_EXPECTED_TESTS = 2

# test.run 里实跑的 gtest 用例数。test/unittest/*.cpp 合计 26 个 TEST 宏，
# 其中 TCastFloat.cpp 没有被 ADD_EXECUTABLE(test.run ...) 收录，
# 因此注册并执行的是 25 个。
GTEST_EXPECTED_TESTS = 25

# ctest 汇总行：`100% tests passed, 0 tests failed out of 2`
_CTEST_SUMMARY = re.compile(r"(\d+)% tests passed, (\d+) tests failed out of (\d+)")
# gtest 汇总行：`[  PASSED  ] 25 tests.`
_GTEST_PASSED = re.compile(r"\[\s+PASSED\s+\]\s+(\d+)\s+tests?\.")


class LimonpConan(ConanFile):
    name = "limonp"
    version = "1.0.2"
    description = "Header-only C++ utility library (string utils, logging, config, LocalVector, Closure, ArgvContext)"
    license = "MIT"
    homepage = "https://github.com/yanyiwu/limonp"
    url = ""  # CI fills this
    topics = ("header-only", "string-util", "logging", "utf8", "gbk", "cppjieba", "limonp")

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 上游 unit test 走 FetchContent 在 configure 期 git clone googletest
        # release-1.12.1（CI worker 不可联网）。这里用 ohpcd 已发布的
        # gtest/1.17.0.1：它的 CMakeDeps 配置声明 GTest::gtest /
        # GTest::gtest_main 等现代 target 名（1.17.0 是扁平 gtest::gtest
        # 布局，缺 gtest_main 组件）。
        self.test_requires("gtest/1.17.0.1")

    def layout(self):
        cmake_layout(self)

    def package_id(self):
        # header-only 库：package_id 不依赖编译器/构建类型/架构
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # 上游用自定义 option ENABLE_UNIT_TESTS（默认 ON）门控 enable_testing()
        # + add_subdirectory(test)；这里显式钉住。
        tc.cache_variables["ENABLE_UNIT_TESTS"] = "ON"
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        # ── 层1：上游 ctest 套件（2 个 ctest 用例，含 25 个 gtest 用例）实跑 ──
        # cwd 必须是 build 根目录（CTestTestfile.cmake 在这里）。`-V` 是必需
        # 的：test.run 的 gtest 汇总行只在**测试**的输出里，而
        # --output-on-failure 会把通过用例的输出吃掉，于是"25 个用例"这条
        # 信息就没了 —— 只看 ctest 的 2/2 无法发现 gtest 用例集缩水。
        log = os.path.join(self.build_folder, "ctest.log")
        # 末尾 `|| true` 是为了把 ctest 的原文读回来再判 —— 有用例失败时
        # ctest 返回非 0，self.run 会先抛异常而丢掉日志。
        self.run(
            'ctest -V > "{}" 2>&1 || true'.format(log),
            cwd=self.build_folder,
        )
        with open(log, encoding="utf-8", errors="replace") as fh:
            text = fh.read()

        if "No tests were found" in text:
            raise ConanException(
                "ctest registered 0 tests —— 零执行不能算通过。\n" + text[-2000:]
            )
        m = _CTEST_SUMMARY.search(text)
        if m is None:
            raise ConanException(
                "ctest summary line not found — the suite did not run:\n" + text[-2000:]
            )
        failed, total = int(m.group(2)), int(m.group(3))
        if failed != 0:
            raise ConanException(
                "upstream ctest not all green: {} failed out of {}\n".format(failed, total)
                + text[-4000:]
            )
        if total < CTEST_EXPECTED_TESTS:
            raise ConanException(
                "only {} ctest cases were registered (expected >= {}) — test set shrank"
                "\n".format(total, CTEST_EXPECTED_TESTS) + text[-2000:]
            )

        # gtest 层：test.run 内部的逐用例账。ctest 只把整个二进制当成 1 个
        # 用例，所以必须解析 gtest 自己的汇总行才能确认 25 个 TEST 宏全都
        # 注册并执行了。
        if re.search(r"\[\s+FAILED\s+\]", text):
            raise ConanException(
                "gtest reported FAILED cases inside test.run:\n" + text[-4000:]
            )
        g = _GTEST_PASSED.search(text)
        if g is None:
            raise ConanException(
                "gtest summary line '[  PASSED  ] N tests.' not found — "
                "test.run did not run to completion:\n" + text[-4000:]
            )
        gtest_total = int(g.group(1))
        if gtest_total < GTEST_EXPECTED_TESTS:
            raise ConanException(
                "only {} gtest cases ran (expected >= {}) — test set shrank\n".format(
                    gtest_total, GTEST_EXPECTED_TESTS
                )
                + text[-2000:]
            )
        self.output.info(
            "upstream ctest: {} cases registered, {} gtest cases ran, all passed".format(
                total, gtest_total
            )
        )

    def package(self):
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "limonp")
        self.cpp_info.set_property("cmake_target_name", "limonp::limonp")
