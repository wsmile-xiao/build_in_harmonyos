#!/usr/bin/env python3
"""Conan recipe — arg_router 1.3.0（header-only C++ 命令行参数解析与路由库）。

上游：github.com/cmannett85/arg_router（Camden Mannett，BSL-1.0），交付物为
`include/arg_router/**/*.hpp` 头文件集合，CMake 构建，**零二进制产物**。

━━ 源码三路取证（W0-1，2026-09-28 设备实测）━━
  * `git ls-remote --tags` → 9 个 tag 全量命中（v0.1.0 … v1.4.0），
    `v1.3.0` = ea82e8c94c84b8df80b38a37b65162c70d10b276（轻量 tag，无 peel 行）；
  * 任务平台任务卡 url 指向官方 tag 归档，实测下载 sha256 =
    4ef2ec923046c26d65b19f06630b3180a81189362d8920a68113c7d921ca968b（299 585 B，解包 3.6 M）
    == 任务卡记录的 CCI 值 4ef2ec92…，逐字一致；
  * conandata.yml 的 sources 即该官方 URL + 该 sha256（R39）。

━━ W0 生死关结论 ━━
  1. 版本可得性：**通过**（tag + tarball + sha256 三路一致）。
  2. 硬依赖：**通过，但与任务卡「0 依赖」不符**——上游 CMakeLists `find_package(Boost 1.74
     REQUIRED)`、`unit_test.cmake` 再取 `COMPONENTS filesystem`，源码 include
     `<boost/mp11/{algorithm,bind,utility}.hpp>`、`<boost/lexical_cast.hpp>`，上游自带
     conanfile.py 亦写 `self.requires("boost/[>=1.74.0]")`。按 W0-2 实查
     `conan list -r=ohpcd "boost/*"` → 15 个版本，且
     `conan install --requires=boost/1.90.0 --build=never`（同 profile）rc=0 命中远端
     binary（os=OHOS/clang15/armv8/libc++/cppstd=17/Release）⇒ 依赖可得、不构成止损，
     按实有依赖登记（manifest.dependencies 与本文件 requirements 同步 boost/1.90.0）。
  3. 平台不可移植判据：**全零命中**——ISA 专属头（altivec.h/mmx/3dnow/*mmintrin/arm_neon/
     x86intrin 等）、glibc printf 钩子族（printf.h/register_printf_*）、
     架构可移植性档（`#error Unknown CPU|other architectures are not supported|
     allowed_architectures`）三组 grep 在 `include/ test/ examples/` 下均为 0 行，
     `__x86_64__/__aarch64__/_MSC_VER` 等条件编译宏同样 0 行 ⇒ 不触发 mexce 类深核、不止损。

━━ 平台适配点（**零源码补丁**）━━
  本配方不改上游任何源文件（conandata `patches: {}`），适配全部在配方侧完成：
  * `DISABLE_VCPKG=ON`：上游 `external/vcpkg` 子模块在 tag 归档里为空目录，
    不关会把不存在的 `CMAKE_TOOLCHAIN_FILE` 交给 CMake，configure 直接失败。
  * **span-lite/0.11.0 依赖**：`basic_types.hpp` 的 span 选择器是
    `#if __cplusplus >= 202000L → <span> #else → <nonstd/span.hpp>`；上游 `vcpkg.json`
    明列 `span-lite`、CMakeLists 也 `find_package(span-lite QUIET)` —— **C++17 面
    （本包声明的最低标准，也是 example/c++17* 与 test_package 消费面）必须有它**。
    远端 0.11.0 有本 profile binary，`cmake_target_name = nonstd::span-lite` 正是
    `library.cmake` 里 `$<TARGET_EXISTS:nonstd::span-lite>` 的目标名，
    `cmake_file_name = span-lite` 也正对 `find_package(span-lite QUIET)`。
  * **`CMAKE_PROJECT_INCLUDE` 钩子**（generate() 落盘 `arg_router_adapt_hook.cmake`）两件事：
    ① `unset(CMAKE_CXX_STANDARD)` —— 撤销 conan toolchain 无条件强加的**全局**标准
       （profile=17；命令行/cache 传值全被它盖掉，实测 -DCMAKE_CXX_STANDARD=20 无效）。
       全局 17 会造成**标准错位**：`unit_test.cmake` 见其已定义 ⇒ 主测试树不再加
       `cxx_std_20` ⇒ 17，而 `death_test.cmake` 是无条件 `target_compile_features(cxx_std_20)`
       ⇒ 8 个 death 目标 20（实测 compile_commands 全为 -std=c++20）。于是「只在 C++17
       存在」的用例被编进主测试树、death 目标却用 C++20 编它们的片段 ⇒ **实测 4 个 death
       用例假失败**（期望 static_assert 文本未触发）。unset 后回到**上游默认形态**
       （unit_test.cmake 的 `if(NOT DEFINED CMAKE_CXX_STANDARD)` 成立 ⇒ 主测试树 cxx_std_20，
       与 death 目标同为 20；各 example 自带 cxx_std_17/cxx_std_20，互不影响）。
    ② 补 `Boost::boost` 目标 —— ohpcd 的 `boost/1.85.0` 只导出 `Boost::headers`/
       `Boost::filesystem`/… 与**小写**根目标，上游 `library.cmake` 无条件链 `Boost::boost`
       （CMake 目标名大小写敏感）⇒ 补一个 INTERFACE 转发目标到 `Boost::headers`。
  * `BUILD_UNIT_TESTS_AND_EXAMPLES=ON`（上游默认值，显式钉住）⇒ 层 1 上游测试在 build() 实跑。
  * `ENABLE_CLANG_FORMAT_CHECKS=OFF`（上游默认值）⇒ clang-format 目标退化为空目标。

━━ 上游测试面（R51 三步法；N 取候选数法最大值）━━
  上游测试入口唯一：`test/CMakeLists.txt` → 单个聚合可执行 `arg_router_test`
  （Boost.Test，64 个 TU（63 个 *_test.cpp + test_helpers.cpp），`add_test(NAME arg_router_test
   COMMAND arg_router_test -l message)`，`CTestTestfile.cmake` 注册项 = 1）。
  候选口径（§3.5 四口径不混用）：
    ① 源码宏数 = 364（`grep -rnoE 'BOOST_(AUTO|FIXTURE|PARAMETER|TEMPLATE)_TEST_CASE' test/`
       → 360 条 BOOST_AUTO_TEST_CASE + 4 条 BOOST_FIXTURE_TEST_CASE；62 个文件、116 个 SUITE 声明）
    ② 框架注册数 = 354 —— 差额 −10 已逐项归因：`include/arg_router/config.hpp` 仅在
       `__cplusplus >= 202002L && !AR_DISABLE_CPP20_STRINGS` 时定义 `AR_ENABLE_CPP20_STRINGS`
       （上游默认 = 主测试树 C++20 ⇒ **已定义**），于是「只在 C++17 存在」的用例被上游
       自己用条件编译排除：
         · test/multi_lang/root_wrapper_test.cpp    −4（整文件 `#ifndef AR_ENABLE_CPP20_STRINGS`，
           C++20 下 `arg_router::multi_lang` 命名空间本就不存在）
         · test/multi_lang/string_selector_test.cpp −1（同上）
         · test/utility/compile_time_string_test.cpp −5（`#else` 分支的 C++17 `S_` 宏族用例；
           `#ifdef` 分支的 7 例照常注册）
       合计 −10；反向 `#ifdef AR_ENABLE_CPP20_STRINGS` 的 6 个 policy 文件的
       `string_literal_test`（各 1 例）在 C++20 下**正常注册**（已含在 364 内）。
       364 − 10 = 354。（逐行跟踪 `#ifdef/#ifndef/#else/#endif` 活跃态脚本复算：364 → 354，
       inactive 10，与 `--list_content` 实测互证。）
    ③ assertion 数（源码静态）= 749 条 `BOOST_CHECK*/REQUIRE/WARN*`（test/*.cpp 746 +
       test_helpers/test_printers .hpp 3）；逐行守卫跟踪显示 10 个未编译用例只贡献 10 条
       （全在 root_wrapper_test.cpp）⇒ 执行面 739 条（静态口径，与运行期 assertion pass
       count 分栏）。
    ④ 消费者断言数 = test_package 的鸿蒙特有测试 6 条（见 test_package/MANIFEST.yml），不进上游分母。
  ⇒ **N（上游用例总数，候选数法最大值）= 364**（源码宏数 ≥ 框架注册数）；
    N′（本次实跑）= 框架注册数 = 354，NOT_RUN = 10（上式归因），逐项证据见 build() 的
    `[upstream-tests]` 日志行与 reports/test-report.md。

反假绿硬断言（任一不满足即 conan create 失败，不写假 PASS）：
  * `CTestTestfile.cmake` 注册项必须 == 1（防 `ctest` 空跑）；
  * `--list_content` 的**用例行**数必须 == EXPECTED_REGISTERED_CASES（354）。
    Boost 1.85 的 `--list_content` 是 HRF 树（`<indent><name>*`，`*` = RS_ENABLED，
    master suite 不打印、**没有 `Case:` 前缀**）⇒ 用例数 = 总行数 − 名字以 `_suite` 结尾的
    套件行；直接数 `Case:` 会恒为 0。
  * 层 1 用官方 ctest 入口（TEST_QUALITY_SPEC §3.1 的 CMake 口径）：
    `ctest --output-on-failure -V` rc == 0，且必须出现 `0 tests failed out of 1`
    与上游程序的 `*** No errors detected` 收尾摘要；
  * N − N′ == 10（差额归因失效即失败）；
  * 包内头文件数 == 源码侧头文件数（防 install/copy 假绿）。
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
)


class ArgrouterConan(ConanFile):
    name = "arg_router"
    version = "1.3.0"
    description = "C++ command line argument parsing and routing"
    license = "BSL-1.0"
    homepage = "https://github.com/cmannett85/arg_router"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("header-only", "command-line", "argument-parser", "cpp17", "cpp20")

    package_type = "header-library"
    implements = ["auto_header_only_mode"]

    settings = "os", "compiler", "build_type", "arch"

    # 源码宏数（候选口径 ①，N 的取值来源）
    EXPECTED_SOURCE_MACROS = 364
    # 框架注册数（候选口径 ②，= 实跑 N′）：上游默认（C++20，见 _HOOK_CMAKE ①）下
    # `AR_ENABLE_CPP20_STRINGS` 已定义 ⇒ 10 个「仅 C++17 存在」的用例不注册
    # ⇒ 364 − 10 = 354（逐文件归因见 docstring）
    EXPECTED_REGISTERED_CASES = 354
    # ctest 注册项（反假绿：上游只有 1 个聚合可执行）
    EXPECTED_CTEST_ENTRIES = 1

    # ── CMake 适配钩子（generate() 落盘，经 CMAKE_PROJECT_INCLUDE 在 project() 末尾执行）──
    # 职责有二，都不改上游任何源文件：
    #
    # ① 撤销 conan toolchain 强加的**全局** C++ 标准。
    #   conan_toolchain.cmake 无条件 `set(CMAKE_CXX_STANDARD <profile cppstd>)`（=17），
    #   命令行与 cache 传值全被它盖掉（实测 -DCMAKE_CXX_STANDARD=20 无效、
    #   compile_commands 仍为 -std=c++17）。全局 17 会制造**标准错位**：
    #   `unit_test.cmake` 看到 CMAKE_CXX_STANDARD 已定义 ⇒ 不再给主测试树加 cxx_std_20
    #   → 主测试树 17；而 `death_test.cmake` 是**无条件** `target_compile_features(cxx_std_20)`
    #   → 8 个 death 目标 20（CMake 取 max，实测 compile_commands 全部 -std=c++20）。
    #   于是「只在 C++17 存在」的用例（`#ifndef AR_ENABLE_CPP20_STRINGS` 的 multi_lang
    #   根包装、`S_` 宏族）被编进主测试树，却让 death 目标用 C++20 去编译它们的片段
    #   ⇒ 实测 4 个 death 用例假失败（期望的 static_assert 文本根本没触发）。
    #   unset 之后回到**上游默认**：unit_test.cmake 的 `if(NOT DEFINED CMAKE_CXX_STANDARD)`
    #   成立 ⇒ 主测试树 `cxx_std_20`，与 death 目标同为 20，上游自己用条件编译把那 10 个
    #   「仅 C++17 存在」的用例排除掉（这正是上游 pr_checker 默认 job 的形态）。
    #   各 example 目标自带 `cxx_std_17`/`cxx_std_20`，不受影响。
    #
    # ② 补 `Boost::boost` 目标：ohpcd 的 boost/1.85.0 导出的是 Boost::headers /
    #   Boost::filesystem / Boost::system … 与**小写**根目标 boost::boost，而上游
    #   cmake/build_types/library.cmake 无条件 `target_link_libraries(arg_router INTERFACE
    #   Boost::boost)`（CMake 目标名大小写敏感）⇒ 补一个 INTERFACE 转发目标到
    #   Boost::headers，语义等价（header-only 用法，只需要 include 路径）。
    #   目标定义在顶层目录作用域 ⇒ test/、examples/ 子目录均可见；INTERFACE_LINK_LIBRARIES
    #   到 generate 期才解析，此时上游的 find_package(Boost) 已定义 Boost::headers。
    _HOOK_CMAKE = """
