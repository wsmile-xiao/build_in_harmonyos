#!/usr/bin/env python3
"""Conan recipe — inversify-cpp 2.1.0 (header-only C++17 IoC/DI 容器).

上游交付形态：纯头文件（include/mosure/**，另有 amalgamated single_include/），
零运行依赖、零编译产物 —— package_type=header-library + implements auto_header_only_mode，
package() 只交付 include/ 与 licenses/。

上游测试面（R51 上游测试三步法）：
- 上游唯一构建面是 Bazel（根 BUILD / WORKSPACE / .bazelrc），设备与 CI worker 均无 bazel；
  上游测试源在 test/*.cpp（6 个 TU，Catch2 v2 单头 third_party/catch.hpp 随包 vendored），
  用例宏为 SCENARIO/GIVEN/WHEN/THEN + REQUIRE，另有 2 个 BENCHMARK 落在 speed.cpp 的 SCENARIO 内。
- 本配方 build() 直接用 profile 的 C++ 编译器把 6 个 TU 编成一个测试可执行并真跑，
  命令与上游 BUILD 的 cc_binary("test") 逐项对齐（-std=c++17 -DINVERSIFY_BINDING_INSPECTION
  -I include -I third_party -I test），干净轮 G2/W3 日志可见
  `All tests passed (25 assertions in 5 test cases)`。
- 计数口径（候选数法取最大、四口径不混用）：口径①源码宏 SCENARIO=5、口径②框架注册
  `--list-tests`=5 ⇒ **N=5（单位=用例）**；口径③断言=25（单位=断言，运行期自报
  `25 assertions in 5 test cases`，单列不与用例数混）；口径④消费者断言 23 在
  test_package，不进上游分母。①②差额 0。
"""
import glob
import json
import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout
from conan.tools.scm import Version


class InversifyCppConan(ConanFile):
    name = "inversify-cpp"
    version = "2.1.0"
    description = "C++17 inversion of control and dependency injection container library."
    license = "MIT"
    homepage = "https://github.com/mosure/inversify-cpp"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("ioc", "container", "dependency-injection", "header-only")

    package_type = "header-library"
    implements = ["auto_header_only_mode"]

    settings = "os", "arch", "compiler", "build_type"
    # header-only：源码只读，build() 直接读 source_folder，不复制到 build 目录
    no_copy_source = True

    def export_sources(self):
        # G1 结构门禁：本包零补丁（conandata.yml 无 patches 键），调用即打印
        # "No patches defined in conandata" 并返回，不引入任何文件
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    @property
    def _min_cppstd(self):
        # 与 CCI recipes/inversify-cpp/all/conanfile.py 同口径（上游 README 与
        # BUILD 的 cc_library(-std=c++17) 自报 17）
        return 17

    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, self._min_cppstd)
        minimum_version = {
            "gcc": "7",
            "msvc": "191",
            "Visual Studio": "15.7",
            "clang": "6",
            "apple-clang": "11",
        }.get(str(self.settings.compiler), False)
        if minimum_version and Version(str(self.settings.compiler.version)) < minimum_version:
            raise ConanInvalidConfiguration(
                f"inversify-cpp requires C++{self._min_cppstd}, "
                f"but {self.settings.compiler} {self.settings.compiler.version} is too old.")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    # ── 上游测试集成（R51；上游构建面是 Bazel，此处按上游 BUILD 参数等价直编）──
    @property
    def _cxx(self):
        conf = self.conf.get("tools.build:compiler_executables", default=None)
        if isinstance(conf, dict):
            return conf.get("cpp") or conf.get("c") or "clang++"
        if isinstance(conf, str):
            try:
                parsed = json.loads(conf)
            except ValueError:
                parsed = None
            if isinstance(parsed, dict):
                return parsed.get("cpp") or parsed.get("c") or "clang++"
        return "clang++"

    def build(self):
        # G1 结构门禁：本包 conandata 无 patches 键 ⇒ 打印 "No patches defined" 后返回
        apply_conandata_patches(self)
        if self.conf.get("tools.build:skip_test", default=False):
            return
        src = self.source_folder
        test_srcs = sorted(glob.glob(os.path.join(src, "test", "*.cpp")))
        if not test_srcs:
            raise ConanInvalidConfiguration(
                "上游 test/*.cpp 未命中：上游测试面缺失，无法执行上游测试（禁止静默跳过）")
        binary = os.path.join(self.build_folder, "inversify-cpp-upstream-test")
        cmd = [self._cxx,
               "-std=c++17",
               "-DINVERSIFY_BINDING_INSPECTION",
               "-I", os.path.join(src, "include"),
               "-I", os.path.join(src, "third_party"),
               "-I", os.path.join(src, "test"),
               *test_srcs,
               "-o", binary]
        # 单进程顺序编译 6 个 TU：不引入 -j 超订（本机 affinity 8 / os.cpu_count 20）
        self.run(" ".join(shlex.quote(part) for part in cmd), cwd=src)
        # 真跑上游用例：汇总行 `All tests passed (25 assertions in 5 test cases)`
        self.run(shlex.quote(binary), cwd=self.build_folder)

    def package(self):
        copy(self, "*",
             src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "inversify-cpp")
        self.cpp_info.set_property("cmake_target_name", "inversify-cpp::inversify-cpp")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
