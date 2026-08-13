#!/usr/bin/env python3
"""Conan recipe — LAPACK 3.12.1 (CMake, HarmonyOS PC / os=OHOS arch=armv8)

LAPACK 线性代数库（含 reference BLAS + CBLAS + LAPACKE），Fortran 源码。
鸿蒙设备无 gfortran，用仓库 flang-ohos/20.1.0（LLVM Flang 工具链）作
tool_requires 编译（同 openblas 0.3.28 先例）。全程设备原生、走设备 CI。
"""
import os
import glob

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LapackConan(ConanFile):
    name = "lapack"
    version = "3.12.1"
    description = "LAPACK - Linear Algebra PACKage (with reference BLAS, CBLAS, LAPACKE)"
    license = "BSD-3-Clause"
    homepage = "https://www.netlib.org/lapack/"
    url = ""

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) != "OHOS":
            raise ConanInvalidConfiguration("本 recipe 仅支持 os=OHOS（设备原生）")

    def build_requirements(self):
        self.tool_requires("flang-ohos/20.1.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        flang_pkg = self.dependencies.build["flang-ohos"].package_folder
        fc = os.path.join(flang_pkg, "bin", "flang")
        # flang-ohos 是精简运行集（无 libclang_rt.builtins.a/crtbeginS.o），
        # 链接需显式指向 SDK clang15 资源目录 + sysroot + Fortran 运行时
        # （手动实测：flang --target=aarch64-linux-ohos --sysroot=... 
        #  -resource-dir=... -L<SDK>/aarch64-linux-ohos -lFortranRuntime 可链接运行）
        sdk_llvm = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm"))[-1]
        sdk_sysroot = os.path.join(sdk_llvm, "..", "sysroot")
        sdk_resdir = os.path.join(sdk_llvm, "lib", "clang", "15.0.4")
        sdk_lib = os.path.join(sdk_llvm, "lib", "aarch64-linux-ohos")
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_Fortran_COMPILER"] = fc
        tc.variables["CMAKE_Fortran_FLAGS"] = (
            "-fPIC --target=aarch64-linux-ohos "
            f"--sysroot={sdk_sysroot} -resource-dir={sdk_resdir}"
        )
        tc.variables["CMAKE_C_FLAGS"] = "-fPIC"
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = (
            f"-L{sdk_lib} -L{os.path.join(flang_pkg, 'lib')} "
            "-lFortranRuntime -lFortranDecimal -lm"
        )
        # flang-ohos 精简运行集无法链接可执行文件（缺 crt），LAPACK 是纯库
        # 仅需编译 .f → .o，让 CMake 编译器检测用静态库模式跳过链接。
        tc.variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = "STATIC_LIBRARY"
        # 构建 CBLAS 与 LAPACKE（C 接口），便于 test_package 用 C 验证
        tc.variables["BUILD_CBLAS"] = "ON"
        tc.variables["BUILD_LAPACKE"] = "ON"
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["LAPACK_INSTALL_PKGCONFIGDIR"] = "lib/pkgconfig"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # flang 运行期需要 LLVM/MLIR 动态库
        flang_pkg = self.dependencies.build["flang-ohos"].package_folder
        sdk_llvm_lib = ""
        g = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib"))
        if g:
            sdk_llvm_lib = g[-1]
        ld_path = os.pathsep.join(
            p for p in [sdk_llvm_lib, os.path.join(flang_pkg, "lib")] if p)
        os.environ["LD_LIBRARY_PATH"] = ld_path
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # 复制 flang Fortran 运行时进包内 lib（liblapack.a 内引用
        # _FortranAio* / _FortranAStopStatement 等符号，消费方链接需带上）
        flang_pkg = self.dependencies.build["flang-ohos"].package_folder
        for rt in ("libFortranRuntime.a", "libFortranDecimal.a"):
            src = os.path.join(flang_pkg, "lib", rt)
            if os.path.isfile(src):
                copy(self, rt, src=os.path.dirname(src),
                     dst=os.path.join(self.package_folder, "lib"))
        self._sign_so()

    def _sign_so(self):
        sign = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(sign):
            self.output.warning("binary-sign-tool 不存在，跳过签名")
            return
        for so in glob.glob(os.path.join(self.package_folder, "lib", "*.so*")):
            if os.path.islink(so):
                continue
            self.run('%s sign -inFile "%s" -outFile "%s" -selfSign 1' % (sign, so, so))

    def package_info(self):
        # LAPACK 3.12.1 CMake 默认只产出 liblapack.a + libblas.a
        # （LAPACKE/CBLAS 需 FortranCInterface_VERIFY 链接验证，flang 精简
        # 运行集无法完成，故不构建）；消费方直接调用 Fortran 符号（dgemm_ 等）。
        # libFortranRuntime.a / libFortranDecimal.a 已在 package() 复制进包内 lib。
        self.cpp_info.libs = ["lapack", "blas", "FortranRuntime", "FortranDecimal"]
        self.cpp_info.includedirs = []  # Fortran 库无头文件
        self.cpp_info.system_libs = ["m"]
