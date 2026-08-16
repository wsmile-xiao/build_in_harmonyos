#!/usr/bin/env python3
"""Conan recipe — tachyon 0.99.5（手写 Makefile，产命令行光线追踪器）

Tachyon 是并行光线追踪器。上游 `unix/Makefile` 是手写 Makefile（非 autotools），
按"架构目标"分派：`make linux-arm-thr` 这类目标各自把 CFLAGS/LIBS 一套值传给
递归 make。**aarch64 的目标在原始 tarball 里没有**，由 sage/passagemath 的
`Make-arch.patch` 补上 —— 本 recipe 沿用同一份补丁，与上游 wheel 的构建方式一致。

产物只有一个可执行文件 `bin/tachyon`（`all` 目标 = libtachyon.a + libmgf + tachyon，
不含 OptiX/OpenGL 那些 demo）。直接消费方是 `passagemath-tachyon` 的 wheel，
它把 `bin/tachyon` 塞进 wheel 的 `sage_wheels/bin/`。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class TachyonConan(ConanFile):
    name = "tachyon"
    version = "0.99.5"
    description = "Tachyon — 并行/多线程光线追踪器（命令行渲染器）"
    license = "BSD-3-Clause"
    homepage = "https://jedi.ks.uiuc.edu/~johns/raytracer/"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "patches/*"

    # 上游 Make-arch 的目标名（由 0001 补丁补上）。ARCH 同时决定产物目录 compile/<ARCH>/。
    _ARCH_TARGET = "linux-arm-thr"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # PNG 输出（-format PNG）需要 libpng。不声明 zlib：tachyon 自己不调 zlib，
        # 它只经 libpng 间接用到；多声明一个直接依赖反而可能与 libpng 钉的版本冲突。
        self.requires("libpng/1.6.58.1")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _tool(self, name, fallback):
        """构建期调外部工具一律解析成绝对路径（与 R33 同源）：
        这份 musl 上的 exec 不做 PATH 查找，裸名调用会 ENOENT。"""
        import shutil as _shutil
        return _shutil.which(name) or fallback

    def build(self):
        apply_conandata_patches(self)
        cc = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict).get(
            "c", "/data/service/hnp/bin/clang")
        make = self._tool("make", "/data/service/hnp/bin/make")
        ar = self._tool("ar", "/data/service/hnp/bin/ar")
        ranlib = self._tool("ranlib", "/data/service/hnp/bin/ranlib")
        # ⚠️ `${STRIP} <binary>` 紧跟在链接之后跑（unix/Makefile:169）。strip 改动字节
        # 会**让链接器刚打上的自签失效**，故 package() 里必须重签（_sign_binaries）。
        strip = self._tool("strip", "/data/service/hnp/bin/strip")

        # libpng 的 -I/-L/-l 直接从 cpp_info 取，不经 pkg-config：
        # 上游 Makefile 只认 PNGINC/PNGLIB 两个字符串变量，本来就是拼出来喂进去的，
        # 中间再套一层 pkg-config 只是多一个会失败的环节。
        png = self.dependencies["libpng"].cpp_info
        png_root = self.dependencies["libpng"].package_folder
        def _abs(paths):
            return [p if os.path.isabs(p) else os.path.join(png_root, p) for p in (paths or [])]
        pnginc = " ".join("-I" + p for p in _abs(png.includedirs))
        pnglib = " ".join(["-L" + p for p in _abs(png.libdirs)]
                          + ["-l" + l for l in (png.libs or ["png16"])])

        unix = os.path.join(self.source_folder, "unix")
        self.run(
            '"{make}" -C "{unix}" {target} CC="{cc}" AR="{ar}" RANLIB="{ranlib}" STRIP="{strip}" '
            'USEPNG=-DUSEPNG PNGINC="{pnginc}" PNGLIB="{pnglib}" -j1'.format(
                make=make, unix=unix, target=self._ARCH_TARGET, cc=cc, ar=ar,
                ranlib=ranlib, strip=strip, pnginc=pnginc, pnglib=pnglib))

    def package(self):
        built = os.path.join(self.source_folder, "compile", self._ARCH_TARGET, "tachyon")
        if not os.path.isfile(built):
            raise RuntimeError("没产出 tachyon 可执行文件: " + built)
        copy(self, "tachyon", src=os.path.dirname(built),
             dst=os.path.join(self.package_folder, "bin"))
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # 鸿蒙 PC 的 XPM 要求被 exec 的 ELF 带有效代码签名，否则报 Permission denied。
        # 本包**必须**重签：构建里 strip 跑在链接之后，链接器的自签已被改废。
        if self.settings.os != "OHOS":
            return
        import glob as _glob
        bindir = os.path.join(self.package_folder, "bin")
        objcopy = self._tool("llvm-objcopy", "/data/service/hnp/bin/llvm-objcopy")
        signer = self._tool("binary-sign-tool", "/data/service/hnp/bin/binary-sign-tool")
        for f in sorted(_glob.glob(os.path.join(bindir, "*"))):
            if os.path.islink(f) or not os.path.isfile(f) or not self._is_elf(f):
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        # 纯工具包：无库、无头
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
