#!/usr/bin/env python3
"""Conan recipe for simbody 3.8 — CMake multibody dynamics library.

Simbody 由三个 CMake 库组成：SimTKcommon / SimTKmath / SimTKsimbody。
依赖 BLAS/LAPACK（Fortran 参考实现，来自制品仓 lapack/3.12.1，包内含
libFortranRuntime/libFortranDecimal）。OHOS 平台适配（CMakeLists + NiceTypeName）
由 conandata.yml 登记的两个补丁完成。
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
import os


class SimbodyConan(ConanFile):
    name = "simbody"
    version = "3.8"
    description = "Simbody is a high-quality open-source multibody dynamics library for physical simulation (SimTKsimbody/SimTKmath/SimTKcommon)"
    license = "Apache-2.0"
    homepage = "https://github.com/simbody/simbody"
    url = "https://github.com/simbody/simbody"
    topics = ("multibody", "dynamics", "simulation", "physics")

    package_type = "library"

    # R32: settings.os 判断必须用 in ("Linux", "OHOS")
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Simbody 使用 BLAS/LAPACK 的 Fortran 符号（sdot_ 等），
        # lapack 包内含 liblapack.a/libblas.a/libFortranRuntime.a/libFortranDecimal.a
        self.requires("lapack/3.12.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # OHOS 平台 Make jobserver FIFO 创建失败，限制并行编译
        os.environ["CMAKE_BUILD_PARALLEL_LEVEL"] = "1"
        # 未知平台不自动带 -soname，显式设置（否则测试/下游加载失败）
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        # R26: 系统同名库静态编译；simbody 非系统同名，遵循 shared 选项
        tc.variables["SIMBODY_BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # 上游测试保持开启（适配验证与测试台账依据）
        tc.variables["BUILD_TESTING"] = "ON"
        # 可视化器依赖 OpenGL/GLUT，鸿蒙不构建
        tc.variables["BUILD_VISUALIZER"] = "OFF"
        # 文档安装开销大且非库交付物，关闭
        tc.variables["INSTALL_DOCS"] = "OFF"
        # 示例构建验证用（安装仅头文件/库/示例源码，不产生 CLI 交付物）
        tc.variables["BUILD_EXAMPLES"] = "ON"
        # BLAS/LAPACK：使用制品仓 lapack 包内静态库（含 Fortran 运行时）
        lapack_lib_dir = os.path.join(
            self.dependencies["lapack"].package_folder, "lib")
        blas_libs = [os.path.join(lapack_lib_dir, n) for n in (
            "liblapack.a", "libblas.a", "libFortranRuntime.a", "libFortranDecimal.a")]
        tc.variables["BUILD_USING_OTHER_LAPACK"] = ";".join(blas_libs)
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
        self.cpp_info.libs = ["SimTKsimbody", "SimTKmath", "SimTKcommon"]
        # 头文件安装在 include/simbody 子目录
        self.cpp_info.includedirs = ["include/simbody"]
        # 依赖 lapack 的 Fortran 符号需传给下游
        self.cpp_info.requires = ["lapack::lapack"]
        self.cpp_info.system_libs = ["m", "pthread", "dl"]
