#!/usr/bin/env python3
"""Conan recipe for PT-SCOTCH 7.0.12 (CMake) — OHOS/HarmonyOS PC.

PT-SCOTCH 是 SCOTCH 的**并行（MPI）**版本：在分布式内存下做图/网格划分与稀疏
矩阵排序。它与串行版 SCOTCH 出自**同一上游源码树**（`-DBUILD_PTSCOTCH=ON` 即
额外产出 `libptscotch*` 与 `ptscotch.h`），但二者是不同的 conan 包：

  * `scotch/7.0.12`（他人归档，本 PR 不修改）—— 串行版，产物仅
    `scotch.h` / `libscotch.a`；
  * `ptscotch/7.0.12`（本包）—— 并行版，产物含 `ptscotch.h` /
    `libptscotch.a`，是 TriBITS `FindTPLScotch.cmake` 在
    `TPL_ENABLE_MPI` 时**强制要求**的对象（该分支要求 `ptscotch.h` 与
    `ptscotch ptscotcherr scotch scotcherr` 四个库）。

之所以不直接给 `scotch` 加选项：该归档属他人（SKILL §0.2 不越权修改他人归档），
且仓内已有 `superlu`（串行）/`superlu-dist`（MPI）这一「同名拆分」先例。
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get


class PtscotchConan(ConanFile):
    name = "ptscotch"
    version = "7.0.12"
    description = ("PT-SCOTCH — parallel (MPI) graph and mesh partitioning "
                   "library, the distributed-memory companion of SCOTCH")
    license = "CECILL-C"
    homepage = "https://gitlab.inria.fr/scotch/scotch"
    url = "https://gitlab.inria.fr/scotch/scotch"

    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("PT-SCOTCH supports Linux and OHOS")

    def requirements(self):
        # MPI 运行时：PT-SCOTCH 的并行划分依赖它（与仓内 trilinos 同选 mpich）。
        self.requires("mpich/5.0.1.2")
        # 可选压缩后端（上游 USE_ZLIB/USE_LZMA/USE_BZ2）。默认开启以匹配
        # scotch 包的既有配置，保证两者行为一致。
        self.requires("bzip2/1.0.8")
        self.requires("xz/5.6.2")
        self.requires("zlib/1.3.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        if not os.path.isfile(os.path.join(self.source_folder, "CMakeLists.txt")):
            raise ConanInvalidConfiguration(
                "unexpected source layout: CMakeLists.txt not found")

    # ── 工具 ──────────────────────────────────────────────────────────
    @staticmethod
    def _library(folder, names):
        """在包的 lib/ 下按候选名找库文件（静态优先）。"""
        for name in names:
            matches = glob.glob(os.path.join(folder, "lib", name))
            if matches:
                return matches[0]
        return os.path.join(folder, "lib", names[0])

    def generate(self):
        tc = CMakeToolchain(self)
        mpi = self.dependencies["mpich"]
        mpi_root = mpi.package_folder
        mpi_bin = os.path.join(mpi_root, "bin")

        def _mpi_wrapper(name):
            cand = os.path.join(mpi_bin, name)
            if not os.path.isfile(cand):
                raise ConanInvalidConfiguration(
                    f"mpich: wrapper {name} not found under {mpi_bin}")
            return cand

        # MPI：CMake 的 FindMPI 在 OHOS 上无法自行解析，显式给 wrapper
        # （与仓内 trilinos / superlu-dist 同款做法）。
        tc.cache_variables["MPI_C_COMPILER"] = _mpi_wrapper("mpicc")
        tc.cache_variables["MPIEXEC_EXECUTABLE"] = _mpi_wrapper("mpiexec")
        tc.cache_variables["MPIEXEC_NUMPROC_FLAG"] = "-n"

        # 压缩后端：直接给 conan 制品的库与头路径，跳过上游的目录搜索。
        for dep, var, names in (
            ("bzip2", "BZIP2", ["libbz2.a", "libbz2.so"]),
            ("xz", "LIBLZMA", ["liblzma.a", "liblzma.so"]),
            ("zlib", "ZLIB", ["libz.a", "libz.so"]),
        ):
            folder = self.dependencies[dep].package_folder
            lib = self._library(folder, names)
            tc.cache_variables[f"{var}_LIBRARY"] = lib
            tc.cache_variables[f"{var}_LIBRARIES"] = lib
            tc.cache_variables[f"{var}_INCLUDE_DIR"] = os.path.join(folder, "include")
            tc.cache_variables[f"{var}_INCLUDE_DIRS"] = os.path.join(folder, "include")

        # 构建开关：**并行版是本包的全部意义**，故 BUILD_PTSCOTCH 恒为 ON。
        tc.variables["BUILD_SHARED_LIBS"] = False
        tc.variables["BUILD_PTSCOTCH"] = True
        # Fortran 接口关闭：设备无 gfortran；本包的 **C 接口**完整可用。
        tc.variables["BUILD_FORTRAN"] = False
        tc.variables["BUILD_LIBESMUMPS"] = False
        tc.variables["BUILD_LIBSCOTCHMETIS"] = False
        # 上游测试（src/check/）需要外部矩阵数据文件与多进程 MPI，见
        # test_package/MANIFEST.yml 的申报；此处关闭以保持包构建精简。
        tc.variables["ENABLE_TESTS"] = False
        tc.variables["THREADS"] = True
        tc.variables["USE_ZLIB"] = True
        tc.variables["USE_LZMA"] = True
        tc.variables["USE_BZ2"] = True
        tc.generate()

    def build(self):
        mpi_lib = os.path.join(self.dependencies["mpich"].package_folder, "lib")
        # 上游在构建期要**运行**自举工具（dummysizes / ptdummysizes）来生成
        # scotch.h、ptscotch.h 等头文件；这些工具动态链接 libmpi.so，若
        # loader 找不到会报
        #   Error loading shared library libmpi.so.12: (needed by ./dummysizes)
        # 并让 make 以 Error 127 失败（实测）。故构建期把 MPI 的 lib 目录
        # 放进 LD_LIBRARY_PATH。
        env = dict(os.environ)
        prev = env.get("LD_LIBRARY_PATH", "")
        env["LD_LIBRARY_PATH"] = mpi_lib + (":" + prev if prev else "")
        os.environ["LD_LIBRARY_PATH"] = env["LD_LIBRARY_PATH"]

        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE_en.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # 链接序：并行层在前（ptscotch → scotch），错误库随后。
        self.cpp_info.libs = ["ptscotch", "ptscotcherr", "ptscotcherrexit",
                              "scotch", "scotcherr", "scotcherrexit"]
        self.cpp_info.set_property("cmake_file_name", "ptscotch")
        self.cpp_info.set_property("cmake_target_name", "ptscotch::ptscotch")
        self.cpp_info.set_property("pkg_config_name", "ptscotch")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]

        # 本包**公开头**直接包含 <mpi.h>（src/libscotch/library_pt.h），
        # 所以消费者的编译行必须有 MPI 头文件目录。
        # 但制品仓 mpich/5.0.1.2 经 CMakeDeps 生成的 `mpich_INCLUDE_DIRS_RELEASE`
        # 为**空**（实测），导致 `MPI::MPI_C` 目标不带 include 目录 —— 消费方编译
        # 即报 `fatal error: 'mpi.h' file not found`。
        # 该缺陷位于他人归档（archives/m/mpich），按 SKILL §0.2 不越权修改，
        # 故在本包侧显式把 MPI 头目录转发给下游。
        mpi_inc = os.path.join(
            self.dependencies["mpich"].package_folder, "include")
        if os.path.isdir(mpi_inc):
            self.cpp_info.includedirs.append(mpi_inc)
