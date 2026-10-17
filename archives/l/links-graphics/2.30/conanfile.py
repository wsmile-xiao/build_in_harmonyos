#!/usr/bin/env python3
import os
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout

class LinksgraphicsConan(ConanFile):
    name = "links-graphics"
    version = "2.30"
    description = "Text and graphics mode WWW browser with framebuffer driver"
    license = "GPL-2.0"
    homepage = "http://links.twi.cz"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/3.5.6.1.1")
        self.requires("bzip2/1.0.8")
        self.requires("libpng/1.6.58.2")
        self.requires("libjpeg/10")
        self.requires("libtiff/4.7.2")
        self.requires("libwebp/1.6.0")
        self.requires("fontconfig/2.18.3")
        self.requires("zlib/1.3.2", override=True)
        self.requires("zstd/1.5.7", override=True)
        self.requires("freetype/2.14.3", override=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.extra_cflags.append("-Wno-int-conversion")
        tc.configure_args.append("--enable-graphics")
        tc.configure_args.append("--with-ssl")
        tc.configure_args.append("--with-fb")
        tc.configure_args.append("--without-x")
        tc.configure_args.append("--without-svgalib")
        tc.configure_args.append("--without-directfb")
        tc.configure_args.append("--without-atheos")
        tc.configure_args.append("--without-haiku")
        tc.generate()
        deps = AutotoolsDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        configure = os.path.join(self.source_folder, "configure")
        if self.settings.os in ("Linux", "OHOS"):
            replace_in_file(self, configure, "#! /bin/sh", "#! /system/bin/sh", strict=False)
            replace_in_file(self, configure, "#!/bin/sh", "#!/system/bin/sh", strict=False)
            replace_in_file(self, configure, "#! /bin/bash", "#! /data/service/hnp/bin/bash", strict=False)
            replace_in_file(self, configure, "#!/bin/bash", "#!/data/service/hnp/bin/bash", strict=False)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
