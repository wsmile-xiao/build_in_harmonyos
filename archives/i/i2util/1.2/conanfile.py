#!/usr/bin/env python3
"""Conan recipe for I2util — Internet2 utility library.

Command-line parsing, error logging, threading, SHA-1/HMAC-SHA1/PBKDF2,
random number and hash table support used by BWCTL, OWAMP and other tools.
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain


class I2UtilConan(ConanFile):
    name = "i2util"
    version = "1.2"
    description = "Internet2 utility library (error logging, CLI parsing, threading, SHA-1/HMAC/PBKDF2)"
    license = "Apache-2.0"
    homepage = "http://software.internet2.edu/sources/I2util/"
    url = "http://software.internet2.edu/sources/I2util/I2util-1.2.tar.gz"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: OS 判断必须包含 OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("i2util is supported only on Linux/OHOS")

    def requirements(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # 上游 configure 仅构建静态库（AC_PROG_RANLIB，无 libtool shared）
        # 不传 --enable-static/--disable-shared（configure 不识别的选项）
        tc = AutotoolsToolchain(self)
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
        self.cpp_info.libs = ["I2util"]
