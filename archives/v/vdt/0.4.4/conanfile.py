#!/usr/bin/env python3
"""Conan recipe — vdt 0.4.4 (CMake, C++ math library).

vdt（Vector Development Toolkit）是 CERN 出品的快速数学函数向量化库：
头文件内联单/双精度实现 + 共享库（数组签名 `void(unsigned,T*,T*)`）。
- 顶层构建系统为 CMake（CMakeLists.txt），configure 阶段需要 Python
  运行 src/signatures_generator.py 生成 src/vdtMath_signatures.cc（官方要求）。
- 无任何强制第三方依赖（Vc/SVML 均为可选，默认关闭）。
- 构建产物：libvdt.so + include/vdt/*.h。
- 上游测试随 -DDIAG=ON 构建（progs/units/*_test.cpp，12 个独立用例），
  本配方在 build() 内真实编译并运行全部 12 个测试二进制。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get

# 上游 progs/units/CMakeLists.txt 注册的 12 个独立函数单元测试
UPSTREAM_UNIT_TESTS = [
    "exp_test", "log_test", "sqrt_test", "sin_test", "cos_test", "inv_test",
    "tan_test", "tanh_test", "asin_test", "acos_test", "atan_test", "atan2_test",
]


class VdtConan(ConanFile):
    name = "vdt"
    version = "0.4.4"
    description = ("Vectorised math library: fast inline implementations of "
                   "mathematical functions (double/single precision) for "
                   "autovectorised loops")
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
        # codeload URL 末段是 tag 名、无 .tar.gz 后缀，必须显式给 filename，
        # 否则 get() 会按 zip 处理报 BadZipFile（libmongocrypt 实测）。
        get(self, filename="vdt-0.4.4.tar.gz",
            **self.conan_data["sources"], strip_root=True)

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
        # 必须跟随 options.shared：写死会导致消费方 -o shared=False 静默失效。
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        # CMake 4.x 移除了 <3.5 的兼容（vdt 声明 cmake_minimum_required 3.2）。
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # 平台指令集选项按 arch 守卫（上游默认 SSE=ON 是 x86 专属）：
        #   - aarch64：开 NEON 走向量路径；x86 专属的 SSE/AVX/FMA 全部关闭
        #     （aarch64 上 -msse 是未知选项）。
        #   - 其他 arch：不强制关 x86 选项，保留上游默认检测。
        if self.settings.arch in ("armv8", "armv7", "armv8.3-a"):
            tc.variables["NEON"] = "ON"
            tc.variables["SSE"] = "OFF"
            tc.variables["AVX"] = "OFF"
            tc.variables["AVX2"] = "OFF"
            tc.variables["FMA"] = "OFF"
        # 上游测试（progs/units）只在 DIAG=ON 时注册：本配方打开 DIAG，
        # 在 build() 内真实编译并运行 12 个上游单元测试。
        tc.variables["DIAG"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(build_script_folder="")
        cmake.build()
        self._run_upstream_unit_tests()

    def _run_upstream_unit_tests(self):
        """真实执行上游 12 个单元测试二进制（progs/units/*_test.cpp）。

        上游顶层 CMakeLists.txt 把 CMAKE_RUNTIME_OUTPUT_DIRECTORY 固定为
        ${CMAKE_SOURCE_DIR}/bin，因此可执行文件落在 source_folder/bin。
        """
        bindir = os.path.join(self.source_folder, "bin")
        if not os.path.isdir(bindir):
            raise ConanException(
                "上游测试二进制目录不存在：%s（DIAG=ON 未生效？）" % bindir)
        ran = []
        for name in UPSTREAM_UNIT_TESTS:
            exe = os.path.join(bindir, name)
            if not os.path.isfile(exe):
                raise ConanException("缺少上游测试二进制：%s" % exe)
            self.run("./%s" % name, cwd=bindir, env="conanbuild")
            ran.append(name)
        self.output.info("上游单元测试执行完成：%d/%d（%s）"
                         % (len(ran), len(UPSTREAM_UNIT_TESTS), ", ".join(ran)))

    def package(self):
        CMake(self).install()

    def package_info(self):
        self.cpp_info.libs = ["vdt"]
        self.cpp_info.set_property("cmake_file_name", "vdt")
        self.cpp_info.set_property("cmake_target_name", "vdt")
