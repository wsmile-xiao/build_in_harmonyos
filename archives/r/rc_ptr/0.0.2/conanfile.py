#!/usr/bin/env python3
"""Conan recipe — rc_ptr 0.0.2（header-only C++17 单线程引用计数指针）.

rc_ptr（上游导出 CMake INTERFACE 目标 `rc_ptr`，头文件 `include/rc_ptr/rc_ptr.hpp`，
命名空间 `memory::`）提供单线程环境下的引用计数智能指针 `rc_ptr` / 非持有观察者
`weak_rc_ptr` / `enable_rc_from_this` 与 `make_rc` 工厂，控制块默认用 std::allocator。

交付形态：
- package_type="header-library"，package() 只交付 include/rc_ptr/ 与 LICENSE_1_0.txt，无编译产物；
- 源码零改动、零补丁（patches: {}），上游 2 个 tag 中的 v0.0.2 归档；
- 配方 requires()/tool_requires() = 0（软件本体 0 依赖，仅依赖 C++17 标准库）。

上游测试面（R51/四口径不混用，全部在 build() 内真实执行）：
- 110 个 Catch2 用例 + 305 条断言在设备实测全通过（Catch2 运行自报
  `All tests passed (305 assertions in 110 test cases)`）；
- 源码词面 TEST_CASE = 112，其中 allocator.cpp 的 2 个 pmr 用例被上游自己的
  `#if (__has_include(<memory_resource>))` 排除（OHOS SDK libc++ 无 <memory_resource>，
  探针 `HAS_MEMRES=0`、`fatal error: 'memory_resource' file not found`）⇒ NOT_RUN=2、
  申报 N=112 / N'=110，配方对两种工具链形态都做硬校验（110/305 或 112/311），其余计数一律失败；
- 测试框架 Catch2 v2.13.7 上游走 FetchContent git clone（CI worker git 协议不通），
  本配方在 source() 随 conandata 第二源预置到 _deps/catch2-src +
  FETCHCONTENT_SOURCE_DIR_CATCH2 指向本地（observable_unique_ptr/snitch 先例），构建期零网络。
"""
import io
import json
import os
import re

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run, check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get

# 源码词面 TEST_CASE 数（test/*.cpp 全量，grep -rEho 'TEST_CASE\s*\(' = 112）。
EXPECTED_SOURCE_TEST_CASES = 112
# 形态一：OHOS SDK libc++ 无 <memory_resource> ⇒ 上游 #if 排除 2 个 pmr 用例 ⇒ 注册 110；
# 形态二：若工具链提供 <memory_resource> ⇒ 112 个用例全部注册运行。
EXPECTED_RUN_CASES_NO_PMR = 110
EXPECTED_RUN_CASES_PMR = 112
# 对应断言执行数（Catch2 自报；源码断言宏 307 = 301 非 pmr + 6 pmr，
# owner_before 两处循环内 REQUIRE 各展开 3 次 ⇒ 301 + 4 = 305，pmr 全跑则 +6 = 311）。
EXPECTED_ASSERTIONS_NO_PMR = 305
EXPECTED_ASSERTIONS_PMR = 311


