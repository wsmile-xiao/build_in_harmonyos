#!/usr/bin/env python3
"""Conan recipe — cblas 3.12.1 (Makefile, HarmonyOS PC / os=OHOS arch=armv8)

Netlib CBLAS：BLAS 的标准 C 接口绑定（lapack 3.12.1 发行版中的 CBLAS 组件）。
主体是 C 包装层，另含少量 Fortran 桥接子例程（CBLAS/src/*.f，如 sdotsub.f），
链接时需要一个 BLAS 实现提供 ddot_/dgemm_ 等 LP64 Fortran 符号。

依赖：
  - requires openblas/0.3.34（ohpcd 已发布；提供 LP64 Fortran BLAS 符号，测试驱动
    以其静态库链接，运行期零环境依赖）
  - tool_requires flang-ohos/20.1.0（编 CBLAS/src 的 Fortran 桥接 .f；C 端用设备
    hnp clang，经 profile conf tools.build:compiler_executables 取得）

源码：Reference-LAPACK lapack 3.12.1 官方 tarball（netlib CBLAS 自 LAPACK 3.x 起
随 LAPACK 发行，netlib.org/blas/cblas.tgz 是不含 3.12.1 的历史独立包）。本包只
构建其中的 CBLAS 组件（上游 make 入口 CBLAS/Makefile → src 产 libcblas.a；
testing 产 12 个 blat 驱动并 make run 跑上游测试）。绕开 CMake 路径的原因：
顶层 CMake 的 CBLAS 构建需 FortranCInterface_VERIFY 混合链接验证，flang-ohos
精简运行集无法完成（同 lapack 包 BUILD_CBLAS=ON 实际未产 CBLAS 的先例）；
make 路径无此依赖，探索实测可全程设备原生构建并跑通全部上游测试。
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


class CblasConan(ConanFile):
    name = "cblas"
    version = "3.12.1"
    description = "CBLAS - the standard C interface to BLAS (CBLAS component of LAPACK 3.12.1)"
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
        self.requires("openblas/0.3.34")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _sdk_llvm(self):
        g = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm"))
        if not g:
            raise ConanException("未找到 ohos-sdk llvm 工具链目录")
        return g[-1]

    def generate(self):
        # 生成上游 make 构建入口（CBLAS/Makefile → include $(TOPSRCDIR)/make.inc）所需
        # 的 make.inc；变量集为设备原生探索实测所得。库与测试产物一律指向 build_folder，
        # 不在源码树留二进制。GNU make 内置 .f.o 规则用 $(FC) $(FFLAGS) 编 Fortran 桥接。
        flang_pkg = self.dependencies.build["flang-ohos"].package_folder
        fc = os.path.join(flang_pkg, "bin", "flang")
        ob_libdir = self.dependencies["openblas"].cpp_info.libdirs[0]
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
            "CFLAGS = -O2 -fPIC\n"
            "FC = %s --target=aarch64-linux-ohos --sysroot=%s -resource-dir=%s\n"
            "FFLAGS = -O2 -fPIC\n"
            "FFLAGS_DRV = $(FFLAGS)\n"
            "FFLAGS_NOOPT = -O0\n"
            "LDFLAGS = -L%s -L%s -lFortranRuntime -lFortranDecimal -lm\n"
            "AR = %s\n"
            "ARFLAGS = cr\n"
            "RANLIB = %s\n"
            "TIMER = INT_ETIME\n"
            "BLASLIB      = %s/libopenblas.a\n"
            "CBLASLIB     = %s/libcblas.a\n"
            "LAPACKLIB    = %s/liblapack_unused.a\n"
            "TMGLIB       = %s/libtmglib_unused.a\n"
            "LAPACKELIB   = %s/liblapacke_unused.a\n"
            "DOCSDIR       = %s/docs_unused\n"
            % (cc, sysroot, fc, sysroot, resdir, sdklib,
               os.path.join(flang_pkg, "lib"), ar, ranlib,
               ob_libdir, build, build, build, build, build)
        )
        save(self, os.path.join(self.source_folder, "make.inc"), make_inc)

    def build(self):
        apply_conandata_patches(self)
        # LD_LIBRARY_PATH：SDK llvm/lib 给 flang/lld 运行期依赖（libLLVM/libMLIR、
        # libxml2），flang 包 lib 同理。直接改 os.environ（self.run 的 env= 参数是
        # conan env-file 名列表、非 dict）；并清 HiShell 污染的构建 env。
        flang_pkg = self.dependencies.build["flang-ohos"].package_folder
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
            [os.path.join(self._sdk_llvm(), "lib"), os.path.join(flang_pkg, "lib")])
        for k in ("CFLAGS", "CXXFLAGS", "CPPFLAGS", "LDFLAGS"):
            os.environ.pop(k, None)
        src = self.source_folder
        # 1) libcblas.a（153 个 cblas_ 导出符号）
        self.run("make -j1 -C CBLAS", cwd=src)
        # 2) 上游测试：12 个 blat 驱动（level1/2/3 × s/d/c/z 四精度）
        self.run("make -j1 -C CBLAS/testing", cwd=src)
        # 3) 运行上游测试：blat1 自包含；blat2/3 读源码树内 *in2/*in3 数据文件
        self.run("make -C CBLAS/testing run", cwd=src)
        # 4) 测试计数（统计单位 = 测试程序验证行；blat1 为 subprogram 结果，
        #    blat2/3 为 column-major/row-major 计算与 error-exit 检查行）
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
        save(self, os.path.join(self.build_folder, "cblas_upstream_test_summary.txt"),
             "\n".join(rows) + "\n")
        self.output.info("上游 CBLAS 测试统计：%s" % rows[-1])
        if total_fail:
            raise ConanException(
                "上游 CBLAS 测试存在失败项（PASS=%d FAIL=%d）" % (total_pass, total_fail))

    def package(self):
        copy(self, "libcblas.a", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"))
        # 公开头文件：cblas.h（标准接口）、cblas_mangling.h（make 期由 *_with_flags.h.in
        # 复制生成）、cblas_f77.h（f77 底层绑定）。测试头与模板不出包。
        inc_src = os.path.join(self.source_folder, "CBLAS", "include")
        for h in ("cblas.h", "cblas_mangling.h", "cblas_f77.h"):
            copy(self, h, src=inc_src, dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["cblas"]
        # BLAS 符号由 openblas 提供，经 requires 依赖链自动传递给消费方
        self.cpp_info.system_libs = ["m"]
