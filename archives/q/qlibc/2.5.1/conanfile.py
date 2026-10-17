#!/usr/bin/env python3
"""Conan recipe for qlibc 2.5.1 — general purpose C/C++ library.

Upstream: https://github.com/wolkykim/qlibc (BSD-2-Clause)
Build system: autotools (configure + make); builds libqlibc + libqlibcext
(static and shared). Only dependency is pthread (system lib).
"""
import os
import glob

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class QlibcConan(ConanFile):
    name = "qlibc"
    version = "2.5.1"
    description = "Simple and powerful general purpose C/C++ library with containers and utilities"
    license = "BSD-2-Clause"
    homepage = "https://github.com/wolkykim/qlibc"
    url = "https://github.com/wolkykim/qlibc"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("qlibc is supported only on Linux/OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)
        # qlibc 是 in-source 构建：手写 Makefile.in 使用相对对象路径
        # （containers/qtreetbl.o 等），out-of-source 布局下 make 找不到
        # 目标文件，必须把 build 目录指回源码根目录（先例 abc/abduco）。
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # NOTE: upstream configure does not support --enable-static/--disable-shared;
        # it always builds both static and shared archives. R26 (system-name lib
        # isolation) does not apply: qlibc is not a system-named library.
        tc.configure_args.extend([
            "--disable-debug",
        ])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Remove libtool *.la wrappers if present.
        for _la in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(_la)
        # qlibc upstream 始终同时构建静态与共享库，且共享库的 DT_NEEDED
        # 记录字面相对路径（../lib/libqlibc.so.2），脱离源码树后加载失败。
        # shared=False 时只保留静态 .a，保证消费者干净链接（R26 口径）。
        if not self.options.shared:
            for _so in glob.glob(os.path.join(self.package_folder, "lib", "*.so*")):
                if os.path.islink(_so) or os.path.isfile(_so):
                    os.remove(_so)

    def package_info(self):
        self.cpp_info.libs = ["qlibc", "qlibcext"]
        self.cpp_info.system_libs = ["pthread"]
        self.cpp_info.includedirs = ["include"]
