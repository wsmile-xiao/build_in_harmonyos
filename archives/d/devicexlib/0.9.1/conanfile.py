#!/usr/bin/env python3
"""Conan recipe — devicexlib 0.9.1 (CMake, HarmonyOS PC / os=OHOS arch=armv8)

deviceXlib (MaX CoE components) - Fortran 设备抽象层（malloc/mapping/memcpy/
linalg 的 CPU/GPU 统一封装），供 Quantum ESPRESSO 等使用。

语言构成：98.8% Fortran（C 仅 34 行）。OHOS 设备无 gfortran，用仓库
flang-ohos/20.1.0（设备原生 LLVM Flang 工具链包）作 tool_requires 提供
Fortran 编译器（同 openblas 0.3.34 / lapack 3.12.1 仓内先例）。
CPU-only 路径：DEVXLIB_ENABLE_ACC=OFF + DEVXLIB_ENABLE_GPU_BLAS=OFF
（见 patches/0001-cmake-cpu-off-option.patch）。
"""

import os
import glob

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class DevicexlibConan(ConanFile):
    name = "devicexlib"
    version = "0.9.1"
    description = "deviceXlib - Fortran abstraction layer for device memory management and linear algebra (MaX CoE)"
    license = "MIT"
    homepage = "https://gitlab.com/max-centre/components/devicexlib"
    url = "https://gitlab.com/max-centre/components/devicexlib"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) != "OHOS":
            raise ConanInvalidConfiguration(
                "This recipe targets os=OHOS device-native builds only")

    def requirements(self):
        # devxlib_linalg 封装 gemm/gemv/axpy/dot -> 链接期需要 LAPACK/BLAS
        # （lapack 3.12.1 仓内 recipe 自带 reference BLAS，设备原生 flang 构建）
        self.requires("lapack/3.12.1")

    def build_requirements(self):
        # 上游 CMake project(... LANGUAGES Fortran C)：设备无 gfortran，
        # 用本仓设备原生 LLVM Flang 工具链包提供 CMAKE_Fortran_COMPILER
        self.tool_requires("flang-ohos/20.1.0")

    def layout(self):
        from conan.tools.layout import basic_layout
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _flang_pkg(self):
        return self.dependencies.build["flang-ohos"].package_folder

    def _sdk_native(self):
        # 设备 OHOS SDK native 目录（sysroot/llvm），路径含版本号用 glob 兜底
        g = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native"))
        if not g:
            raise ConanInvalidConfiguration("OHOS SDK native dir not found on this device")
        return g[-1]

    def _write_find_shims(self, lapack_pkg):
        """上游硬编码 find_package(LAPACK REQUIRED) / find_package(OpenMP
        REQUIRED)。FindLAPACK/FindOpenMP 的链接探测在 flang 精简运行集 +
        SDK 组合下不可靠（缺 builtins/crt、libomp 需显式路径），改为确定性
        Find 模块 shim：直接映射到 conan lapack 包与 SDK libomp.a。
        CPU-only 构建不使用 OpenMP 编译开关（OpenMP 仅 OPENACC/OPENMPGPU
        路径链接，见 src/CMakeLists.txt），shim 即最终语义。"""
        lapack_lib = os.path.join(lapack_pkg, "lib")
        flang_lib = os.path.join(self._flang_pkg(), "lib")
        find_lapack = """# Conan recipe shim: map find_package(LAPACK REQUIRED) onto the
# conan lapack/3.12.1 package (reference lapack+blas, device-native build).
if(NOT TARGET LAPACK::LAPACK)
  add_library(LAPACK::LAPACK UNKNOWN IMPORTED)
  set_target_properties(LAPACK::LAPACK PROPERTIES
    IMPORTED_LOCATION "{lapack_lib}/liblapack.a"
    INTERFACE_LINK_LIBRARIES "{lapack_lib}/libblas.a;{flang_lib}/libFortranRuntime.a;{flang_lib}/libFortranDecimal.a;m")
endif()
set(LAPACK_FOUND TRUE)
set(LAPACK_LIBRARIES "{lapack_lib}/liblapack.a" "{lapack_lib}/libblas.a")
""".format(lapack_lib=lapack_lib, flang_lib=flang_lib)
        find_openmp = """# Conan recipe shim: CPU-only devXlib never links OpenMP targets
# (only OPENACC/OPENMPGPU paths do). Provide a deterministic found-answer
# so the upstream REQUIRED gate passes without a flang/SDK link probe.
if(NOT TARGET OpenMP::OpenMP_C)
  add_library(OpenMP::OpenMP_C INTERFACE IMPORTED)
endif()
if(NOT TARGET OpenMP::OpenMP_Fortran)
  add_library(OpenMP::OpenMP_Fortran INTERFACE IMPORTED)
endif()
set(OpenMP_C_FOUND TRUE)
set(OpenMP_Fortran_FOUND TRUE)
set(OpenMP_FOUND TRUE)
"""
        with open(os.path.join(self.generators_folder, "FindLAPACK.cmake"), "w") as f:
            f.write(find_lapack)
        with open(os.path.join(self.generators_folder, "FindOpenMP.cmake"), "w") as f:
            f.write(find_openmp)

    def generate(self):
        flang_pkg = self._flang_pkg()
        fc = os.path.join(flang_pkg, "bin", "flang")
        sdk_native = self._sdk_native()
        sdk_sysroot = os.path.join(sdk_native, "sysroot")
        # flang-ohos 是精简运行集（无 builtins/crt），链接资源指向 SDK clang 15
        sdk_resdir = os.path.join(sdk_native, "llvm", "lib", "clang", "15.0.4")
        sdk_llvm_lib = os.path.join(sdk_native, "llvm", "lib")
        sdk_lib = os.path.join(sdk_llvm_lib, "aarch64-linux-ohos")
        lapack_pkg = self.dependencies["lapack"].package_folder
        self._write_find_shims(lapack_pkg)

        tc = CMakeToolchain(self)
        tc.variables["CMAKE_Fortran_COMPILER"] = fc
        tc.variables["CMAKE_Fortran_FLAGS"] = (
            "-fPIC --target=aarch64-linux-ohos "
            "--sysroot={} -resource-dir={}".format(sdk_sysroot, sdk_resdir)
        )
        tc.variables["CMAKE_C_FLAGS"] = "-fPIC"
        # flang 精简运行集：编译器探测等的链接检查需显式喂 Fortran 运行时
        tc.variables["CMAKE_Fortran_STANDARD_LIBRARIES"] = (
            "-L{} -lFortranRuntime -lFortranDecimal".format(
                os.path.join(flang_pkg, "lib"))
        )
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = (
            "-L{} -L{} -L{} -L{} -lFortranRuntime -lFortranDecimal".format(
                sdk_lib, sdk_llvm_lib, os.path.join(flang_pkg, "lib"),
                os.path.join(lapack_pkg, "lib"))
        )
        tc.variables["CMAKE_SHARED_LINKER_FLAGS"] = (
            "-L{} -L{}".format(sdk_lib, os.path.join(flang_pkg, "lib"))
        )
        # Find 模块 shim 的搜索路径
        tc.variables["CMAKE_MODULE_PATH"] = self.generators_folder
        # Fortran 静态库模式探测（精简运行集不适合反复链可执行文件）
        tc.variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = "STATIC_LIBRARY"
        # CPU-only（本 run 无 GPU；见 patches/0001 的 OFF 选项）
        tc.variables["DEVXLIB_ENABLE_ACC"] = "OFF"
        tc.variables["DEVXLIB_ENABLE_GPU_BLAS"] = "OFF"
        tc.generate()

    def build(self):
        # flang 运行期需要 libLLVM/libMLIR/libclang-cpp；lld 需要 SDK libxml2
        flang_pkg = self._flang_pkg()
        sdk_llvm_lib = os.path.join(self._sdk_native(), "llvm", "lib")
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
            p for p in [sdk_llvm_lib, os.path.join(flang_pkg, "lib")] if p)
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # HMDFS 不支持 GNU make 的 FIFO jobserver（同 openblas 先例），
        # -j20 会让 Fortran 模块编译乱序抢跑（.mod 未生成即被消费），必须串行
        os.environ["CMAKE_BUILD_PARALLEL_LEVEL"] = "1"
        cmake.build()

        # 上游测试：CMake 同树构建 8 个 test_*.x（linalg/malloc/mapping/buffer/
        # memcpy/memcpy_async/memset/pinned，与 autotools `make test` 的
        # tests/run.sh TEST_LIST 一致；test_memset target 由补丁 0003 补入
        # 上游 CMake 源清单）。设备原生构建，直接运行；每个套件输出重定向到
        # 独立文件后再回显，保证逐套件计数与日志可配对。
        if can_run(self):
            for test_bin in ("test_linalg.x", "test_malloc.x", "test_mapping.x",
                             "test_buffer.x", "test_memcpy.x",
                             "test_memcpy_async.x", "test_memset.x",
                             "test_pinned.x"):
                src_bin = os.path.join(self.build_folder, "src", test_bin)
                out_file = os.path.join(self.build_folder, "src",
                                        test_bin.replace(".x", ".out"))
                self.output.info("=== upstream test: {} ===".format(test_bin))
                self.run("{} > {} 2>&1".format(src_bin, out_file))
                self.run("cat {}".format(out_file))
        else:
            self.output.info("Skipping upstream runtime tests while cross-building")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        # flang Fortran 运行时随包分发（libdevXlib.a 引用 _FortranA* 符号）
        flang_pkg = self._flang_pkg()
        for rt in ("libFortranRuntime.a", "libFortranDecimal.a"):
            copy(self, rt, src=os.path.join(flang_pkg, "lib"),
                 dst=os.path.join(self.package_folder, "lib"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["devXlib", "FortranRuntime", "FortranDecimal"]
        self.cpp_info.requires = ["lapack::lapack"]
        self.cpp_info.system_libs = ["m", "pthread"]
        self.cpp_info.includedirs = []
