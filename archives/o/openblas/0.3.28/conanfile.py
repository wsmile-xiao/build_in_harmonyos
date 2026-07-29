#!/usr/bin/env python3
"""Conan recipe — openblas 0.3.28 (Makefile, HarmonyOS PC / os=OHOS arch=armv8)

**设备原生** recipe：在鸿蒙 PC 真机上 `conan create`，用 tool_requires 的 flang-ohos 提供
Fortran 编译器编 LAPACK。全程设备原生、走设备 CI、package() 里直接 binary-sign-tool 签名。
(用户选定的 B 方案；mac 交叉版见 notes.md「附录」。)

依赖：
  - tool_requires flang-ohos/20.1.0（设备原生编好的 LLVM Flang 工具链，本仓 f/flang-ohos/）
  - C 编译/链接用设备 hnp clang（/data/service/hnp/bin/clang）
"""
import os
import glob
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.errors import ConanInvalidConfiguration


class OpenblasConan(ConanFile):
    name = "openblas"
    version = "0.3.28"
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"blas_target": ["ANY"]}
    default_options = {"blas_target": "ARMV8"}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("本 recipe 仅支持 os=OHOS arch=armv8（设备原生）")

    def build_requirements(self):
        self.tool_requires("flang-ohos/20.1.0")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _prepare_env(self):
        """构建与打包共用的环境准备，并返回 make 变量串。

        build() 与 package() 都要用**同一套** make 变量——Makefile.system 会依据它们推导
        库名（libopenblas_<TARGET><线程后缀>-r<ver>）与安装布局，两阶段给的不一致会导致
        install 找不到 build 出来的产物。故集中在此，不用实例属性传递（那样 export-pkg
        单独跑 package() 时会 AttributeError）。
        """
        flang_pkg = self.dependencies.build["flang-ohos"].package_folder
        fc = os.path.join(flang_pkg, "bin", "flang")
        rt = os.path.join(flang_pkg, "lib", "libFortranRuntime.a")
        dec = os.path.join(flang_pkg, "lib", "libFortranDecimal.a")
        # 设备 hnp 工具链（实测可用；不走 conf 以免 tools.build:compiler_executables 里未解析变量）
        cc = "/data/service/hnp/bin/clang"
        ar = "/data/service/hnp/bin/llvm-ar"
        ranlib = "/data/service/hnp/bin/llvm-ranlib"

        # LD_LIBRARY_PATH：① SDK llvm/lib 给 lld 正确 libxml2.so.16（HiShell 污染会搞坏 lld）
        #                  ② flang 包 lib 给 flang 运行期的 libLLVM/libMLIR/libclang-cpp
        # 直接改 os.environ（self.run 的 env= 参数是 conan env-file 名列表、非 dict）。
        sdk_llvm_lib = ""
        g = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib"))
        if g:
            sdk_llvm_lib = g[-1]
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
            p for p in [sdk_llvm_lib, os.path.join(flang_pkg, "lib")] if p)
        # 清 HiShell 污染的构建 env
        for k in ("CFLAGS", "CXXFLAGS", "CPPFLAGS", "LDFLAGS", "CMAKE_PREFIX_PATH", "PKG_CONFIG_PATH"):
            os.environ.pop(k, None)

        return ('TARGET=%s BINARY=64 HOSTCC="%s" CC="%s" FC="%s" '
                'F_COMPILER=FLANGNEW NOFORTRAN=0 AR="%s" RANLIB="%s" NO_SHARED=0 '
                'FEXTRALIB="%s %s -lm"'
                % (str(self.options.blas_target), cc, cc, fc, ar, ranlib, rt, dec))

    def build(self):
        apply_conandata_patches(self)
        self.run("make -j%s %s shared" % (os.cpu_count() or 8, self._prepare_env()),
                 cwd=self.source_folder)

    def package(self):
        # 【必须走 make install，不能直接 copy 源码树里的头文件】
        # OpenBLAS 有三个头文件是 **install 期才产生/加工** 的：
        #   · openblas_config.h —— Makefile.install 由 config.h + openblas_config_template.h 拼出，
        #                          源码树里根本不存在
        #   · lapack.h          —— 同样 install 期生成
        #   · cblas.h           —— 源码树里的那份 #include "common.h"（OpenBLAS 内部头，不外发）；
        #                          install 会 `sed 's/common/openblas_config/g'`（Makefile.install:88）
        #                          后再装出去
        # 直接 copy 源文件的话，前两个悄悄缺失、第三个则是坏的——消费方一旦
        # `#include <cblas.h>` 就报 `'common.h' file not found`。
        # （本仓 0.3.34 配方即为直接 copy，其已发布包存在此缺陷；因其 test_package 用 dlopen、
        #  从不 include 头文件，故长期未被发现。）
        # make install 顺带还生成 lib/pkgconfig/openblas.pc 与 lib/cmake/openblas/。
        self.run('make %s PREFIX="%s" install' % (self._prepare_env(), self.package_folder),
                 cwd=self.source_folder)
        self._sign_so()

    def _sign_so(self):
        # 设备原生：XPM 要求 dlopen 的 .so 自签。cmake/SDK-toolchain 链接的 .so 自签有效需重签；
        # 此处 clang 直链，稳妥起见统一重签（binary-sign-tool 在设备 hnp bin）。
        sign = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(sign):
            self.output.warning("binary-sign-tool 不存在，跳过签名（消费端需自签）")
            return
        for so in glob.glob(os.path.join(self.package_folder, "lib", "*.so*")):
            if os.path.islink(so):
                continue
            self.run('%s sign -inFile "%s" -outFile "%s" -selfSign 1' % (sign, so, so))

    def package_info(self):
        self.cpp_info.libs = ["openblas"]
        self.cpp_info.set_property("pkg_config_name", "openblas")
        self.cpp_info.system_libs = ["m", "pthread"]
