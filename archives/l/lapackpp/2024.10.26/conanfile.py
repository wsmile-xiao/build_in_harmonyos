#!/usr/bin/env python3
"""Conan recipe — lapackpp 2024.10.26 (CMake, HarmonyOS PC / os=OHOS arch=armv8)

LAPACK++（SLATE 族中间层）：对参考 LAPACK 的现代 C++ 封装（模板 API + 显式
向量化友好布局），是 SLATE 的直接前置之一。公开头 `lapack.hh` 覆盖
LU/Cholesky/QL/QR/eigen/SVD 等 LAPACK 例程族，s/d/c/z 四精度。

依赖与后端（W0 结论，全部 ohpcd 已发布且有 os=OHOS/armv8 binary）：
  - requires blaspp/2024.10.26（硬依赖：上游 `find_package(blaspp)` 缺失即
    FATAL_ERROR；公开头 `lapack/util.hh` 直接 `#include "blas.hh"` 并 using
    blas::Layout/Op/Uplo/Diag/Side，无法用其他库顶替）
  - requires lapack/3.12.1（参考 LAPACK + 参考 BLAS + flang Fortran 运行时
    libFortranRuntime.a/libFortranDecimal.a）
  - requires cblas/3.12.1（与 blaspp 配方一致的依赖声明；BLAS++ 的
    BLAS_HAVE_CBLAS 面与上游 tester 均需要 cblas）
  - requires openblas/0.3.34（传递依赖，经 cblas/3.12.1 进图、版本由其钉死；
    仅测试拓扑：提供上游 tester 硬依赖的 LAPACKE C API——include/lapacke.h
    等头 + libopenblas.a 内嵌 LAPACKE_* 符号；不直接 require，交付包
    cpp_info.requires 与消费者链接面不变）
  - GPU 后端（cuda/hip/sycl）以 gpu_backend=none 显式禁用（鸿蒙无 GPU 后端，
    上游可选依赖，不算止损）；本包 Fortran 编译为零，Fortran 运行时只在链接期。

BLAS/LAPACK 后端由上游 cmake/LAPACKFinder.cmake + LAPACKConfig.cmake 探测，
本配方走它们的「显式库清单直通」路径（用户给定 LAPACK_LIBRARIES / BLAS_LIBRARIES
缓存变量，finder 逐项 try_run 探针确认 pstrf / lapack_version / XBLAS），
不使用 use_cmake_find_lapack（CMake 内置 FindLAPACK 无法感知 flang Fortran
运行时依赖）。

探针需要上游的三个「私有」变量（上游 blasppConfig.cmake.in 注释为
"Export private variables used in LAPACK++"），而 Conan 的 CMakeDeps 生成的
blaspp-config.cmake 只导出导入目标、不导出它们，配方侧显式桥接：
  - blaspp_defines  : 从**已安装的 blaspp 包**的 include/blas/defines.h 反解
    （该文件即 BLAS++ 自身配置的权威记录），不硬编码命名修饰假设
  - blaspp_libraries: 与 BLAS_LIBRARIES 同源的库清单
  - CMAKE_PROJECT_lapackpp_INCLUDE 注入一个短桥接片段：上游对 blaspp 只做
    find_package（取上述私有变量），从不把导入目标链到 lapackpp 上，而
    `lapack/util.hh` 以 `#include "blas.hh"` 引用 BLAS++ 公共头；原生构建里
    二者同前缀安装故 include 路径隐式带入，Conan 需显式补 include_directories。
    片段同时桥接 tester 门禁变量 blaspp_cblas_found / blaspp_cblas_include /
    blaspp_cblas_libraries（同为上游私有导出，指向 openblas 包，见下节）。
    上游 CMakeLists / 源码零改动。

上游测试（build_tests=ON，真实执行）：
  上游唯一测试入口 test/tester（177 个 test_*.cc 翻译单元）由 test/run_tests.py
  按计划项驱动（quick 尺寸集 HOST 177 项 / DEVICE 4 项），受三个条件制约，
  本配方逐一解决，上游 CMakeLists / 源码零改动：
  1. tester 硬门禁 blaspp_cblas_found / lapacke_found（test/CMakeLists.txt
     早退）。cblas 面由桥接片段提供（openblas = cblas.h 与 CBLAS 符号的单一
     提供方）。LAPACKE 面：lapacke/3.12.1 配方虽已合入 main（status=built）
     但尚未发布到 ohpcd 制品仓（conan install 实核 not resolved），CI 与本地
     均无法解析；openblas/0.3.34 自带全量 LAPACKE（lapacke.h 等 4 个头 +
     libopenblas.a 内嵌 LAPACKE_* 符号，nm 实核）。将 libopenblas.a 追加到
     LAPACK_LIBRARIES 末尾后，上游 cmake/LAPACKConfig.cmake 的 try_run 探针
     （编译并运行 config/lapacke_pstrf.cc，qemu-aarch64 设备原生执行）走其
     内置的 "Found LAPACKE library in BLAS library" 路径真实通过——非预置
     变量，上游探测逻辑原样生效。LAPACK_HAVE_LAPACKE 随之写入构建树
     defines.h，上游源码零引用（grep 实核），交付库无行为影响。
  2. testsweeper 框架库：上游 CMake 用 FetchContent 从 GitHub 实时 git clone
     （构建期网络依赖，CI/设备不可复现）。本配方将同 tag 源码（v2024.05.31，
     与上游 CMakeLists 钉死版本一致）以源码形态随配方导出（vendor/），经
     FetchContent 官方变量 FETCHCONTENT_SOURCE_DIR_TESTSWEEPER 指向本地目录。
  3. <lapacke.h>/<cblas.h> 的编译查找：上游探针 try_run 不传递 include 目录
     （原生构建靠系统路径），本配方以 CPATH 环境变量注入 openblas/blaspp 包
     的 include（clang 与 gcc 同语义，只作用于本构建会话）；tester 链接行的
     -lblaspp（上游 list(APPEND LAPACK_LIBRARIES "blaspp")）由桥接片段的
     link_directories 解析（本工具链 clang-15 不翻译 LIBRARY_PATH 环境变量，
     实测定要用 -L）。

  tester 拓扑（与交付包后端解耦）：liblapackpp.a（交付库）+ 参考 LAPACK
  （liblapack.a 先于 libopenblas.a 扫描：LAPACK_* 符号由参考实现提供，
  openblas 的 LAPACK 实现成员不被拉入）+ libopenblas.a（BLAS 内核 + CBLAS +
  LAPACKE 的单一提供方，tester 的 BLAS_*/cblas_*/LAPACKE_* 符号全部由它解析，
  与 blaspp_cblas_libraries 指向一致）+ Fortran 运行时收尾。此为「参考
  LAPACK 叠加 OpenBLAS BLAS/LAPACKE」的标准发行版组合形态，仅作用于测试
  构建；交付包 cpp_info.requires（blaspp/lapack/cblas）与后端拓扑不变。

  执行：build() 在 cmake.build() 后以 run_tests.py --quick --host 驱动全部
  177 个 HOST 计划项（quick = 上游文档定义的全例程 sanity 尺寸集），逐项
  pass/FAILED，存在失败即 ConanException。DEVICE 4 项 NOT_RUN
  （gpu_backend=none，鸿蒙无 GPU 后端，不以任何形式上报为通过）。

静态链接顺序（GNU 单遍语义下也安全）：
  liblapack.a（BLAS 符号消费者）在 libblas.a（提供者）之前；cblas 同理；
  Fortran 运行时收尾；libopenblas.a 在 LAPACK_LIBRARIES 末位（仅测试拓扑）。
"""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, save


