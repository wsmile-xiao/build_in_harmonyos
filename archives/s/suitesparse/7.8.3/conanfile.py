#!/usr/bin/env python3
"""Conan recipe — suitesparse 7.8.3 (CMake, HarmonyOS PC / os=OHOS arch=armv8)

SuiteSparse 稀疏矩阵算法套件。本配方**只建 cvxopt 所需的 7 个子库**
（suitesparse_config / amd / camd / ccolamd / colamd / cholmod / umfpack），
不建 GraphBLAS、SPQR、KLU、ParU 等——它们体量大、依赖多，且当前无消费方。

依赖：openblas（提供 BLAS + LAPACK；cholmod / umfpack 需要）
"""
import os
import glob
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches
from conan.tools.cmake import cmake_layout
from conan.errors import ConanInvalidConfiguration


class SuiteSparseConan(ConanFile):
    name = "suitesparse"
    version = "7.8.3"
    package_type = "shared-library"
    description = "A suite of sparse matrix algorithms (AMD/CAMD/CCOLAMD/COLAMD/CHOLMOD/UMFPACK)"
    license = "LGPL-2.1-or-later AND GPL-2.0-or-later"
    homepage = "https://people.engr.tamu.edu/davis/suitesparse.html"
    settings = "os", "arch", "compiler", "build_type"

    # 只建 cvxopt 需要的子集。顺序即依赖序，CMake 会自行处理。
    _PROJECTS = "suitesparse_config;amd;camd;ccolamd;colamd;cholmod;umfpack"

    def validate(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("本 recipe 仅支持 os=OHOS arch=armv8（设备原生）")

    def requirements(self):
        # cholmod / umfpack 需要 BLAS 与 LAPACK，openblas 两者都提供
        self.requires("openblas/0.3.34")

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    # ------------------------------------------------------------------ 工具

    def _ohos_toolchain(self):
        ut = self.conf.get("tools.cmake.cmaketoolchain:user_toolchain", default=[], check_type=list)
        ndk = os.environ.get("OHOS_NDK_HOME", "")
        for _c in list(ut) + ([os.path.join(ndk, "build/cmake/ohos.toolchain.cmake")] if ndk else []):
            if _c and os.path.isfile(_c):
                return _c
        _g = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake"))
        if _g:
            return _g[-1]
        raise ConanInvalidConfiguration(
            "找不到 ohos.toolchain.cmake：设 OHOS_NDK_HOME 或 profile [conf] user_toolchain")

    _HNP_BIN = "/data/service/hnp/bin"

    def _tool(self, name):
        # SDK 的 llvm/bin 只有 llvm-ar、没有 llvm-ranlib，而 ohos.toolchain 会把 CMAKE_RANLIB
        # 指到那个不存在的路径 → 造静态库时报 "Error running link command: no such file or
        # directory"。hnp bin 下的 llvm-ranlib 是指向 llvm-ar 的软链（LLVM 按 argv[0] 改行为）。
        import shutil
        cand = os.path.join(self._HNP_BIN, name)
        if os.path.isfile(cand) or os.path.islink(cand):
            return cand
        return shutil.which(name) or ""

    def _openblas_lib(self):
        """openblas 包里的实名 .so（libopenblas_armv8p-r<ver>.so），优先取实体而非软链。"""
        libdir = os.path.join(self.dependencies["openblas"].package_folder, "lib")
        hits = sorted(glob.glob(os.path.join(libdir, "libopenblas_*.so")))
        if hits:
            return hits[0]
        cand = os.path.join(libdir, "libopenblas.so")
        if os.path.exists(cand):
            return cand
        raise ConanInvalidConfiguration("openblas 包 lib/ 下找不到 libopenblas*.so：%s" % libdir)

    # ------------------------------------------------------------------ 构建

    def build(self):
        apply_conandata_patches(self)
        for _v in ("CFLAGS", "CXXFLAGS", "CPPFLAGS", "LDFLAGS", "LIBS",
                   "PKG_CONFIG_PATH", "CMAKE_PREFIX_PATH", "LD_LIBRARY_PATH"):
            os.environ.pop(_v, None)
        _tmp = os.path.join(self.build_folder, "_tmp")     # HMDFS 默认 TMPDIR 不可写
        os.makedirs(_tmp, exist_ok=True)
        os.environ["TMPDIR"] = _tmp

        blas = self._openblas_lib()
        ob_inc = os.path.join(self.dependencies["openblas"].package_folder, "include")

        # SuiteSparseBLAS.cmake 第 21 行：若环境里定义了 BLA_VENDOR 就直接采纳，
        # 不再逐个 vendor 试（Intel/ARM/OpenBLAS/FLAME…）。设成 OpenBLAS 让解析确定化。
        os.environ["BLA_VENDOR"] = "OpenBLAS"

        bdir = os.path.join(self.build_folder, "build-ohos")
        defs = [
            '-DCMAKE_TOOLCHAIN_FILE="%s"' % self._ohos_toolchain(),
            "-DOHOS_ARCH=arm64-v8a",
            "-DCMAKE_BUILD_TYPE=%s" % self.settings.build_type,
            "-DCMAKE_INSTALL_LIBDIR=lib",       # ohos.toolchain 64 位默认 lib64/，conan 找 lib/
            "-DBUILD_SHARED_LIBS=ON",
            "-DBUILD_STATIC_LIBS=OFF",
            "-DCMAKE_POSITION_INDEPENDENT_CODE=ON",
            '-DSUITESPARSE_ENABLE_PROJECTS="%s"' % self._PROJECTS,
            # OpenMP：设备工具链是 clang，SuiteSparse 找 GNU libgomp 会落空；关掉更干净
            # （PyPI 的 cvxopt wheel 正是因为开着 OpenMP 才 vendored 了 libgomp）。
            "-DSUITESPARSE_USE_OPENMP=OFF",
            # 本套子库无需 Fortran（那是 SPQR/ParU 等才用）
            "-DSUITESPARSE_USE_FORTRAN=OFF",
            "-DSUITESPARSE_USE_CUDA=OFF",
            "-DSUITESPARSE_USE_PYTHON=OFF",
            "-DSUITESPARSE_DEMOS=OFF",
            "-DSUITESPARSE_USE_64BIT_BLAS=OFF",  # 本仓 openblas 是 LP64（dgemm_ 有、dgemm_64_ 无）
            "-DSUITESPARSE_USE_STRICT=ON",       # 上面这些 OFF 当硬约束，别悄悄回退
            # 交叉 toolchain 会 set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY) 覆盖命令行，
            # find_package(BLAS) 搜不到 conan 依赖 → 直接预设结果缓存变量。
            # CMake 的 FindBLAS/FindLAPACK 每个 vendor 分支都由 if(NOT xxx_LIBRARIES) 守着，
            # 预设即全部跳过搜索、直接采用。
            '-DBLAS_LIBRARIES="%s"' % blas,
            '-DLAPACK_LIBRARIES="%s"' % blas,
            '-DCMAKE_INCLUDE_PATH="%s"' % ob_inc,
        ]
        for _var, _name in (("CMAKE_RANLIB", "llvm-ranlib"), ("CMAKE_AR", "llvm-ar")):
            _p = self._tool(_name)
            if _p:
                defs.append('-D%s="%s"' % (_var, _p))

        jobs = self.conf.get("tools.build:jobs", default=os.cpu_count() or 4, check_type=int)
        self.run('cmake -B "%s" -S "%s" %s' % (bdir, self.source_folder, " ".join(defs)))
        self.run('cmake --build "%s" -j %s' % (bdir, jobs))

    def package(self):
        bdir = os.path.join(self.build_folder, "build-ohos")
        self.run('cmake --install "%s" --prefix "%s"' % (bdir, self.package_folder))
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # 鸿蒙 PC XPM 要求 dlopen 的 .so 与被 exec 的可执行文件都有代码签名。
        # cmake/SDK-toolchain 产的自签无效，且 install 是复制、会破坏链接器自签。
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        targets += glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True)
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                p = os.path.join(bindir, name)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for f in targets:
            if os.path.islink(f):     # 只签真实 ELF，跳版本化 .so 的软链
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        # 链接序：上层在前。umfpack → cholmod → {amd,camd,ccolamd,colamd} → suitesparseconfig
        self.cpp_info.libs = ["umfpack", "cholmod", "camd", "ccolamd", "colamd", "amd",
                              "suitesparseconfig"]
        # 头装在 include/suitesparse/，而消费方按 #include <cholmod.h> 写（cvxopt 即如此）
        self.cpp_info.includedirs = ["include/suitesparse", "include"]
        self.cpp_info.set_property("cmake_file_name", "SuiteSparse")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
