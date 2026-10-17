#!/usr/bin/env python3
"""Conan recipe — lapack64 3.12.1 (Makefile, HarmonyOS PC / os=OHOS arch=armv8)

LAPACK 线性代数库的 64 位整数索引变体（上游 CMake BUILD_INDEX64=ON 语义下的
LAPACK 组件，库实名 liblapack64.a），源码同为 Reference-LAPACK v3.12.1 官方
tarball（与 lapack/cblas64 包同源同 SHA-256）。Fortran 侧以 flang
-fdefault-integer-8 编译（实测 default integer 变 8 字节），导出无后缀
Fortran 符号（dgemm_ 等，ILP64 语义）——与 cblas64 包的 libblas64.a 同一
命名惯例，二者链接兼容。

依赖：
  - requires cblas64/3.12.1：提供 ILP64 参考 BLAS（libblas64.a）与 Fortran
    静态运行时，随 cpp_info 传递给消费方（上游 BUILD_INDEX64 构建即
    blas64+lapack64 一体产出；ohpcd 无 ILP64 BLAS 独立包，BLAS64 由 cblas64
    包成对提供）
  - tool_requires flang-ohos/20.1.0（编 INSTALL 探针对象与 SRC 全部 Fortran
    源；同 lapack/cblas64/openblas 先例）

上游 make 构建（SRC/Makefile，include 顶层 make.inc）；绕开 CMake 的原因同
lapack/cblas64 包（FortranCInterface 链接验证不可用）。
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)


class Lapack64Conan(ConanFile):
    name = "lapack64"
    version = "3.12.1"
    description = ("LAPACK 64-bit integer index variant (liblapack64.a, ILP64 Fortran "
                   "symbols, BUILD_INDEX64 semantics of LAPACK 3.12.1)")
    license = "BSD-3-Clause"
    homepage = "https://www.netlib.org/lapack/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("本 recipe 仅支持 os=OHOS arch=armv8（设备原生）")

    def build_requirements(self):
        self.tool_requires("flang-ohos/20.1.0")

    def requirements(self):
        self.requires("cblas64/3.12.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _sdk_llvm(self):
        g = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm"))
        if not g:
            raise ConanException("未找到 ohos-sdk llvm 工具链目录")
        return g[-1]

    def generate(self):
        # 生成顶层 make.inc（SRC/Makefile include 它）。64 位模式变量与上游
        # CMake BUILD_INDEX64 等价：Fortran 端 -fdefault-integer-8；C 端宏
        # -DWeirdNEC -DLAPACK_ILP64 -DHAVE_LAPACK_CONFIG_H（SRC 为纯 Fortran，
        # CFLAGS 仅 make.inc 完整性保留）。TIMER=NONE：库内计时桩返回 0，
        # 不依赖 etime 等平台扩展（BLAS64 算法本身不用计时）。
        flang_pkg = self.dependencies.build["flang-ohos"].package_folder
        blas_pkg = self.dependencies["cblas64"].package_folder
        fc = os.path.join(flang_pkg, "bin", "flang")
        sdk = self._sdk_llvm()
        sysroot = os.path.join(sdk, "..", "sysroot")
        resdir = os.path.join(sdk, "lib", "clang", "15.0.4")
        sdklib = os.path.join(sdk, "lib", "aarch64-linux-ohos")
        ar = "/data/service/hnp/bin/llvm-ar"
        ranlib = "/data/service/hnp/bin/llvm-ranlib"
        build = self.build_folder
        make_inc = (
            "SHELL = /bin/sh\n"
            "CC = /data/service/hnp/bin/clang --target=aarch64-linux-ohos --sysroot=%s\n"
            "CFLAGS = -O2 -fPIC -DWeirdNEC -DLAPACK_ILP64 -DHAVE_LAPACK_CONFIG_H\n"
            "FC = %s --target=aarch64-linux-ohos --sysroot=%s -resource-dir=%s\n"
            "FFLAGS = -O2 -fPIC -fdefault-integer-8\n"
            "FFLAGS_DRV = $(FFLAGS)\n"
            "FFLAGS_NOOPT = -O0 -fPIC -fdefault-integer-8\n"
            "LDFLAGS = -L%s -L%s -lFortranRuntime -lFortranDecimal -lm\n"
            "AR = %s\n"
            "ARFLAGS = cr\n"
            "RANLIB = %s\n"
            "TIMER = NONE\n"
            "BLASLIB      = %s/libblas64.a\n"
            "CBLASLIB     = %s/libcblas64_unused.a\n"
            "LAPACKLIB    = %s/liblapack64.a\n"
            "TMGLIB       = %s/libtmglib64_unused.a\n"
            "LAPACKELIB   = %s/liblapacke64_unused.a\n"
            "DOCSDIR       = %s/docs_unused\n"
            % (sysroot, fc, sysroot, resdir, sdklib,
               os.path.join(flang_pkg, "lib"), ar, ranlib,
               os.path.join(blas_pkg, "lib"), build, build, build, build, build)
        )
        save(self, os.path.join(self.source_folder, "make.inc"), make_inc)

    def build(self):
        # 本配方无补丁（conandata.yml patches: {}），该调用为 no-op；
        # 保留以统一仓库配方骨架（G1 要求 export_sources/补丁应用入口）。
        apply_conandata_patches(self)
        # LD_LIBRARY_PATH：SDK llvm/lib 给 flang/lld 运行期依赖，flang 包 lib 同理。
        flang_pkg = self.dependencies.build["flang-ohos"].package_folder
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
            [os.path.join(self._sdk_llvm(), "lib"), os.path.join(flang_pkg, "lib")])
        for k in ("CFLAGS", "CXXFLAGS", "CPPFLAGS", "LDFLAGS"):
            os.environ.pop(k, None)
        src = self.source_folder
        # 1) INSTALL 探针对象：dlamch（机器常数探测，显式 -O0 防优化改变
        #    舍入/下溢探测行为；单引号防 shell 展开，$(FFLAGS_NOOPT) 由 make
        #    展开）与 TIMER=NONE 计时桩。SRC/Makefile 直接引用这三个 ../INSTALL/*.o
        self.run("make -C INSTALL dlamch.o FFLAGS='$(FFLAGS_NOOPT)'", cwd=src)
        self.run("make -C INSTALL second_NONE.o dsecnd_NONE.o", cwd=src)
        # 2) LAPACK 主库（四精度全量 SRC，~1300 个 .f）→ liblapack64.a
        self.run("make -j2 -C SRC", cwd=src)

    def package(self):
        lib = os.path.join(self.package_folder, "lib")
        copy(self, "liblapack64.a", src=self.build_folder, dst=lib)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # ILP64 BLAS（libblas64.a）与 Fortran 静态运行时由 cblas64 依赖的
        # cpp_info 传递；本包只加 LAPACK 主库。Fortran 库无头文件。
        self.cpp_info.libs = ["lapack64"]
        self.cpp_info.includedirs = []
