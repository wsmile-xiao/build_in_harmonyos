#!/usr/bin/env python3
"""Conan recipe — blaspp 2024.10.26 (CMake, HarmonyOS PC / os=OHOS arch=armv8)

BLAS++（SLATE 族中间层）：对 BLAS/LAPACK 的现代 C++ 封装（模板 API + batch
API）。是 lapackpp 2024.10.26 的前置硬依赖（lapackpp CMakeLists 对
find_package(blaspp) 缺失即 FATAL_ERROR，公开头 lapack/util.hh 直接 using
blas::Layout/Op/Uplo/Diag/Side，无法用其他库顶替）。

依赖与后端（W0 结论）：
  - requires lapack/3.12.1（ohpcd 已发布；内含参考 LAPACK + 参考 BLAS +
    flang Fortran 运行时 libFortranRuntime.a/libFortranDecimal.a）
  - requires cblas/3.12.1（ohpcd 已发布；上游 tester 需要 cblas.h + cblas
    符号，仅测试消费者使用）
  - BLAS/LAPACK 后端由上游 cmake/BLASFinder.cmake 探测：本配方走它内置的
    第一候选「BLAS_LIBRARIES 直通」（用户显式给定库清单），逐项 try_compile
    探针确定 Fortran 名字修饰与整型宽度；不使用 use_cmake_find_blas（CMake
    内置 FindBLAS 无法感知 flang Fortran 运行时依赖）。
  - GPU 后端（cuda/hip/sycl）以 gpu_backend=none 显式禁用（鸿蒙无 GPU 后端，
    上游可选依赖，不算止损）；OpenMP 以 use_openmp=OFF 禁用。
  - Fortran 源码编译为零：本包纯 C++，Fortran 只出现在链接期（lapack 包
    随包的 libFortranRuntime.a），无需 flang tool_requires。

上游测试：test/ 生成单一 tester 可执行，由 test/run_tests.py 按计划项驱动
（每项 = 例程 × 参数集）。tester 需要 testsweeper 库，上游 CMake 用
FetchContent 从 GitHub 实时 git clone（构建期网络依赖，CI/设备不可复现）。
本配方将该 tag（v2024.05.31，与上游 CMakeLists 钉死版本一致）以源码形态
随配方导出（vendor/），经 FetchContent 官方变量
FETCHCONTENT_SOURCE_DIR_TESTSWEEPER 指向本地目录，上游 CMakeLists 零改动。

静态链接顺序（GNU 单遍语义下也安全）：
  BLAS_LIBRARIES = [liblapack.a, libcblas.a, libblas.a, libFortranRuntime.a,
                    libFortranDecimal.a, m]
  LAPACK_LIBRARIES = [liblapack.a, libFortranRuntime.a, libFortranDecimal.a, m]
  lapack.a（BLAS 符号的消费者）先于 libblas.a（提供者）；cblas 同理；
  Fortran 运行时最后。链接探测与 tester 链接均满足「用户在提供者之前」。
"""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)


