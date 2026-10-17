#!/usr/bin/env python3
"""Conan recipe — blas 3.12.1 (Makefile, HarmonyOS PC / os=OHOS arch=armv8)

Netlib 参考 BLAS（reference BLAS）：BLAS 3.12.1 现随 LAPACK 3.12.1 发行
（netlib.org/blas/ 官方声明 BLAS is now part of LAPACK release；独立
blas.tgz 是不含 3.12.1 的历史包），故源码取 netlib 官方 LAPACK 3.12.1
tarball 中的 BLAS/ 组件（与仓库 lapack/3.12.1、cblas/3.12.1 同源同版本，
官方 HTTPS 源、SHA-256 实测核验）。

主体是纯 Fortran 77 源码（157 个 .f 文件）。鸿蒙设备无 gfortran，用仓库
flang-ohos/20.1.0（LLVM Flang 工具链）作 tool_requires 编译（同 lapack/
openblas/cblas 先例）。走上游 make 路径：BLAS/Makefile → SRC 产 libblas.a；
TESTING 产 12 个 blat 驱动（level1/2/3 × s/d/c/z 四精度）并 make run 跑
上游测试。绕开 CMake 路径的原因：顶层 CMake 的 BLAS 目标仍会执行 Fortran
链接探针，flang-ohos 精简运行集无法完成（同 lapack 先例）；make 路径无
此依赖，探索实测可全程设备原生构建并跑通全部上游测试。
"""
import glob
import os
import re

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)


class BlasConan(ConanFile):
    name = "blas"
    version = "3.12.1"
    description = "Reference BLAS - Basic Linear Algebra Subprograms (netlib, BLAS component of LAPACK 3.12.1)"
    license = "BSD-3-Clause"
    homepage = "https://www.netlib.org/blas/"
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

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _sdk_llvm(self):
        g = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm"))
        if not g:
            raise ConanException("未找到 ohos-sdk llvm 工具链目录")
        return g[-1]

    def generate(self):
        # 生成上游 make 构建入口（BLAS/Makefile → include $(TOPSRCDIR)/make.inc，
        # SRC/TESTING 同样 include 顶层 make.inc）所需变量集；库与测试产物一律
        # 指向 build_folder，不在源码树留二进制。GNU make 内置 .f.o 规则用
        # $(FC) $(FFLAGS) 编 Fortran 源。
        flang_pkg = self.dependencies.build["flang-ohos"].package_folder
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
            "FC = %s --target=aarch64-linux-ohos --sysroot=%s -resource-dir=%s\n"
            "FFLAGS = -O2 -fPIC\n"
            "FFLAGS_DRV = $(FFLAGS)\n"
            "FFLAGS_NOOPT = -O0\n"
            "LDFLAGS = -L%s -L%s -lFortranRuntime -lFortranDecimal -lm\n"
            "AR = %s\n"
            "ARFLAGS = cr\n"
            "RANLIB = %s\n"
            "TIMER = INT_ETIME\n"
            "BLASLIB      = %s/libblas.a\n"
            "LAPACKLIB    = %s/liblapack_unused.a\n"
            "TMGLIB       = %s/libtmglib_unused.a\n"
            "LAPACKELIB   = %s/liblapacke_unused.a\n"
            "DOCSDIR      = %s/docs_unused\n"
            % (fc, sysroot, resdir, sdklib, os.path.join(flang_pkg, "lib"),
               ar, ranlib, build, build, build, build, build)
        )
        save(self, os.path.join(self.source_folder, "make.inc"), make_inc)

    def build(self):
        apply_conandata_patches(self)
        # LD_LIBRARY_PATH：SDK llvm/lib 给 flang/lld 运行期依赖（libLLVM/libMLIR、
        # libxml2），flang 包 lib 同理。直接改 os.environ；并清 HiShell 污染的构建 env。
        flang_pkg = self.dependencies.build["flang-ohos"].package_folder
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
            [os.path.join(self._sdk_llvm(), "lib"), os.path.join(flang_pkg, "lib")])
        for k in ("CFLAGS", "CXXFLAGS", "CPPFLAGS", "LDFLAGS"):
            os.environ.pop(k, None)
        src = self.source_folder
        # 1) libblas.a（4 精度全部例程：SRC 157 个 .f）
        self.run("make -j1 -C BLAS", cwd=src)
        # 2) 上游测试：12 个 blat 驱动（level1/2/3 × s/d/c/z 四精度）
        self.run("make -j1 -C BLAS/TESTING", cwd=src)
        # 3) 运行上游测试：blat1 自包含；blat2/3 读源码树内 *blat2/3.in 数据文件
        self.run("make -C BLAS/TESTING run", cwd=src)
        # 4) 测试计数（统计单位 = 测试程序验证行，blat1/2/3 均为 PASS 标记行）
        pat_pass = re.compile(r"----- PASS -----|PASSED THE")
        pat_fail = re.compile(r"FAIL", re.IGNORECASE)
        total_pass = 0
        total_fail = 0
        rows = []
        for f in sorted(glob.glob(os.path.join(src, "BLAS", "TESTING", "*blat*.out"))):
            text = open(f, errors="replace").read()
            p = len(pat_pass.findall(text))
            n = len(pat_fail.findall(text))
            total_pass += p
            total_fail += n
            rows.append("%s: PASS=%d FAIL=%d" % (os.path.basename(f), p, n))
        rows.append("TOTAL: PASS=%d FAIL=%d" % (total_pass, total_fail))
        save(self, os.path.join(self.build_folder, "blas_upstream_test_summary.txt"),
             "\n".join(rows) + "\n")
        self.output.info("上游 BLAS 测试统计：%s" % rows[-1])
        if total_fail:
            raise ConanException(
                "上游 BLAS 测试存在失败项（PASS=%d FAIL=%d）" % (total_pass, total_fail))

    def package(self):
        copy(self, "libblas.a", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"))
        # 复制 flang Fortran 运行时进包内 lib（libblas.a 内 xerbla.o 引用
        # _FortranAio* / _FortranAStopStatement 等符号，消费方链接需带上，
        # 同 lapack/3.12.1 先例）
        flang_pkg = self.dependencies.build["flang-ohos"].package_folder
        for rt in ("libFortranRuntime.a", "libFortranDecimal.a"):
            src = os.path.join(flang_pkg, "lib", rt)
            if os.path.isfile(src):
                copy(self, rt, src=os.path.dirname(src),
                     dst=os.path.join(self.package_folder, "lib"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # 参考 BLAS 是纯 Fortran 库，无头文件；消费方直接调用 Fortran 符号
        # （ddot_/dgemm_ 等 LP64 符号，尾下划线约定）。
        self.cpp_info.libs = ["blas", "FortranRuntime", "FortranDecimal"]
        self.cpp_info.includedirs = []  # Fortran 库无头文件
        self.cpp_info.system_libs = ["m"]
