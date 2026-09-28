#!/usr/bin/env python3
"""Conan recipe — namedtype 1.1.0（header-only C++ 强类型命名库）.

上游 joboccara/NamedType 是 INTERFACE（header-only）库：
  - 根 CMakeLists.txt 只 `add_library(NamedType INTERFACE)`，**没有 install 规则**，
    所以 package() 直接按头文件树复制；
  - 上游自带 `test/`（Catch1 单头 test/catch.hpp + test/main.cpp），根
    `set(ENABLE_TEST ON CACHE BOOL "Enable test")` 默认开启，本配方在 build()
    里真实编译并运行它（R51 上游测试三步法），把 Catch 的
    "All tests passed (N assertions in M test cases)" 与源码静态清点对账，
    两边不相等即直接失败——防 "All 0 tests passed" 假绿（device-facts §二.22）。

两处适配（证据与根因见 notes.md、$TASK_DIR/w0-evidence.md）：
  0001  named_type_impl.hpp 缺 #include <tuple> → header 非自包含（补一行）
  0002  test/CMakeLists.txt 非 MSVC 分支带 4 个 GCC 专属 -W* 开关
        （-Wlogical-op -Wnoexcept -Wstrict-null-sentinel -Wuseless-cast），
        clang 15 报 unknown warning option 且被上游 -Werror 放大成硬错；
        补丁追加 -Wno-unknown-warning-option，只降级该一条诊断，
        其余 -Werror 告警面全部保留（先例 a/asterisk-* 与 a/acpica/20251212
        同判据）。放在补丁里而非工具链注入，是为了让「解包 + 打补丁 + 裸
        cmake」这条 clean-verify(G0) 路径同样能构建成功。
"""
import os
import re
import signal
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)


class NamedtypeConan(ConanFile):
    name = "namedtype"
    version = "1.1.0"
    description = "NamedType — a header-only C++11/17 library to create strongly typed distinct types (fluent::NamedType)"
    license = "MIT"
    homepage = "https://github.com/joboccara/NamedType"
    url = ""  # CI fills this

    package_type = "header-library"
    implements = ["auto_header_only_mode"]

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # 根 CMakeLists.txt: set(ENABLE_TEST ON CACHE BOOL "Enable test")
        # 默认即 ON；显式钉死，使 test/ 的构建输入不随 profile 漂移。
        # （clang 未知告警名的处理见补丁 0002，不在工具链里注入——这样
        #   「解包 + 打补丁 + 裸 cmake」的 clean-verify(G0) 路径同样可构建。）
        tc.variables["ENABLE_TEST"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if can_run(self):
            self._run_upstream_tests()
        else:
            self.output.info("[upstream-tests] SKIP: 交叉构建 can_run=False")

    # ── 上游测试（R51 上游测试三步法）────────────────────────────────────
    def _run_upstream_tests(self):
        """编译并运行上游 test/（Catch1），并与源码静态清点对账。

        判绿三件套（device-facts §二.22）：
          ① 解析 Catch 的 "All tests passed (N assertions in M test cases)"；
          ② N/M 必须 > 0（"All 0 tests passed" 即红警）；
          ③ N/M 必须等于对 test/main.cpp 的静态清点（框架注册 == 源码宏）。
        """
        src = os.path.join(self.source_folder, "test", "main.cpp")
        if not os.path.isfile(src):
            raise Exception(f"上游测试源缺失: {src}")
        static_cases = self._count_test_cases(src)
        static_asserts = self._count_assertions(src)
        self.output.info(
            "[upstream-tests] 静态清点 test/main.cpp: "
            f"TEST_CASE={static_cases}, 断言宏={static_asserts}")

        exe = os.path.join(self.build_folder, "test", "NamedTypeTest")
        if not os.path.isfile(exe):
            raise Exception(f"上游测试程序未生成: {exe}")

        rc, out, err = self._run_cmd(f'"{exe}"', cwd=os.path.join(self.build_folder, "test"),
                                     timeout=600)
        for line in (out + err).strip().splitlines():
            self.output.info(f"[upstream-catch] {line}")
        if rc != 0:
            raise Exception(f"上游测试程序 rc={rc}（存在失败断言）")

        m = re.search(r"All tests passed \((\d+) assertions in (\d+) test cases\)", out)
        if not m:
            raise Exception("未在上游测试输出中找到 'All tests passed (N assertions in M test cases)'，"
                            "不得据 rc=0 判绿")
        n_assert, n_case = int(m.group(1)), int(m.group(2))
        if n_assert <= 0 or n_case <= 0:
            raise Exception(f"0 用例/0 断言通过（假绿红警）: {out.strip()}")
        if (n_assert, n_case) != (static_asserts, static_cases):
            raise Exception(
                f"运行期与静态清点不一致: 运行期 {n_assert}/{n_case} vs "
                f"静态 {static_asserts}/{static_cases}（框架注册数与源码宏数必须对账）")
        self.output.info(
            f"[upstream-tests] RUN rc=0 → {n_assert}/{n_assert} 断言、"
            f"{n_case}/{n_case} 用例全部通过（运行期 == 静态清点）")

    @staticmethod
    def _run_cmd(cmd, cwd=None, timeout=600):
        proc = subprocess.Popen(
            cmd, shell=True, cwd=cwd, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, stdin=subprocess.DEVNULL,
            start_new_session=True)
        try:
            out, err = proc.communicate(timeout=timeout)
            return proc.returncode, out, err
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                proc.kill()
            out, err = proc.communicate()
            return -1, out, err

    @staticmethod
    def _count_test_cases(main_cpp):
        with open(main_cpp, encoding="utf-8", errors="replace") as fh:
            return len(re.findall(r"^\s*TEST_CASE\s*\(", fh.read(), re.M))

    @staticmethod
    def _count_assertions(main_cpp):
        # Catch1 断言宏族：REQUIRE/CHECK 加可选 _Xxx 后缀（THROWS/NOTHROW/THROWS_AS…）
        with open(main_cpp, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        # 去掉整行注释，避免注释里的示例被计数
        text = "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("//"))
        return len(re.findall(r"\b(?:REQUIRE|CHECK)(?:_[A-Z_]+)?\s*\(", text))

    # ── 打包（上游无 install 规则，按头文件树复制）─────────────────────────
    def package(self):
        copy(self, "*.hpp",
             src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"),
             keep_path=True)
        copy(self, "LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "namedtype")
        self.cpp_info.set_property("cmake_target_name", "namedtype::namedtype")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
