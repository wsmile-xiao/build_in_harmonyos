#!/usr/bin/env python3
"""Conan recipe — observable_unique_ptr 0.7.3（header-only C++17 观察者智能指针）.

observable_unique_ptr（上游导出 CMake 目标 `oup::oup`，单头文件
`include/oup/observable_unique_ptr.hpp`）提供 unique-ownership 语义、可被
`observer_ptr` 观察生命周期的智能指针（observable_unique_ptr / observable_sealed_ptr）。

交付形态：
- package_type="header-library"，package() 只交付 include/ 树与 LICENSE，无编译产物；
- 源码零改动、零补丁（patches: []），上游 14 个 tag 中的 v0.7.3 归档；
- 配方 requires() = 0（软件本体 0 依赖，stdlib-only）。

上游测试面（rule4/R51，全部在 build() 内真实执行）：
- 12 个编译期用例：tests/CMakeLists.txt 的 run_compile_test(...)，configure 阶段以
  try_compile 判定，通过打 `Test <name> passed.`、失败打 `FAILED test:`（失败不改
  configure 退出码，故本配方在 build() 内显式判定并计数，防静默假绿）；
- 4253 个运行期用例 / 30587 条断言：snitch 注册口径，170 个 TEMPLATE_LIST_TEST_CASE
  × owner_types 25 个类型 + 3 个 TEST_CASE，由 snitch 自报
  `all tests passed (4253 test cases, 30587 assertions)`；
- 测试框架 snitch v1.3.2 上游走 FetchContent git clone（CI worker git 协议不通），
  本配方在 source() 随 conandata 第二源预置到 _deps/snitch-src +
  FETCHCONTENT_SOURCE_DIR_SNITCH 指向本地（libassert-cpp 先例），构建期零网络。
"""
import io
import json
import os
import re

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get

# 上游 tests/CMakeLists.txt 的 run_compile_test(...) 调用数（12）。
EXPECTED_COMPILE_TESTS = 12
# snitch 注册口径：170 TEMPLATE_LIST_TEST_CASE × 25 类型 + 3 TEST_CASE。
EXPECTED_RUNTIME_CASES = 4253
EXPECTED_RUNTIME_ASSERTIONS = 30587


