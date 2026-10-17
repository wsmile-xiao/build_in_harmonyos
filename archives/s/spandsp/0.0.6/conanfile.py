#!/usr/bin/env python3
"""Conan recipe for spandsp 0.0.6 — telephony DSP library (Autotools).

SpanDSP is a library of DSP functions for telephony: G.711/G.722/G.726 codecs,
FAX (T.4/T.30/T.38), modems (V.17/V.22bis/V.27ter/V.29), DTMF, echo cancel,
and other telephony signal processing primitives.

OHOS adaptation notes:
  - Upstream ships a 2008-era config.guess/config.sub that cannot recognize
    HarmonyOS. patches/0001 adds ohos support to both scripts (E007/E072).
  - Core library build requires libtiff at configure time (src fax/t30/t38
    code includes tiffio.h and links -ltiff unconditionally).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class SpandspConan(ConanFile):
    name = "spandsp"
    version = "0.0.6"
    description = "A library of DSP functions for telephony (G.711/G.722/G.726 codecs, FAX T.4/T.30/T.38, modems, DTMF)"
    license = "LGPL-2.1-only"
    homepage = "https://www.soft-switch.org/"
    url = "https://www.soft-switch.org/"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libtiff/4.7.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System-name library -> static by default
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # R49/E524: 依赖注入 — configure 强制需要 libtiff 的头文件与库
        tiff_pkg = self.dependencies["libtiff"].package_folder
        tc.configure_args.append(f"CPPFLAGS=-I{tiff_pkg}/include")
        tc.configure_args.append(f"LDFLAGS=-L{tiff_pkg}/lib -Wl,-rpath,{tiff_pkg}/lib")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        # -j1: HMDFS 上并行 install 多个 install-sh -d 创建同一目录会
        #     报 "File exists"（E129 类似平台限制），必须串行
        autotools = Autotools(self)
        autotools.install(args=["-j1"])

    def package_info(self):
        self.cpp_info.libs = ["spandsp"]
