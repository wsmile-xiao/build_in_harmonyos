#!/usr/bin/env python3
"""Conan recipe — clove-unit 2.4.6 (CMake, header-only C unit-testing framework).

clove-unit 是**单头文件**（`clove-unit.h`，198 KB）的 C 单元测试框架（可与 C++
互操作），带测试自动发现：runner 通过 `dl_iterate_phdr` + ELF `SHT_SYMTAB`
符号表扫描定位 `__clove_sym___<suite>___<test>` 形态的用例函数。上游以 CMake
`INTERFACE` 目标交付（`add_library(clove-unit INTERFACE)`），**无编译单元、
无 .a/.so**，故 `package_type = "header-library"`（同 CCI 官方配方）。

交付面：`include/clove-unit.h` + `licenses/LICENSE`（`package_info` 不带 bin/lib，
R38 纯库包不写 commands.json）。

上游测试（层 1，写在 `build()` 内，conan create 即执行）：
  `CLOVE_CMAKE__UC_BUILD=ON`  → tests/functs（CLoveUnitTest，clove 框架注册
      175 用例 / 22 suite）+ tests/functs/resources/prj01（3 用例，被 INTE 集成
      用例子进程执行）+ tests/stricts/clove-c、clove-cpp（-Werror 严格编译检查）
      + examples/clove101、clovepp（上游 CI 仅编译）
  `CLOVE_CMAKE__UC_SANITY=ON` → tests/stricts/clove-sanity 的 12 条 CTest 命令
      （Sanity_uc_*，上游 CI `sanity_check` job 的执行面）
  合计 CTest 注册命令 13 条、上游 CI 实跑用例 190。

补丁 `0001-sanity-drop-unsupported-leak-sanitizer.patch`：上游 sanity 目标硬编码
`-fsanitize=address,leak,undefined`，而设备/CI 的 clang-15 对
`aarch64-unknown-linux-ohos` 目标直接拒绝该选项——
`clang-15: error: unsupported option '-fsanitize=leak' for target 'aarch64-unknown-linux-ohos'`
（LeakSanitizer 在 OHOS 目标上未启用）。补丁只移除 `leak` 一个 sanitizer 选项，
**保留 ASan/UBSan，测试源码与 CTest 注册零改动**（依据 docs/TEST_QUALITY_SPEC.md
§3.3：平台不兼容的测试用 conandata patches 修复）。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get

# 上游 CI 两个 job 的 CTest 注册命令数：
#   UC_BUILD  → 1 条（CLoveUnitTest）
#   UC_SANITY → 12 条（Sanity_uc_default/help/version/include/exclude/pretty/
#               csv/json/list/list_pretty/list_csv/list_json）
UPSTREAM_CTEST_REGISTERED = 13


class CloveUnitConan(ConanFile):
    name = "clove-unit"
    version = "2.4.6"
    description = ("Single-header Unit Testing framework for C "
                   "(interoperable with C++) with test autodiscovery feature")
    license = "MIT"
    homepage = "https://github.com/fdefelici/clove-unit"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("unit-testing", "testing", "c", "c11", "header-only")

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        # R32: 平台判断用 in (...)，不能 == "Linux"
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "clove-unit 仅在 Linux/OHOS 目标上验证过，当前 os={}".format(self.settings.os))

    def layout(self):
        cmake_layout(self)

    def package_id(self):
        # header-only：所有 settings 组合产出相同包内容
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # no_copy_source=True：源码不会复制进 build()，补丁必须在 source() 打
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # 开启上游 dev 用例（两个开关在上游 CMakeLists 里默认都是 OFF）：
        # UC_BUILD  = 上游 CI 的 build_windows / build_macos / build_ubuntu job
        # UC_SANITY = 上游 CI 的 sanity_check job
        tc.variables["CLOVE_CMAKE__UC_BUILD"] = True
        tc.variables["CLOVE_CMAKE__UC_SANITY"] = True
        # CLOVE_CMAKE__CPP_STRICT_WARN_AS_ERROR 上游默认 OFF，保持不变
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # ── 层 1：上游官方测试（docs/TEST_QUALITY_SPEC.md §3.1，必做）──
        self._run_upstream_ctest()

    def _run_upstream_ctest(self):
        """先断言注册数再执行——防空跑假绿（§二.22：ctest 0 注册时 rc=0）。

        上游测试一律在**沙箱 HOME**（build 目录内 `clove-test-home/`）下执行，
        不写用户真实 HOME。
        """
        sandbox = os.path.join(str(self.build_folder), "clove-test-home")
        os.makedirs(sandbox, exist_ok=True)
        n = UPSTREAM_CTEST_REGISTERED
        # ① 打印注册清单（日志里的正向证据：`Total Tests: 13`）
        self.run("HOME=%s ctest -N" % sandbox, cwd=str(self.build_folder))
        # ② 断言注册数，不符即 17，杜绝 `No tests were found!!!` + rc=0 的结构性假绿
        self.run(
            'HOME=%s ctest -N 2>&1 | grep -E "Total Tests: %d" >/dev/null || '
            '{ echo "FATAL: ctest registered != %d (empty-run false green)" >&2; '
            'exit 17; }' % (sandbox, n, n),
            cwd=str(self.build_folder))
        # ③ 真实执行 13 条命令：1×CLoveUnitTest（175 用例）+ 12×Sanity_uc_*
        self.run("HOME=%s ctest --output-on-failure" % sandbox, cwd=str(self.build_folder))
        self.output.info(
            "upstream ctest done: %d/%d registered commands executed"
            % (UPSTREAM_CTEST_REGISTERED, UPSTREAM_CTEST_REGISTERED))

    def package(self):
        # 上游 CMakeLists 用 clove_join_paths 把 CMAKE_INSTALL_PREFIX 改写成
        # `${CMAKE_INSTALL_PREFIX}/clove-unit/${VERSION}`，直接 `cmake.install()`
        # 会把头文件落进 `<pkg>/clove-unit/2.4.6/include/`（conan 需要 `<pkg>/include/`），
        # 故按 CCI 官方配方口径显式收纳（同 CCI recipes/clove-unit/all）。
        copy(self, "LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "clove-unit.h",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "clove-unit")
        self.cpp_info.set_property("cmake_target_name", "clove-unit::clove-unit")
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
