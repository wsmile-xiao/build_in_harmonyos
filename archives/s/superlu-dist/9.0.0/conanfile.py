#!/usr/bin/env python3
"""Conan recipe for SuperLU_DIST 9.0.0 (CMake) — OHOS/HarmonyOS PC.

SuperLU_DIST 是 SuperLU 的**分布式内存**版本：按 MPI 进程网格划分矩阵，
用 ParMETIS 做填充约减排序，是 Trilinos/Amesos2 的 SuperLUDist TPL 上游。
与仓内 `superlu`（串行版）是两个不同的包，不可互相替代。

关键适配点：
  * `find_package(MPI REQUIRED)` —— conan 不生成 FindMPI，故显式给出
    `MPI_C_COMPILER`/`MPI_CXX_COMPILER`/`MPIEXEC_EXECUTABLE` 指向依赖包
    的 wrapper，让 CMake 从 wrapper 反解头文件与库（与 trilinos 同款做法）。
  * BLAS 用制品仓 openblas（`TPL_ENABLE_INTERNAL_BLASLIB=OFF` +
    `TPL_BLAS_LIBRARIES`），避免随包再发一份通用 libblas.a 污染生态。
  * ParMETIS 通过 `TPL_PARMETIS_INCLUDE_DIRS` / `TPL_PARMETIS_LIBRARIES`
    给绝对路径，跳过上游的目录搜索（conan 包布局非标准）。
  * Fortran 关闭（`XSDK_ENABLE_Fortran=OFF`）——设备无 gfortran，且本包
    的 C 接口已完整；开启会引入未适配的 Fortran 层。
"""
import os
import textwrap

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.cmake.toolchain.blocks import Block
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get, save)


