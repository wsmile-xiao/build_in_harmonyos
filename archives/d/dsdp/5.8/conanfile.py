#!/usr/bin/env python3
"""Conan recipe — dsdp 5.8 (手写 Makefile, HarmonyOS PC / os=OHOS arch=armv8)

DSDP：半定规划（SDP）内点法求解器，cvxopt 的 dsdp 模块用它。

上游是 2005 年前后的老项目，构建系统很旧且不完整：
  · make.include 里 CC=gcc、ARCH="ar cr"、RANLIB=ranlib 全是**裸名**，且 SH_LD 被注释掉
  · 只有 `dsdplibrary` 产静态库 lib/libdsdp.a；`oshared` 目标依赖未定义的 SH_LD，
    且其写法是 `-Wl,-soname,${DSDPLIBSO}`——soname 会被烤成**全路径**，
    下游 DT_NEEDED 随之烤死绝对路径（本仓 expat/poppler 都栽过这个）
  · 无可用的 install 目标（`install:` 实为 make example/test/dmatlab）

故本配方：make 只用来产静态库，共享库与安装步骤全部自己做。

依赖：openblas（提供 BLAS + LAPACK）
"""
import os
import glob
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches
from conan.tools.layout import basic_layout
from conan.errors import ConanInvalidConfiguration


class DsdpConan(ConanFile):
    name = "dsdp"
    version = "5.8"
    package_type = "shared-library"
    description = "Semidefinite programming solver (dual-scaling interior point method)"
    license = "DSDP"      # 类 BSD 的自有许可，见源码 dsdp-license
    homepage = "https://www.mcs.anl.gov/hs/software/DSDP/"
    settings = "os", "arch", "compiler", "build_type"

    _SOVERSION = "5"
    _SOFULL = "5.8"

    def validate(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("本 recipe 仅支持 os=OHOS arch=armv8（设备原生）")

    def requirements(self):
        self.requires("openblas/0.3.34")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    _HNP_BIN = "/data/service/hnp/bin"

    def _tool(self, name):
        import shutil
        cand = os.path.join(self._HNP_BIN, name)
        if os.path.isfile(cand) or os.path.islink(cand):
            return cand
        return shutil.which(name) or ""

    def _openblas_lib(self):
        libdir = os.path.join(self.dependencies["openblas"].package_folder, "lib")
        hits = sorted(glob.glob(os.path.join(libdir, "libopenblas_*.so")))
        if hits:
            return hits[0]
        return os.path.join(libdir, "libopenblas.so")

    def build(self):
        apply_conandata_patches(self)
        for _v in ("CFLAGS", "CXXFLAGS", "CPPFLAGS", "LDFLAGS", "LIBS",
                   "PKG_CONFIG_PATH", "CMAKE_PREFIX_PATH", "LD_LIBRARY_PATH"):
            os.environ.pop(_v, None)
        _tmp = os.path.join(self.build_folder, "_tmp")
        os.makedirs(_tmp, exist_ok=True)
        os.environ["TMPDIR"] = _tmp

        sf = self.source_folder
        cc = self._tool("clang") or "/data/service/hnp/bin/clang"
        ar = self._tool("llvm-ar")
        ranlib = self._tool("llvm-ranlib")

        # ① 静态库：make 变量全部命令行覆盖成**全路径**工具
        #    （make.include 里是裸名 gcc/ar/ranlib，最小 PATH 下必然找不到，
        #     且 OHOS 无 gcc；见 SKILL「自定义 build 里调工具：别假设在 PATH」）
        self.run('make dsdplibrary DSDPROOT="{sf}" CC="{cc}" ARCH="{ar} cr" '
                 'RANLIB="{rl}" OPTFLAGS="-O2 -fPIC" DSDPTIMER=DSDP_TIME'
                 .format(sf=sf, cc=cc, ar=ar, rl=ranlib), cwd=sf)

        # ② 共享库自己链：从静态库整体导出，并给**纯 soname**（不能用上游 oshared，
        #    它会把 soname 写成全路径）。链上 openblas 以解析 BLAS/LAPACK 符号。
        blas = self._openblas_lib()
        libdir = os.path.join(sf, "lib")
        so = os.path.join(libdir, "libdsdp.so.%s" % self._SOFULL)
        self.run('"{cc}" -shared -o "{so}" '
                 '-Wl,--whole-archive "{a}" -Wl,--no-whole-archive '
                 '-Wl,-soname,libdsdp.so.{sov} "{blas}" -lm'
                 .format(cc=cc, so=so, a=os.path.join(libdir, "libdsdp.a"),
                         sov=self._SOVERSION, blas=blas), cwd=sf)

    def package(self):
        sf = self.source_folder
        pkg = self.package_folder
        copy(self, "*.h", src=os.path.join(sf, "include"),
             dst=os.path.join(pkg, "include"), keep_path=False)
        copy(self, "libdsdp.so.*", src=os.path.join(sf, "lib"),
             dst=os.path.join(pkg, "lib"), keep_path=False)
        # 版本软链：libdsdp.so -> .so.5 -> .so.5.8
        libdir = os.path.join(pkg, "lib")
        real = "libdsdp.so.%s" % self._SOFULL
        for link in ("libdsdp.so.%s" % self._SOVERSION, "libdsdp.so"):
            p = os.path.join(libdir, link)
            if os.path.lexists(p):
                os.remove(p)
            os.symlink(real if link.endswith(self._SOVERSION) else
                       "libdsdp.so.%s" % self._SOVERSION, p)
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # 鸿蒙 PC XPM 要求 dlopen 的 .so 有代码签名；此处是自己 clang 直链后再复制进包，
        # 复制会破坏链接器自签，故统一重签。
        targets = [f for f in glob.glob(os.path.join(self.package_folder, "lib", "*.so*"))
                   if not os.path.islink(f) and self._is_elf(f)]
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for f in targets:
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        self.cpp_info.libs = ["dsdp"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
