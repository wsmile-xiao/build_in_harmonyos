from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
import os


class E2FsprogsConan(ConanFile):
    name = "e2fsprogs"
    version = "1.47.0"
    description = "Ext2/3/4 filesystem utilities and libraries"
    license = "GPL-2.0-or-later AND LGPL-2.0"
    homepage = "https://e2fsprogs.sourceforge.net/"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # Fix HMDFS hardlink issue: replace LN with cp -a in all generated Makefiles
        self.run("find . -name Makefile -exec sed -i 's/^LN = .*ln$/LN = cp -a/' {} +")
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.components["ext2fs"].libs = ["ext2fs"]
        self.cpp_info.components["ext2fs"].requires = ["com_err"]
        self.cpp_info.components["com_err"].libs = ["com_err"]
        self.cpp_info.components["e2p"].libs = ["e2p"]
        self.cpp_info.components["ss"].libs = ["ss"]
        self.cpp_info.components["ss"].requires = ["com_err"]
        self.cpp_info.components["uuid"].libs = ["uuid"]
        self.cpp_info.components["blkid"].libs = ["blkid"]
        self.cpp_info.components["blkid"].requires = ["uuid"]
