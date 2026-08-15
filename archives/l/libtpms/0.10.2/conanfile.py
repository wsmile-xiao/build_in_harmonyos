#!/usr/bin/env python3
"""Conan recipe for building libtpms 0.10.2 with Autotools."""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


def _drop_umask_077(path):
    with open(path, "r", encoding="utf-8") as handle:
        data = handle.read()
    data = data.replace(
        'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
        'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`')
    data = data.replace('(umask 077 && mkdir "$tmp")', 'mkdir "$tmp"')
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(data)


class LibtpmsConan(ConanFile):
    name = "libtpms"
    version = "0.10.2"
    description = "Library providing software emulation of TPM 1.2 and TPM 2.0"
    license = "BSD-3-Clause"
    homepage = "https://github.com/stefanberger/libtpms"
    url = "https://github.com/stefanberger/libtpms"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/3.5.6")

    def build_requirements(self):
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        AutotoolsDeps(self).generate()
        tc = AutotoolsToolchain(self)
        if self.options.get_safe("fPIC"):
            tc.cflags.append("-fPIC")
        # Conan 的 Release 工具链默认把 NDEBUG 注入 CPPFLAGS（ndebug 属性），
        # 会把上游测试 fuzz.cc 里带副作用的 assert(TPM_Malloc(...)) 编译掉，
        # 导致 memcpy(NULL) 段错误；上游默认不定义 NDEBUG，置 None 以匹配上游。
        tc.ndebug = None
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--with-openssl")
        tc.configure_args.append("--with-tpm2")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        for tool, variable in (("autoconf", "AUTOCONF"),
                               ("autoheader", "AUTOHEADER"),
                               ("autom4te", "AUTOM4TE")):
            path = shutil.which(tool)
            if path:
                os.environ[variable] = path
        self.run("autoreconf --install --force", cwd=self.source_folder,
                 env="conanbuild")
        _drop_umask_077(os.path.join(self.source_folder, "configure"))
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j4"])
        autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["tpms"]