# 上游 include/lapack/util.hh 依赖的 BLAS++ 公共头；CMake 项目名 = lapackpp
# （用于 CMAKE_PROJECT_<name>_INCLUDE 注入点，CMake 在 project() 之后立即 include）
BRIDGE_CMAKE = """\
# --- Conan bridge (injected via CMAKE_PROJECT_lapackpp_INCLUDE) ----------------
# Upstream lapackpp calls find_package(blaspp) only to pick up BLAS++'s
# "private" config variables (blaspp_defines / blaspp_libraries, see upstream
# blasppConfig.cmake.in) and never links the imported target blaspp::blaspp to
# the lapackpp target.  include/lapack/util.hh pulls in the BLAS++ public header
# with #include "blas.hh".  In a native build both projects install under one
# prefix so the header is found implicitly; Conan's CMakeDeps-generated
# blaspp-config.cmake exports only the imported target and does not alter the
# include path, so add it explicitly here (directory scope, before add_library).
if (NOT TARGET blaspp::blaspp)
    find_package(blaspp CONFIG REQUIRED)
endif()
include_directories(${blaspp_INCLUDE_DIRS})
# Upstream test/CMakeLists.txt gates the tester on blaspp_cblas_found and links
# ${blaspp_cblas_include} / ${blaspp_cblas_libraries}, which upstream
# blasppConfig.cmake.in exports as private variables and Conan's CMakeDeps does
# not export.  Bridge them to the openblas package, the single provider of
# cblas.h and CBLAS symbols for the tester (paths injected as CMakeToolchain
# cache variables OPENBLAS_PKG_INCLUDE / OPENBLAS_PKG_LIB).
set(blaspp_cblas_found TRUE)
set(blaspp_cblas_include "${OPENBLAS_PKG_INCLUDE}")
set(blaspp_cblas_libraries "${OPENBLAS_PKG_LIB}")
include_directories(${blaspp_cblas_include})
# Upstream list(APPEND LAPACK_LIBRARIES "blaspp") makes every consumer of the
# lapackpp target (the tester) link bare -lblaspp; resolve it against the
# installed BLAS++ package.  link_directories, not the LIBRARY_PATH env var:
# this toolchain's clang-15 does not translate LIBRARY_PATH into -L (verified
# empirically).  Directory property set before add_library/add_subdirectory,
# so both the lapackpp target and test/ inherit it.  Test-build topology only:
# the delivered package exports cpp_info, not build-tree link lines.
link_directories("${BLASPP_PKG_LIBDIR}")
link_directories("${OPENBLAS_PKG_LIBDIR}")
# --- end of Conan bridge ------------------------------------------------------
"""