class SuperluDistConan(ConanFile):
    name = "superlu-dist"
    version = "9.0.0"
    description = ("SuperLU_DIST — distributed memory, MPI based library for "
                   "solving large sparse systems of linear equations")
    license = "BSD-3-Clause"
    homepage = "https://github.com/xiaoyeli/superlu_dist"
    url = "https://github.com/xiaoyeli/superlu_dist"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # MPI 实现必须与 parmetis 一致：parmetis/4.0.3 硬绑 open-mpi/5.0.10，
        # 若此处用 mpich 会在依赖图上冲突（同一进程需两份 MPI 运行时）。
        self.requires("open-mpi/5.0.10")
        # 排序：ParMETIS（并行）+ 其自带的 METIS 由 parmetis 包一并提供
        self.requires("parmetis/4.0.3")
        # BLAS：openblas 同时提供 BLAS/LAPACK
        self.requires("openblas/0.3.33")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        if not os.path.isfile(os.path.join(self.source_folder, "SRC", "CMakeLists.txt")):
            raise ConanException("unexpected source layout: SRC/CMakeLists.txt not found")

    def _mpi_wrapper(self, *names):
        """生成一个 MPI wrapper 脚本，返回其绝对路径。

        不能直接把依赖包里的 `mpicc` 交给 CMake：open-mpi 的 wrapper 是
        `opal_wrapper` 的软链，运行期需要两样东西，而 FindMPI 探测时不会提供：

          * `OPAL_PREFIX` —— 否则 wrapper 去 `//share/openmpi/` 找数据文件
            （实测报 `Cannot open configuration file .../mpicc-wrapper-data.txt`）；
          * `LD_LIBRARY_PATH` 指向本包的 lib/ —— 否则报
            `Error loading shared library libpmix.so.2 / libevent_core-2.1.so.7 /
             libhwloc.so.15`（这些 .so 都在包内，但未进 loader 搜索路径）。

        故生成一层 shell wrapper 把两者设好再 exec，CMake 从 wrapper 反解
        头文件与库即可（与 trilinos 配方同款思路）。
        """
        mpi = self.dependencies["open-mpi"]
        mpi_root = mpi.package_folder
        mpi_bin = os.path.join(mpi_root, "bin")
        target = None
        for nm in names:
            cand = os.path.join(mpi_bin, nm)
            if os.path.isfile(cand):
                target = cand
                break
        if target is None:
            raise ConanException(f"no MPI wrapper among {names} under {mpi_bin}")

        mpi_lib = os.path.join(mpi_root, "lib")
        wrapper = os.path.join(self.build_folder, f"ohc_mpi_{names[0]}")
        os.makedirs(os.path.dirname(wrapper), exist_ok=True)
        save(self, wrapper,
             "#!/bin/sh\n"
             "# 由 conanfile.py 生成：补上 open-mpi wrapper 运行期所需的环境\n"
             f"OPAL_PREFIX={mpi_root}\n"
             "export OPAL_PREFIX\n"
             f"LD_LIBRARY_PATH={mpi_lib}:${{LD_LIBRARY_PATH}}\n"
             "export LD_LIBRARY_PATH\n"
             f"exec {target} \"$@\"\n")
        os.chmod(wrapper, 0o755)
        return wrapper

    def generate(self):
        tc = CMakeToolchain(self)

        class OhosLinuxPlatformBlock(Block):
            """让 CMake 把 OHOS 呈现为 Linux 且**非**交叉编译。

            CMake 没有 Platform/HarmonyOS.cmake，识别系统时会打印
            「System is unknown to cmake, create: Platform/HarmonyOS …」，
            平台相关模块不加载；而 FindMPI 的探测需要「编译 + 链接 + 运行」，
            若被判为交叉编译则 try_run 全部失败。产物与构建机同架构，
            可直接运行，故置 CMAKE_CROSSCOMPILING FALSE。
            （与仓内 trilinos / bliss / neovim-qt 同款做法。）
            """
            template = textwrap.dedent(
                """\
                set(CMAKE_SYSTEM_NAME Linux)
                set(CMAKE_HOST_SYSTEM_NAME Linux)
                set(CMAKE_CROSSCOMPILING FALSE)
                set(CMAKE_SYSTEM_PROCESSOR aarch64)
                set(CMAKE_HOST_SYSTEM_PROCESSOR aarch64)
                """
            )

            def context(self):
                return {}

        tc.blocks["user_toolchain"] = OhosLinuxPlatformBlock
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"

        # 上游 CMake 要求 >= 3.18.1；本机 CMake 4.x 会因 policy 版本过旧报警，
        # 显式抬高策略下限（与 parmetis 配方同款）。
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"

        # Fortran / 文档 / 示例：均关闭（设备无 gfortran，C 接口已完整）
        tc.variables["XSDK_ENABLE_Fortran"] = False
        tc.variables["enable_doc"] = False
        tc.variables["enable_examples"] = False
        tc.variables["enable_tests"] = False

        # MPI：conan 不生成 FindMPI，显式给 wrapper 让 CMake 反解
        tc.cache_variables["MPI_C_COMPILER"] = self._mpi_wrapper("mpicc")
        tc.cache_variables["MPI_CXX_COMPILER"] = self._mpi_wrapper("mpicxx", "mpic++")
        tc.cache_variables["MPIEXEC_EXECUTABLE"] = self._mpi_wrapper("mpiexec")
        tc.cache_variables["MPIEXEC_NUMPROC_FLAG"] = "-n"

        # BLAS：禁用上游内置 CBLAS，改链接制品仓 openblas
        tc.cache_variables["TPL_ENABLE_INTERNAL_BLASLIB"] = False
        blas_lib = os.path.join(
            self.dependencies["openblas"].package_folder, "lib", "libopenblas.a")
        if not os.path.isfile(blas_lib):
            raise ConanException(f"openblas: {blas_lib} not found")
        tc.cache_variables["TPL_BLAS_LIBRARIES"] = blas_lib

        # ParMETIS：给绝对路径（跳过上游目录搜索）
        parmetis = self.dependencies["parmetis"]
        pm_inc = os.path.join(parmetis.package_folder, "include")
        pm_lib = os.path.join(parmetis.package_folder, "lib")
        if not os.path.isfile(os.path.join(pm_inc, "parmetis.h")):
            raise ConanException(f"parmetis: parmetis.h not found under {pm_inc}")
        # 链接序：parmetis → metis
        libs = [os.path.join(pm_lib, f) for f in ("libparmetis.a", "libmetis.a")]
        missing = [p for p in libs if not os.path.isfile(p)]
        if missing:
            raise ConanException(f"parmetis: missing libs {missing}")
        tc.cache_variables["TPL_ENABLE_PARMETISLIB"] = True
        tc.cache_variables["TPL_PARMETIS_INCLUDE_DIRS"] = pm_inc
        tc.cache_variables["TPL_PARMETIS_LIBRARIES"] = ";".join(libs)

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # 许可证：上游 License.txt 在源码根
        from conan.tools.files import copy
        copy(self, "License.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # 产物库名由上游 OUTPUT_NAME 决定：libsuperlu_dist.a / .so
        self.cpp_info.libs = ["superlu_dist"]
        self.cpp_info.set_property("cmake_file_name", "superlu-dist")
        self.cpp_info.set_property("cmake_target_name", "superlu-dist::superlu-dist")
        self.cpp_info.set_property("pkg_config_name", "superlu-dist")
        if self.settings.os in ("Linux", "OHOS"):
            # 上游 CMakeLists 默认 enable_openmp=TRUE，会 find_package(OpenMP)
            # 并把 -fopenmp 加进 CMAKE_C_FLAGS。设备 clang 支持 OpenMP
            # （实测 -fopenmp 可用，SDK 内 libomp.a/.so 齐全），于是静态库内
            # 保留了 __kmpc_* / omp_* 等符号（实测 195 个未定义）——静态库不做
            # 未定义符号检查，但消费者链接时必须能解析它们。
            #
            # 注意**不能**只写 system_libs=["omp"]（= 裸 -lomp）：那样二进制的
            # DT_NEEDED 会有 libomp.so，却不带 RUNPATH，运行期报
            #   Error loading shared library libomp.so: (needed by ./test_superlu_dist)
            # （实测）。而 -fopenmp 由 clang 驱动链接时会同时加上
            # RUNPATH=/data/service/hnp/.../llvm/lib（实测 llvm-readelf 可见），
            # 二进制可直接运行。故用链接标志而非 system_libs
            # （仓内先例：archives/p/perceptualdiff/2.1 用 exelinkflags=-fopenmp=libomp）。
            self.cpp_info.exelinkflags = ["-fopenmp"]
            self.cpp_info.sharedlinkflags = ["-fopenmp"]
            self.cpp_info.system_libs = ["m"]
        else:
            self.cpp_info.system_libs = ["m"]

        # 本包**公开头**直接包含 <mpi.h>（SRC/include/superlu_defs.h:56），
        # 所以消费者的编译行必须有 MPI 的头文件目录。
        # 但制品仓里 open-mpi/5.0.10 生成的 CMakeDeps 数据中
        # `open-mpi_INCLUDE_DIRS_RELEASE` 为**空**（实测），导致
        # `MPI::MPI_C` 目标不带 include 目录 —— 消费方编译即报
        #   fatal error: 'mpi.h' file not found
        # 该缺陷在他人归档（archives/o/open-mpi）内，按 SKILL §0.2 铁律不越权修改，
        # 故在本包侧显式把 MPI 头目录转发出去，保证公开头可被消费。
        mpi_inc = os.path.join(
            self.dependencies["open-mpi"].package_folder, "include")
        if os.path.isdir(mpi_inc):
            self.cpp_info.includedirs.append(mpi_inc)
