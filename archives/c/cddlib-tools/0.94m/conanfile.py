#!/usr/bin/env python3
"""Conan recipe — cddlib-tools 0.94m (autotools command-line tools)

cddlib-tools is the command-line tool set of cddlib 0.94m:
scdd / lcdd / redcheck / fourier / projection / adjacency / allfaces /
cddexec / testlp* etc.  The same upstream tarball builds both the libcdd
library and these tools; this recipe packages the tool binaries.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class CddlibtoolsConan(ConanFile):
    name = "cddlib-tools"
    version = "0.94m"
    description = "cddlib-tools 0.94m command-line tools (Double Description method)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/cddlib/cddlib"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}
    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["-j1"])
        # 删掉 libtool 的 .la：里面烤死 libdir 绝对路径，会把下游引到死路。
        import glob as _glob, os as _os
        for _la in _glob.glob(_os.path.join(self.package_folder, "lib", "*.la")):
            _os.remove(_la)

    def package_info(self):
        # 命令工具放 bin/；libcdd/libcddgmp 随包装入 lib/（工具的运行时依赖）
        self.cpp_info.bindirs = ["bin"]