# arg_router 1.3.0 — 适配钩子（由 conanfile.py generate() 写入，勿手改）
unset(CMAKE_CXX_STANDARD)

if(NOT TARGET Boost::boost)
    add_library(Boost::boost INTERFACE IMPORTED)
    set_property(TARGET Boost::boost PROPERTY INTERFACE_LINK_LIBRARIES Boost::headers)
endif()
"""

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # W0-2 实查（见模块 docstring）：任务卡写「0 依赖」与源码不符，boost 是硬依赖且
        # ohpcd 远端 binary 可得 ⇒ 按实有依赖登记。
        # 选型（15 个远端版本逐个实查，2026-09-28）：上游 test/ 链要
        #   ① `<boost/process/{io,search_path,system,child}.hpp>` —— Boost.Process **v1**
        #      顶层头；Boost ≥1.88 已把 v1 挪进 `boost/process/v1/`（实测 1.90.0.4 包内
        #      `boost/process/` 只有 v2 头 + `v1/` 子目录，那四个头全缺）⇒ 1.90/1.91 系列全出局；
        #   ② `Boost::filesystem` 编译产物 —— `boost/1.90.0` 是裁剪版（只导出 headers +
        #      unit_test_framework .a），`boost/1.90.0.3/.4.1` 走 BOOST_INCLUDE_LIBRARIES
        #      选择性安装且不含 process，同样出局；
        #   ③ 远端必须已有本 profile（os=OHOS/clang15/armv8/libc++/cppstd=17/Release）binary。
        # ⇒ 只有 `boost/1.85.0` 三项全中：整棵 `boost/*` 头文件 + `libboost_filesystem.a` +
        #   远端 binary 32b74e3e…，且自带 OHOS musl 的
        #   BOOST_SP_NO_PTHREAD_SETCANCELSTATE 传播（R8）。其缺 `Boost::boost` 目标一项
        #   由 generate() 落盘的 CMake 钩子补齐（见 _HOOK_CMAKE）。
        self.requires("boost/1.85.0")
        # span-lite：C++17 下 basic_types.hpp 取 `<nonstd/span.hpp>`；上游 vcpkg.json 明列
        # 该项、CMakeLists `find_package(span-lite QUIET)`，即**上游默认配置就是
        # C++17 + span-lite**（pr_checker.yml:155 亦以 CMAKE_CXX_STANDARD=17 跑测试）。
        # 远端 0.11.0 有本 profile binary；其 cmake_target_name=nonstd::span-lite 正是
        # library.cmake `$<TARGET_EXISTS:nonstd::span-lite>` 的目标名。
        self.requires("span-lite/0.11.0")

    def layout(self):
        cmake_layout(self)

    def validate(self):
        # 库本体最低 C++17（上游 conanfile.py 的 check_min_cppstd(self, 17) 同口径）
        if self.settings.get_safe("compiler.cppstd"):
            check_min_cppstd(self, 17)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # 本轮 patches: {} ⇒ 空操作；保留调用以遵守「补丁一律从 conandata.yml 施加」
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # —— 适配点（全部是 cache 变量 + 一个 CMake 钩子，零源码补丁）——
        tc.cache_variables["DISABLE_VCPKG"] = "ON"
        tc.cache_variables["BUILD_UNIT_TESTS_AND_EXAMPLES"] = "ON"
        tc.cache_variables["BUILD_CPP20_EXAMPLES"] = "ON"
        tc.cache_variables["ENABLE_CLANG_FORMAT_CHECKS"] = "OFF"
        # C++20 + Boost::boost 目标：conan_toolchain.cmake 会**无条件**
        # `set(CMAKE_CXX_STANDARD <profile cppstd>)`（本机 profile=17），命令行与 cache
        # 传值都被它盖掉（实测 -DCMAKE_CXX_STANDARD=20 无效、compile_commands 仍是
        # -std=c++17），只能在 project() 之后用 CMAKE_PROJECT_INCLUDE 钩子重置。
        hook = os.path.join(self.build_folder, "arg_router_adapt_hook.cmake")
        os.makedirs(self.build_folder, exist_ok=True)
        with open(hook, "w", encoding="utf-8") as fh:
            fh.write(self._HOOK_CMAKE)
        tc.cache_variables["CMAKE_PROJECT_INCLUDE"] = hook
        tc.generate()
        CMakeDeps(self).generate()
        # 并行度上限：conan 的 CMake helper 会追加 `-j<tools.build:jobs>`，该 conf 缺省取
        # os.cpu_count()（本机 20 / affinity 8 ⇒ 2.5× 超订，device-facts §一.7）
        self.conf.define("tools.build:jobs", 4)

    # ── 反假绿辅助 ────────────────────────────────────────────────
    def _test_cwd(self):
        """ctest 注册项所在目录 —— 上游 death test 用 `cmake --build ..` 回到构建根，
        cwd 必须与 CTest 的默认工作目录（add_test 所在 CMAKE_CURRENT_BINARY_DIR）一致。"""
        return os.path.join(self.build_folder, "test")

    def _test_binary(self):
        return os.path.join(self._test_cwd(), "arg_router_test")

    def _count_ctest_entries(self):
        path = os.path.join(self._test_cwd(), "CTestTestfile.cmake")
        if not os.path.isfile(path):
            return -1, []
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        names = re.findall(r"^\s*add_test\(\s*([^\s)]+)", text, flags=re.M)
        return len(names), names

    def _run_logged(self, args, log_path, env_extra=None):
        """用 self.run（conanbuild env ⇒ PATH 内有 cmake/ninja/clang）跑子进程，
        stdout+stderr 落 log 文件，返回 rc（不因非零退出抛异常）。"""
        cmd = " ".join("'" + a.replace("'", "'\\''") + "'" for a in args)
        old_home = os.environ.get("HOME")
        if env_extra and "HOME" in env_extra:
            os.makedirs(env_extra["HOME"], exist_ok=True)
            os.environ["HOME"] = env_extra["HOME"]
        try:
            with open(log_path, "w", encoding="utf-8") as fh:
                rc = self.run(cmd, stdout=fh, stderr=subprocess.STDOUT,
                              cwd=self._test_cwd(), env="conanbuild",
                              ignore_errors=True)
            return rc, log_path
        finally:
            if old_home is None:
                os.environ.pop("HOME", None)
            else:
                os.environ["HOME"] = old_home

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        # ── 反假绿 1：官方注册面 ────────────────────────────────
        n_entries, entry_names = self._count_ctest_entries()
        self.output.info(f"[upstream-tests] ctest 注册项 = {n_entries} "
                         f"(期望 {self.EXPECTED_CTEST_ENTRIES}) 已注册: {entry_names}")
        if n_entries != self.EXPECTED_CTEST_ENTRIES:
            raise Exception(f"ctest 注册项 {n_entries} != {self.EXPECTED_CTEST_ENTRIES}，"
                            f"测试入口可能未生成（防 ctest 空跑）；已注册: {entry_names}")

        # ── 反假绿 2：框架注册数（--list_content，不执行用例，廉价）──
        list_log = os.path.join(self.build_folder, "upstream-list-content.log")
        rc, _ = self._run_logged([self._test_binary(), "--list_content"], list_log)
        with open(list_log, encoding="utf-8", errors="replace") as fh:
            listed = fh.read()
        # Boost 1.85 的 --list_content 是 HRF 树：`<indent><name>*`（`*` = RS_ENABLED），
        # master suite 不打印、没有 `Case:` 前缀 ⇒ 用例数 = 总行数 − 名字以 `_suite` 结尾的套件行。
        # （逐行守卫脚本独立复算的活跃用例数 = 354，与此处实测互证。）
        def _unit_name(line: str) -> str:
            t = line.strip()
            if t.endswith("*"):
                t = t[:-1].rstrip()
            return t.split(":", 1)[0].strip()

        listed_units = [l for l in listed.splitlines() if l.strip()]
        listed_cases = [l for l in listed_units if not _unit_name(l).endswith("_suite")]
        listed_suites = [l for l in listed_units if _unit_name(l).endswith("_suite")]
        self.output.info(f"[upstream-tests] --list_content 行数={len(listed_units)} "
                         f"套件={len(listed_suites)} 用例={len(listed_cases)}")
        self.output.info(f"[upstream-tests] --list_content 框架注册数 = {len(listed_cases)}"
                         f"（源码宏数 {self.EXPECTED_SOURCE_MACROS}，期望注册 "
                         f"{self.EXPECTED_REGISTERED_CASES}）rc={rc}")
        if rc != 0:
            raise Exception(f"--list_content rc={rc}，测试可执行文件异常")
        if len(listed_cases) != self.EXPECTED_REGISTERED_CASES:
            raise Exception(
                f"框架注册数 {len(listed_cases)} != {self.EXPECTED_REGISTERED_CASES}"
                f"（源码宏数 {self.EXPECTED_SOURCE_MACROS} − 10 条 "
                f"`#ifndef AR_ENABLE_CPP20_STRINGS`/`#else` 分支在 C++20 下不编译）。"
                f"差额未按预期 ⇒ 某些 TU 未编译或注册面变化，先查该步。")

        # ── 层 1：上游官方测试（TEST_QUALITY_SPEC §3.1 的 CMake 口径 = ctest；
        #    沙箱 HOME，device-facts §一.11）────────────────────────────
        # 用 `ctest --output-on-failure -V` 而非 `cmake.test()`：-V 把上游测试程序的
        # stdout 原样带回日志（含 `*** No errors detected` 与 death test 的执行消息），
        # 且 RUN 行本身是 CI L1c 门禁（grep "ctest"）的执行证据。
        run_log = os.path.join(self.build_folder, "upstream-tests.log")
        old_home = os.environ.get("HOME")
        sandbox = os.path.join(self.build_folder, "test-home")
        os.makedirs(sandbox, exist_ok=True)
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

        summary_ok = "*** No errors detected" in out
        ctest_ok = re.search(r"0 tests failed out of 1", out) is not None
        case_line = re.search(r"Test #1: arg_router_test .*", out)
        self.output.info(
            f"[upstream-tests] ctest rc={rc} ctest全过判定={'是' if ctest_ok else '否'} "
            f"程序摘要={'有' if summary_ok else '无'} "
            f"用例行={case_line.group(0) if case_line else '<未见>'}")
        if rc != 0:
            tail = "\n".join(out.splitlines()[-60:])
            raise Exception(f"上游测试 ctest rc={rc}（日志尾部）：\n{tail}")
        if not ctest_ok:
            raise Exception("ctest 未给出 `0 tests failed out of 1` —— "
                            "测试可能未真正执行（防 ctest 假绿）")
        if not summary_ok:
            raise Exception("上游测试程序未输出 `*** No errors detected` 收尾摘要")

        # ── 反假绿 3：N 与 N′ 的差额必须等于 10（归因不变）────────
        # N′（实跑）= 框架注册数：ctest 未带任何 `--run_test` 过滤，Boost.Test 默认
        # 全量执行已注册用例；ctest `0 tests failed out of 1` + 程序 rc=0（Boost.Test
        # 任一断言失败即非零退出）⇒ 已注册即已执行且全部通过。
        registered = len(listed_cases)
        delta = self.EXPECTED_SOURCE_MACROS - registered
        self.output.info(
            f"[upstream-tests] N(源码宏数)={self.EXPECTED_SOURCE_MACROS} "
            f"N'(框架注册=实跑)={registered} PASS={registered} FAIL=0 SKIP=0 "
            f"NOT_RUN={delta}（差额 10 = root_wrapper_test.cpp 4 + "
            f"string_selector_test.cpp 1（两文件整块 `#ifndef AR_ENABLE_CPP20_STRINGS`）+ "
            f"compile_time_string_test.cpp 5（`#else` C++17 分支），C++20 下上游条件编译排除）")
        if delta != 10:
            raise Exception(f"N − N' = {delta} != 10，差额归因失效（见 docstring §上游测试面）")

    def package(self):
        # header-only：交付 include/arg_router 头文件 + 许可证/README。
        # 不走上游 `cmake --install`：其 `install(EXPORT)` 会写出引用 `Boost::boost` /
        # `nonstd::span-lite` 的 arg_router-config.cmake，与 CMakeDeps 生成的配置在
        # `find_package(arg_router)` 上构成双配置竞争；Conan 侧由 cpp_info 提供目标。
        copy(self, "*.hpp",
             src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)
        copy(self, "README.md",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

        # 反假绿：安装树实物清点（头文件数必须 == 源码侧头文件数）
        def _hpp_count(base):
            n = 0
            for _root, _dirs, files in os.walk(base):
                n += sum(1 for f in files if f.endswith(".hpp"))
            return n

        src_headers = _hpp_count(os.path.join(self.source_folder, "include"))
        pkg_headers = _hpp_count(os.path.join(self.package_folder, "include"))
        self.output.info(f"[package] 头文件清点 源码={src_headers} 包内={pkg_headers}")
        if not pkg_headers or pkg_headers != src_headers:
            raise Exception(f"安装树头文件清点不符: 源码 {src_headers} != "
                            f"包内 {pkg_headers}（防 install 假绿）")

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "arg_router")
        self.cpp_info.set_property("cmake_target_name", "arg_router::arg_router")
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        # 不把包根 / share/arg_router 放进 CMAKE_PREFIX_PATH，避免上游 config 与
        # CMakeDeps 生成的 config 二选一歧义
        self.cpp_info.builddirs = []