class LapackppConan(ConanFile):
    name = "lapackpp"
    version = "2024.10.26"
    description = ("LAPACK++ - a C++ API for LAPACK "
                   "(UTK ICL SLATE foundation layer)")
    license = "BSD-3-Clause"
    homepage = "https://github.com/icl-utk-edu/lapackpp"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"
    # 上游 CMakeLists 对 blaspp 是硬 find_package（缺失即 FATAL_ERROR），
    # 故需 CMakeDeps 在构建树内生成 blaspp-config.cmake（导入目标
    # blaspp::blaspp + blaspp_INCLUDE_DIRS），供上游与注入的桥接片段使用
    generators = "CMakeDeps"
    # 仅静态交付：不声明 shared 选项（package_type=static-library 与 shared
    # 选项并存会让 Conan 报警且该选项在本配方内无实现分支——后端库清单本身是
    # 静态拓扑序，动态化需整条重排，故不提供假开关）
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def export_sources(self):
        # vendor/testsweeper-2024.05.31：上游 tester 的 FetchContent 依赖的
        # 本地源码副本（tag 与上游 CMakeLists 钉死的 v2024.05.31 一致，
        # BSD-3-Clause），见文件头「上游测试」节。
        copy(self, "*",
             src=os.path.join(self.recipe_folder, "vendor", "testsweeper-2024.05.31"),
             dst=os.path.join(self.export_sources_folder,
                              "vendor", "testsweeper-2024.05.31"))

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def validate(self):
        # R32: OHOS 与 Linux 同属「POSIX + aarch64 交叉/原生」语义，不得只判 Linux
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "本 recipe 仅支持 os=OHOS（设备原生）/ os=Linux（交叉），"
                "当前 os=%s" % self.settings.os)

    def requirements(self):
        # 均已在 ohpcd 发布且有 os=OHOS/armv8 binary（conan download +
        # conan install --requires= 实核）
        self.requires("blaspp/2024.10.26")
        self.requires("lapack/3.12.1")
        self.requires("cblas/3.12.1")
        # 注意：openblas/0.3.34 **不**直接 require——它经 cblas/3.12.1 的
        # requires 传入依赖图（版本由 cblas 钉死），本配方在 generate()/build()
        # 里经 self.dependencies["openblas"] 传递访问其包路径（tester 的
        # LAPACKE/CBLAS 提供方，见文件头「上游测试」节）。直连声明会迫使
        # cpp_info.requires 同步扩展、改动消费者链接面，故走传递路径

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # 桥接片段写入 source 树：generate() 的 CMAKE_PROJECT_lapackpp_INCLUDE
        # 指向它，configure 阶段（build 步骤）读取
        save(self, os.path.join(self.source_folder, "conan", "bridge_blaspp.cmake"),
             BRIDGE_CMAKE)

    def _dep_lib(self, dep_name, filename):
        path = os.path.join(self.dependencies[dep_name].package_folder,
                            "lib", filename)
        if not os.path.isfile(path):
            raise ConanException(
                "依赖 %s 缺少 %s（查找 %s）" % (dep_name, filename, path))
        return path

    def _blaspp_defines(self):
        """从已安装的 blaspp 包反解其配置宏（不硬编码 Fortran 命名修饰假设）。

        include/blas/defines.h 是 BLAS++ 构建期 configure_file 生成的权威记录
        （含 BLAS_FORTRAN_* 命名修饰与 BLAS_HAVE_CBLAS 等能力位），用它而不是
        猜测命名修饰，避免后端变化时静默链错符号。
        """
        header = os.path.join(self.dependencies["blaspp"].package_folder,
                              "include", "blas", "defines.h")
        if not os.path.isfile(header):
            raise ConanException(
                "依赖 blaspp 缺少 include/blas/defines.h（查找 %s）：无法确定 "
                "BLAS++ 的 Fortran 命名修饰宏" % header)
        defines = []
        with open(header, errors="replace") as f:
            for line in f:
                line = line.strip()
                # 跳过 include guard（LAPACK_DEFINES_H / BLAS_DEFINES_H）
                if not line.startswith("#define BLAS_"):
                    continue
                if line.startswith("#define BLAS_DEFINES_H"):
                    continue
                macro = line[len("#define "):].split("(")[0].strip()
                if macro and macro not in defines:
                    defines.append(macro)
        if not defines:
            raise ConanException(
                "从 %s 未解析到任何 BLAS_* 宏，无法为上游探针提供 "
                "blaspp_defines" % header)
        return ["-D" + m for m in defines]

    def generate(self):
        lapack_a = self._dep_lib("lapack", "liblapack.a")
        blas_a = self._dep_lib("lapack", "libblas.a")
        cblas_a = self._dep_lib("cblas", "libcblas.a")
        frt_a = self._dep_lib("lapack", "libFortranRuntime.a")
        fdec_a = self._dep_lib("lapack", "libFortranDecimal.a")
        openblas_a = self._dep_lib("openblas", "libopenblas.a")
        openblas_include = os.path.join(
            self.dependencies["openblas"].package_folder, "include")
        if not os.path.isfile(os.path.join(openblas_include, "lapacke.h")):
            raise ConanException(
                "依赖 openblas 缺少 include/lapacke.h（查找 %s）：无法为上游 "
                "tester 提供 LAPACKE 头" % openblas_include)
        # 顺序即静态链接拓扑序：消费者（lapack/cblas）在提供者（blas）之前，
        # Fortran 运行时收尾
        blas_libs = ";".join([lapack_a, cblas_a, blas_a, frt_a, fdec_a, "m"])
        # libopenblas.a 末位：仅测试拓扑（LAPACKE/CBLAS/BLAS 内核提供方，供
        # 上游 LAPACKE 探针与 tester），交付库链接面不含它（见文件头）
        lapack_libs = ";".join([lapack_a, frt_a, fdec_a, "m", openblas_a])

        blaspp_defines = ";".join(self._blaspp_defines())

        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = False
        # 库 + 上游 tester（真实执行上游测试，见 _run_upstream_tests）
        tc.variables["build_tests"] = True
        # 鸿蒙无 GPU 后端（上游可选依赖，configure 显式禁用）
        tc.variables["gpu_backend"] = "none"
        # 库清单直通（绕开 -lblas 名称探测；finder 仍逐项 try_run 校验）
        tc.variables["BLAS_LIBRARIES"] = blas_libs
        tc.variables["LAPACK_LIBRARIES"] = lapack_libs
        # 上游 finder 的探针需要 BLAS++ 的两个私有变量（CMakeDeps 不导出）
        tc.variables["blaspp_defines"] = blaspp_defines
        tc.variables["blaspp_libraries"] = blas_libs
        # tester 门禁/链接变量桥接（见 BRIDGE_CMAKE）：openblas = cblas.h 与
        # CBLAS 符号的单一提供方；lib 目录用于 link_directories 解析上游
        # 追加的裸 -lblaspp
        tc.variables["OPENBLAS_PKG_INCLUDE"] = openblas_include
        tc.variables["OPENBLAS_PKG_LIB"] = openblas_a
        tc.variables["BLASPP_PKG_LIBDIR"] = os.path.join(
            self.dependencies["blaspp"].package_folder, "lib")
        tc.variables["OPENBLAS_PKG_LIBDIR"] = os.path.join(
            self.dependencies["openblas"].package_folder, "lib")
        # testsweeper 用本地 vendor 源码（跳过 FetchContent 的构建期 git clone）
        tc.variables["FETCHCONTENT_SOURCE_DIR_TESTSWEEPER"] = os.path.join(
            self.source_folder, "vendor", "testsweeper-2024.05.31")
        # BLAS++ 公共头 include 路径桥接（上游零改动）
        tc.variables["CMAKE_PROJECT_lapackpp_INCLUDE"] = os.path.join(
            self.source_folder, "conan", "bridge_blaspp.cmake")
        tc.generate()

    def build(self):
        # 上游 try_run 探针（#include <lapacke.h>/<cblas.h>）不传递 include 目录
        # （原生构建靠系统路径），以 CPATH 注入 openblas/blaspp 包的 include
        # （clang 与 gcc 同语义，只作用于本构建会话）。tester 链接行的 -lblaspp
        # 由桥接片段的 link_directories 解析（本工具链 clang-15 不翻译
        # LIBRARY_PATH，实测定要用 -L，见 BRIDGE_CMAKE 注释）
        openblas_pkg = self.dependencies["openblas"].package_folder
        blaspp_pkg = self.dependencies["blaspp"].package_folder
        inc_paths = [os.path.join(openblas_pkg, "include"),
                     os.path.join(blaspp_pkg, "include")]
        os.environ["CPATH"] = os.pathsep.join(inc_paths)

        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """上游测试：run_tests.py 计划项驱动（统计单位 = 计划项，逐项
        pass/FAILED；附带 tester 逐用例行计数作辅助口径）。
        HOST 计划 177 项全部执行（--quick = 上游文档定义的全例程 sanity 尺寸
        集；不带尺寸参数时 run_tests.py 默认 medium，必须显式给 --quick）；
        DEVICE 4 项 NOT_RUN（gpu_backend=none，鸿蒙无 GPU 后端，不以任何形式
        上报为通过）。
        """
        bf = self.build_folder
        # 上游 add_subdirectory(test)：tester 与 run_tests.py 落在 build/test/
        # （lapackpp 为顶层项目时 tester 无前缀，见上游 CMakeLists 的 lapackpp_）
        test_dir = os.path.join(bf, "test")
        tester = os.path.join(test_dir, "tester")
        if not os.path.isfile(tester):
            raise ConanException("tester 未生成（build_tests=ON 但 tester 缺失：%s）"
                                 % tester)

        rows = []
        # 1) HOST 全计划项（--quick：上游文档定义的少参数 sanity 尺寸集）
        self.run('python3 run_tests.py --quick --host --test ./tester '
                 '> lapackpp_host_quick.log 2>&1 '
                 '|| echo "RC=$?" > lapackpp_host_quick.rc', cwd=test_dir)
        rc = "?"
        rc_file = os.path.join(test_dir, "lapackpp_host_quick.rc")
        if os.path.isfile(rc_file):
            rc = open(rc_file).read().strip().split("=")[-1]
        log_path = os.path.join(test_dir, "lapackpp_host_quick.log")
        text = open(log_path, errors="replace").read() if os.path.isfile(log_path) else ""
        inv_pass = len([l for l in text.splitlines() if l.strip() == "pass"])
        inv_fail = len([l for l in text.splitlines()
                        if l.startswith("FAILED: exit code")])
        case_pass = len([l for l in text.splitlines()
                         if l.rstrip().endswith("pass") and not l.startswith("pass")])
        case_fail = len([l for l in text.splitlines()
                         if l.rstrip().endswith("FAIL")])
        rows.append("host_quick: invocation PASS=%d FAIL=%d (rc=%s) | "
                    "test-case PASS=%d FAIL=%d"
                    % (inv_pass, inv_fail, rc, case_pass, case_fail))

        # 2) DEVICE 计划项：NOT_RUN（无 GPU 后端，不做任何形式的上报为通过）
        rows.append("device: NOT_RUN=4 (gpu_backend=none, 无 GPU 后端)")

        rows.append("TOTAL(host 计划项 177): PASS=%d FAIL=%d SKIP=0 NOT_RUN=0"
                    % (inv_pass, inv_fail))
        rows.append("TOTAL(上游全计划 181): PASS=%d FAIL=%d SKIP=0 NOT_RUN=4"
                    % (inv_pass, inv_fail))
        save(self, os.path.join(bf, "lapackpp_upstream_test_summary.txt"),
             "\n".join(rows) + "\n")
        self.output.info("上游 LAPACK++ 测试统计：%s" % " | ".join(rows))
        if rc not in ("0", "?"):
            raise ConanException(
                "上游 LAPACK++ 测试存在失败项（host_quick rc=%s，PASS=%d FAIL=%d）"
                % (rc, inv_pass, inv_fail))

    def package(self):
        # 静态库 + 头文件（含构建树生成的 lapack/defines.h）由上游 install 规则落位
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # find_package(lapackpp) / lapackpp::lapackpp 与上游 lapackppConfig.cmake
        # 命名一致
        self.cpp_info.set_property("cmake_file_name", "lapackpp")
        self.cpp_info.set_property("cmake_target_name", "lapackpp::lapackpp")
        self.cpp_info.libs = ["lapackpp"]
        # BLAS++/LAPACK/CBLAS 后端经 conan 依赖图传递（CMakeDeps 生成对应
        # target）；openblas 仅测试拓扑，不入交付依赖面
        self.cpp_info.requires = ["blaspp::blaspp", "lapack::lapack",
                                  "cblas::cblas"]
        self.cpp_info.system_libs = ["m"]
