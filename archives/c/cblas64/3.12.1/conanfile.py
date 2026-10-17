#!/usr/bin/env python3
"""Conan recipe — cblas64 3.12.1 (Makefile, HarmonyOS PC / os=OHOS arch=armv8)

Netlib CBLAS 的 64 位整数索引接口（cblas_*_64，cblas.h 的 CBLAS_API64 模式，
等价上游 CMake BUILD_INDEX64=ON 时的 CBLAS 组件），源码同为 lapack 3.12.1
官方 tarball。链接需要一个 ILP64（8 字节整数）BLAS：ohpcd 暂无 ILP64 BLAS
发布，本包按上游 BUILD_INDEX64 的构建语义在包内一并构建参考 BLAS 的 64 位
整数变体（BLAS/SRC + flang -fdefault-integer-8 → libblas64.a），两者成对提供。

依赖：
  - tool_requires flang-ohos/20.1.0（编 BLAS64 全部 Fortran 源、CBLAS/src 的
    Fortran 桥接 .f，以及测试驱动主程序）
  - 无外部 requires（ILP64 BLAS 由包内 libblas64.a 提供）

上游 make 构建（CBLAS/Makefile + BLAS/SRC/Makefile，include 顶层 make.inc）；
绕开 CMake 的原因见 cblas 包（FortranCInterface 验证不可用）。上游
BUILD_INDEX64 + CBLAS 组合存在三处缺陷，经补丁修复后 12 个 blat 驱动
340 PASS / 0 FAIL（详见 conandata.yml patches 与 notes.md）。
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


class Cblas64Conan(ConanFile):
    name = "cblas64"
    version = "3.12.1"
    description = ("CBLAS 64-bit integer index interface (cblas_*_64 API, CBLAS64 mode "
                   "of LAPACK 3.12.1) with reference ILP64 BLAS")
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

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _sdk_llvm(self):
        g = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm"))
        if not g:
            raise ConanException("未找到 ohos-sdk llvm 工具链目录")
        return g[-1]

    def generate(self):
        # 生成顶层 make.inc（BLAS/SRC 与 CBLAS 两级 Makefile 都 include 它）。
        # 64 位模式变量集为设备原生探索实测：
        #   - C 端宏与上游 CMake BUILD_INDEX64 一致（-DWeirdNEC -DLAPACK_ILP64
        #     -DHAVE_LAPACK_CONFIG_H）+ -DCBLAS_API64（上游在 src 的 _64_cobj 目标
        #     上加的 API 改名宏），F77_GLOBAL_SUFFIX 以 -D 恒等直通（见 0001 补丁）
        #   - Fortran 端 -fdefault-integer-8（flang，实测 default integer 变 8 字节）
        flang_pkg = self.dependencies.build["flang-ohos"].package_folder
        fc = os.path.join(flang_pkg, "bin", "flang")
        sdk = self._sdk_llvm()
        sysroot = os.path.join(sdk, "..", "sysroot")
        resdir = os.path.join(sdk, "lib", "clang", "15.0.4")
        sdklib = os.path.join(sdk, "lib", "aarch64-linux-ohos")
        cc_exec = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = cc_exec.get("c", "/data/service/hnp/bin/clang")
        ar = "/data/service/hnp/bin/llvm-ar"
        ranlib = "/data/service/hnp/bin/llvm-ranlib"
        build = self.build_folder
        make_inc = (
            "SHELL = /bin/sh\n"
            "CC = %s --target=aarch64-linux-ohos --sysroot=%s\n"
            "CFLAGS = -O2 -fPIC -DWeirdNEC -DCBLAS_API64 -DLAPACK_ILP64 "
            "-DHAVE_LAPACK_CONFIG_H -D'F77_GLOBAL_SUFFIX(a,b)=F77_GLOBAL(a,b)'\n"
            "FC = %s --target=aarch64-linux-ohos --sysroot=%s -resource-dir=%s\n"
            "FFLAGS = -O2 -fPIC -fdefault-integer-8\n"
            "FFLAGS_DRV = $(FFLAGS)\n"
            "FFLAGS_NOOPT = -O0 -fdefault-integer-8\n"
            "LDFLAGS = -L%s -L%s -lFortranRuntime -lFortranDecimal -lm\n"
            "AR = %s\n"
            "ARFLAGS = cr\n"
            "RANLIB = %s\n"
            "TIMER = INT_ETIME\n"
            "BLASLIB      = %s/libblas64.a\n"
            "CBLASLIB     = %s/libcblas64.a\n"
            "LAPACKLIB    = %s/liblapack64_unused.a\n"
            "TMGLIB       = %s/libtmglib64_unused.a\n"
            "LAPACKELIB   = %s/liblapacke64_unused.a\n"
            "DOCSDIR       = %s/docs_unused\n"
            % (cc, sysroot, fc, sysroot, resdir, sdklib,
               os.path.join(flang_pkg, "lib"), ar, ranlib,
               build, build, build, build, build, build)
        )
        save(self, os.path.join(self.source_folder, "make.inc"), make_inc)

    def build(self):
        apply_conandata_patches(self)
        # LD_LIBRARY_PATH：SDK llvm/lib 给 flang/lld 运行期依赖，flang 包 lib 同理。
        flang_pkg = self.dependencies.build["flang-ohos"].package_folder
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
            [os.path.join(self._sdk_llvm(), "lib"), os.path.join(flang_pkg, "lib")])
        for k in ("CFLAGS", "CXXFLAGS", "CPPFLAGS", "LDFLAGS"):
            os.environ.pop(k, None)
        src = self.source_folder
        # 1) ILP64 参考 BLAS（libblas64.a，155 个导出；xerbla.f 引用 Fortran I/O）
        self.run("make -j1 -C BLAS/SRC", cwd=src)
        # 2) libcblas64.a（153 个 cblas_*_64 导出符号）
        self.run("make -j1 -C CBLAS", cwd=src)
        # 3) 上游测试：12 个 blat 驱动（level1/2/3 × s/d/c/z 四精度，64 位模式）
        self.run("make -j1 -C CBLAS/testing", cwd=src)
        self.run("make -C CBLAS/testing run", cwd=src)
        # 4) 测试计数（统计单位 = 测试程序验证行，同 cblas 包）
        pat_pass = re.compile(r"----- PASS -----|PASSED THE")
        pat_fail = re.compile(r"FAIL", re.IGNORECASE)
        total_pass = 0
        total_fail = 0
        rows = []
        for f in sorted(glob.glob(os.path.join(src, "CBLAS", "testing", "*test*.out"))):
            text = open(f, errors="replace").read()
            p = len(pat_pass.findall(text))
            n = len(pat_fail.findall(text))
            total_pass += p
            total_fail += n
            rows.append("%s: PASS=%d FAIL=%d" % (os.path.basename(f), p, n))
        rows.append("TOTAL: PASS=%d FAIL=%d" % (total_pass, total_fail))
        save(self, os.path.join(self.build_folder, "cblas64_upstream_test_summary.txt"),
             "\n".join(rows) + "\n")
        self.output.info("上游 CBLAS64 测试统计：%s" % rows[-1])
        if total_fail:
            raise ConanException(
                "上游 CBLAS64 测试存在失败项（PASS=%d FAIL=%d）" % (total_pass, total_fail))

    def package(self):
        lib = os.path.join(self.package_folder, "lib")
        copy(self, "libcblas64.a", src=self.build_folder, dst=lib)
        # ILP64 参考 BLAS 成对提供（cblas64 包装层把调用转发给其中的 ILP64 符号）
        copy(self, "libblas64.a", src=self.build_folder, dst=lib)
        # libblas64.a 的 xerbla.f 使用 Fortran I/O，消费方链接需 Fortran 运行时
        #（同 lapack 包先例：把 flang 的静态运行时复制进包内 lib）
        flang_pkg = self.dependencies.build["flang-ohos"].package_folder
        for rt in ("libFortranRuntime.a", "libFortranDecimal.a"):
            copy(self, rt, src=os.path.join(flang_pkg, "lib"), dst=lib)
        inc_src = os.path.join(self.source_folder, "CBLAS", "include")
        for h in ("cblas.h", "cblas_64.h", "cblas_mangling.h", "cblas_f77.h"):
            copy(self, h, src=inc_src, dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["cblas64", "blas64", "FortranRuntime", "FortranDecimal"]
        self.cpp_info.system_libs = ["m"]
