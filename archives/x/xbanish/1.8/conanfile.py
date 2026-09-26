#!/usr/bin/env python3
"""Conan recipe for xbanish 1.8 -- X11 utility that hides the mouse cursor while typing.

Upstream ships a single C file whose Makefile hardcodes an X11BASE prefix and a
system-wide install prefix; this recipe instead compiles the same translation
unit directly against the conan X11 dependency packages (R36: no host X11 on CI
workers or on the device).

Upstream also carries an unused `#include <X11/Intrinsic.h>` -- grep shows 0 Xt
symbols referenced anywhere in xbanish.c, and every macro/API the file does use
(XWidthOfScreen, XHeightOfScreen, DefaultScreenOfDisplay, XQueryPointer,
XWarpPointer, ...) is declared in X11/Xlib.h.  That header ships only with
libXt, whose published recipe pins libx11/1.8.13, while both published libXi
recipes pin libx11/6.4.0, so the two cannot share one graph.  Patch 0001 drops
the dead include, which lets this package sit entirely on the libx11/6.4.0 line
already used by clipnotify/1.0.2 (verified: conan install --build=never resolves
9 OHOS binaries for it).

E549: the produced ELF is self-signed with binary-sign-tool before packaging.
OHOS has no X server, so the consumer test asserts the deterministic no-X error
path plus the four recorded DT_NEEDED X libraries (see test_package/).
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class XbanishConan(ConanFile):
    name = "xbanish"
    version = "1.8"
    description = "X11 utility that hides the mouse cursor when you start typing"
    license = "ISC"
    homepage = "https://github.com/jcs/xbanish"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 上游 Makefile 的 LIBS = -lX11 -lXfixes -lXi -lXext，逐条映射到制品仓
        # 已发布的 libx11/6.4.0 版本线（W0 实测见 archives/x/xbanish/1.8/notes.md）。
        # 刻意不引 libxt：xbanish 不使用任何 Xt 符号（补丁 0001 删除死 include）。
        self.requires("libx11/6.4.0", transitive_headers=True, transitive_libs=True)
        self.requires("libxfixes/6.1.0", transitive_headers=True, transitive_libs=True)
        self.requires("libxi/6.1.0", transitive_headers=True, transitive_libs=True)
        self.requires("libxext/6.4.0", transitive_headers=True, transitive_libs=True)
        # X11/X.h、X11/extensions 协议头
        self.requires("xorgproto/2025.1", transitive_headers=True)

    def layout(self):
        basic_layout(self)

    def generate(self):
        # conanbuild 环境提供 $CC/$CFLAGS/$LDFLAGS（R33：不依赖 shell 预置变量）
        AutotoolsToolchain(self).generate()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ── E549 ELF 自签名（clipnotify/cc-connect 同款实现） ────────────────

    def _find_tool(self, name):
        import glob as g

        for d in sorted(
            g.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/bin")
        ):
            p = os.path.join(d, name)
            if os.path.isfile(p):
                return p
        for d in ("/data/service/hnp/bin",):
            p = os.path.join(d, name)
            if os.path.isfile(p):
                return p
        return shutil.which(name)

    def _sign_elf(self, binary_path):
        from conan.errors import ConanException

        objcopy = self._find_tool("llvm-objcopy")
        sign_tool = self._find_tool("binary-sign-tool")
        if not sign_tool or not objcopy:
            raise ConanException("binary-sign-tool/llvm-objcopy not found (E549)")
        subprocess.run(
            [objcopy, "--remove-section", ".codesign", binary_path],
            capture_output=True,
            timeout=30,
        )
        tmp = binary_path + ".signed.tmp"
        for _ in range(3):
            r = subprocess.run(
                [
                    sign_tool,
                    "sign",
                    "-inFile",
                    binary_path,
                    "-outFile",
                    tmp,
                    "-selfSign",
                    "1",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if r.returncode == 0 and os.path.isfile(tmp):
                shutil.move(tmp, binary_path)
                os.chmod(binary_path, 0o775)
                return
        if os.path.exists(tmp):
            os.remove(tmp)
        from conan.errors import ConanException

        raise ConanException(f"signing failed for {binary_path}")

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        dep_incs = " ".join(
            f"-I{os.path.join(dep.package_folder, inc)}"
            for dep in self.dependencies.host.values()
            for inc in dep.cpp_info.includedirs
        )
        dep_libs = " ".join(
            f"-L{os.path.join(dep.package_folder, libdir)}"
            for dep in self.dependencies.host.values()
            for libdir in dep.cpp_info.libdirs
        )
        out = os.path.join(self.build_folder, "xbanish")
        # 上游 Makefile 同一编译式，仅把其硬编码的 X11BASE include/lib 路径
        # 换成 conan 依赖包路径（R49：全部指向依赖包私有目录，不注入共享前缀）
        self.run(
            f'$CC -O2 -Wall {dep_incs} "{src}/xbanish.c" -o "{out}" {dep_libs} '
            "-lX11 -lXfixes -lXi -lXext",
            env="conanbuild",
        )
        self._sign_elf(out)

    def package(self):
        copy(
            self,
            "xbanish",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )
        copy(
            self,
            "xbanish.1",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "man", "man1"),
            keep_path=False,
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
