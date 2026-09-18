#!/usr/bin/env python3
"""Conan recipe — vdt 0.4.6 (CMake, C++ math library).

vdt（Vector Development Toolkit）是 CERN 出品的快速数学函数向量化库：
头文件内联单/双精度实现 + 可选共享库（数组签名 `void(unsigned,T*,T*)`）。
- 顶层构建系统为 CMake（CMakeLists.txt），configure 阶段需要 Python
  运行 signatures_generator.py 生成 vdtMath_signatures.cc（官方要求）。
- 无任何强制第三方依赖（Vc/SVML 均为可选，默认关闭）。
- 构建产物：libvdt.so + include/vdt/*.h。
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class VdtConan(ConanFile):
    name = "vdt"
    version = "0.4.6"
    description = "Vectorised math library: fast inline implementations of mathematical functions (double/single precision) for autovectorised loops"
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/dpiparo/vdt"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports_sources = "patches/*.patch"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        cmake_layout(self, src_folder=".")

    def generate(self):
        tc = CMakeToolchain(self)
        # os=OHOS 时 conan 默认把 CMAKE_SYSTEM_NAME 设成 "HarmonyOS"，而本机
        # cmake 平台文件叫 Modules/Platform/OHOS.cmake（内容仅 include Linux），
        # 名字对不上会导致平台变量留空（SONAME 链接标志丢失等）。带 os 守卫覆盖。
        if self.settings.os == "OHOS":
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
        # 64 位默认可能装到 lib64/，conan cpp_info.libdirs 与 test_package 找 lib/。
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        # 必须跟随 options.shared（fftw 同款教训）：写死会导致消费方 -o shared=False
        # 静默失效——package_id 变了内容却仍是动态库。
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        # CMake 4.x 移除了 <3.5 的兼容（vdt 声明 cmake_minimum_required 3.2）。
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # 平台指令集选项按 arch 守卫（上游默认 SSE=ON 是 x86 专属）：
        #   - aarch64：开 NEON 走向量路径；x86 专属的 SSE/AVX/FMA 全部关闭
        #     （aarch64 上 -msse 是未知选项，cern 0.4.6 实撞记录）。
        #   - 其他 arch（x86_64 等）：不强制关 x86 选项，保留上游默认检测
        #     （NEON 是 ARM-only，强行 -DNEON=ON 会导致 x86 构建失败/静默降级）。
        if self.settings.arch in ("armv8", "armv7", "armv8.3-a"):
            tc.variables["NEON"] = "ON"
            tc.variables["SSE"] = "OFF"
            tc.variables["AVX"] = "OFF"
            tc.variables["AVX2"] = "OFF"
            tc.variables["FMA"] = "OFF"
        # 诊断程序（bench + units 测试）不进配方构建；上游测试已在 worktree 内
        # 以 DIAG=ON 全量构建并运行（证据见 reports/，防止污染 clean 构建）。
        tc.variables["DIAG"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(build_script_folder="")
        cmake.build()

    def package(self):
        CMake(self).install()

    def package_info(self):
        self.cpp_info.libs = ["vdt"]
        self.cpp_info.set_property("cmake_file_name", "vdt")
        self.cpp_info.set_property("cmake_target_name", "vdt")