class BlasppConan(ConanFile):
    name = "blaspp"
    version = "2024.10.26"
    description = "BLAS++ - a C++ API for BLAS (SLATE foundation layer)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/icl-utk-edu/blaspp"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)
        # vendor/testsweeper-2024.05.31：上游 tester 的 FetchContent 依赖的
        # 本地源码副本（tag 一致，BSD-3-Clause），见文件头说明。
        copy(self, "*",
             src=os.path.join(self.recipe_folder, "vendor", "testsweeper-2024.05.31"),
             dst=os.path.join(self.export_sources_folder,
                              "vendor", "testsweeper-2024.05.31"))

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            del self.options.fPIC

    def validate(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("本 recipe 仅支持 os=OHOS arch=armv8（设备原生）")

    def requirements(self):
        # ohpcd 已发布（conan list -r=ohpcd 实核，2026-09-22）
        self.requires("lapack/3.12.1")
        self.requires("cblas/3.12.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _dep_lib(self, dep_name, filename):
        folder = self.dependencies[dep_name].package_folder
        path = os.path.join(folder, "lib", filename)
        if not os.path.isfile(path):
            raise ConanException(
                "依赖 %s 缺少 %s（查找 %s）" % (dep_name, filename, path))
        return path

    def generate(self):
        lapack_a = self._dep_lib("lapack", "liblapack.a")
        blas_a = self._dep_lib("lapack", "libblas.a")
        cblas_a = self._dep_lib("cblas", "libcblas.a")
        frt_a = self._dep_lib("lapack", "libFortranRuntime.a")
        fdec_a = self._dep_lib("lapack", "libFortranDecimal.a")
        # 顺序即静态链接拓扑序：消费者（lapack/cblas）在提供者（blas）之前，
        # Fortran 运行时收尾（见文件头「静态链接顺序」）。
        blas_libs = ";".join([lapack_a, cblas_a, blas_a, frt_a, fdec_a, "m"])
        lapack_libs = ";".join([lapack_a, frt_a, fdec_a, "m"])

        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = False
        # 库 + 上游 tester（build_tests=ON 时构建 tester，供 build() 跑上游测试）
        tc.variables["build_tests"] = True
        # 可选后端全部显式关闭：鸿蒙无 GPU；OpenMP 关闭避免引入 libomp 依赖面
        tc.variables["gpu_backend"] = "none"
        tc.variables["use_openmp"] = False
        # 上游 BLASFinder/LAPACKFinder 的第一候选：显式库清单直通
        tc.variables["BLAS_LIBRARIES"] = blas_libs
        tc.variables["LAPACK_LIBRARIES"] = lapack_libs
        # testsweeper 用本地 vendor 源码（跳过 FetchContent 的构建期 git clone）
        tc.variables["FETCHCONTENT_SOURCE_DIR_TESTSWEEPER"] = os.path.join(
            self.source_folder, "vendor", "testsweeper-2024.05.31")
        tc.generate()

    def build(self):
        # cblas.h / -lcblas 的发现：上游 CBLASConfig 探针用 INCLUDE_DIRECTORIES
        # 空 + try_compile("-lcblas")，头与库都依赖编译器搜索路径环境变量
        # （CPATH/LIBRARY_PATH，clang 与 gcc 同语义）。只作用于本构建会话。
        cblas_pkg = self.dependencies["cblas"].package_folder
        lapack_pkg = self.dependencies["lapack"].package_folder
        inc_paths = [os.path.join(cblas_pkg, "include"),
                     os.path.join(lapack_pkg, "include")]
        lib_paths = [os.path.join(cblas_pkg, "lib"),
                     os.path.join(lapack_pkg, "lib")]
        os.environ["CPATH"] = os.pathsep.join(inc_paths)
        os.environ["LIBRARY_PATH"] = os.pathsep.join(lib_paths)

        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """上游测试：run_tests.py 计划项驱动（统计单位 = 计划项，逐项 pass/FAILED；
        附带 tester 逐用例行计数作辅助口径）。HOST 计划 56 项全部执行
        （--quick 尺寸集 = 上游 run_tests.py 文档定义的全例程 sanity 跑法）；
        DEVICE 34 项 NOT_RUN（gpu_backend=none，鸿蒙无 GPU 后端）。
        medium 全尺寸不做：实测量化依据见 notes.md「上游测试」节
        （batch 类计划项 medium 单项 >75 分钟未完成，全量预计数小时，
        超出 CI conan create 3600s 超时预算）。
        """
        bf = self.build_folder
        # 上游 add_subdirectory(test)：tester 与 run_tests.py 落在 build/test/
        test_dir = os.path.join(bf, "test")
        tester = os.path.join(test_dir, "tester")
        if not os.path.isfile(tester):
            raise ConanException("tester 未生成（build_tests=ON 但 tester 缺失：%s）"
                                 % tester)

        rows = []
        # 1) HOST 全计划项（--quick：上游文档定义的少参数 sanity 尺寸集；
        #    不带尺寸参数时 run_tests.py 默认 medium，必须显式给 --quick）
        self.run('python3 run_tests.py --quick --host > blaspp_host_quick.log 2>&1 '
                 '|| echo "RC=$?" > blaspp_host_quick.rc', cwd=test_dir)
        rc = "?"
        rc_file = os.path.join(test_dir, "blaspp_host_quick.rc")
        if os.path.isfile(rc_file):
            rc = open(rc_file).read().strip().split("=")[-1]
        log_path = os.path.join(test_dir, "blaspp_host_quick.log")
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
        rows.append("device: NOT_RUN=34 (gpu_backend=none, 无 GPU 后端)")

        rows.append("TOTAL(host 计划项 56): PASS=%d FAIL=%d SKIP=0 NOT_RUN=0"
                    % (inv_pass, inv_fail))
        rows.append("TOTAL(上游全计划 90): PASS=%d FAIL=%d SKIP=0 NOT_RUN=34"
                    % (inv_pass, inv_fail))
        save(self, os.path.join(bf, "blaspp_upstream_test_summary.txt"),
             "\n".join(rows) + "\n")
        self.output.info("上游 BLAS++ 测试统计：%s" % " | ".join(rows))
        if rc not in ("0", "?"):
            raise ConanException(
                "上游 BLAS++ 测试存在失败项（host_quick rc=%s，PASS=%d FAIL=%d）"
                % (rc, inv_pass, inv_fail))

    def package(self):
        # 静态库 + 头文件（含构建树生成的 defines.h）由上游 install 规则落位
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # find_package(blaspp) / blaspp::blaspp 与上游 blasppConfig.cmake 命名一致，
        # 下游 lapackpp 即按此名消费
        self.cpp_info.set_property("cmake_file_name", "blaspp")
        self.cpp_info.set_property("cmake_target_name", "blaspp::blaspp")
        self.cpp_info.libs = ["blaspp"]
        # BLAS/LAPACK 后端经 conan 依赖图传递（CMakeDeps 生成对应 target）；
        # cblas::cblas 传递 openblas 作为末端 BLAS 符号提供者
        self.cpp_info.requires = ["lapack::lapack", "cblas::cblas"]
        self.cpp_info.system_libs = ["m"]
