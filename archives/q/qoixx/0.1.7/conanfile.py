#!/usr/bin/env python3
"""Conan recipe — qoixx 0.1.7 (header-only, 上游裸 Makefile 构建面).

qoixx（上游见 homepage）是 QOI（Quite OK Image Format）的单头 C++20 编解码实现：
交付物只有 include/qoixx.hpp（54335 字节），**0 conan 依赖**
（W0：ci/scripts/preflight_check.sh qoixx/0.1.7 预检通过；上游无 find_package，
doctest/stb/qoi 三个 git 子模块只服务上游测试与上游基准/转换工具）。

上游测试面（R51 上游测试三步法；N 候选数法与逐项归因见 test_package/MANIFEST.yml）：
  * 入口：上游 Makefile 的 `make test` → bin/test（src/test.cpp + doctest 子模块头）。
  * N（候选最大值）= 38 = doctest 运行期断言数；源码宏 2 / 框架注册 test case 2 /
    SUBCASE 16 / 源码断言语句 24 均 ≤ 38，差额逐项归因写在 MANIFEST.yml。
  * build() 内实跑并做**反假绿硬断言**：输出必须同时命中 `test cases:  2 |  2 passed`
    与 `assertions: 38 | 38 passed`（§二.22「All 0 tests passed」是判绿禁用词），
    任一不符 ⇒ conan create 直接失败，不靠 rc 单判。

平台适配点（0 补丁，不改上游任何源文件）：
  1. **有 SIMD 快路径**：qoixx.hpp 的 arm_sve.h / arm_neon.h / immintrin.h 全是
     `#if defined(__ARM_FEATURE_SVE / __ARM_NEON / __AVX2__)` 条件 include，本平台
     aarch64 上 `__ARM_NEON` 默认定义 ⇒ NEON 快路径进入构建面（探针实测）。设备实测
     NEON 快路径下上游 38/38 断言全过 ⇒ **不加** QOIXX_NO_SIMD（README 提供该宏作为
     架构可移植性开关，本平台不需要，交付头保持上游默认行为）。
  2. **std::ranges 需要 -fexperimental-library**：OHOS libc++ 15.0.4 上
     `std::ranges::copy` / `std::ranges::subrange` 默认不可用（探针：不加该旗标报
     `no member named 'copy' in namespace 'std::ranges'`；加了 rc=0）。上游测试与
     上游工具都用到 ranges —— 用编译旗标解决，不 patch 上游测试源。
  3. 构建面只跑上游测试目标 `bin/test`：CXXFLAGS 覆盖上游 Makefile 默认值，
     去掉 `-march=native -mtune=native`（设备与 CI worker CPU 不同；且 NEON 快路径
     是 aarch64 基线特性，不依赖该旗标）。
  4. 上游另两个目标 bin/qoibench（基准工具，加同一旗标后可编译）与 bin/qoiconv
     （转换工具，clang 15 对 `overloaded` 推导指引判 no matching constructor，
     上游 CI 用 clang-17 故看不到）**都不是交付物**，本包不打包、不进 commands.json。
"""
import os
import re
import shlex

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rmdir,
)
from conan.tools.layout import basic_layout


