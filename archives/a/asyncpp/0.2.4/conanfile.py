#!/usr/bin/env python3
"""Conan recipe — asyncpp 0.2.4 (C++20 coroutine library for async/parallel programming).

CMake 构建，静态库 libasyncpp.a，0 个运行期依赖（上游 conanfile.txt 里的
catch2/celero 只服务上游单测与 benchmark）。

OHOS 适配要点（逐条证据见 notes.md，补丁逐条说明见 conandata.yml）：

* **工具链缺口**：OHOS SDK 26.0.0.18 的 clang 15.0.4 + libc++ 15004 缺
  ``std::jthread`` / ``std::stop_token`` / ``std::chrono::clock_cast``、缺
  ``std::vector::operator<=>``，且**不支持 C++20 括号聚合初始化（P0960）**；
  ``std::ranges`` 算法、ranges 视图与 ``<format>`` 被默认关掉，须
  ``_LIBCPP_ENABLE_EXPERIMENTAL`` 才可用（patches/0001-0010，全部为可移植性改写，
  上游用例与断言零改动）。
* **C++20**：OHOS profile 把 ``compiler.cppstd`` 钉在 17，而 asyncpp 必须 C++20
  （协程/concepts）⇒ generate() 覆盖 CMakeToolchain 的 cppstd 块为 20；
  validate() 只在 profile 显式高于 20 时才拒绝（libpqxx 8.0.1 同口径）。
* **上游单测**：test/（Catch2 3.x，154 个注册用例）在 build() 内构建并直跑，
  Catch2 汇总行 ``All tests passed (N assertions in 154 test cases)`` 直接落进
  conan-create.log 供 N/N′ 对账。**N 是断言数、随并发调度逐轮波动，不是稳定口径**
  （本机实测逐轮不同）；**用例数恒为 154**，所有申报口径一律以用例数为准，
  逐轮断言数与波动区间只记在 `reports/test-report.md` 与 PR 正文（工作区证据，不入库）。上游 CMake 没有 enable_testing()，
  ``ctest`` 会以 ``No tests were found!!!`` + rc=0 假绿（device-facts §二.22），
  故不使用 ctest 作为判据。
* **benchmark** 关闭：上游 benchmark/ 需要可选依赖 Celero（设备与 ohpcd 均无），
  按 W0「可选依赖缺省禁用」口径处理。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run, check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class AsyncppConan(ConanFile):
    name = "asyncpp"
    version = "0.2.4"
    description = "A C++20 coroutine library for asynchronous and parallel programming"
    license = "MIT"
    homepage = "https://github.com/petiaccja/asyncpp"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("coroutine", "c++20", "async", "parallel", "concurrency")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "run_upstream_tests": [True, False],
    }
    default_options = {"shared": False, "fPIC": True, "run_upstream_tests": True}

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # 上游单测框架（test/CMakeLists.txt: find_package(Catch2 3 REQUIRED)）。
        # test_requires 不传播给消费者；包本身 0 运行期依赖。
        if self.options.run_upstream_tests and can_run(self):
            self.test_requires("catch2/3.8.1")

    def validate(self):
        # 上游要求 C++20（协程 + concepts）。OHOS profile 固定 compiler.cppstd=17，
        # 但 clang 15.0.4 + libc++ 15004 实测可完整编译 asyncpp 的 C++20 源码
        # （generate() 把 cppstd 块覆盖为 20，证据见 notes.md），因此只在 profile
        # 显式抬高门槛（非 17/20）时才拒绝，绝不用被压低的 17 去卡。
        if str(self.settings.compiler.get_safe("cppstd", "17")) not in (
            "17", "20", "gnu17", "gnu20", "23", "gnu23",
        ):
            check_min_cppstd(self, 20)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.user_presets_path = False
        # OHOS profile 的 compiler.cppstd=17 会让 conan 注入 -std=c++17，
        # 覆盖 cppstd 块为 20（asyncpp 必须 C++20；libpqxx 8.0.1 同口径）。
        tc.blocks["cppstd"].values["cppstd"] = "20"
        run_tests = bool(self.options.run_upstream_tests) and can_run(self)
        tc.variables["ASYNCPP_BUILD_TESTS"] = "ON" if run_tests else "OFF"
        # 上游 benchmark/ 需要可选依赖 Celero（ohpcd 缺档）⇒ 按 W0 可选依赖缺省禁用。
        tc.variables["ASYNCPP_BUILD_BENCHMARKS"] = "OFF"
        # 只在 OHOS 上开启 libc++ experimental（std::ranges / <format>）。
        tc.variables["ASYNCPP_LIBCXX_EXPERIMENTAL"] = "ON" if str(self.settings.os) == "OHOS" else "OFF"
        tc.generate()
        CMakeDeps(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if self.options.run_upstream_tests and can_run(self):
            # 上游 CMake 未调用 enable_testing() ⇒ ctest 恒空跑（rc=0 假绿），
            # 判据用 Catch2 二进制直跑：--durations yes 让 154 个用例名逐行落日志，
            # 结尾汇总行给出用例数与断言数（N/N′ 对账的原始证据）。
            test_bin = os.path.join(self.build_folder, "bin", "test")
            self.run('"%s" --durations yes' % test_bin)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE.md",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "asyncpp")
        self.cpp_info.set_property("cmake_target_name", "asyncpp::asyncpp")
        self.cpp_info.libs = ["asyncpp"]
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
        if str(self.settings.os) == "OHOS":
            # src/testing/interleaver.cpp 使用 std::format；OHOS 共享 libc++ 的
            # format 运行时符号在 libc++experimental.a（libpqxx 8.0.1、
            # ladybug 0.18.2 同口径）。公开头不依赖 experimental 特性，
            # 因此不向消费者下发 _LIBCPP_ENABLE_EXPERIMENTAL 宏。
            self.cpp_info.system_libs.append("c++experimental")
