#!/usr/bin/env python3
"""Conan recipe — clfft 2.12.2 (CMake).

AMD clFFT: OpenCL FFT library. Produces libclFFT.so (or .a).

OHOS adaptation notes:
- Dependencies: OpenCL headers (opencl-headers) + libOpenCL (opencl-icd-loader).
  Boost/FFTW/gtest are for the optional client/tests/examples — all disabled.
- The upstream src/CMakeLists.txt uses find_package(OpenCL) which reads
  OpenCL_INCLUDE_DIR / OpenCL_LIBRARY cache vars (same as clpeak recipe).
- OHOS has no OpenCL device at runtime; tests/examples disabled accordingly.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches


class ClfftConan(ConanFile):
    name = "clfft"
    version = "2.12.2"
    description = "clFFT — AMD OpenCL FFT library"
    license = "Apache-2.0"
    homepage = "https://github.com/clMathLibraries/clFFT"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def requirements(self):
        # OpenCL：头文件 + ICD loader（libOpenCL.so）
        self.requires("opencl-headers/2026.05.29", transitive_headers=True, transitive_libs=True)
        self.requires("opencl-icd-loader/v2024.05.08", transitive_headers=True, transitive_libs=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # 上游 cmake_minimum_required 2.6/2.8.3 与 CMake 4.x 不兼容
        # （"Compatibility with CMake < 3.5 has been removed"）→ 显式放宽（clpeak 同款）
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["BUILD_RUNTIME"] = "ON"
        tc.variables["BUILD_CLIENT"] = "OFF"
        tc.variables["BUILD_TEST"] = "OFF"
        tc.variables["BUILD_LOADLIBRARIES"] = "OFF"
        tc.variables["BUILD_EXAMPLES"] = "OFF"
        tc.variables["BUILD_CALLBACK_CLIENT"] = "OFF"
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # find_package(OpenCL) 读取的缓存变量（同 clpeak 方案）
        oc_inc = []
        oc_lib = []
        for dep_name in ("opencl-headers", "opencl-icd-loader"):
            if dep_name in self.dependencies:
                dep = self.dependencies[dep_name]
                oc_inc += dep.cpp_info.includedirs
                oc_lib += dep.cpp_info.libdirs
        if oc_inc:
            tc.variables["OpenCL_INCLUDE_DIR"] = ";".join(oc_inc)
        if oc_lib:
            # OpenCL_LIBRARY 指向 libOpenCL.so（loader 提供）
            for d in oc_lib:
                cand = os.path.join(d, "libOpenCL.so")
                if os.path.isfile(cand):
                    tc.variables["OpenCL_LIBRARY"] = cand
                    break
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # clFFT 的 CMakeLists.txt 在 src/ 子目录：用 build_script_folder 指定；
        # CMAKE_POLICY_VERSION_MINIMUM 经命令行 -D 传入（CMake 4.x 对旧
        # cmake_minimum_required <3.5 的官方豁免方式，toolchain 内变量不生效）
        cmake.configure(
            build_script_folder="src",
            variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"},
        )
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # clFFT 的 CMake install 默认装到 lib64/（GNUInstallDirs），conan 消费者
        # 走 lib/ ——把 lib64 内容合并到 lib/（若存在）
        pkg_lib64 = os.path.join(self.package_folder, "lib64")
        pkg_lib = os.path.join(self.package_folder, "lib")
        if os.path.isdir(pkg_lib64):
            os.makedirs(pkg_lib, exist_ok=True)
            for name in os.listdir(pkg_lib64):
                src = os.path.join(pkg_lib64, name)
                dst = os.path.join(pkg_lib, name)
                if os.path.isfile(src) and not os.path.exists(dst):
                    shutil.copy2(src, dst)
            self.output.info("merged lib64/ -> lib/")
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "clFFT")
        self.cpp_info.libs = ["clFFT"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.requires = ["opencl-headers::opencl-headers",
                                  "opencl-icd-loader::opencl-icd-loader"]
