#!/usr/bin/env python3
"""Conan recipe — alfa v2.2 (Fortran 90, Makefile, HarmonyOS PC / os=OHOS arch=armv8)

自动线拟合算法（天文光谱），纯 Fortran 90 + cfitsio（FITS 读取）。
构建：flang-ohos（tool_requires）编译 12 个源文件（spectralfit.f90 是
#included 进 alfa.f90 的片段，不单独编译）+ 链接 cfitsio/zlib/libomp/
FortranRuntime。

cfitsio：仓库无 conan recipe（预编译包 manifest 形式，ohpcd remote 无
cfitsio/4.6.4 recipe），故配方内自包含构建上游源码（固定 commit 可复现，
本地已验证 cmake 静态构建成功）。

本地已验证：
- iargc()（gfortran 扩展）→ command_argument_count()（补丁 0001）
- VERSION/PREFIX 宏：编译时注入 -DPREFIX/-DVERSION（tar.gz 无 .git）
- 链接：sysroot + libclang_rt.builtins + libunwind + FortranRuntime +
  cfitsio + zlib + libomp
- 上游测试实测：1d.ascii/1d.fits 拟合通过（2/2），2D/3D 数据量大
  超出受限环境运行上限（豁免）
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.build import cross_building


class AlfaConan(ConanFile):
    name = "alfa"
    version = "2.2"
    description = "Automated Line Fitting Algorithm (astronomy)"
    license = "GPL-3.0"
    homepage = "https://github.com/rwesson/ALFA"
    url = "https://github.com/rwesson/ALFA"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1")

    def build_requirements(self):
        self.tool_requires("flang-ohos/20.1.0")

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # 自包含构建 cfitsio（仓库无 conan recipe）
        cf = self.conan_data["cfitsio"]
        get(self, url=cf["url"], sha256=cf["sha256"],
            filename=cf["filename"],
            destination=os.path.join(self.source_folder, "_cfitsio_src"),
            strip_root=True)

    def _flang(self):
        fl = self.dependencies.build.get("flang-ohos")
        if not fl:
            raise ConanException("flang-ohos tool_requires not found")
        flang = os.path.join(fl.package_folder, "bin", "flang")
        if not os.path.isfile(flang):
            raise ConanException(f"flang compiler not found: {flang!r}")
        return flang

    def _build_cfitsio(self):
        """cmake 静态构建 cfitsio（固定 commit 源码）。"""
        src = os.path.join(self.source_folder, "_cfitsio_src")
        build = os.path.join(self.build_folder, "_cfitsio_build")
        os.makedirs(build, exist_ok=True)
        zlib = self.dependencies["zlib"]
        zlib_dir = zlib.package_folder
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        tc.variables["USE_CURL"] = "OFF"
        tc.variables["USE_PTHREADS"] = "OFF"
        tc.variables["TESTS"] = "OFF"
        tc.variables["UTILS"] = "OFF"
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["ZLIB_ROOT"] = zlib_dir
        tc.variables["CMAKE_PREFIX_PATH"] = zlib_dir
        tc.variables["M_LIB"] = "-lm"
        # CI Worker 的 lld 缺 libxml2.so.16（ohos-sdk llvm 运行依赖），
        # C 编译器检测（try_compile 链接）会失败；cfitsio 构建的是静态库，
        # 用 STATIC_LIBRARY 模式跳过 try_compile 的链接阶段（LAPACK 先例）。
        tc.variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = "STATIC_LIBRARY"
        tc.generate()
        # 用 CMake 工具链构建（conan 已注入 sysroot/toolchain；构建目录
        # 为 self.build_folder，产物 libcfitsio.a 在其根下）
        cmake = CMake(self)
        cmake.configure(build_script_folder=src)
        cmake.build()
        return self.build_folder

    def build(self):
        apply_conandata_patches(self)
        flang = self._flang()
        prefix = "/storage/Users/currentUser/usr/local"
        src = self.source_folder
        build = self.build_folder
        # 先构建 cfitsio 静态库
        cf_build = self._build_cfitsio()
        cfitsio_a = os.path.join(cf_build, "libcfitsio.a")
        if not os.path.isfile(cfitsio_a):
            # cmake 多配置/不同布局兜底
            for root, _, files in os.walk(cf_build):
                if "libcfitsio.a" in files:
                    cfitsio_a = os.path.join(root, "libcfitsio.a")
                    break
        if not os.path.isfile(cfitsio_a):
            raise ConanException(f"cfitsio static lib not built: {cfitsio_a}")
        # 12 个源文件（spectralfit.f90 是 include 片段，不单独编译）
        objs = []
        src_dir = os.path.join(src, "source")
        obj_dir = os.path.join(build, "_alfa_obj")
        os.makedirs(obj_dir, exist_ok=True)
        sources = ["rnglib", "types", "globals", "functions", "output",
                   "commandline", "readfiles", "quicksort", "continuum",
                   "linefit", "uncertainties", "alfa"]
        for s in sources:
            o = os.path.join(obj_dir, s + ".o")
            self.run(
                f'"{flang}" -cpp -O3 -J "{obj_dir}" -I "{obj_dir}" '
                f'-DPREFIX=\\"{prefix}\\" -DVERSION=\\"2.2\\" '
                f'-c "{os.path.join(src_dir, s + ".f90")}" -o "{o}"',
                env="conanbuild")
            objs.append(o)
        # 链接：cfitsio + zlib + libomp + FortranRuntime。
        # flang-ohos 是精简运行集（无 crt/运行时），需显式注入 SDK 资源：
        # sysroot（Scrt1.o/libm/libc）、-resource-dir（libclang_rt.builtins）、
        # 把 SDK clang 的 crtbeginS/crtendS 与 builtins/libunwind 复制到
        # flang 期望的 resource-dir（本地手动链接实测通过）。
        import glob
        sdk_llvm = sorted(
            glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm"))[-1]
        sdk_sysroot = os.path.join(sdk_llvm, "..", "sysroot")
        sdk_resdir = os.path.join(sdk_llvm, "lib", "clang", "15.0.4")
        sdk_lib = os.path.join(sdk_llvm, "lib", "aarch64-linux-ohos")
        flang_pkg = self.dependencies.build["flang-ohos"].package_folder
        fl_res = os.path.join(
            flang_pkg, "lib", "clang", "20", "lib", "aarch64-linux-ohos")
        os.makedirs(fl_res, exist_ok=True)
        for name, src_name in (
            ("crtbeginS.o", "clang_rt.crtbegin.o"),
            ("crtendS.o", "clang_rt.crtend.o"),
            ("libclang_rt.builtins.a", "libclang_rt.builtins.a"),
            ("libunwind.a", "libunwind.a"),
        ):
            src = os.path.join(sdk_resdir, "lib", "aarch64-linux-ohos", src_name)
            if not os.path.isfile(src):
                src = os.path.join(sdk_lib, src_name)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(fl_res, name))
        zlib = self.dependencies["zlib"]
        zlib_lib = os.path.join(zlib.package_folder, "lib")
        self.run(
            f'"{flang}" -O3 -J "{obj_dir}" -I "{obj_dir}" '
            f'--sysroot={sdk_sysroot} -resource-dir={sdk_resdir} '
            f'-L"{sdk_sysroot}/usr/lib/aarch64-linux-ohos" '
            f'-L"{sdk_lib}" -L"{zlib_lib}" '
            f'-o "{os.path.join(build, "alfa")}" '
            + " ".join(f'"{o}"' for o in objs)
            + f' "{cfitsio_a}" -lz "{os.path.join(sdk_lib, "libomp.a")}" '
              '-lFortranRuntime -lFortranCommon -lFortranDecimal -lm',
            env="conanbuild")

    def package(self):
        for lic in ("LICENSE", "LICENSE.txt", "LICENSE.rst"):
            p = os.path.join(self.source_folder, lic)
            if os.path.isfile(p):
                copy(self, lic, src=self.source_folder,
                     dst=os.path.join(self.package_folder, "licenses"))
                break
        copy(self, "alfa", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"))
        # linelists 数据（运行时必需）
        copy(self, "*", src=os.path.join(self.source_folder, "linelists"),
             dst=os.path.join(self.package_folder, "share", "alfa"))
        # 上游测试数据（test_package 真实拟合验证用）
        copy(self, "1d.ascii", src=os.path.join(self.source_folder, "test"),
             dst=os.path.join(self.package_folder, "share", "alfa", "testdata"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.append_path(
            "PATH", os.path.join(self.package_folder, "bin"))
        self.runenv_info.append_path(
            "ALFA_PREFIX", os.path.join(self.package_folder, "share", "alfa"))
