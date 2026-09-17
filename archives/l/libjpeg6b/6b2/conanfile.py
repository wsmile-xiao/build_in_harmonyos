#!/usr/bin/env python3
"""Conan recipe — libjpeg6b 6b2 (IJG jpeg-6b, Debian autotools lineage)"""

import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class Libjpeg6bConan(ConanFile):
    name = "libjpeg6b"
    version = "6b2"
    description = "IJG jpeg-6b reference implementation of the JPEG image codec (Debian 6b lineage, CVE-2013-6629/6630 fixed)"
    license = "IJG"
    homepage = "https://www.ijg.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    # R26: libjpeg6b installs SONAME libjpeg.so.62, which collides with the
    # classic-API SONAME shipped by libjpeg-turbo. Default to static so the
    # package cannot shadow the system library.
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # AutotoolsToolchain maps the shared/fPIC options to
        # --enable-shared/--disable-shared and --with-pic.
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # -j1: HMDFS 不支持 make jobserver 的 mkfifo，且上游 install 规则会并发
        # 创建 $(includedir)（install-data-local 与 install-includeHEADERS 各建
        # 一次，install-sh 对竞态 EEXIST 直接报错），全程串行规避。
        autotools.make(args=["-j1"])
        # Upstream self-test (check-local): djpeg/cjpeg/jpegtran encode/decode
        # the reference images shipped with the tarball and byte-compare the
        # results with cmp (6 assertions).
        autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["-j1"])
        copy(self, "README", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "README.6b2", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["jpeg"]
        self.cpp_info.bindirs = ["bin"]
