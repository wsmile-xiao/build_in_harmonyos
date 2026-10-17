#!/usr/bin/env python3
"""Conan recipe — sockpp 1.0.0（C++ 套接字库，CMake 构建）。

上游: https://github.com/fpagliughi/sockpp （tag v1.0.0）
许可证: BSD-3-Clause；运行期依赖: 0（仅测试需要 Catch2，test_requires）

OHOS / HarmonyOS 适配要点（详见 notes.md）:

1. E092 平台名 —— conan 的 CMakeToolchain 不写 CMAKE_SYSTEM_NAME，CMake 退回
   `uname=HarmonyOS` 得到「System is unknown to cmake」，平台变量
   （CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG 等）留空 ⇒ 共享库丢失 DT_SONAME
   （实测无 CMAKE_SYSTEM_NAME 时 readelf -d 无 SONAME 条目）。按 E092
   rec_priority=1 显式钉 CMAKE_SYSTEM_NAME=Linux + CMAKE_SYSTEM_PROCESSOR=aarch64，
   修后 DT_SONAME 恢复为 libsockpp.so.1。
2. 上游 tests/unit/CMakeLists.txt 只在子目录 include(CTest)，顶层 CMakeLists
   没有 enable_testing() ⇒ 构建根目录根本不生成 CTestTestfile.cmake，在根目录
   跑 `ctest` 打印「No tests were found!!!」且 **rc=0**（假绿）。测试必须在
   tests/unit 子目录内执行。
3. 上游未把 test_inet6_address.cpp / test_result.cpp 列入 add_executable，
   test_socket.cpp 与 test_stream_socket.cpp 各有一个 `#if 0` 死块用例 ⇒
   源码 TEST_CASE 宏 43 个、实际注册并执行 33 个；差额 10 逐项归因
   （8 个未进上游构建 + 2 个死块），见 notes.md 与 reports/test-report.md。
4. R26：默认静态库（shared=False），可选 shared=True。
"""
import json
import os
import re
import subprocess

from conan import ConanFile
from conan.tools.build import check_min_cppstd, cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rmdir,
)


class SockppConan(ConanFile):
    name = "sockpp"
    version = "1.0.0"
    license = "BSD-3-Clause"
    homepage = "https://github.com/fpagliughi/sockpp"
    url = ""  # CI fills this
    description = "Modern C++ socket library"
    topics = ("sockets", "networking", "cpp")
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "run_upstream_tests": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "run_upstream_tests": True,
    }
    implements = ["auto_shared_fpic"]

    # CMakeDeps 只为测试依赖 Catch2 服务（find_package(Catch2 REQUIRED)）
    generators = "CMakeDeps"
    languages = "C++"

    def export_sources(self):
        # 本包无补丁（conandata.yml 无 patches: 段）；保留该入口以满足
        # conan-verify G1 的配方完整性检查，并让未来补丁随配方一起导出。
        export_conandata_patches(self)

    def requirements(self):
        # 运行期 0 依赖（W0-2 已核 ohpcd 远端）
        pass

    def build_requirements(self):
        if self.options.run_upstream_tests:
            # 仅测试期需要，不传播给消费者（同 socket-wrapper 的 cmocka 用法）
            self.test_requires("catch2/3.8.1")

    def validate(self):
        check_min_cppstd(self, 14)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)

        # R26: 默认静态；上游两个目标互斥开关
        tc.variables["SOCKPP_BUILD_SHARED"] = "ON" if self.options.shared else "OFF"
        tc.variables["SOCKPP_BUILD_STATIC"] = "OFF" if self.options.shared else "ON"
        tc.variables["SOCKPP_BUILD_EXAMPLES"] = "OFF"
        tc.variables["SOCKPP_BUILD_DOCUMENTATION"] = "OFF"
        tc.variables["SOCKPP_BUILD_CAN"] = "OFF"
        tc.variables["SOCKPP_BUILD_TESTS"] = (
            "ON" if self.options.run_upstream_tests else "OFF"
        )

        if str(self.settings.os) == "OHOS":
            # E092: 见文件头注释 1（钉 Linux 让平台模块生效、保住 DT_SONAME）
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
            # GNUInstallDirs 在 Linux 分支可能落到 lib64；钉 lib/ 与
            # cpp_info.libdirs 一致
            tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"

        if self.options.run_upstream_tests:
            # 上游 include(Catch) 需要 Catch2 安装的 CMake 模块目录；
            # CMakeDeps 生成的 Catch2Config 不会把它放进 CMAKE_MODULE_PATH。
            catch2 = self.dependencies["catch2"]
            tc.variables["CMAKE_MODULE_PATH"] = os.path.join(
                catch2.package_folder, "lib", "cmake", "Catch2"
            ).replace("\\", "/")

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if self.options.run_upstream_tests and not cross_building(self):
            self._run_upstream_tests()

    def _run_upstream_tests(self):
        """在 tests/unit 子目录内跑上游 CTest 套件（见文件头注释 2）。

        全部用例真实执行；任一失败即抛异常让 conan create 失败（不吞错）。
        """
        unit_dir = os.path.join(self.build_folder, "tests", "unit")
        exe = os.path.join(unit_dir, "unit_tests")
        if not os.path.isfile(exe):
            raise RuntimeError(f"上游测试可执行文件缺失: {exe}")

        env = Environment()
        if self.options.shared:
            # OHOS loader 不搜索可执行文件所在目录
            env.append_path("LD_LIBRARY_PATH", self.build_folder)

        with env.vars(self).apply():
            # 逐用例证据（33 行 Passed/Failed 落在 conan create 日志里）
            self.run("ctest -N", cwd=unit_dir)
            self.run("ctest --output-on-failure -j1", cwd=unit_dir)

            # Catch2 聚合摘要（断言数口径）——单独跑一遍取 summary
            proc = subprocess.run(
                [exe],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                errors="replace",
                timeout=1800,
            )
            out = proc.stdout or ""
            m = re.search(
                r"All tests passed \((\d+) assertions in (\d+) test cases\)", out
            )
            if m:
                assertions, cases, failed = int(m.group(1)), int(m.group(2)), 0
            else:
                m2 = re.search(
                    r"test cases: (\d+) \| (\d+) passed \| (\d+) failed", out
                )
                if not m2:
                    raise RuntimeError(
                        "无法解析 Catch2 摘要，拒绝在无读数的情况下判定测试结论。"
                        f" 尾部输出:\n{out[-2000:]}"
                    )
                cases = int(m2.group(1))
                failed = int(m2.group(3))
                ma = re.search(
                    r"assertions: (\d+) \| (\d+) passed \| (\d+) failed", out
                )
                assertions = int(ma.group(1)) if ma else 0

        if proc.returncode != 0 or failed:
            raise RuntimeError(
                f"上游单测失败: exit={proc.returncode} failed_cases={failed}\n"
                f"{out[-3000:]}"
            )

        upstream = {
            "status": "passed",
            "framework": "catch2",
            "command": "ctest --output-on-failure -j1 (cwd=build/tests/unit)",
            "discovered": cases,
            "executed": cases,
            "passed": cases,
            "failed": 0,
            "skipped": 0,
            "assertions": assertions,
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False)
        )

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        # 上游 install(EXPORT) 落下的 cmake 配置与 CMakeDeps 生成物重名；
        # 保留会让 find_package 解析到上游目标名，交由 conan 侧统一提供。
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "sockpp")
        self.cpp_info.set_property("cmake_target_name", "sockpp::sockpp")
        self.cpp_info.libs = ["sockpp"]