class ObservableUniquePtrConan(ConanFile):
    name = "observable_unique_ptr"
    version = "0.7.3"
    description = "Unique-ownership smart pointers with observable lifetime (header-only, oup::)"
    license = "MIT"
    homepage = "https://github.com/cschreib/observable_unique_ptr"
    url = "https://github.com/cschreib/observable_unique_ptr"
    topics = ("memory", "smart-pointer", "observer", "header-only")
    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"run_upstream_tests": [True, False]}
    default_options = {"run_upstream_tests": True}

    # header-only：源码只读，build()/package() 直接从 source_folder 读取
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32：平台判断用 in，不用 ==
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.name} is validated for Linux/OHOS, not {self.settings.os}"
            )

    def package_id(self):
        # header-only：所有配置同一份包内容
        self.info.clear()

    def layout(self):
        cmake_layout(self)

    def source(self):
        # 主源：官方 tag 归档（zip，URL/sha256 与 conan-center-index 同条目一致）
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)
        # 测试框架 snitch v1.3.2（上游 FetchContent 固定版本）：预置到 _deps/snitch-src，
        # 由 generate() 的 FETCHCONTENT_SOURCE_DIR_SNITCH 指向，构建期不发起任何下载。
        snitch = dict(self.conan_data["snitch"])
        get(
            self,
            **snitch,
            strip_root=True,
            destination=os.path.join(self.source_folder, "_deps", "snitch-src"),
        )

    def generate(self):
        tc = CMakeToolchain(self)
        # 打开上游测试面（tests/CMakeLists.txt：snitch 运行期套件 + 12 个编译期用例）
        tc.variables["OUP_DO_TEST"] = True
        # FetchContent 用本地预置的 snitch 源，不做网络访问
        tc.variables["FETCHCONTENT_SOURCE_DIR_SNITCH"] = os.path.join(
            self.source_folder, "_deps", "snitch-src"
        ).replace("\\", "/")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        if not self.options.run_upstream_tests:
            self.output.info("run_upstream_tests=False: 上游测试按选项跳过")
            return
        if not can_run(self):
            self.output.info("Cross-building: 上游测试在构建期跳过（can_run=False）")
            return

        cmake = CMake(self)

        # ── configure：上游 12 个编译期用例在此阶段以 try_compile 判定 ──
        # 结果只以 message()/WARNING 打印、不改变 configure 退出码，故捕获输出显式判定，
        # 计数不符或出现 FAILED 一律 fail（反静默：不允许 0 条判据被当成通过）。
        cfg_buf = io.StringIO()
        try:
            cmake.configure(stdout=cfg_buf, stderr=cfg_buf)
        except Exception:
            self.output.info("cmake configure 输出（尾部）:\n" + cfg_buf.getvalue()[-6000:])
            raise
        cfg_out = cfg_buf.getvalue()
        passed = [
            line.strip()
            for line in cfg_out.splitlines()
            if "Test " in line and line.strip().endswith("passed.")
        ]
        failed = [line.strip() for line in cfg_out.splitlines() if "FAILED test:" in line]
        for line in passed:
            self.output.info("COMPILE_TEST_PASS " + line)
        for line in failed:
            self.output.error("COMPILE_TEST_FAIL " + line)
        if failed or len(passed) != EXPECTED_COMPILE_TESTS:
            raise ConanException(
                "上游编译期用例判定失败: passed={} failed={} expected={}".format(
                    len(passed), len(failed), EXPECTED_COMPILE_TESTS
                )
            )
        self.output.info(
            "upstream compile-time tests: {}/{} passed".format(
                len(passed), EXPECTED_COMPILE_TESTS
            )
        )

        # ── build：只编译运行期测试可执行（benchmarks 属 EXCLUDE 之外的目标，不参与）──
        cmake.build(target="oup_runtime_tests")

        # ── run：snitch 自报用例数与断言数，逐字解析后落机器可读 marker ──
        exe = os.path.join(self.build_folder, "tests", "oup_runtime_tests")
        if not os.path.isfile(exe):
            raise ConanException(f"upstream test binary missing: {exe}")
        run_buf = io.StringIO()
        try:
            self.run(f'"{exe}"', env="conanbuild", stdout=run_buf, stderr=run_buf)
        except Exception:
            self.output.info("上游运行期测试输出（尾部）:\n" + run_buf.getvalue()[-6000:])
            raise
        run_out = run_buf.getvalue()
        summary = [
            line.strip() for line in run_out.splitlines() if "test cases" in line
        ]
        for line in summary:
            self.output.info("UPSTREAM_RUNTIME_SUMMARY " + line)
        match = re.search(
            r"(all tests passed|tests failed) \((\d+) test cases, (\d+) assertions",
            run_out,
        )
        if not match:
            raise ConanException(
                "未在上游运行期测试输出中找到 snitch 计数摘要（可能 0 用例运行）"
            )
        status, cases, assertions = match.group(1), int(match.group(2)), int(match.group(3))
        if status != "all tests passed":
            raise ConanException(f"上游运行期测试未全通过: {status}")
        if cases != EXPECTED_RUNTIME_CASES or assertions != EXPECTED_RUNTIME_ASSERTIONS:
            raise ConanException(
                "上游运行期计数与申报口径不符: cases={} (期望 {}), assertions={} (期望 {})".format(
                    cases, EXPECTED_RUNTIME_CASES, assertions, EXPECTED_RUNTIME_ASSERTIONS
                )
            )
        marker = {
            "status": "passed",
            "framework": "snitch v1.3.2",
            "command": "tests/oup_runtime_tests",
            "discovered": cases,
            "executed": cases,
            "passed": cases,
            "failed": 0,
            "assertions": assertions,
            "compile_time_cases": len(passed),
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False))

    def package(self):
        # header-only：把上游 include 树与许可证原样交付
        copy(
            self,
            pattern="*",
            src=os.path.join(self.source_folder, "include"),
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            pattern="LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
        # 与上游 CMake 导出目标一致（conan-center-index recipes/observable_unique_ptr 同值）：
        # find_package(oup) + oup::oup
        self.cpp_info.set_property("cmake_file_name", "oup")
        self.cpp_info.set_property("cmake_target_name", "oup::oup")
        self.cpp_info.set_property("pkg_config_name", "oup")
