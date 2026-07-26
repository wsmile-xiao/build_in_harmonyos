#!/usr/bin/env python3
"""Conan recipe — openblas 0.3.34 (Makefile, HarmonyOS PC / os=OHOS arch=armv8)

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
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.errors import ConanInvalidConfiguration


class OpenblasConan(ConanFile):
    name = "openblas"
    version = "0.3.34"
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

    def build(self):
        apply_conandata_patches(self)
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

        target = str(self.options.blas_target)
        cmd = (
            'make -j%s TARGET=%s BINARY=64 HOSTCC="%s" CC="%s" FC="%s" '
            'F_COMPILER=FLANGNEW NOFORTRAN=0 AR="%s" RANLIB="%s" NO_SHARED=0 '
            'FEXTRALIB="%s %s -lm" shared'
            % (os.cpu_count() or 8, target, cc, cc, fc, ar, ranlib, rt, dec)
        )
        self.run(cmd, cwd=self.source_folder)

    def package(self):
        sf = self.source_folder
        copy(self, "libopenblas*.so*", src=sf, dst=os.path.join(self.package_folder, "lib"))
        copy(self, "libopenblas*.a", src=sf, dst=os.path.join(self.package_folder, "lib"))
        copy(self, "cblas.h", src=sf, dst=os.path.join(self.package_folder, "include"))
        for h in ("lapack.h", "lapacke.h", "lapacke_config.h", "lapacke_mangling.h",
                  "lapacke_utils.h", "f77blas.h", "openblas_config.h"):
            copy(self, h, src=sf, dst=os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "lapacke*.h", src=os.path.join(sf, "lapack-netlib", "LAPACKE", "include"),
             dst=os.path.join(self.package_folder, "include"), keep_path=False)
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
