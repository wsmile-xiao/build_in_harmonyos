#!/usr/bin/env python3
"""Conan recipe — PaStiX 6.4.0（CMake，鸿蒙 PC / os=OHOS arch=armv8）

PaStiX 是 Inria/LaBRI 的并行稀疏直接求解器（supernodal）。本包为**静态库**组合面
（BUILD_SHARED_LIBS=OFF，SMP 调度，不含 MPI 通信层）：

  产物（install 面）：
    - libpastix.a / libpastix_kernels.a / libspm.a（C 求解器主体）
    - libpastixf.a / libspmf.a（Fortran 包装，随装，见 package_info 说明）
    - include/pastix.h + include/pastix/*.h + include/spm.h + include/spm/*.h
    - lib/cmake/pastix（export 命名空间 PASTIX::）+ pastix.pc / pastixf.pc
    - share/doc/pastix/examples（上游把示例可执行文件装到此处，非 bin/）

依赖矩阵：
    - requires openblas/0.3.34    CBLAS + LAPACK + LAPACKE 单一提供者
    - requires scotch/7.0.12      SCOTCH 图剖分（int32 构建 → PASTIX_INT64=OFF 与之匹配）
    - requires hwloc/2.14.0       拓扑/亲和性（上游为可选依赖，本包显式启用）
    - tool_requires flang-ohos/20.1.0  Fortran 前端。上游 project() 声明 Fortran 为必需
      语言（即使不开 STARPU/PARSEC，源码树仍含 Fortran 源文件），设备与 NDK 均无
      Fortran 编译器；full_mode 保证 .mod ABI 与构建者一致。

上游查找设施（morse find_* 模块）与注入点：
    FindSCOTCH / FindCBLAS / FindLAPACKE 支持 <PKG>_INCDIR / <PKG>_LIBDIR 显式提示；
    FindHWLOC 仅走 pkg-config（本 recipe 给 PKG_CONFIG_PATH）；
    FindSCOTCH 内部 find_library(z/m/rt)、CMake 内建 FindBLAS 的 find_library 依赖
    CMAKE_PREFIX_PATH（本 recipe 把各依赖包目录全部并入）。

Fortran 工具链（设备实测，见 notes.md）：
    flang 可直接作 CMAKE_Fortran_COMPILER，但必须给全 --target/--sysroot/-resource-dir，
    链接期另加 -L<SDK>/llvm/lib/aarch64-linux-ohos（libunwind.a 仅在该目录），
    否则 ld.lld 报 cannot open Scrt1.o / unable to find library -l:libunwind.a。
    configure 期的 check_fortran_function_exists（BLAS 线程函数探测）与
    check_c_source_runs（SCOTCH int 位宽探测）都会真实运行编译器与产物，故 build()
    全程维护 LD_LIBRARY_PATH = <SDK llvm lib> : <flang 包 lib> : <各依赖 libdir>。
"""
import glob
import os
import re
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    load,
)


