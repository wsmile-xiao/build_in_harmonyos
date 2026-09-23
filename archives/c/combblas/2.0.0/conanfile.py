#!/usr/bin/env python3
"""Conan recipe — CombBLAS 2.0.0 (CMake, C++14, MPI + OpenMP).

Combinatorial BLAS: extensible distributed-memory parallel graph library
(PASSIONLab). Mostly templated header-only code plus a small binary library
(CommGrid/MPIType/MPIOp/MemoryPool/hash/mmio).

OHOS adaptation notes:
- Dep: mpich/4.0.3 (ohpcd) — find_package(MPI REQUIRED). mpich package
  exports CMakeDeps target MPI::MPI_C (cmake_target_name), while CombBLAS
  links MPI::MPI_CXX when available; ensure MPI_CXX include/lib reachable.
- OpenMP: clang -fopenmp (no conan package needed), find_package(OpenMP).
- Static linking (default shared=False) to match R26.
- Upstream tests need testinputs (testdata_combblas1.6.1.tgz from
  eecs.berkeley.edu); CI network-blocked -> kept out of the build, the
  recipe builds library + installs headers only; upstream tests verified
  separately (see manifest).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches


class CombblasConan(ConanFile):
    name = "combblas"
    version = "2.0.0"
    description = "Combinatorial BLAS - distributed-memory parallel graph analytics library"
    license = "BSD-3-Clause"
    homepage = "https://github.com/PASSIONLab/CombBLAS"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # MPI：mpich/4.0.3（ohpcd 已发布，gforker 进程管理器，OHOS 可运行）
        self.requires("mpich/4.0.3", transitive_headers=True, transitive_libs=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        self._patch_mpio_compat()
        self._patch_pbbs_mallopt()
        self._patch_gnu_parallel()

    def _patch_gnu_parallel(self):
        """Applications/BipartiteMatchings/ApproxWeightPerfectMatching.h include
        GCC 扩展头 <parallel/algorithm>/<parallel/numeric>（libstdc++ 并行模式），
        OHOS clang + libc++ 无 → 替换为普通 <algorithm>/<numeric>（__gnu_parallel
        仅并行加速非必需）。"""
        hdr = os.path.join(self.source_folder, "Applications", "BipartiteMatchings",
                           "ApproxWeightPerfectMatching.h")
        if not os.path.isfile(hdr):
            self.output.warning("ApproxWeightPerfectMatching.h not found; gnu_parallel patch skipped")
            return
        text = open(hdr, encoding="utf-8", errors="ignore").read()
        old1 = "#include <parallel/algorithm>"
        old2 = "#include <parallel/numeric>"
        changed = False
        if old1 in text:
            text = text.replace(old1, "#include <algorithm>")
            text = text.replace(old2, "#include <numeric>")
            changed = True
        # __gnu_parallel::sort 是 GCC 并行模式扩展命名空间，clang 无 → std::sort
        if "__gnu_parallel::sort" in text:
            text = text.replace("__gnu_parallel::sort", "std::sort")
            changed = True
        if changed:
            open(hdr, "w", encoding="utf-8").write(text)
            self.output.info("patched ApproxWeightPerfectMatching.h: <parallel/algorithm>/<parallel/numeric> -> <algorithm>/<numeric>, __gnu_parallel::sort -> std::sort")
        else:
            self.output.info("ApproxWeightPerfectMatching.h parallel include not matched; skip")

    def _patch_pbbs_mallopt(self):
        """PBBS/utils.h 用 glibc 的 mallopt(M_MMAP_MAX/M_TRIM_THRESHOLD)（GNU 特有），
        OHOS musl libc 无这些宏 → 守卫掉（仅 glibc 生效，其它平台跳过）。"""
        hdr = os.path.join(self.source_folder, "include", "CombBLAS", "PBBS", "utils.h")
        if not os.path.isfile(hdr):
            self.output.warning("PBBS/utils.h not found; mallopt patch skipped")
            return
        text = open(hdr, encoding="utf-8", errors="ignore").read()
        old = """static int __ii =  mallopt(M_MMAP_MAX,0);
static int __jj =  mallopt(M_TRIM_THRESHOLD,-1);"""
        new = """#ifdef __GLIBC__
