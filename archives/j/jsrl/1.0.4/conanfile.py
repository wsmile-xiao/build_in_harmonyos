#!/usr/bin/env python3
"""Conan recipe — jsrl 1.0.4（Adobe 的 C++17 JSON 解析/编码库，零运行依赖）。

上游：github.com/adobe/jsrl（Apache-2.0），交付物 `libjsrl.{a,so}` + `include/jsrl/*.hpp`，
CMake 构建（`cmake_minimum_required(3.14...3.27)`，设备 cmake 4.1.2 实测可过）。

━━ 源码三路取证（W0-1，2026-09-28 设备实测）━━
  * `git ls-remote --tags https://github.com/adobe/jsrl` → 5 个 tag 全量命中
    （1.0.0 / 1.0.1 / 1.0.2 / 1.0.3 / **1.0.4**，**无 `v` 前缀形态**），
    `1.0.4` = 2868f64f0f66b993a161bd91b2cb747933c0b54a；
  * 任务卡 url（GitHub tag 归档）实时下载 sha256 =
    6d530713ba00f8c762f55393c96c14a0d6eb9b6f8744aa87125e63af88ff1885（63 976 B，解包 557 K）
    == task-scout 归档副本 == CCI 归档配方 conandata 的 sha256，**三路逐字一致**；
  * conandata.yml 的 sources 即该官方 URL + 该 sha256（R39）。
  * 上游当前 HEAD（ce9cec7，2026-09-28 现场 `git clone --depth 1 --sparse` 取 tests/）
    的 TEST 宏清点同为 148 ⇒ 声明 N 的下界口径同样满足。

━━ W0 生死关结论 ━━
  1. 版本可得性：**通过**（tag + tarball + sha256 三路一致）。
  2. 硬依赖：**通过，与任务卡「0 依赖」一致** —— 上游 CMakeLists 除 `tests/` 的
     `find_package(GTest)`（找不到就 FetchContent 拉 googletest v1.14.0）外**无任何
     find_package/requires**；库本体零依赖。GTest 属测试期依赖，按
     `self.test_requires("gtest/1.17.0")` 提供（对 ohpcd 远端执行
     `conan download gtest/1.17.0 --only-recipe` rc=0、远端已有本 profile binary），
     不进包依赖链、不传播给消费者。
  3. 平台不可移植判据：**全零命中** —— ISA 专属头（altivec/mmx/3dnow/*mmintrin/
     arm_neon/x86intrin/__SSE/__AVX）、glibc printf 钩子族（printf.h/register_printf_*）、
     架构可移植性档（`#error Unknown CPU|other architectures are not supported|
     allowed_architectures`）、架构/平台条件编译宏（__x86_64__|__aarch64__|_MSC_VER|
     __OHOS__|_WIN32|__APPLE__|__linux__）四组 grep 在全仓（src/ tests/ CMakeLists）
     各 0 行 ⇒ 架构可移植性**档 A（无任何架构专属代码）**，不触发止损。

━━ 平适配点（**零源码补丁**）━━
  本配方不改上游任何源文件（conandata `patches: {}`），适配全部在配方侧：
  * `JSRL_BUILD_TESTS=ON`（上游默认值）⇒ 层 1 上游测试在 build() 内实跑；
  * `JSRL_INSTALL=ON`（上游默认值）⇒ 走上游 `cmake --install`；
  * GTest 走**包内自带的 GTestConfig.cmake**：`cmake_find_mode=none` 关掉 CMakeDeps
    对 gtest 的生成 + `GTest_DIR` 指向 `<gtest 包>/lib/cmake/GTest`（与上游
    `find_package(GTest)` 的 CONFIG 路径同名对齐），避免与 CMake 自带 FindGTest 模块、
    以及 CMakeDeps 生成的 `gtest-config.cmake`（小写目标 `gtest::gtest`）三方竞争；
    上游 tests/CMakeLists.txt 用的是 `GTest::gtest` / `GTest::gtest_main` 目标名，
    正是 gtest 自带 config 导出的名字（abseil/cpp-httplib/benchmark 同款走法）；
  * `tools.build:jobs=4`：cpu_count=20 / affinity=8，不钉会 2.5× 超订（device-facts §一.7）；
  * 静态构建时补 `JSRL_STATIC_DEFINE`（上游 CMakeLists 已 PUBLIC 传播，包侧同口径再声明一次）。

━━ 上游测试面（R51 三步法；N 取候选数法最大值）━━
  上游测试入口唯一：根 CMakeLists `if(JSRL_BUILD_TESTS) enable_testing() +
  add_subdirectory(tests)` → `tests/CMakeLists.txt` 注册 **4 个 ctest 项**
  （gtest 可执行 jsrl_general_number_test / jsrl_mod_test / jsrl_test / jsrlpp_test）。
  候选口径（§3.5 四口径不混用）：
    ① 源码宏数 = **148** —— `grep -hoE '^\s*(TEST|TEST_F|TEST_P)\s*\(' <src>/tests/*.cpp | wc -l`
       → jsrl_test 53 + jsrl_mod_test 43 + jsrl_format_test 36 + jsrlpp_test 11
         + jsrl_general_number_test 5（上游当前 HEAD 同值 148）。
    ② 框架注册数 = **112**（`--gtest_list_tests` 逐二进制清点 5+43+53+11；
       `ctest -N` → `Total Tests: 4`）—— 即本次实跑 N′。
    ③ assertion 数（源码静态）= 950 条 EXPECT_*/ASSERT_*（285 EXPECT_EQ + 240 EXPECT_PRED +
       188 EXPECT_THROW + …），**断言单位，单列不作 N**。
    ④ 消费者断言数 = test_package 的鸿蒙特有测试 9 条（见 test_package/MANIFEST.yml），
       **不进上游分母**。
  ⇒ **N（上游用例总数，候选数法最大值）= 148**（① 与 ② 同为「测试用例数」单位）；
    N′ = 112，NOT_RUN = 36（= jsrl_format_test 全部用例），逐项归因见下。

━━ NOT_RUN 36 项归因（既非 PASS 也非 SKIP，不进通过率分子）━━
  `tests/CMakeLists.txt:46` 的门是
  `if(CMAKE_CXX_STANDARD GREATER_EQUAL 20)` —— 只有 C++20 才 `add_jsrl_test(jsrl_format_test)`。
  上游 `.github/workflows/ci.yml` **不传** `CMAKE_CXX_STANDARD`，根 CMakeLists 走
  `if(NOT DEFINED CMAKE_CXX_STANDARD) set(CMAKE_CXX_STANDARD 17)` ⇒ **上游自己的 CI
  同样不编译 jsrl_format_test**（本包与上游 CI 同口径：ctest 注册项 = 4）。
  在 OHOS 上即使把全局标准抬到 C++20 也编不过，三步实测证据（2026-09-28，见 notes.md 问题 2）：
    1. 本机 libc++15 的 `<format>` 被平台配置**整体禁用**：
       `<libcxx-ohos>/include/c++/v1/__config:255` `#define _LIBCPP_HAS_NO_INCOMPLETE_FORMAT`
       （`__has_include(<format>)` 为真但 `std::format`/`std::formatter` 均未定义）；
    2. 强开 `-D_LIBCPP_ENABLE_EXPERIMENTAL` 后**链接失败**：
       `undefined symbol: typeinfo for std::__n1::format_error` / `~format_error()`
       （OHOS 的 libc++.so 构建时未编入 format 支持，缺的正是 format_error 的 key function）；
    3. 自补 format_error 析构后**编译失败 17 处**：libc++ 的
       `__formattable` 概念形参按值取 `T`，而 `jsrl::Json::Error` 是抽象类
       （`jsrl.hpp:900` `~Error() noexcept override = 0`）⇒
       `call to deleted function '__determine_arg_t<…, jsrl::Json::Error>'`、
       `format_arg_store.h:157/158/163/166` 常量表达式连环失败。
  ⇒ jsrl_format_test 在本平台**不可编译**，属 §3.5「OHOS 缺特性」（平台标准库未提供
    `std::format`）+ 上游该用例对 libc++ 概念检查不兼容；按 NOT_RUN 申报，
    **不写 PASS、不删测试、不改上游测试**。

反假绿硬断言（任一不满足即 conan create 失败，不写假 PASS）：
  * `tests/CTestTestfile.cmake` 的 `add_test(` 注册项必须 == 4（防 ctest 空跑）；
  * `tests/jsrl_format_test` 可执行**必须不存在**（上游翻转 C++20 门会立刻暴露，不静默少跑）；
  * 4 个二进制 `--gtest_list_tests` 用例合计必须 == 112（框架注册数）；
  * `ctest --test-dir <build> --output-on-failure -V` rc == 0，输出必须含
    `100% tests passed, 0 tests failed out of 4`，且 `[  PASSED  ]` 汇总行求和 == 112、
    不含 `All 0 tests`（假绿禁用词）；
  * 安装树清点：`include/jsrl/*.hpp` 恰为 6 件（5 个源码头 + 生成的 jsrl_export.hpp），
    `libjsrl.*` 恰为 1 件（防 install/copy 假绿）。
"""
import os
import re
import subprocess

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rmdir,
)


