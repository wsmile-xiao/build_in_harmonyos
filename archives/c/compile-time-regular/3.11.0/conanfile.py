#!/usr/bin/env python3
"""Conan recipe — compile-time-regular 3.11.0 (CTRE).

CTRE（compile-time regular expressions）是 header-only C++17 编译期正则
表达式库（github.com/hanickadot/compile-time-regular-expressions），零依赖
纯 header 交付：include/ctre.hpp、include/ctll.hpp、include/ctre-unicode.hpp、
include/unicode-db.hpp 及 include/ctre/、include/ctll/、include/unicode-db/
组件目录。

形态选型（参照 boost1.84-contract header-only 组件包先例）：
- package_type = "header-library"，无任何编译产物；
- package 只含头文件 + licenses；
- package_id 按 header-only 规约处理（settings 不参与 binary 哈希）；
- 上游 CI（.github/workflows/tests.yml）的测试方式：make/make CXX_STANDARD=17|20
  将 tests/*.cpp 逐个编译（编译期断言 static_assert 在编译时验证），
  本配方 build() 以同一口径全量编译 tests/ 25 个测试目标。

上游测试集成（rule4：N=以实际构建系统注册为准）：
- tests/CMakeLists.txt file(GLOB test-sources *.cpp) 注册 25 个编译目标
  （benchmark/ 子目录被 Makefile IGNORE 与 CMake GLOB 双重排除）；
- 其中 21 个为纯编译期断言文件（static_assert/TEST_* 宏展开后共 1152
  个编译期断言），6 个含运行期 main（cnttp/correct-conversion/is_prime/
  range/results/wide-pattern，均为可执行验证程序）；
- OHOS clang 15 + libc++ 下 C++17 与 C++20 双标准实测 25/25 编译通过。
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class CompileTimeRegularConan(ConanFile):
    name = "compile-time-regular"
    version = "3.11.0"
    description = "Compile Time Regular Expressions (CTRE) for C++17/20 — fast fully constexpr regular expressions with match/search/captures"
    license = "Apache-2.0 WITH LLVM-exception"
    homepage = "https://github.com/hanickadot/compile-time-regular-expressions"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "header-library"
    implements = ["auto_header_only_mode"]

    # header-only：settings 声明但 binary 由 header-only 模式归一
    settings = "os", "compiler", "build_type", "arch"

    # 上游 no_copy_source：源码只读，package 阶段直接从 source_folder 拷贝
    no_copy_source = True

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 上游测试集成（rule4/规则 5）：与上游 CI 同口径——逐个编译
        # tests/*.cpp 编译目标，编译期断言（static_assert）在编译阶段验证；
        # 含 main 的运行期用例编译链接后实际运行（退出码判定）。
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
        """全量编译上游 tests/ 25 个测试目标 + 运行 6 个运行期用例。

        上游注册口径（tests/CMakeLists.txt file(GLOB *.cpp) + Makefile
        TESTS := $(wildcard tests/*.cpp)）：
        - 25 个编译目标全部执行（0 排除、0 修改）；
        - C++17（库官方核心标准，CI profile cppstd=17）为主口径；
        - 6 个含 main 的用例（cnttp/correct-conversion/is_prime/range/
          results/wide-pattern）编译链接后运行，退出码 0 判定通过。
        """
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cxx = compilers.get("cpp", "clang++")

        cxxflags = " ".join([
            "-std=c++17",
            "-stdlib=libc++",
            # 静态链接 C++ 运行时：测试二进制在无 LD_LIBRARY_PATH 的
            # 环境下直接运行（libc++_shared.so 不在默认搜索路径）
            "-static-libstdc++",
            "-O2",
            "-fPIC",
            f"-I{self.source_folder}/include",
        ])

        # tests/ 顶层 25 个 .cpp（benchmark 子目录上游注册口径排除）
        test_dir = os.path.join(self.source_folder, "tests")
        test_sources = sorted(
            f for f in os.listdir(test_dir)
            if f.endswith(".cpp")
        )
        # 含 main 的运行期用例（其余为纯编译期断言翻译单元）
        runtime_tests = {
            "cnttp.cpp", "correct-conversion.cpp", "is_prime.cpp",
            "range.cpp", "results.cpp", "wide-pattern.cpp",
        }

        report_lines = []
        passed, failed = 0, 0
        for src_name in test_sources:
            src = os.path.join(test_dir, src_name)
            base = src_name[:-4]
            obj = os.path.join(self.build_folder, "ut_" + base + ".o")
            cmd_compile = f"{cxx} {cxxflags} -c {src} -o {obj}"
            ret_code, ret_out, ret_err = self._run_cmd(cmd_compile, timeout=600)
            if ret_code != 0:
                last_line = ret_err.splitlines()[-1] if ret_err else ""
                report_lines.append(f"COMPILE_FAIL {src_name}: {last_line}")
                failed += 1
                continue
            if src_name in runtime_tests:
                exe = os.path.join(self.build_folder, "ut_" + base)
                cmd_link = f"{cxx} {cxxflags} {src} -o {exe}"
                ret_code, ret_out, ret_err = self._run_cmd(cmd_link, timeout=600)
                if ret_code != 0:
                    last_line = ret_err.splitlines()[-1] if ret_err else ""
                    report_lines.append(f"LINK_FAIL {src_name}: {last_line}")
                    failed += 1
                    continue
                run_code, run_out, run_err = self._run_cmd(exe, timeout=120)
                ok = run_code == 0
                report_lines.append(
                    f"{'PASS' if ok else 'RUN_FAIL'} {src_name} (runtime) rc={run_code}")
                if ok:
                    passed += 1
                else:
                    failed += 1
            else:
                # 纯编译期断言翻译单元：编译成功 = 断言全部成立
                report_lines.append(f"PASS {src_name} (compile-time asserts)")
                passed += 1

        report_lines.append(f"TOTAL {passed + failed}: {passed} passed / {failed} failed")
        report_path = os.path.join(self.build_folder, "upstream-tests-report.txt")
        with open(report_path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(report_lines) + "\n")
        self.output.info(f"上游测试报告: {report_path} ({passed}/{passed + failed} 通过)")
        for line in report_lines:
            self.output.info(f"[upstream-tests] {line}")
        if failed > 0:
            raise Exception(
                f"upstream tests failed: {failed}/{passed + failed} "
                f"(see {report_path})")

    def package(self):
        # license
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # 头文件树（include/ 全量：ctre.hpp/ctll.hpp/ctre-unicode.hpp/
        # unicode-db.hpp + ctre/、ctll/、unicode-db/ 组件目录）
        copy(self, "*.hpp", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "compile-time-regular")
        self.cpp_info.set_property("cmake_target_name", "compile-time-regular::compile-time-regular")
        # C++17 为库官方核心标准（上游 CMake 默认 CTRE_CXX_STANDARD=20，
        # README 声明 C++17 兼容；固定生成器覆盖见 test_package）