class RcPtrConan(ConanFile):
    name = "rc_ptr"
    version = "0.0.2"
    description = "Reference counted smart pointer for single-threaded environments (header-only, memory::)"
    license = "BSL-1.0"
    homepage = "https://github.com/Chylynsky/rc_ptr"
    url = "https://github.com/Chylynsky/rc_ptr"
    topics = ("memory", "smart-pointer", "header-only")
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
        # 上游硬性要求 C++17（根 CMakeLists: CMAKE_CXX_STANDARD 17）
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, 17)

    def package_id(self):
        # header-only：所有配置同一份包内容
        self.info.clear()

    def layout(self):
        cmake_layout(self)

    def source(self):
        # 主源：官方 tag 归档（URL/sha256 与 conan-center-index recipes/rc_ptr conandata 一致）
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)
        # 测试框架 Catch2 v2.13.7（上游 test/CMakeLists.txt FetchContent 固定 tag）：
        # 预置到 _deps/catch2-src，由 generate() 的 FETCHCONTENT_SOURCE_DIR_CATCH2 指向，
        # 构建期不发起任何下载（CI worker 对 GitHub git 协议不通）。
        catch2 = dict(self.conan_data["catch2"])
        get(
            self,
            **catch2,
            strip_root=True,
            destination=os.path.join(self.source_folder, "_deps", "catch2-src"),
        )

    def generate(self):
        tc = CMakeToolchain(self)
        # 打开上游测试面（test/CMakeLists.txt：Catch2 套件，18 个 test/*.cpp）
        tc.variables["RC_PTR_BUILD_TESTS"] = True
        # FetchContent 用本地预置的 Catch2 源，不做网络访问
        tc.variables["FETCHCONTENT_SOURCE_DIR_CATCH2"] = os.path.join(
            self.source_folder, "_deps", "catch2-src"
        ).replace("\\", "/")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        if not self.options.run_upstream_tests:
            self.output.info("run_upstream_tests=False: 上游测试按选项跳过（默认 True 不跳过）")
            return
        if not can_run(self):
            self.output.info("Cross-building: 上游测试在构建期跳过（can_run=False）")
            return

        cmake = CMake(self)
        cmake.configure()
        # 上游唯一测试可执行（根 CMakeLists: add_subdirectory(test rc_ptr-test)）
        cmake.build(target="rc_ptr-test")

        exe = os.path.join(self.build_folder, "rc_ptr-test", "rc_ptr-test")
        if not os.path.isfile(exe):
            raise ConanException(f"upstream test binary missing: {exe}")

        run_buf = io.StringIO()
        try:
            self.run(f'"{exe}"', env="conanbuild", stdout=run_buf, stderr=run_buf)
        except Exception:
            self.output.info("上游测试输出（尾部）:\n" + run_buf.getvalue()[-6000:])
            raise
        run_out = run_buf.getvalue()

        # Catch2 摘要：`All tests passed (305 assertions in 110 test cases)`
        match = re.search(
            r"(All tests passed|tests failed) \((\d+) assertions in (\d+) test cases\)",
            run_out,
        )
        if not match:
            raise ConanException(
                "未在上游测试输出中找到 Catch2 计数摘要（可能 0 用例运行，禁止假绿）"
            )
        status = match.group(1)
        assertions = int(match.group(2))
        cases = int(match.group(3))

        if status != "All tests passed":
            raise ConanException(f"上游测试未全通过: {status} ({cases} cases)")
        # 反静默硬校验：只接受两种工具链形态（pmr 头有/无），其余计数一律失败
        if cases == EXPECTED_RUN_CASES_PMR:
            expected_assertions = EXPECTED_ASSERTIONS_PMR
            pmr_note = "pmr 用例 2 个已编译运行（工具链提供 <memory_resource>）"
        elif cases == EXPECTED_RUN_CASES_NO_PMR:
            expected_assertions = EXPECTED_ASSERTIONS_NO_PMR
            pmr_note = (
                "pmr 用例 2 个被上游 #if (__has_include(<memory_resource>)) 排除 "
                "（OHOS SDK libc++ 无 <memory_resource>）=> NOT_RUN=2"
            )
        else:
            raise ConanException(
                "上游测试用例数与申报口径不符: cases={}（期望 {} 或 {}）".format(
                    cases, EXPECTED_RUN_CASES_NO_PMR, EXPECTED_RUN_CASES_PMR
                )
            )
        if assertions != expected_assertions:
            raise ConanException(
                "上游测试断言执行数与申报口径不符: assertions={}（期望 {}）".format(
                    assertions, expected_assertions
                )
            )
        if cases > EXPECTED_SOURCE_TEST_CASES:
            raise ConanException(
                f"上游测试用例数 {cases} 超过源码宏数 {EXPECTED_SOURCE_TEST_CASES}（口径反噬）"
            )

        self.output.info(f"UPSTREAM_PMR_NOTE {pmr_note}")
        self.output.info(
            "UPSTREAM_SOURCE_TEST_CASES={} RUN={} ASSERTIONS={} NOT_RUN={}".format(
                EXPECTED_SOURCE_TEST_CASES,
                cases,
                assertions,
                EXPECTED_SOURCE_TEST_CASES - cases,
            )
        )
        marker = {
            "status": "passed",
            "framework": "Catch2 v2.13.7",
            "command": "rc_ptr-test/rc_ptr-test",
            "declared_n": EXPECTED_SOURCE_TEST_CASES,
            "discovered": cases,
            "executed": cases,
            "passed": cases,
            "failed": 0,
            "not_run": EXPECTED_SOURCE_TEST_CASES - cases,
            "assertions": assertions,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False))

    def package(self):
        # header-only：把上游 include 树与许可证原样交付（保持 rc_ptr/rc_ptr.hpp 相对路径）
        copy(
            self,
            pattern="*.hpp",
            src=os.path.join(self.source_folder, "include"),
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            pattern="LICENSE_1_0.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
        # 上游未导出 CMake 配置文件，按 Conan 默认命名（conan-center-index recipes/rc_ptr 同值）：
        # find_package(rc_ptr) + rc_ptr::rc_ptr
        self.cpp_info.set_property("cmake_file_name", "rc_ptr")
        self.cpp_info.set_property("cmake_target_name", "rc_ptr::rc_ptr")
