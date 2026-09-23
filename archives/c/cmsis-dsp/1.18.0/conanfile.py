#!/usr/bin/env python3
"""Conan recipe for CMSIS-DSP 1.18.0 (CMake static library).

- 官方源: https://github.com/ARM-software/CMSIS-DSP (tag v1.18.0)
- 纯 C 库，零第三方依赖；CMAKE_SYSTEM_NAME=HarmonyOS 由 OHOS 适配版 conan 自动映射
- HOST=ON 使上游 configDsp.cmake 定义 __GNUC_PYTHON__，绕过 CMSIS-Core
  （cmsis_compiler.h）依赖——上游唯一支持的免 CMSIS-Core 构建路径（arm_math_types.h 注释明示）
- 产物: libCMSISDSP.a + include/CMSIS-DSP/** + CMake package
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class CmsisDspConan(ConanFile):
    name = "cmsis-dsp"
    version = "1.18.0"
    description = "ARM CMSIS-DSP: optimized DSP library for Cortex-M/A (standalone, no CMSIS-Core)"
    license = "Apache-2.0"
    homepage = "https://github.com/ARM-software/CMSIS-DSP"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    exports_sources = "patches/*"
    exports = "conandata.yml"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # HOST=ON -> __GNUC_PYTHON__ -> 免 CMSIS-Core 依赖 (上游唯一 standalone 路径)
        tc.variables["HOST"] = "ON"
        tc.variables["CMSISDSP_INSTALL"] = "ON"
        tc.variables["NEON"] = "ON"
        tc.variables["NEONEXPERIMENTAL"] = "OFF"
        tc.variables["DISABLEFLOAT16"] = "OFF"
        tc.variables["BUILD_SHARED_LIBS"] = "OFF" if not self.options.shared else "ON"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "CMSISDSP")
        self.cpp_info.set_property("cmake_target_name", "CMSISDSP::CMSISDSP")
        self.cpp_info.libs = ["CMSISDSP"]
        self.cpp_info.includedirs = ["include/CMSIS-DSP"]
        # 消费者编译必须定义 __GNUC_PYTHON__ 才能免 CMSIS-Core(cmsis_compiler.h) 依赖。
        # 与上游 HOST=ON 构建导出的 INTERFACE_COMPILE_DEFINITIONS 行为一致（configDsp.cmake）。
        self.cpp_info.defines = ["__GNUC_PYTHON__"]
