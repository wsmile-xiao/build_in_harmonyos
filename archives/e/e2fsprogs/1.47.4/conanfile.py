from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
import os


class E2FsprogsConan(ConanFile):
    name = "e2fsprogs"
    version = "1.47.4"
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
        # 显式三元组跳过 config.guess：1.47.4 自带的 config.guess(2025-07-10) 没有
        # HarmonyOS 探测分支（设备 uname -s = HarmonyOS 时 cannot guess build type），
        # 而 config.sub 已原生认 linux-ohos，纯 shell 规范化、不碰编译器探针/HMDFS 临时文件。
        # build==host → 原生模式（同 1.47.0 手工构建时的 build_alias/host_alias 做法）。
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
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