static int __ii =  mallopt(M_MMAP_MAX,0);
static int __jj =  mallopt(M_TRIM_THRESHOLD,-1);
#endif"""
        if old in text:
            text = text.replace(old, new)
            open(hdr, "w", encoding="utf-8").write(text)
            self.output.info("patched PBBS/utils.h: guard glibc mallopt (musl lacks M_MMAP_MAX/M_TRIM_THRESHOLD)")
        else:
            self.output.info("PBBS/utils.h mallopt block not matched; skip")

    def _patch_mpio_compat(self):
        """ohpcd 的 mpich/4.0.3 配方 --disable-romio（ROMIO=MPI-IO 实现被禁用），
        mpi.h 缺 MPI_File_open/read_at/write/close 声明与 MPI_MODE_CREATE/WRONLY/RDONLY
        宏（MPI_File 类型有 typedef 但 ADIOI_FileD 结构未定义）。
        CombBLAS 的 SpParHelper.cpp/FullyDistSpVec.cpp/SpParMat.cpp 用了这些 MPI-IO
        API（读 Matrix Market 文件 / DebugPrintKeys）。补全 ADIOI_FileD 结构 + 用
        stdio 实现 MPI-IO 子集（语义等价：fopen/fseek/fread/fwrite），
        patch 进 CombBLAS.h 主头。"""
        compat = """/* OHOS mpio compat: mpich (--disable-romio) lacks MPI-IO function decls.
 * mpi.h typedefs struct ADIOI_FileD *MPI_File but the struct is undefined —
 * define it here and provide stdio-based stand-ins for the MPI-IO subset
 * CombBLAS uses (single-process semantics: fopen/fseek/fread/fwrite). */
#include <cstdio>
#include <mpi.h>
#ifndef MPI_MODE_CREATE
#define MPI_MODE_CREATE 1
#endif
#ifndef MPI_MODE_RDONLY
#define MPI_MODE_RDONLY 2
#endif
#ifndef MPI_MODE_WRONLY
#define MPI_MODE_WRONLY 4
#endif
/* mpi.h: typedef struct ADIOI_FileD *MPI_File; — complete the struct */
struct ADIOI_FileD { FILE * f; };
inline int MPI_File_open(MPI_Comm comm, const char * name, int amode, MPI_Info info, MPI_File * fh) {
    const char * mode = (amode & MPI_MODE_CREATE) ? "wb+" : "rb";
    FILE * f = std::fopen(name, mode);
    if (!f) return 1;
    *fh = new ADIOI_FileD();
    (*fh)->f = f;
    return 0;
}
inline int MPI_File_close(MPI_File * fh) {
    if (*fh) { if ((*fh)->f) std::fclose((*fh)->f); delete *fh; *fh = nullptr; }
    return 0;
}
inline int MPI_File_set_view(MPI_File fh, MPI_Offset disp, MPI_Datatype etype, MPI_Datatype filetype, const char * datarep, MPI_Info info) {
    return std::fseek(fh->f, (long)disp, SEEK_SET);
}
/* 元素大小必须取自 MPI_Type_size(dt)，不能用 (dt==MPI_CHAR)?1:sizeof(int) 猜测：
   CombBLAS 用 MPI_Type_contiguous(sizeof(mystruct), MPI_CHAR, &dt) 造出的是
   带 sizeof(mystruct) 偏移/大小的派生类型（如 {int ind; double num;} → 16 字节），
   而 sizeof(int)=4 会让 fwrite/fread 只搬 1/4 数据 → 读到残缺记录 → 段错误。 */
inline int OHOS_mpio_elemsize(MPI_Datatype dt, int * out) {
    return MPI_Type_size(dt, out);
}
inline int MPI_File_write(MPI_File fh, const void * buf, int count, MPI_Datatype dt, MPI_Status * st) {
    int dsize = 0;
    if (OHOS_mpio_elemsize(dt, &dsize) != MPI_SUCCESS || dsize <= 0) return 1;
    size_t wr = std::fwrite(buf, (size_t)dsize, count, fh->f);
    if (st) { st->count_lo = (int)wr; st->count_hi_and_cancelled = 0; }
    return (wr == (size_t)count) ? 0 : 1;
}
inline int MPI_File_write_all(MPI_File fh, const void * buf, int count, MPI_Datatype dt, MPI_Status * st) {
    return MPI_File_write(fh, buf, count, dt, st);
}
inline int MPI_File_read_at(MPI_File fh, MPI_Offset offset, void * buf, int count, MPI_Datatype dt, MPI_Status * st) {
    if (std::fseek(fh->f, (long)offset, SEEK_SET) != 0) return 1;
    int dsize = 0;
    if (OHOS_mpio_elemsize(dt, &dsize) != MPI_SUCCESS || dsize <= 0) return 1;
    size_t got = std::fread(buf, (size_t)dsize, count, fh->f);
    if (st) { st->count_lo = (int)got; st->count_hi_and_cancelled = 0; }
    return 0;
}
/* end OHOS mpio compat */
"""
        hdr = os.path.join(self.source_folder, "include", "CombBLAS", "CombBLAS.h")
        if not os.path.isfile(hdr):
            self.output.warning("CombBLAS.h not found; mpio compat skipped")
            return
        text = open(hdr, encoding="utf-8", errors="ignore").read()
        marker = "/* OHOS mpio compat"
        if marker in text:
            self.output.info("mpio compat already patched")
            return
        # 插到 #include <mpi.h> 之后（保证 MPI_File 类型可用）
        pos = text.find("#include <mpi.h>")
        if pos == -1:
            pos = text.find("#include")
        nl = text.find("\n", pos)
        text = text[:nl+1] + compat + text[nl+1:]
        open(hdr, "w", encoding="utf-8").write(text)
        self.output.info("patched CombBLAS.h: added stdio-based mpio compat (mpich no ROMIO)")

    def generate(self):
        tc = CMakeToolchain(self)
        # CMake 4.x 兼容：上游 cmake_minimum_required(3.3) 与 CMake 4.x 冲突，
        # 需命令行 -DCMAKE_POLICY_VERSION_MINIMUM=3.5 注入（toolchain CACHE 变量
        # 在 cmake_minimum_required 检查时未生效，clfft 同款方案）
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # 依赖 include/lib 路径注入（CombBLAS 用 find_package(MPI)，但 mpich 的
        # CMakeDeps target 是 MPI::MPI_C 而 CombBLAS 链接 MPI::MPI_CXX——确保
        # 两套 include/lib 都可达）
        mpi_include = None
        for _n, dep in self.dependencies.items():
            for p in dep.cpp_info.includedirs:
                flag = "-I" + p
                if flag not in tc.extra_cxxflags:
                    tc.extra_cxxflags.append(flag)
                if flag not in tc.extra_cflags:
                    tc.extra_cflags.append(flag)
            for p in dep.cpp_info.libdirs:
                flag = "-L" + p
                if flag not in tc.extra_sharedlinkflags:
                    tc.extra_sharedlinkflags.append(flag)
                if flag not in tc.extra_exelinkflags:
                    tc.extra_exelinkflags.append(flag)
            # 【CI 修复】取 mpich 的真实 include 目录，用于下面预置 FindMPI 变量。
            if dep.ref.name == "mpich" and dep.cpp_info.includedirs:
                mpi_include = os.path.abspath(dep.cpp_info.includedirs[0])
        # 【CI 修复】mpich 的 mpicc wrapper 与 mpich.pc 硬编码了构建期 prefix
        # （-I<hidden-prefix>/include），FindMPI 通过 `mpicc -show` 抓取该路径并写入
        # MPI::MPI_C{,_CXX} 的 INTERFACE_INCLUDE_DIRECTORIES。本地该 prefix 恰好存在
        # 故不报错，CI 上不存在 → CMake 报 "Imported target MPI::MPI_C includes
        # non-existent path"。FindMPI 对 COMPILER_INCLUDE_DIRS/HEADER_DIR 的赋值均为
        # `if(NOT <var>)`（见 FindMPI.cmake:906/1168），**预置这些 cache 变量即可
        # 阻止 wrapper 探测结果污染 target**；同时仍保留 mpicc 提供链接参数。
        if mpi_include:
            for var in ("MPI_C_COMPILER_INCLUDE_DIRS", "MPI_CXX_COMPILER_INCLUDE_DIRS",
                        "MPI_C_HEADER_DIR", "MPI_CXX_HEADER_DIR"):
                tc.variables[var] = mpi_include
            # 供 CMake 侧二次兜底（见 cmake.configure 的 variables）
            self._mpi_include = mpi_include
        # MPI 编译器包装：mpich 的 mpicc 提供 MPI 编译/链接必要参数；
        # 用 clang + 显式 -I/-L（Conan 注入）避免依赖 mpicc 包装
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # CMake 4.x 对旧 cmake_minimum_required(<3.5) 的官方豁免：CMAKE_POLICY_VERSION_MINIMUM
        # 必须经命令行 -D 传入（toolchain 内变量不生效，clfft/clpeak 同款）
        variables = {"CMAKE_POLICY_VERSION_MINIMUM": "3.5"}
        # 兜底：命令行 -D 优先于 toolchain 的 CACHE 写法，确保 FindMPI 必定读到我方路径
        mpi_include = getattr(self, "_mpi_include", None)
        if mpi_include:
            for var in ("MPI_C_COMPILER_INCLUDE_DIRS", "MPI_CXX_COMPILER_INCLUDE_DIRS",
                        "MPI_C_HEADER_DIR", "MPI_CXX_HEADER_DIR"):
                variables[var] = mpi_include
        cmake.configure(variables=variables)
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["CombBLAS"]
        self.cpp_info.includedirs = ["include"]
        # 传递 MPI 依赖：CombBLAS 公共头大量使用 MPI 类型/宏
        self.cpp_info.requires = ["mpich::mpich"]
        self.cpp_info.bindirs = ["bin"]