class JsrlConan(ConanFile):
    name = "jsrl"
    version = "1.0.4"
    description = ("JSRL - JSON Serialization and Reading Library: UTF-8 native, "
                   "immutable, high-fidelity number representation")
    license = "Apache-2.0"
    homepage = "https://github.com/adobe/jsrl"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("json", "parser", "cpp17", "high-fidelity-numbers")

    package_type = "library"
    implements = ["auto_shared_fpic"]

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    # ── 上游测试面常量（docstring「上游测试面」给出全部取数命令）──
    EXPECTED_SOURCE_MACROS = 148     # ① 源码宏数 = N（候选最大值）
    EXPECTED_REGISTERED_CASES = 112  # ② 框架注册数 = N′（本次实跑）
    EXPECTED_CTEST_ENTRIES = 4       # ctest 注册项（防 ctest 空跑）
    EXPECTED_NOT_RUN = 36            # jsrl_format_test（C++20 门 + 平台缺 std::format）
    TEST_BINARIES = (
        "jsrl_general_number_test",
        "jsrl_mod_test",
        "jsrl_test",
        "jsrlpp_test",
    )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # W0-2：库本体零依赖（上游 CMakeLists 除 tests/ 的 GTest 外无 find_package）。
        pass

    def build_requirements(self):
        # 仅上游测试需要；不传播给消费者，不进包依赖链（manifest `test_dependencies`）。
        self.test_requires("gtest/1.17.0")

    def layout(self):
        cmake_layout(self)

    def validate(self):
        # 库本体最低 C++17（上游 check_min_cppstd 同口径）
        if self.settings.get_safe("compiler.cppstd"):
            check_min_cppstd(self, 17)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # 本轮 patches: {} ⇒ 空操作；保留调用以遵守「补丁一律从 conandata.yml 施加」
        apply_conandata_patches(self)

    def generate(self):
        deps = CMakeDeps(self)
        # GTest 用**包内自带**的 lib/cmake/GTest/GTestConfig.cmake（导出上游要用的
        # GTest::gtest / GTest::gtest_main 目标名），关掉 CMakeDeps 对 gtest 的再生成，
        # 避免小写 gtest-config.cmake / CMake 自带 FindGTest 模块三方竞争。
        deps.set_property("gtest", "cmake_find_mode", "none")
        deps.generate()

        tc = CMakeToolchain(self)
        tc.cache_variables["JSRL_BUILD_TESTS"] = True   # 上游默认值，显式钉住（层 1 上游测试）
        tc.cache_variables["JSRL_INSTALL"] = True       # 上游默认值
        tc.cache_variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        gtest = self.dependencies["gtest"]
        tc.cache_variables["GTest_DIR"] = os.path.join(
            gtest.package_folder, "lib", "cmake", "GTest"
        ).replace("\\", "/")
        tc.generate()

        # 并行度上限：conan 的 CMake helper 会追加 `-j<tools.build:jobs>`，
        # 该 conf 缺省取 os.cpu_count()（本机 20 / affinity 8 ⇒ 2.5× 超订，
        # device-facts §一.7）
        self.conf.define("tools.build:jobs", 4)

    # ── 反假绿辅助 ────────────────────────────────────────────────
    def _run_logged(self, args, log_path, cwd=None):
        """用 self.run（conanbuild env ⇒ PATH 内有 cmake/ctest/clang）跑子进程，
        stdout+stderr 落 log 文件，返回 (rc, 文本)；不因非零退出抛异常。"""
        cmd = " ".join("'" + a.replace("'", "'\\''") + "'" for a in args)
        with open(log_path, "w", encoding="utf-8") as fh:
            rc = self.run(cmd, stdout=fh, stderr=subprocess.STDOUT,
                          cwd=cwd or self.build_folder, env="conanbuild",
                          ignore_errors=True)
        with open(log_path, encoding="utf-8", errors="replace") as fh:
            return rc, fh.read()

    def _ctest_entries(self):
        path = os.path.join(self.build_folder, "tests", "CTestTestfile.cmake")
        if not os.path.isfile(path):
            return -1
        with open(path, encoding="utf-8", errors="replace") as fh:
            return len(re.findall(r"^\s*add_test\(", fh.read(), flags=re.M))

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        tests_dir = os.path.join(self.build_folder, "tests")

        # ── 反假绿 1：官方注册面（防 ctest 空跑）────────────────
        entries = self._ctest_entries()
        self.output.info(f"[upstream-tests] ctest 注册项 = {entries} "
                         f"(期望 {self.EXPECTED_CTEST_ENTRIES})")
        if entries != self.EXPECTED_CTEST_ENTRIES:
            raise Exception(f"ctest 注册项 {entries} != {self.EXPECTED_CTEST_ENTRIES}，"
                            f"测试入口可能未生成（防 ctest 空跑）")

        # ── 反假绿 2：jsrl_format_test 必须不存在（36 例 NOT_RUN 的显式断言）──
        fmt_bin = os.path.join(tests_dir, "jsrl_format_test")
        if os.path.exists(fmt_bin):
            raise Exception(
                "tests/jsrl_format_test 意外生成 —— 上游 C++20 门（tests/CMakeLists.txt:46）"
                "或平台 std::format 能力发生变化；NOT_RUN=36 的归因失效，先重新清点 N")

        # ── 反假绿 3：框架注册数（--gtest_list_tests，不执行用例，廉价）──
        listed_total = 0
        for name in self.TEST_BINARIES:
            log = os.path.join(self.build_folder, f"upstream-list-{name}.log")
            rc, text = self._run_logged([os.path.join(tests_dir, name),
                                         "--gtest_list_tests"], log, cwd=tests_dir)
            if rc != 0:
                raise Exception(f"{name} --gtest_list_tests rc={rc}，测试可执行异常；"
                                f"日志：{log}")
            # gtest 列举行：套件行顶格且以 '.' 结尾，用例行缩进 2 空格
            cases = sum(1 for line in text.splitlines()
                        if line.startswith("  ") and line.strip())
            self.output.info(f"[upstream-tests] {name} 框架注册用例 = {cases}")
            listed_total += cases
        self.output.info(
            f"[upstream-tests] 框架注册数合计 = {listed_total}"
            f"（期望 {self.EXPECTED_REGISTERED_CASES}；源码宏数 "
            f"{self.EXPECTED_SOURCE_MACROS} − jsrl_format_test "
            f"{self.EXPECTED_NOT_RUN} = {self.EXPECTED_SOURCE_MACROS - self.EXPECTED_NOT_RUN}）")
        if listed_total != self.EXPECTED_REGISTERED_CASES:
            raise Exception(f"框架注册数 {listed_total} != {self.EXPECTED_REGISTERED_CASES}"
                            f"（源码宏数 {self.EXPECTED_SOURCE_MACROS} − C++20 门控的 "
                            f"jsrl_format_test {self.EXPECTED_NOT_RUN}）。"
                            f"差额不符 ⇒ 某些 TU 未编译或注册面变化，先查该步")

        # ── 层 1：上游官方测试（TEST_QUALITY_SPEC §3.1 的 CMake 口径 = ctest；
        #    沙箱 HOME，device-facts §一.11）────────────────────────────
        run_log = os.path.join(self.build_folder, "upstream-tests.log")
        sandbox = os.path.join(self.build_folder, "test-home")
        os.makedirs(sandbox, exist_ok=True)
        old_home = os.environ.get("HOME")
        os.environ["HOME"] = sandbox
        try:
            with open(run_log, "w", encoding="utf-8") as fh:
                rc = self.run(
                    f'ctest --test-dir "{self.build_folder}" --output-on-failure -V',
                    stdout=fh, stderr=subprocess.STDOUT,
                    cwd=self.build_folder, env="conanbuild", ignore_errors=True)
        finally:
            if old_home is None:
                os.environ.pop("HOME", None)
            else:
                os.environ["HOME"] = old_home
        with open(run_log, encoding="utf-8", errors="replace") as fh:
            out = fh.read()

        ctest_ok = re.search(
            r"100% tests passed, 0 tests failed out of "
            + str(self.EXPECTED_CTEST_ENTRIES), out) is not None
        passed = sum(int(m) for m in
                     re.findall(r"\[\s+PASSED\s+\]\s+(\d+) tests?\.", out))
        no_zero = "All 0 tests" not in out
        self.output.info(
            f"[upstream-tests] ctest rc={rc} 全过判定={'是' if ctest_ok else '否'} "
            f"[PASSED] 求和={passed}（期望 {self.EXPECTED_REGISTERED_CASES}） "
            f"无 All-0-tests={'是' if no_zero else '否'}")
        if rc != 0:
            tail = "\n".join(out.splitlines()[-60:])
            raise Exception(f"上游测试 ctest rc={rc}（日志尾部）：\n{tail}")
        if not ctest_ok:
            raise Exception("ctest 未给出 `100% tests passed, 0 tests failed out of 4` —— "
                            "测试可能未真正执行（防 ctest 假绿）")
        if not no_zero:
            raise Exception("日志出现 `All 0 tests` —— 判绿禁用词（device-facts §二.22）")
        if passed != self.EXPECTED_REGISTERED_CASES:
            raise Exception(f"`[  PASSED  ]` 求和 {passed} != {self.EXPECTED_REGISTERED_CASES}")

        # ── 台账（供 PR 正文/test-report 复算，逐字可见）──
        n = self.EXPECTED_SOURCE_MACROS
        n_prime = self.EXPECTED_REGISTERED_CASES
        self.output.info(
            f"[upstream-tests] 台账 N={n} N'={n_prime} PASS={n_prime} FAIL=0 SKIP=0 "
            f"NOT_RUN={n - n_prime}（jsrl_format_test，C++20 门 + 平台缺 std::format，"
            f"归因见 conanfile docstring）TOTAL={n_prime}+0+0+{n - n_prime}==N 成立")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

        # 上游会 install 自带的 jsrlConfig.cmake / jsrl.pc，与 CMakeDeps 生成的配置
        # 在 `find_package(jsrl)` 上构成双配置竞争 ⇒ 删除（CCI 同口径）
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

        # 反假绿：安装树清点（防 install/copy 假绿）
        headers = []
        libs = []
        for root, _dirs, files in os.walk(self.package_folder):
            for f in files:
                full = os.path.join(root, f)
                rel = os.path.relpath(full, self.package_folder)
                if rel.startswith(os.path.join("include", "jsrl") + os.sep) and f.endswith(".hpp"):
                    headers.append(f)
                elif f.startswith("libjsrl."):
                    libs.append(rel)
        expected_headers = ["jsrl.hpp", "jsrl_export.hpp", "jsrl_format.hpp",
                            "jsrl_general_number.hpp", "jsrl_mod.hpp", "jsrlpp.hpp"]
        self.output.info(f"[package] 头文件清点={sorted(headers)} 库={sorted(libs)}")
        if sorted(headers) != expected_headers:
            raise Exception(f"安装树头文件清点不符: 得到 {sorted(headers)} != "
                            f"{expected_headers}（防 install 假绿）")
        if len(libs) != 1:
            raise Exception(f"安装树库文件清点不符: {libs}（应恰 1 件 libjsrl.*）")

    def package_info(self):
        self.cpp_info.libs = ["jsrl"]
        if not self.options.shared:
            # 上游 CMakeLists 在非 shared 时 PUBLIC 传播该宏，包侧同口径声明
            self.cpp_info.defines = ["JSRL_STATIC_DEFINE"]
        # 库目录按 package() 实际落点回填（GNUInstallDirs 在不同前缀下可能给 lib/lib64）
        for root, _dirs, files in os.walk(self.package_folder):
            for f in files:
                if f.startswith("libjsrl."):
                    rel = os.path.relpath(root, self.package_folder)
                    self.cpp_info.libdirs = ["."] if rel == "." else [rel]
        self.cpp_info.set_property("cmake_file_name", "jsrl")
        self.cpp_info.set_property("cmake_target_name", "jsrl::jsrl")
        self.cpp_info.set_property("pkg_config_name", "jsrl")
