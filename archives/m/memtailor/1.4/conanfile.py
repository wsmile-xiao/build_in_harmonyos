#!/usr/bin/env python3
"""Conan recipe — memtailor 1.4 (Macaulay2/memtailor) on OpenHarmony PC.

memtailor 是 Macaulay2/Frobby 生态里的 C++ 专用内存分配器库：Arena（栈式/
LIFO 分配器，几何增长）与 BufferPool（固定尺寸缓冲池，free list）。C++17 +
CMake + autotools 双构建，零第三方运行时依赖（只链接 Threads）。

OHOS 适配要点（三个上游缺陷，见 patches/）：
- **上游测试链接的是 find_package(GTest) 的旧式 target 名**
  `GTest::GTest` / `GTest::Main`。Conan 的 gtest/1.17.0.1 由 CMakeDeps 生成
  GTestConfig.cmake，只声明 `GTest::gtest` / `GTest::gtest_main` /
  `GTest::gmock` / `GTest::gmock_main` —— configure 期 target not found。
  patch 0002 换成 Conan 的现代 target 名（同 archives/b/biosoup/0.10.0）。
- **上游 `include(CTest)`（= `enable_testing()`）写在 `src/CMakeLists.txt`
  这个子目录里**。CMake 只在 `enable_testing()` 被调用的那个目录及其子目录
  生成 `CTestTestfile.cmake`，于是 `<build>/src/CTestTestfile.cmake` 存在、
  顶层 build 目录没有。结果：在 build 根目录跑 `ctest` 得到
  `No tests were found!!!`，**退出码是 0** —— 测试一个没跑却全绿。
  patch 0001 把 `include(CTest)` 提到顶层 CMakeLists.txt。
- **上游 `install(TARGETS memtailor LIBRARY DESTINATION lib)` 只声明了
  LIBRARY**：静态库落在 ARCHIVE 类别，根本不会被安装；同时 `memtailor.h`
  （伞头文件）只挂在 `PUBLIC_HEADER` 属性上，没有 `PUBLIC_HEADER DESTINATION`
  也不会被安装 —— 消费者 `#include <memtailor.h>` 直接 file not found。
  patch 0001 一并补齐。

上游测试：`src/test/` 三个 TU（ArenaTest 12 / BufferPoolTest 6 /
MemoryBlocksTest 4）共 **22 个 TEST 用例**，无任何 `#ifdef` 门控，
aarch64/OHOS 上全部注册并实跑。
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

# build() 内实跑的上游 ctest 用例数。用于"绿但空转"防护：ctest 在
# 一个用例都没注册时输出 "No tests were found!!!" 且**退出码为 0**，
# 只看退出码会把"零执行"当成通过。
CTEST_EXPECTED_TESTS = 22

# ctest 汇总行：`100% tests passed, 0 tests failed out of 22`
_CTEST_SUMMARY = re.compile(r"(\d+)% tests passed, (\d+) tests failed out of (\d+)")


class MemtailorConan(ConanFile):
    name = "memtailor"
    version = "1.4"
    description = "C++ special-purpose memory allocators (arena allocator + fixed-size buffer pool)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/Macaulay2/memtailor"
    url = ""  # CI fills this
    topics = ("memory", "allocator", "arena", "memory-pool", "frobby", "macaulay2")

    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def requirements(self):
        # 上游 BUILD_TESTING 走 find_package(GTest)，找不到时退回
        # FetchContent 在 configure 期 git clone googletest v1.16.0
        # （CI worker 不可联网）。这里用 ohpcd 已发布的 gtest/1.17.0.1：
        # 它的 CMakeDeps 配置声明 GTest::gtest / GTest::gtest_main 等现代
        # target 名（1.17.0 是扁平 gtest::gtest 布局，缺 gtest_main 组件）。
        self.test_requires("gtest/1.17.0.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # 上游在 src/CMakeLists.txt 里用 if(BUILD_TESTING) 门控测试目标，
        # 该 option 由 include(CTest) 提供（默认 ON）；这里显式钉住。
        tc.cache_variables["BUILD_TESTING"] = "ON"
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        # ── 层1：上游 gtest 套件（22 用例 / 3 个 suite）全量实跑 ──────────
        # cwd 必须是 build 根目录：patch 0001 把 enable_testing() 提到顶层后，
        # CTestTestfile.cmake 才会生成在这里（上游写在 src/ 子目录里，
        # 在此处跑 ctest 只会得到 "No tests were found!!!" 且退出码 0）。
        log = os.path.join(self.build_folder, "ctest.log")
        # 末尾 `|| true` 是为了把 ctest 的原文读回来再判 —— 有用例失败时
        # ctest 返回非 0，self.run 会先抛异常而丢掉日志。
        self.run(
            'ctest --output-on-failure > "{}" 2>&1 || true'.format(log),
            cwd=self.build_folder,
        )
        with open(log, encoding="utf-8", errors="replace") as fh:
            text = fh.read()

        if "No tests were found" in text:
            raise ConanException(
                "ctest registered 0 tests (enable_testing() 未被上层目录调用)"
                " —— 零执行不能算通过。\n" + text[-2000:]
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
                "only {} upstream tests were registered (expected >= {}) — test set shrank"
                "\n".format(total, CTEST_EXPECTED_TESTS) + text[-2000:]
            )
        self.output.info(
            "upstream ctest suite: {} tests registered, all passed".format(total)
        )

    def package(self):
        # Conan 2 的 copy() 没有 rename= 参数（旧写法）。先复制上游 license.txt，
        # 再就地改名成 Conan 惯例的 LICENSE。
        licenses = os.path.join(self.package_folder, "licenses")
        copy(self, "license.txt", src=self.source_folder, dst=licenses)
        os.replace(
            os.path.join(licenses, "license.txt"),
            os.path.join(licenses, "LICENSE"),
        )
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["memtailor"]
        self.cpp_info.includedirs = ["include"]
