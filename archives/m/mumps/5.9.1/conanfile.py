#!/usr/bin/env python3
"""Conan recipe — mumps 5.9.1 (Makefile, flang-ohos + openblas)

MUMPS (MUltifrontal Massively Parallel sparse direct Solver) 是 IPOPT 等
数值优化库的核心稀疏线性求解器。本配方：
  - 用 flang-ohos/20.1.0（LLVM Flang 工具链）编译 Fortran 源
  - 用 openblas 提供 BLAS/LAPACK 后端
  - 生成 Makefile.inc 驱动上游 Makefile 构建全部精度库（s/d/c/z）
"""
import glob
import os

from conan import ConanFile
from conan.tools.files import get, export_conandata_patches, apply_conandata_patches, copy


class MumpsConan(ConanFile):
    name = "mumps"
    version = "5.9.1"
    description = "MUMPS: MUltifrontal Massively Parallel sparse direct Solver"
    license = "CeCILL-C"
    homepage = "https://mumps-solver.org/"
    url = ""  # CI fills this

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    exports_sources = "patches/*"

    def requirements(self):
        self.requires("openblas/0.3.28")

    def build_requirements(self):
        self.tool_requires("flang-ohos/20.1.0")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _prepare_env(self):
        """构建环境：定位 flang 包与 SDK，设置 LD_LIBRARY_PATH，清理 HiShell 污染。"""
        flang_pkg = self.dependencies.build["flang-ohos"].package_folder
        fc = os.path.join(flang_pkg, "bin", "flang")
        # LD_LIBRARY_PATH：①SDK llvm/lib 给 lld 正确 libxml2.so.16（HiShell 污染会搞坏 lld）
        #                  ②flang 包 lib 给 flang 运行期的 libLLVM/libMLIR/libclang-cpp
        sdk_llvm_lib = ""
        g = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib"))
        if g:
            sdk_llvm_lib = g[-1]
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
            p for p in [sdk_llvm_lib, os.path.join(flang_pkg, "lib")] if p)
        # 清 HiShell 污染的构建 env
        for k in ("CFLAGS", "CXXFLAGS", "CPPFLAGS", "LDFLAGS", "CMAKE_PREFIX_PATH", "PKG_CONFIG_PATH"):
            os.environ.pop(k, None)
        return flang_pkg, fc, sdk_llvm_lib

    def generate(self):
        """生成 Makefile.inc（MUMPS 的构建配置唯一入口）。"""
        blas_pkg = self.dependencies["openblas"].package_folder
        flang_pkg, fc, sdk_llvm_lib = self._prepare_env()
        cc = "/data/service/hnp/bin/clang"
        ar = "/data/service/hnp/bin/llvm-ar cr "
        ranlib = "/data/service/hnp/bin/llvm-ranlib"
        # examples 链接需要 SDK runtime（libclang_rt.builtins.a / libunwind.a）+ sysroot
        sdk_root = sdk_llvm_lib.replace("/llvm/lib", "")
        resdir = os.path.join(sdk_llvm_lib, "clang", "15.0.4")
        sysroot = os.path.join(sdk_root, "sysroot")
        unw = os.path.join(sdk_llvm_lib, "aarch64-linux-ohos")

        mkinc = """# MUMPS %s Makefile.inc for HarmonyOS PC (aarch64, flang + openblas)
PLAT    =
LIBEXT_SHARED  = .so
SONAME = -soname
SHARED_OPT = -shared
FPIC_OPT = -fPIC
FPIC = -fPIC
RPATH_OPT = -Wl,-rpath,
LIBEXT  = .a
OUTC    = -o
OUTF    = -o
RM      = /bin/rm -f
CC      = %s
FC      = %s
FL      = %s
AR      = %s
RANLIB  = %s
LAPACK  = -L%s/lib -lopenblas
INCSEQ  = -I$(topdir)/libseq
LIBSEQ  = $(LAPACK) -L$(topdir)/libseq -lmpiseq$(PLAT)
LIBBLAS = -L%s/lib -lopenblas
LIBOTHERS = -lpthread -L%s/lib -lFortranRuntime -lFortranDecimal -lFortranCommon -lm
CDEFS = -DAdd_
OPTF    = -O2
OPTC    = -O2 -I.
OPTL    = -O2 -resource-dir %s --sysroot=%s -L%s
INCS = $(INCSEQ)
LIBS = $(LIBSEQ)
LIBSEQNEEDED = libseqneeded
ORDERINGSF  = -Dpord
ORDERINGSC  = $(ORDERINGSF)
LPORDDIR = $(topdir)/PORD/lib/
IPORD    = -I$(topdir)/PORD/include/
LPORD    = -L$(LPORDDIR) -lpord$(PLAT)
LORDERINGS = $(LPORD)
IORDERINGSF = $(IPORD)
IORDERINGSC = $(IPORD)
""" % (self.version, cc, fc, fc, ar, ranlib,
       blas_pkg, blas_pkg, flang_pkg, resdir, sysroot, unw)
        with open(os.path.join(self.source_folder, "Makefile.inc"), "w") as f:
            f.write(mkinc)

    def build(self):
        apply_conandata_patches(self)
        self._prepare_env()
        # make all：构建 s/d/c/z 全部精度库 + PORD + libseq
        self.run("make all", cwd=self.source_folder)

    def package(self):
        # 静态库 + 头文件（含 libseq 的 MPI 桩头，串行模式消费者需要）
        # 注意：conan copy 保留通配符相对路径，须将 src 精确到源目录、dst 精确到目标目录
        copy(self, "*.a", src=os.path.join(self.source_folder, "lib"),
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "*.h", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "*.h.in", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "mpi.h", src=os.path.join(self.source_folder, "libseq"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "mpif.h", src=os.path.join(self.source_folder, "libseq"),
             dst=os.path.join(self.package_folder, "include"))
        # flang 编译的静态库依赖 Fortran runtime，打入包内供消费者链接
        flang_pkg = self.dependencies.build["flang-ohos"].package_folder
        for _f in ("libFortranRuntime.a", "libFortranDecimal.a", "libFortranCommon.a"):
            copy(self, _f, src=os.path.join(flang_pkg, "lib"),
                 dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        # 静态库链接顺序敏感：求解器 → common → 排序/MPI 桩 → Fortran runtime → 系统库
        self.cpp_info.libs = ["dmumps", "mumps_common", "pord", "mpiseq",
                              "FortranRuntime", "FortranDecimal", "FortranCommon"]
        self.cpp_info.system_libs = ["m", "pthread"]
        self.cpp_info.set_property("cmake_file_name", "mumps")
        self.cpp_info.set_property("cmake_target_name", "mumps::mumps")
        self.cpp_info.set_property("pkg_config_name", "mumps")