class QoixxConan(ConanFile):
    name = "qoixx"
    version = "0.1.7"
    description = "Single-header QOI (Quite OK Image Format) codec written in C++20"
    license = "MIT"
    homepage = "https://github.com/wx257osn2/qoixx"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("qoi", "image-codec", "simd", "header-only")

    package_type = "header-library"
    implements = ["auto_header_only_mode"]

    settings = "os", "compiler", "build_type", "arch"

    # header-only：源码只读，build()/package() 直接从 source_folder 读取
    no_copy_source = True

    # 上游 doctest 套件的期望计数（反假绿硬断言，取数命令见 test_package/MANIFEST.yml）
    EXPECTED_TEST_CASES = 2
    EXPECTED_ASSERTIONS = 38

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # W0-2 实查：0 conan 依赖（preflight_check 预检通过；上游无 find_package，
        # doctest 头按官方 tag 进 conandata 预下载，不进依赖链）
        pass

    def layout(self):
        basic_layout(self)

    # ── 源码获取（全部走 conandata.yml ⇒ CI 的 mirror fallback + pre-download 生效）──
    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

        # 上游 .gitmodules 的 doctest 子模块（tag 归档不含子模块内容，
        # .dependencies/doctest 解包后是空目录）→ 先移除空占位再解到 Makefile
        # 期望的路径（DOCTEST=-I .dependencies/doctest/doctest）。
        doctest_dir = os.path.join(self.source_folder, ".dependencies", "doctest")
        if os.path.isdir(doctest_dir):
            rmdir(self, doctest_dir)
        get(self, **self.conan_data["doctest_sources"],
            destination=doctest_dir, strip_root=True)
        doctest_h = os.path.join(doctest_dir, "doctest", "doctest.h")
        if not os.path.isfile(doctest_h):
            raise Exception(f"doctest.h 未落到预期路径: {doctest_h}")
        self.output.info(f"[source] doctest 头就位: {doctest_h}")

    # ── 上游测试集成（层 1 必做：conan create 内实跑上游 doctest 套件）────────
    def build(self):
        apply_conandata_patches(self)  # patches 为空（本包 0 补丁），G1 门禁要求该调用面

        if not can_run(self):
            self.output.info("交叉构建（can_run=False）：跳过上游 doctest 套件")
            return

        # R33：编译器从 Conan conf 取 dict 再索引，绝不用 ${CXX}（worker 上为空）
        comp = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = comp.get("cpp", "clang++")
        # -fexperimental-library：OHOS libc++ 15.0.4 的 std::ranges::copy 需要它
        # （上游测试 src/test.cpp 用到）；去掉上游的 -march=native（见文件头适配点 3）
        cxxflags = "-std=c++2a -O2 -Wall -Wextra -pedantic-errors -fexperimental-library"

        # 上游测试在沙箱 HOME 下执行（device-facts §一.11：不写用户真实 HOME）
        sandbox = os.path.join(self.build_folder, "test-home")
        os.makedirs(sandbox, exist_ok=True)
        old_home = os.environ.get("HOME")
        os.environ["HOME"] = sandbox
        log_path = os.path.join(self.build_folder, "upstream-doctest.log")
        try:
            # R9：make -j1；先删旧产物（防改旗标后 make 判 up-to-date 的假绿）
            self.run("make clean", cwd=self.source_folder)
            self.run(
                f"make -j1 CXX={shlex.quote(cxx)} CXXFLAGS={shlex.quote(cxxflags)} bin/test",
                cwd=self.source_folder,
            )
            # 落盘 + 回显 + 透传真实退出码（输出同时进 conan create 日志与本地日志供断言）
            self.run(
                f"./bin/test > {shlex.quote(log_path)} 2>&1; rc=$?; "
                f"cat {shlex.quote(log_path)}; exit $rc",
                cwd=self.source_folder,
            )
        finally:
            if old_home is None:
                os.environ.pop("HOME", None)
            else:
                os.environ["HOME"] = old_home

        with open(log_path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        problems = []
        if not re.search(rf"test cases:\s+{self.EXPECTED_TEST_CASES}\s+\|\s+"
                         rf"{self.EXPECTED_TEST_CASES} passed", text):
            problems.append(f"test cases 行不符（期望 {self.EXPECTED_TEST_CASES} 全过）")
        if not re.search(rf"assertions:\s+{self.EXPECTED_ASSERTIONS}\s+\|\s+"
                         rf"{self.EXPECTED_ASSERTIONS} passed", text):
            problems.append(f"assertions 行不符（期望 {self.EXPECTED_ASSERTIONS} 全过）")
        if "All 0 tests" in text:
            problems.append("命中 'All 0 tests'（0 用例假绿判据）")
        if problems:
            raise Exception("上游 doctest 套件计数断言失败："
                            + "；".join(problems) + "\n" + text[-2000:])
        self.output.info(
            f"[upstream-tests] doctest {self.EXPECTED_TEST_CASES} test cases / "
            f"{self.EXPECTED_ASSERTIONS} assertions 全过（沙箱 HOME 实跑）")

    def package(self):
        copy(self, "qoixx.hpp",
             src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # 上游 LICENSES/ 覆盖 QOI 格式规范与 stb 的再分发条款（qoi.LICENSE /
        # stb.LICENSE）；doctest 只用于上游测试、不随包交付，其许可证一并附上
        copy(self, "*.LICENSE",
             src=os.path.join(self.source_folder, "LICENSES"),
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "qoixx")
        self.cpp_info.set_property("cmake_target_name", "qoixx::qoixx")
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
