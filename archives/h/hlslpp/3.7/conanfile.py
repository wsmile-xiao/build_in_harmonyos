#!/usr/bin/env python3
"""Conan recipe — hlslpp 3.7 (HLSL 风格 C++ 向量/矩阵/四元数数学库，header-only).

hlslpp 提供与 HLSL 着色器语法一致的 float2/3/4、矩阵与四元数类型，供图形/游戏
应用在 CPU 侧复用 HLSL 风格的数学代码。库为纯头文件实现（include/hlsl++.h 及
include/hlsl++/*.h），按目标架构自动选择后端：SSE/AVX（x86）、NEON（aarch64）、
WASM SIMD、scalar。鸿蒙 PC（aarch64）由 config.h 依据 __aarch64__ 自动选择
NEON 后端（include/hlsl++/platforms/neon.h），零第三方依赖。

上游测试位于 unit_tests/（8 个 .cpp），使用自研 hlslpp_unit 断言框架
（BeginTest/EndTest/BeginTestCase/EndTestCase + hlslpp_check），共 46 个测试
用例、1061 处 hlslpp_check 断言。上游构建脚本为 premake5（hlsl++.lua），
不产出 CMake 工程，因此本配方自带 test_upstream/CMakeLists.txt
（exports_sources）编译并执行上游测试；测试运行器由 conan profile 的
CMAKE_CROSSCOMPILING_EMULATOR 注入（qemu-aarch64），故 os=OHOS 交叉编译场景下
也能真实运行上游测试（不因 can_run()==False 而跳过）。

关键适配点（详见 notes.md）：aarch64 上 clang 默认 -ffp-contract=fast，而
ARMv8 强制具备 FMA，导致 mul(mat_bar_2x2, mat_foo_2x3) 的 r[1][1] 因乘加融合
与上游硬编码期望值相差 +1 ULP（2.60000014 vs 2.5999999）。上游 "Float Matrix
Multiplication" 用例使用 tolerance=0.0f 精确比较，故对 FMA 敏感。适配时仅对
上游测试翻译单元关闭 FMA 收缩（-ffp-contract=off），恢复上游期望值，46/46
全部通过；库源码零改动，对外发布的头文件不附加任何编译选项。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rmdir,
)


class HlslppConan(ConanFile):
    name = "hlslpp"
    version = "3.7"
    description = ("hlslpp — HLSL 风格的 C++ 向量/矩阵/四元数数学库"
                   "（header-only；aarch64 自动走 NEON 后端）")
    license = "MIT"
    homepage = "https://github.com/redorav/hlslpp"
    url = "https://github.com/redorav/hlslpp"

    package_type = "header-library"

    settings = "os", "arch", "compiler", "build_type"

    # 上游 unit_tests 使用自研断言框架，无外部测试依赖
    options = {
        "with_upstream_tests": [True, False],
    }
    default_options = {
        "with_upstream_tests": True,
    }

    # 上游为 premake5 工程、无 CMakeLists.txt；test_upstream/ 是本配方自带的测试工程
    exports_sources = os.path.join("test_upstream", "CMakeLists.txt")

    no_copy_source = True

    def export_sources(self):
        copy(self, "CMakeLists.txt",
             src=os.path.join(self.recipe_folder, "test_upstream"),
             dst=os.path.join(self.export_sources_folder, "test_upstream"))
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        if not self.options.with_upstream_tests:
            return
        tc = CMakeToolchain(self)
        tc.generate()

    def _test_runner(self):
        """返回目标二进制的执行方式："" 表示本机可原生执行，None 表示无处执行。

        OHOS profile 的 CMAKE_CROSSCOMPILING_EMULATOR 指向 qemu-aarch64 包装脚本；
        此时 can_run() 仍为 False（os=OHOS 属交叉编译），但二进制实际可执行，
        故显式识别该配置，避免上游测试被静默跳过（rule4）。
        """
        if can_run(self):
            return ""
        extra = self.conf.get("tools.cmake.cmaketoolchain:extra_variables", default={})
        if isinstance(extra, dict) and extra.get("CMAKE_CROSSCOMPILING_EMULATOR"):
            return extra["CMAKE_CROSSCOMPILING_EMULATOR"]
        return None

    def build(self):
        apply_conandata_patches(self)
        if not self.options.with_upstream_tests:
            return
        runner = self._test_runner()
        if runner is None:
            self.output.warning("no runner for target binaries — "
                                "skipping upstream unit tests")
            return
        cmake = CMake(self)
        # 测试工程描述来自 exports_sources，而源码来自 source()
        cmake.configure(
            build_script_folder=os.path.join(self.export_sources_folder, "test_upstream"),
            variables={"HLSLPP_SRC_DIR": self.source_folder},
        )
        cmake.build()
        # 直接调用 ctest 并显式传入 --test-dir，避免 cmake --build --target test
        # 把 ctest 参数误传给底层 make。测试可执行文件的运行器由 profile 的
        # CMAKE_CROSSCOMPILING_EMULATOR（qemu-aarch64）在 CMake 生成期注入。
        if runner:
            self.output.info("running upstream unit tests via %s" % runner)
        ctest_args = " --output-on-failure"
        if runner:
            ctest_args += " --test-dir \"%s\"" % self.build_folder
        self.run("ctest" + ctest_args)

    def package(self):
        copy(self, "*.h", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "*.h", src=os.path.join(self.source_folder, "include", "hlsl++"),
             dst=os.path.join(self.package_folder, "include", "hlsl++"))
        copy(self, "*.natvis", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        rmdir(self, os.path.join(self.package_folder, "lib"))

    def package_id(self):
        # header-only：产物与 os/compiler/build_type 无关 → 单一 package_id
        self.info.clear()

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "hlslpp")
        self.cpp_info.set_property("cmake_target_name", "hlslpp::hlslpp")