class PastixConan(ConanFile):
    name = "pastix"
    version = "6.4.0"
    description = "PaStiX — 并行稀疏直接求解器（supernodal，SMP 静态库组合面）"
    license = "LGPL-3.0-only"
    homepage = "https://gitlab.inria.fr/solverstack/pastix"
    url = "https://gitlab.inria.fr/solverstack/pastix"
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if str(self.settings.os) != "OHOS":
            raise ConanInvalidConfiguration("本 recipe 仅支持 os=OHOS（设备原生）")

    def requirements(self):
        self.requires("openblas/0.3.34")
        self.requires("scotch/7.0.12")
        self.requires("hwloc/2.14.0")
        # 收敛 zlib 版本：scotch 钉 zlib/1.3.1，hwloc/cairo 链钉 zlib/1.3.1.1，
        # 同图的这两个版本无法共存；两版本在 ohpcd 的 OHOS 二进制完全一致
        # （package_id 均为 6b129b06...），override 到较新的 1.3.1.1 不影响链接。
        self.requires("zlib/1.3.1.1", override=True)

    def build_requirements(self):
        # full_mode：Fortran .mod 是编译器私有二进制接口，消费方必须同工具链
        self.tool_requires("flang-ohos/20.1.0", package_id_mode="full_mode")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    # ── Fortran / SDK 工具链 ──────────────────────────────────────────
    def _sdk_native(self):
        """定位唯一一个完整的 OHOS SDK native 根（可用 conf 显式指定）。"""
        configured = self.conf.get("user.pastix:sdk_native", default=None, check_type=str)
        candidates = [configured] if configured else glob.glob(
            "/data/service/hnp/ohos-sdk.org/*/ohos/native")
        valid = []
        for candidate in candidates:
            candidate = os.path.realpath(candidate)
            required = (
                os.path.join(candidate, "sysroot"),
                os.path.join(candidate, "llvm", "bin"),
                os.path.join(candidate, "llvm", "lib"),
                os.path.join(candidate, "llvm", "lib", "aarch64-linux-ohos"),
            )
            clang = os.path.join(candidate, "llvm", "bin", "clang")
            if (all(os.path.isdir(p) for p in required)
                    and os.path.isfile(clang) and os.access(clang, os.X_OK)):
                valid.append(candidate)
        valid = sorted(set(valid))
        if len(valid) != 1:
            raise ConanInvalidConfiguration(
                "需要且仅需要一个完整的 OHOS SDK native 根；请在 "
                "conf 中设置 user.pastix:sdk_native 明确指定")
        return valid[0]

    def _fortran_toolchain(self):
        """返回 (flang 可执行文件, Fortran 编译 flags, 链接 flags, 运行期库目录)。"""
        flang_package = self.dependencies.build["flang-ohos"].package_folder
        flang = os.path.join(flang_package, "bin", "flang")
        flang_lib = os.path.join(flang_package, "lib")
        if not os.path.isfile(flang) or not os.path.isdir(flang_lib):
            raise ConanInvalidConfiguration("flang-ohos 工具包不完整")
        sdk_native = self._sdk_native()
        sdk_clang = os.path.join(sdk_native, "llvm", "bin", "clang")
        runtime_dirs = (os.path.join(sdk_native, "llvm", "lib"), flang_lib)
        # 向 SDK clang 问 resource-dir，避免写死版本号
        probe_env = os.environ.copy()
        probe_env["LD_LIBRARY_PATH"] = os.pathsep.join(runtime_dirs)
        try:
            resource_dir = subprocess.run(
                [sdk_clang, "-print-resource-dir"], check=True, env=probe_env,
                text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.strip()
        except (OSError, subprocess.CalledProcessError) as error:
            raise ConanInvalidConfiguration("无法探测 OHOS SDK clang 的 resource-dir") from error
        resource_dir = os.path.realpath(resource_dir)
        if (not os.path.isdir(resource_dir)
                or os.path.commonpath((sdk_native, resource_dir)) != sdk_native):
            raise ConanInvalidConfiguration("SDK clang 返回了 SDK 之外的 resource-dir")
        compile_flags = [
            "--target=aarch64-unknown-linux-ohos",
            "--sysroot={}".format(os.path.join(sdk_native, "sysroot")),
            "-resource-dir={}".format(resource_dir),
        ]
        # 只在**链接**阶段加 -L：libunwind.a 仅存在于该目录，缺了 ld.lld 直接报
        # `unable to find library -l:libunwind.a`；放进编译 flags 会产生大量 unused 告警。
        link_flags = [
            "-L{}".format(os.path.join(sdk_native, "llvm", "lib", "aarch64-linux-ohos")),
        ]

        def _join(flags):
            return " ".join(flags).replace("\\", "/")

        return (flang.replace("\\", "/"), _join(compile_flags), _join(link_flags),
                runtime_dirs)

    # ── 依赖包目录 ────────────────────────────────────────────────────
    def _dep_folder(self, name):
        try:
            return self.dependencies.host[name].package_folder
        except KeyError:
            return None

    def _pkgconfig_dirs(self):
        """pkg-config 搜索目录（hwloc.pc 是 FindHWLOC 的唯一入口）。

        自生成的 hwloc.pc（见 generate()）放最前，屏蔽依赖包内不可重定位的
        原始 hwloc.pc（prefix=/ 且 Requires.private 指向缺失的 libxml-2.0.pc）。
        """
        dirs = [os.path.join(self.generators_folder, "pkgconfig")]
        for name in ("hwloc", "openblas", "scotch"):
            folder = self._dep_folder(name)
            if not folder:
                continue
            for candidate in ("lib/pkgconfig", "share/pkgconfig", "lib64/pkgconfig"):
                full = os.path.join(folder, candidate)
                if os.path.isdir(full):
                    dirs.append(full)
        return dirs

    def _write_hwloc_pc_shim(self):
        """生成可重定位的 hwloc.pc。

        依赖包内随附的 hwloc.pc 是构建机残留（prefix=/ → -I/include -L/lib），
        且 Require.private 引用路径外的 libxml-2.0.pc，pkg-config 直接解析失败。
        FindHWLOC 只走 pkg-config，这里写入前缀指向实际包目录的替身，并把
        libhwloc.a 的静态闭包（libxml2 → pthread/m/dl）放进 Libs 行，供
        HWLOC_WORKS 探测链接与工程内静态链接使用。
        """
        hwloc = self._dep_folder("hwloc")
        target_dir = os.path.join(self.generators_folder, "pkgconfig")
        os.makedirs(target_dir, exist_ok=True)
        content = (
            "prefix={hwloc}\n"
            "exec_prefix=${{prefix}}\n"
            "libdir=${{prefix}}/lib\n"
            "includedir=${{prefix}}/include\n"
            "\n"
            "Name: hwloc\n"
            "Description: Hardware locality detection and management library\n"
            "Version: 2.14.0\n"
            "Cflags: -I${{includedir}}\n"
            "Libs: -L${{libdir}} -lhwloc -lxml2 -lm -lpthread -ldl\n"
        ).format(hwloc=hwloc)
        with open(os.path.join(target_dir, "hwloc.pc"), "w") as f:
            f.write(content)

    def _prefix_dirs(self):
        """并入 CMAKE_PREFIX_PATH 的依赖包目录（FindSCOTCH 内部 find_library(z/m/rt)、
        CMake 内建 FindBLAS 都靠它兜底）。"""
        prefixes = []
        for name in ("openblas", "scotch", "hwloc", "zlib", "bzip2", "xz"):
            folder = self._dep_folder(name)
            if folder:
                prefixes.append(folder)
        return prefixes

    # ── 配置生成 ──────────────────────────────────────────────────────
    def generate(self):
        # 上游自带 morse Find 模块（FindSCOTCH 内含 SCOTCH_Num 位宽探测、FindHWLOC 走
        # pkg-config、FindCBLAS/LAPACKE 走 *_INCDIR/_LIBDIR），但 Conan 工具链默认
        # CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON，find_package(SCOTCH) 会优先命中 Conan
        # 生成的 config 文件而绕过 Find 模块——SCOTCH_Num_4/SCOTCH_WORKS 缺失导致
        # CMakeLists.txt:451 的 int32 一致性门禁误报。通过官方 conf 关掉
        # PREFER_CONFIG，恢复「模块模式优先」的原生查找次序（下方已为各依赖提供
        # *_INCDIR/_LIBDIR 与 PKG_CONFIG_PATH 提示）。
        self.conf.define("tools.cmake.cmaketoolchain:find_package_prefer_config", False)
        self._write_hwloc_pc_shim()

        flang, fortran_flags, fortran_link_flags, _runtime_dirs = self._fortran_toolchain()
        openblas = self._dep_folder("openblas")
        scotch = self._dep_folder("scotch")
        openblas_include = os.path.join(openblas, "include")
        openblas_lib = os.path.join(openblas, "lib")
        scotch_include = os.path.join(scotch, "include")
        scotch_lib = os.path.join(scotch, "lib")

        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        # Fortran 编译器与 flags：flang 需要 --target/--sysroot/-resource-dir 才可用，
        # 链接需要 -L<SDK>/llvm/lib/aarch64-linux-ohos 才能找到 libunwind.a
        tc.variables["CMAKE_Fortran_COMPILER"] = flang
        tc.variables["CMAKE_Fortran_FLAGS"] = fortran_flags
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = fortran_link_flags
        tc.variables["CMAKE_SHARED_LINKER_FLAGS"] = fortran_link_flags

        # 线性代数与剖分：全部显式给定，防 morse 模块回落到设备侧同名库
        tc.variables["BLAS_INCDIR"] = openblas_include
        tc.variables["BLAS_LIBDIR"] = openblas_lib
        tc.variables["CBLAS_INCDIR"] = openblas_include
        tc.variables["CBLAS_LIBDIR"] = openblas_lib
        tc.variables["LAPACK_INCDIR"] = openblas_include
        tc.variables["LAPACK_LIBDIR"] = openblas_lib
        tc.variables["LAPACKE_INCDIR"] = openblas_include
        tc.variables["LAPACKE_LIBDIR"] = openblas_lib
        tc.variables["SCOTCH_INCDIR"] = scotch_include
        tc.variables["SCOTCH_LIBDIR"] = scotch_lib

        # 构建选项：SMP-only 静态组合
        tc.variables["BUILD_SHARED_LIBS"] = False
        tc.variables["PASTIX_WITH_MPI"] = False
        tc.variables["PASTIX_WITH_FORTRAN"] = True
        tc.variables["PASTIX_INT64"] = False
        tc.variables["PASTIX_ORDERING_SCOTCH"] = True
        tc.variables["PASTIX_ORDERING_METIS"] = False
        tc.variables["PASTIX_WITH_STARPU"] = False
        tc.variables["PASTIX_WITH_PARSEC"] = False
        tc.variables["PASTIX_WITH_CUDA"] = False
        tc.variables["PASTIX_WITH_EZTRACE"] = False
        tc.variables["PASTIX_WITH_PAPI"] = False
        tc.variables["PASTIX_WITH_EXTERNAL_SPM"] = False
        tc.variables["PASTIX_GENERATE_MODEL"] = False

        tc.cache_variables["CMAKE_PREFIX_PATH"] = ";".join(self._prefix_dirs())
        tc.generate()
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

    def _apply_runtime_env(self):
        """构建/测试期加载路径，返回原值以便复原。

        flang 自身要 libLLVM/libMLIR/libclang-cpp（flang-ohos 包 lib/ 与 SDK llvm/lib）；
        configure 期 check_* 产物与 ctest 的测试可执行文件要 openblas/hwloc 等共享库。
        """
        dirs = []
        _flang, _flags, _link_flags, runtime_dirs = self._fortran_toolchain()
        dirs.extend(runtime_dirs)
        for _ref, dep in self.dependencies.items():
            folder = dep.package_folder
            if not folder:
                continue
            for libdir in dep.cpp_info.libdirs:
                dirs.append(libdir if os.path.isabs(libdir) else os.path.join(folder, libdir))
        previous = os.environ.get("LD_LIBRARY_PATH")
        if previous:
            dirs.append(previous)
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(dict.fromkeys(dirs))
        previous_pkg = os.environ.get("PKG_CONFIG_PATH")
        pkg_dirs = self._pkgconfig_dirs()
        if previous_pkg:
            pkg_dirs.append(previous_pkg)
        os.environ["PKG_CONFIG_PATH"] = os.pathsep.join(dict.fromkeys(pkg_dirs))
        return previous, previous_pkg

    @staticmethod
    def _restore_env(previous, previous_pkg):
        if previous is None:
            os.environ.pop("LD_LIBRARY_PATH", None)
        else:
            os.environ["LD_LIBRARY_PATH"] = previous
        if previous_pkg is None:
            os.environ.pop("PKG_CONFIG_PATH", None)
        else:
            os.environ["PKG_CONFIG_PATH"] = previous_pkg

    # ── 构建 ──────────────────────────────────────────────────────────
    def build(self):
        previous, previous_pkg = self._apply_runtime_env()
        try:
            cmake = CMake(self)
            cmake.configure()
            self._verify_configure_contract()
            cmake.build(build_tool_args=["-j16"])
            if can_run(self):
                # 真跑上游全部注册用例；单核 BLAS 防 ctest -j 时线程超卖
                # （run(env=...) 口径是 KEY=VALUE 列表，不是 dict）
                self.run(
                    'ctest --test-dir "{}" --output-on-failure -j8'.format(self.build_folder),
                    env=["OPENBLAS_NUM_THREADS=1", "OMP_NUM_THREADS=1"],
                )
        finally:
            self._restore_env(previous, previous_pkg)

    def _cache_value(self, key):
        cache_path = os.path.join(self.build_folder, "CMakeCache.txt")
        contents = load(self, cache_path)
        match = re.search(
            r"^{}:[^=]*=(.*)$".format(re.escape(key)), contents, re.MULTILINE
        )
        return match.group(1).strip() if match else None

    def _verify_configure_contract(self):
        """configure 结果的硬校验：任何一项对不上都硬失败。

        这些检查同时是「依赖身份」证据：BLAS_LIBRARY 必须指向本包 openblas，
        位宽探测必须落在 int32，hwloc 必须启用（本包显式开启的可选依赖）。
        """
        truthy = {"1", "ON", "TRUE", "YES", "Y"}
        def _require_truthy(key):
            value = self._cache_value(key)
            if value is None or value.strip('"').upper() not in truthy:
                raise ConanException(
                    "configure 契约校验失败：{} = {!r}（期望真值）".format(key, value))

        for key in ("CBLAS_WORKS", "LAPACKE_WORKS", "HWLOC_WORKS", "SCOTCH_Num_4"):
            _require_truthy(key)

        # BLAS 身份：CMake 4 的 FindBLAS 写 BLAS_<vendor>_LIBRARY（如
        # BLAS_openblas_LIBRARY），旧接口写 BLAS_LIBRARY；两种命名统一扫描，
        # 要求命中的库文件位于本包 openblas 依赖目录内。
        cache_contents = load(self, os.path.join(self.build_folder, "CMakeCache.txt"))
        openblas_dir = self._dep_folder("openblas")
        blas_hits = [
            m.group(2).strip()
            for m in re.finditer(
                r"^(BLAS[A-Za-z0-9_]*_LIBRAR(?:Y|IES)):[^=]*=(.+)$",
                cache_contents, re.MULTILINE)
            if "libopenblas" in m.group(2)
        ]
        if not blas_hits or not any(h.startswith(openblas_dir) for h in blas_hits):
            raise ConanException(
                "configure 契约校验失败：BLAS 库 = {!r}，未指向本包 openblas".format(
                    blas_hits))

        for key in ("PASTIX_INT64", "PASTIX_WITH_MPI", "PASTIX_ORDERING_METIS"):
            value = self._cache_value(key)
            if value is not None and value.strip('"').upper() in truthy:
                raise ConanException(
                    "configure 契约校验失败：{} 应为关闭，实为 {!r}".format(key, value))

        # 生成后的 config.h = 消费方实际拿到的 ABI/能力面
        config_h = os.path.join(self.build_folder, "include", "pastix", "config.h")
        contents = load(self, config_h)
        expected_defined = (
            "PASTIX_WITH_FORTRAN", "HAVE_HWLOC", "PASTIX_ORDERING_SCOTCH",
            "HAVE_OPENBLAS_SET_NUM_THREADS",
        )
        for macro in expected_defined:
            if not re.search(r"^#define {}\b".format(macro), contents, re.MULTILINE):
                raise ConanException(
                    "config.h 契约校验失败：#define {} 缺失".format(macro))
        expected_undefined = (
            "PASTIX_WITH_MPI", "PASTIX_WITH_CUDA", "PASTIX_INT64",
            "PASTIX_ORDERING_METIS", "PASTIX_WITH_STARPU", "PASTIX_WITH_PARSEC",
        )
        for macro in expected_undefined:
            if re.search(r"^#define {}\b".format(macro), contents, re.MULTILINE):
                raise ConanException(
                    "config.h 契约校验失败：#define {} 不应出现".format(macro))
        for version in (("PASTIX_VERSION_MAJOR", "6"), ("PASTIX_VERSION_MINOR", "4"),
                        ("PASTIX_VERSION_MICRO", "0")):
            if not re.search(r"^#define {}\s+{}\s*$".format(*version), contents, re.MULTILINE):
                raise ConanException(
                    "config.h 契约校验失败：{} 不是 {}".format(*version))

    # ── 打包 ──────────────────────────────────────────────────────────
    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # 产物面自检：缺一则本包无交付价值，宁可硬失败
        libdir = os.path.join(self.package_folder, "lib")
        for artifact in ("libpastix.a", "libpastix_kernels.a", "libspm.a"):
            if not os.path.isfile(os.path.join(libdir, artifact)):
                raise ConanException("install 面缺少 {}".format(artifact))
        if not os.path.isfile(os.path.join(self.package_folder, "include", "pastix.h")):
            raise ConanException("install 面缺少 include/pastix.h")

    def package_info(self):
        # C/C++ 消费面 = 求解器三件套（静态链接顺序：pastix → kernels → spm）
        self.cpp_info.libs = ["pastix", "pastix_kernels", "spm"]
        # libpastixf/libspmf（Fortran 包装）随安装面落盘，但不写入 libs：
        # 其消费方必须自备 Fortran 运行时（flang-ohos 是构建期工具包，平台没有
        # 消费者可依赖的 Fortran 运行时包），自动声明会把 C/C++ 消费者一并拖入
        # 无法解析的链接。C/C++ 消费面由本声明完整覆盖。
        self.cpp_info.requires = [
            "openblas::openblas",
            "scotch::scotch",
            "hwloc::hwloc",
        ]
        # OHOS bionic：pthread/rt/dl 符号并入 libc，只有一个 -lm（同 scotch 先例口径）
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.set_property("cmake_file_name", "pastix")
        self.cpp_info.set_property("cmake_target_name", "PASTIX::pastix")
        self.cpp_info.set_property("pkg_config_name", "pastix")
