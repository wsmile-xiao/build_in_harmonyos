#!/usr/bin/env python3
"""Conan recipe — btparse 0.35 (BibTeX 解析 C 库, PCCTS 生成解析器).

上游: CPAN AMBS/btparse (作者 Greg Ward, 2005), Autoconf 2.57 + Automake + libtool 1.5.
OHOS 适配点全部以补丁交付:
  - 0001: config.guess 识别 HarmonyOS + HMDFS 下临时目录 umask 022 (知识 E007/E011/E129/E206)
  - 0002: config.sub 接受 aarch64 linux/ohos 三元组 (知识 E072)
  - 0003: configure confstat 临时目录 umask 022 (知识 E011/E136/E206)
上游自带测试 (tests/TESTS: read_test simple_test postprocess_test) 在 build() 内以
`make check` 实测执行。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class BtparseConan(ConanFile):
    name = "btparse"
    version = "0.35"
    description = "A C library to parse and process BibTeX files (PCCTS-based parser)"
    license = "LGPL-2.0-or-later"
    homepage = "https://github.com/ambs/Text-BibTeX"
    url = "https://github.com/ambs/Text-BibTeX"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("btparse 0.35 仅支持 Linux/OHOS")

    def requirements(self):
        pass  # 无外部依赖: PCCTS 1.33 运行时与生成解析器源码均随上游 tarball 发布

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # 上游官方测试: tests/Makefile.am TESTS = read_test simple_test postprocess_test
        autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # 清理 libtool *.la 包装 (Conan 2 copy() 无 delete= 参数, 用 glob 删除)
        import glob
        for _la in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(_la)

    def package_info(self):
        self.cpp_info.libs = ["btparse"]
        # 安装的命令行工具: bin/bibparse (BibTeX 语法检查器)
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
