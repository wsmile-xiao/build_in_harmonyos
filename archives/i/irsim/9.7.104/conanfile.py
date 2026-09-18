#!/usr/bin/env python3
"""Conan recipe for irsim 9.7.104 — switch-level digital circuit simulator.

irsim is a SPICE-like switch-level simulator for digital MOS circuits
(Autotools-style configure + make).  It ships CLI tools (irsim,
gentbl, genspktbl) plus parameter libraries (.prm), so it is packaged
as an application, not a library.

OHOS adaptations (all in patches/, see notes.md):
  1. config.guess/config.sub: HarmonyOS -> aarch64-unknown-linux-ohos
  2. configure umask 077 -> 022 (HMDFS temp dir quirk)
  3. configure graphics branch: fall back to ${NULL_SRCS} when neither
     Tcl nor X11 is available (avoids thread.c needing X11/Xlib.h)
  4. base/mem.c: use the malloc() GetMoreCore path on __OHOS__
     (sbrk() returns failure on this platform)
  5. analyzer/noana.c: provide the 4 no-graphics symbols the base
     module still references (OffsetNode/OffsetVector/EnableInput/
     DisableInput), matching upstream semantics

No third-party conan dependencies (X11/Tcl/Tk optional and not
required for the null-graphics build).
"""
from conan import ConanFile
from conan.tools.files import chdir, get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class IrsimConan(ConanFile):
    name = "irsim"
    version = "9.7.104"
    description = "irsim — switch-level digital circuit simulator (CLI)"
    license = "MIT"
    homepage = "https://github.com/RTimothyEdwards/irsim"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # irsim 顶层 configure 是 "cd scripts && ./configure" 包装脚本（CWD 依赖源码根目录），
        # 因此必须从源码根目录运行 configure/make，不能依赖 Autotools helper 的 build-release 子目录。
        with chdir(self, self.source_folder):
            self.run("./configure --prefix=/", env="conanbuild")
            self.run("make -j1", env="conanbuild")

    def package(self):
        with chdir(self, self.source_folder):
            self.run(f"make install DESTDIR={self.package_folder}", env="conanbuild")
        # 构建期已通过补丁去除顶层 configure 硬编码 CFLAGS="-g"（调试信息会把构建目录
        # 路径嵌入二进制，H3 宿主路径门禁）；此处不再 strip（llvm-strip 会破坏 OHOS
        # 二进制的 codesign 段导致不可执行）。

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", str(self.package_folder) + "/bin")
        self.cpp_info.libdirs = ["lib"]
