#!/usr/bin/env python3
"""Conan recipe for isl 0.28 — autotools, imath multi-precision backend.

isl 是整数集合库（Integer Set Library）。OHOS 平台系统无 gmp.h，
适配采用 isl 自带 imath 多精度整数后端（--with-int=imath），无外部运行时依赖。
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class IslConan(ConanFile):
    name = "isl"
    version = "0.28"
    description = "Integer Set Library for manipulating sets and relations of integer points"
    license = "MIT"
    homepage = "https://libisl.sourceforge.io/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # isl 使用自带 imath 多精度整数后端，避免外部 gmp 依赖
        tc.configure_args.append("--with-int=imath")
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["isl"]
