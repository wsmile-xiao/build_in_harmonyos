#!/usr/bin/env python3
"""Conan recipe — boost1.84-contract 1.84.0 (Boost.Contract component package).

Boost.Contract 是 header-only 组件（默认编译模式即 BOOST_CONTRACT_HEADER_ONLY，
不定义 BOOST_CONTRACT_DYN_LINK/STATIC_LINK 时自动生效，见
boost/contract/core/config.hpp L110）。

组件拆分包定位：
- 依赖元包 boost/1.84.0（提供完整 boost 头文件树，含已 patch 的
  boost/core/detail/sp_thread_sleep.hpp，元包已发布到制品仓）；
- 本包从官方源码 tarball 打包 contract 组件专属头文件
  （boost/contract.hpp + boost/contract/），版本锁定 1.84.0；
- build() 阶段编译并运行上游 libs/contract/test 测试（绕过 b2，
  b2 构建系统在 OHOS 不兼容，E068）。

已知平台限制（与底稿 boost/1.84.0 相同）：
- OHOS musl 无 pthread_setcancelstate，通过 patch +
  BOOST_SP_NO_PTHREAD_SETCANCELSTATE 特性检测宏守卫（R8 合规）。
  该文件（boost/core/...）由元包提供，本包产物不含；patch 用于
  build() 阶段源码树跑上游测试。
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class Boost184ContractConan(ConanFile):
    name = "boost1.84-contract"
    version = "1.84.0"
    description = "Boost.Contract 1.84.0 组件包（契约编程：前置/后置条件、类不变式、子契约转发等，header-only）"
    license = "BSL-1.0"
    homepage = "https://www.boost.org/doc/libs/1_84_0/libs/contract/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 元包提供完整 boost headers（含 contract 依赖的 core/smart_ptr/thread
        # 等 header-only 库与已 patch 的 sp_thread_sleep.hpp）及 4 个编译库。
        self.requires("boost/1.84.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # 上游测试集成（规则 5）：b2 在 OHOS 不可用（E068），手动编译运行
        # libs/contract/test 下的代表性测试（全部基于
        # boost/detail/lightweight_test.hpp，无需链接 Boost.Test 库）。
        self._run_upstream_tests()

    def _run_cmd(self, cmd, timeout):
        """带超时与进程组清理的命令执行（防孤儿 clang++ 占用 CI worker）。"""
        import signal
        import subprocess
        proc = subprocess.Popen(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, stdin=subprocess.DEVNULL, start_new_session=True)
        try:
            out, err = proc.communicate(timeout=timeout)
            return proc.returncode, out, err
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                proc.kill()
            out, err = proc.communicate()
            return -1, out, err

    def _run_upstream_tests(self):
        """编译并运行上游 contract 测试源文件（绕过 b2），统计通过率。

        测试文件来自 boost_1_84_0/libs/contract/test/，使用上游自带
        lightweight_test 框架（boost/detail/lightweight_test.hpp，header-only），
        编译后直接运行，以退出码 0 判定通过。

        子集选择（226 个测试文件中选 32 个代表性用例）：
        - 排除 *_error.cpp：上游为"期望编译失败"用例，需编译期断言框架，
          不适合直接编译运行（上游 Jamfile 中同样仅做 compile-fails 检查）；
        - 排除 lib_*.cpp / *_lib.cpp / disable/*_lib.cpp：库编译模式
          （BOOST_CONTRACT_DYN_LINK/STATIC_LINK）辅助翻译单元，非独立测试；
        - 排除 no_tva 变体：与同名主用例仅差禁用 template virtual args，
          保留主用例即可覆盖；
        - 覆盖 constructor/destructor/function/public_function/invariant/
          old/call_if/check/smoke 核心特性面。
        """
        boost_root = self.source_folder
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cxx = compilers.get("cpp", "clang++")

        if self.settings.build_type == "Debug":
            opt_flags = "-O0 -g"
        else:
            opt_flags = "-O2 -DNDEBUG"
        cxxflags = " ".join([
            "-std=c++17",
            "-stdlib=libc++",
            # 静态链接 C++ 运行时：上游测试二进制在无 LD_LIBRARY_PATH 的
            # 环境下直接运行（libc++_shared.so 不在默认搜索路径）
            "-static-libstdc++",
            opt_flags,
            "-fPIC",
            f"-I{boost_root}",
            # R8：特性检测宏守卫（patch 消费），非平台宏
            "-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE",
            # 上游测试不使用 auto-link（鸿蒙无该机制）
            "-DBOOST_TEST_NO_LIB",
        ])

        test_cases = [
            # (相对路径, 额外编译宏, 说明)
            ("check/ifdef", "", "断言级别宏开关"),
            ("check/audit", "-DBOOST_CONTRACT_AUDITS", "audit 级断言"),
            ("check/axiom", "", "axiom 级断言"),
            ("constructor/smoke", "", "构造函数契约冒烟"),
            ("constructor/access", "", "构造函数访问控制"),
            ("constructor/throwing_body", "", "构造函数体抛异常"),
            ("constructor/throwing_old", "", "old 值拷贝抛异常"),
            ("destructor/smoke", "", "析构函数契约冒烟"),
            ("destructor/throwing_body", "", "析构函数体抛异常"),
            ("function/smoke", "", "自由函数契约冒烟"),
            ("function/throwing_pre", "", "前置条件抛异常"),
            ("function/throwing_post", "", "后置条件抛异常"),
            ("public_function/smoke", "", "成员函数契约冒烟"),
            ("public_function/static", "", "静态成员函数契约"),
            ("public_function/protected", "", "受保护成员函数契约"),
            ("public_function/virtual", "", "虚函数契约"),
            ("public_function/virtual_branch", "", "虚函数分支契约"),
            ("public_function/overload", "", "重载成员函数契约"),
            ("public_function/friend", "", "友元函数契约"),
            ("public_function/max_args", "", "最大参数数契约"),
            ("invariant/decl_const", "", "const 不变式"),
            ("invariant/decl_static", "", "静态不变式"),
            ("old/no_macro", "", "无宏 old 值"),
            ("old/auto", "", "auto old 值"),
            ("old/if_copyable", "", "可拷贝 old 值"),
            ("call_if/false_", "", "call_if false 分支"),
            ("call_if/true_", "", "call_if true 分支"),
            ("call_if/equal_to", "", "call_if STL equal_to"),
            ("call_if/false_void", "", "call_if void 返回"),
            ("call_if/no_equal_call_if", "", "call_if 无相等比较"),
            ("specify/nothing", "", "空契约说明"),
            ("specify/old", "", "old 值说明"),
        ]

        report_lines = []
        passed, failed = 0, 0
        for rel, extra_defs, desc in test_cases:
            src = os.path.join(boost_root, "libs", "contract", "test", rel + ".cpp")
            if not os.path.isfile(src):
                report_lines.append(f"SKIP {rel}: source not found")
                continue
            exe = os.path.join(self.build_folder, "ut_" + rel.replace("/", "_"))
            cmd_compile = f"{cxx} {cxxflags} {extra_defs} {src} -o {exe}"
            ret_code, ret_out, ret_err = self._run_cmd(cmd_compile, timeout=300)
            if ret_code != 0:
                last_line = ret_err.splitlines()[-1] if ret_err else ""
                report_lines.append(f"COMPILE_FAIL {rel} ({desc}): {last_line}")
                failed += 1
                continue
            run_code, run_out, run_err = self._run_cmd(exe, timeout=120)
            ok = run_code == 0
            report_lines.append(f"{'PASS' if ok else 'FAIL'} {rel} ({desc}) rc={run_code}")
            if ok:
                passed += 1
            else:
                failed += 1

        report_lines.append(f"TOTAL {passed + failed}: {passed} passed / {failed} failed")
        report_path = os.path.join(self.build_folder, "upstream-tests-report.txt")
        with open(report_path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(report_lines) + "\n")
        self.output.info(f"上游测试报告: {report_path} ({passed}/{passed + failed} 通过)")
        for line in report_lines[-5:]:
            self.output.info(f"[upstream-tests] {line}")
        if failed > 0:
            raise Exception(
                f"upstream contract tests failed: {failed}/{passed + failed} "
                f"(see {report_path})")

    def package(self):
        # contract 组件专属头文件（其余 boost headers 由元包 boost/1.84.0 提供）
        copy(self, "boost/contract.hpp", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "boost/contract/*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        # R8 合规：向所有消费者传播特性检测宏（元包 boost_headers 组件同样
        # 传播；此处双保险，防止消费者单独引用本包时遗漏）。
        self.cpp_info.defines = ["BOOST_SP_NO_PTHREAD_SETCANCELSTATE"]
        self.cpp_info.set_property("cmake_file_name", "boost1.84-contract")
        self.cpp_info.set_property("cmake_target_name", "boost1.84-contract::boost1.84-contract")
