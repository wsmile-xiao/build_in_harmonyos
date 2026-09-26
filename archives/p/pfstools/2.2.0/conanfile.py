#!/usr/bin/env python3
"""Conan recipe — pfstools 2.2.0 (HDR image processing tools, C++/CMake).

pfstools 是 HDR 图像处理命令行工具集（PFS 流水线：pfsin*/pfsout* 转换器 +
滤波器 + 色调映射 TMO + 标定/对齐）。核心库 libpfs 无任何外部依赖，
全部第三方库都是可选的，本配方走「最小面」：全部可选依赖关闭，
requirements() 为空 —— 如需放开某个可选依赖，再按 conan 实测结果补。

R32 note: 不写 settings.os == "Linux" 分支 —— OHOS 适配版 conan 会把
os=OHOS 映射为 CMAKE_SYSTEM_NAME=HarmonyOS（CMakeToolchain 自动完成）。
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class PfstoolsConan(ConanFile):
    name = "pfstools"
    version = "2.2.0"
    description = "pfstools — HDR image processing tools (PFS pipeline: converters, filters, TMO)"
    license = "LGPL-2.1-or-later"
    homepage = "https://pfstools.sourceforge.net/"
    url = "https://sourceforge.net/projects/pfstools/"  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 核心构建（全部可选依赖关闭）零外部依赖：libpfs 只用 C++ 标准库。
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        # tarball 顶层为单一根目录 pfstools-2.2.0/（无 ./ 前缀）→ strip_root 安全
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26：BUILD_SHARED_LIBS=OFF —— 上游默认即 STATIC，
        # 且避免任何与系统同名的 .so 污染 /lib。
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"

        # ── 关闭全部可选依赖（逐字对应顶层 CMakeLists.txt 的 OPTION 名）──
        # 关掉后这些工具不编译，见各 find_package 处的 MESSAGE 说明。
        tc.variables["WITH_OpenEXR"] = "OFF"        # pfsinexr / pfsoutexr
        tc.variables["WITH_ImageMagick"] = "OFF"    # pfsinimgmagick / pfsoutimgmagick / pfsouthdrhtml
        tc.variables["WITH_NetPBM"] = "OFF"         # pfsinppm / pfsoutppm
        tc.variables["WITH_TIFF"] = "OFF"           # pfsintiff / pfsouttiff
        tc.variables["WITH_QT"] = "OFF"             # pfsview (Qt5 Widgets)
        tc.variables["WITH_MATLAB"] = "OFF"         # Matlab MEX 文件
        tc.variables["WITH_Octave"] = "OFF"         # Octave .oct/.m + pfsoctavelum 等
        tc.variables["WITH_pfsglview"] = "OFF"      # pfsglview (OpenGL + GLUT)
        tc.variables["WITH_FFTW"] = "OFF"           # pfstmo_durand02/fattal02/ferradans11 加速
        tc.variables["WITH_GSL"] = "OFF"            # pfstmo_mantiuk08
        tc.variables["WITH_OpenCV"] = "OFF"         # pfsalign
        tc.variables["WITH_HDRVC"] = "OFF"          # 上游默认已 OFF（internal release only）

        # 上游 CMakeLists.txt 第 1 行是 cmake_minimum_required(VERSION 2.8.8)。
        # 设备/CI cmake = 4.1.2，已移除对 <3.5 的兼容 → configure 直接 FATAL。
        # ⚠ 必须是 cache_variables（命令行 -D）：实测 tc.variables 只写进 toolchain 的
        #   set()，cmake_minimum_required() 读的是 cache，2026-09-24 15:53 G2 因此失败
        #   （见 reports/conan-create.log 的 RUN 行：该变量未出现在 cmake 命令行）。
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"

        tc.generate()

    def build(self):
        # R51：上游无测试入口（0 个 enable_testing / add_test，无 tests/ 目录，
        # 见 notes.md 清点证据）→ 无可运行的上游测试。
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["pfs"]
        # pfs.h / array2d.h 安装到 include/pfs/ → 消费者 #include <pfs/pfs.h>
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "pfstools")
        self.cpp_info.set_property("cmake_target_name", "pfstools::pfs")
