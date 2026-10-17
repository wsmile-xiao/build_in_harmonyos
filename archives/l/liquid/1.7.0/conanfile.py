#!/usr/bin/env python3
"""Conan recipe — liquid 1.7.0 (CMake, HarmonyOS PC / os=OHOS arch=armv8)

liquid-dsp 是一个为软件定义无线电设计的开源数字信号处理 C 库，
MIT 许可，单 shared library 目标，仅依赖 libc + libm。

构建选项：关闭 SIMD 指令检测（OHOS musl aarch64 兼容），关闭 autotests /
benchmarks / examples / sandbox。v1.7.0 的 CMakeLists 未集成 FFTW
（`CMakeLists.txt:47` 仅遗留注释 `# TODO: check for FFTW`），无需 FFTW 开关。

上游测试：CTest `test`（xautotest）仅在 BUILD_AUTOTESTS=ON 时构建。
conan recipe 为保持构建可复现、避免 cross-compile 时运行 autoscript
代码生成器，关闭 autotests；上游测试按 R51 在 HarmonyOS aarch64 真机原生
构建执行并回填（1317/1317 通过、716451 断言通过），证据见
`reports/upstream-autotest-1.7.0.md` 与 `reports/upstream-autotest-1.7.0.json`。
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class LiquidConan(ConanFile):
    name = "liquid"
    version = "1.7.0"
    description = "liquid-dsp - digital signal processing library for software-defined radios"
    license = "MIT"
    homepage = "https://github.com/jgaeddert/liquid-dsp"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # OHOS musl aarch64: 关闭 SIMD 指令集检测与向量化
        # （cmake/FindSIMD.cmake 用 CHECK_C_SOURCE_RUNS()/try_run 探测，
        #   交叉编译下无法在构建 host 上执行 target 探针）
        tc.variables["ENABLE_SIMD"] = False
        # 关闭非必要目标：autotests / benchmarks / examples / sandbox / doc
        tc.variables["BUILD_AUTOTESTS"] = False
        tc.variables["BUILD_BENCHMARKS"] = False
        tc.variables["BUILD_EXAMPLES"] = False
        tc.variables["BUILD_SANDBOX"] = False
        tc.variables["BUILD_DOC"] = False
        # 关闭代码覆盖率
        tc.variables["COVERAGE"] = False
        # 注：FIND_SIMD / FIND_FFTW / ENABLE_STRICT 不是 v1.7.0 的 CMake 选项，
        # 传入会触发 "Manually-specified variables were not used" 警告，故不设置。
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["liquid"]
        self.cpp_info.system_libs = ["m"]
        # 上游 CMakeLists 未使用 install(EXPORT)，CMakeDeps 基于 cpp_info 生成
        self.cpp_info.set_property("cmake_file_name", "liquid")
        self.cpp_info.set_property("cmake_target_name", "liquid::liquid")
