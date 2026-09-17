#!/usr/bin/env python3
# conanfile.py — libotf 0.9.16（HarmonyOS PC / OHOS aarch64 适配）

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rm
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class LibotfConan(ConanFile):
    name = "libotf"
    version = "0.9.16"
    description = "OpenType 字体处理库：OTF 表解析、字形驱动（GSUB/GPOS/GDEF）与字体工具"
    license = "LGPL-2.1-or-later"
    url = "https://download.savannah.nongnu.org/releases/m17n/"
    homepage = "https://www.nongnu.org/m17n/"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"{self.ref} 仅适配 Linux / OHOS（R32）")

    def requirements(self):
        # otf.h 直接包含 <ft2build.h> / FT_FREETYPE_H，且 libotf 运行期依赖 freetype，
        # 因此头文件与库都必须传递给消费者（transitive_headers / transitive_libs）。
        self.requires("freetype/2.14.3", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # 补丁 0003 让 configure 用 pkg-config 探测 freetype（上游调用的
        # freetype-config 自 FreeType 2.10 起已被移除）；AutotoolsToolchain
        # 已把 generators 目录加入 PKG_CONFIG_PATH，这里只需生成 .pc 文件。
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # HMDFS 共享文件系统不支持 make jobserver 的 FIFO（mkfifo），并行构建会报
        # "jobserver unavailable"，故固定 -j1。
        autotools.make(args=["-j1"])

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install()
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["otf"]
        # otfdump / otflist / otftobdf 是 example/ 下的 bin_PROGRAMS，安装到 bin/
        self.cpp_info.bindirs = ["bin"]
