#!/usr/bin/env python3
"""Conan recipe for tiny-dnn 1.0.0a3 (tiny-dnn/tiny-dnn) on OpenHarmony PC.

tiny-dnn 是 header-only 的 C++11 深度学习库（CNN/MLP/RNN 组件、量化推理、
JSON/Binary 序列化）。上游 CMakeLists 里 `add_library(tiny_dnn INTERFACE)`
—— 没有编译产物，`package_type = "header-library"`。

OHOS 适配要点：
- **头文件布局必须整棵发运**：`tiny_dnn/` 内部的 `#include` 同时使用
  `<cereal/...>`（角括号，需 include 根）与 `"third_party/..."`（相对 include
  根），而上游 CMake 的 `install(DIRECTORY .../tiny_dnn ...)` **只装
  tiny_dnn/**，cereal/ 与 third_party/ 缺失。本包把三棵目录并排装进同一个
  include 根，消费者只需一个 `-I`。
- **上游测试只有一个 gtest 可执行文件**：`test/CMakeLists.txt` 用
  DownloadProject 在 **configure 期从 GitHub 拉 googletest（GIT_TAG master）**
  —— CI worker 不可联网。本包改用 Conan 的 `gtest/1.17.0`（已发布到 ohpcd）
  编译 `test/test.cpp` + `test/test_no_duplicate_symbols.cpp` 并在 build() 内实跑。
- **C++ 标准**：上游 CMake 声明 C++11，但 gtest 1.15+ 要求 C++17，故以
  `-std=c++17` 编译（tiny-dnn 用 C++17 编译无告警之外的差异，上游源码零改动）。
- **test_image 用例依赖相对路径**：`test/testhelper.h` 的 `resolve_path()`
  依次试 `""`/`"./test/"`/`"../test/"`…，因此测试二进制必须在**含
  `test/testimage/` 的目录**（即源码根）下运行。
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, get

# build() 内实跑上游 gtest 套件的用例数下限。用于"绿但空转"防护：
# 上游 v1.0.0a3 编译进测试二进制的用例约 200 个，若因配置漂移导致
# 只跑了个位数，这里直接判失败而不是静默通过。
MIN_UPSTREAM_TESTS = 180

# 上游测试的 include 根：仓库根（test.cpp 写 "tiny_dnn/tiny_dnn.h"）
_TEST_SOURCES = ("test.cpp", "test_no_duplicate_symbols.cpp")


class TinyDNNConan(ConanFile):
    name = "tiny-dnn"
    version = "1.0.0a3"
    description = "Header-only C++11 deep learning library (CNN/MLP/RNN, quantization, serialization)"
    license = "BSD-2-Clause"
    homepage = "https://github.com/tiny-dnn/tiny-dnn"
    url = ""  # CI fills this
    topics = ("deep-learning", "neural-network", "header-only", "cnn")

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        # 上游测试用 gtest（test/CMakeLists.txt 的 DownloadProject 在 configure
        # 期联网拉 googletest master，CI worker 上不可用）。这里改用已在 ohpcd
        # 发布的 gtest/1.17.0；gmock 未被任何用例使用，故不链接。
        self.test_requires("gtest/1.17.0#ab1bc3bf51522490eef07a83c2dbd203")

    def package_id(self):
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    # -- build ---------------------------------------------------------------

    def _parse_gtest_summary(self, text):
        """从 gtest 输出解析 (ran, passed, failed)。"""
        ran = re.search(r"^\[=+\]\s*(\d+)\s+tests? from\s+\d+\s+test suites? ran", text, re.M)
        passed = re.search(r"^\[\s+PASSED\s+\]\s*(\d+)\s+tests?", text, re.M)
        failed = re.search(r"^\[\s+FAILED\s+\]\s*(\d+)\s+tests?", text, re.M)
        # gtest 仅在失败数 > 0 时才打印 `[  FAILED  ] N tests, listed below:` 汇总行；
        # 全绿时该行不存在 —— 缺行即零失败，不能当解析失败（-1）。真正的失败
        # 仍由 ran/passed 不等或非零退出码兜住。
        return (
            int(ran.group(1)) if ran else -1,
            int(passed.group(1)) if passed else -1,
            int(failed.group(1)) if failed else 0,
        )

    def build(self):
        src = self.source_folder
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cxx = compilers.get("cpp", "clang++")

        gt = self.dependencies["gtest"].cpp_info
        gt_inc = " ".join('-I"{}"'.format(p) for p in gt.includedirs)
        gt_lib = gt.libdirs[0]

        test_dir = os.path.join(src, "test")
        exe = os.path.join(self.build_folder, "tiny_dnn_test")

        # -Wno-unused-value：上游 test/test_serialization.h:430 的
        # `s1 << (f2, f3) << c4;` 是逗号运算符笔误，gtest 头与之无关；
        # 只压这一条默认开启的告警，不改上游源码。
        sources = " ".join('"{}"'.format(os.path.join(test_dir, s)) for s in _TEST_SOURCES)
        self.run(
            '"{}" -std=c++17 -O1 -Wno-unused-value -I"{}" {} {} '
            '-L"{}" -lgtest -pthread -o "{}"'.format(cxx, src, gt_inc, sources, gt_lib, exe),
            cwd=self.build_folder,
        )

        # 上游 test/testhelper.h 的 resolve_path() 只认相对路径（""/"./test/"…），
        # 故 cwd 必须是含 test/testimage/ 的源码根。
        # self.run 在退出码非 0 时抛异常 —— gtest 有 FAILED 用例即返回 1。
        log = os.path.join(self.build_folder, "gtest.log")
        self.run('"{}" > "{}" 2>&1'.format(exe, log), cwd=src)

        with open(log, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        ran, passed, failed = self._parse_gtest_summary(text)
        if ran < 0 or passed < 0:
            raise ConanException(
                "gtest summary line not found — the suite did not run:\n" + text[-2000:]
            )
        if failed != 0 or passed != ran:
            raise ConanException(
                "upstream gtest suite not all green: ran={} passed={} failed={}".format(
                    ran, passed, failed
                )
            )
        if ran < MIN_UPSTREAM_TESTS:
            raise ConanException(
                "only {} upstream tests ran (expected >= {}) — test set shrank".format(
                    ran, MIN_UPSTREAM_TESTS
                )
            )
        self.output.info("upstream gtest suite: {} tests ran, all passed".format(ran))

    # -- package -------------------------------------------------------------

    def package(self):
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        # 三棵目录并排装进同一个 include 根：
        #   tiny_dnn/    —— 库本体，内部写 "tiny_dnn/..." 与 "third_party/..."
        #   cereal/      —— 序列化后端，被以 <cereal/...> 角括号包含
        #   third_party/ —— gemmlowp / stb / CLCudaAPI，被以 "third_party/..." 包含
        # 上游 CMake 只 install tiny_dnn/，另两棵缺失会导致消费者编译失败。
        include_root = os.path.join(self.package_folder, "include")
        for sub in ("tiny_dnn", "cereal", "third_party"):
            copy(
                self,
                "*",
                src=os.path.join(self.source_folder, sub),
                dst=os.path.join(include_root, sub),
            )

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.set_property("cmake_target_name", "TinyDNN::tiny_dnn")
