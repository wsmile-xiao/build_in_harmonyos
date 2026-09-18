#!/usr/bin/env python3
"""Conan recipe — scrypt 1.3.2 (CLI tool by Colin Percival / Tarsnap).

scrypt is a command-line utility for encrypting files using the scrypt
key derivation function (RFC 7914). configure hard-requires OpenSSL
(AES_encrypt + openssl/aes.h), so openssl is declared as a build/runtime
dependency and its include/lib dirs are injected via CPPFLAGS/LDFLAGS.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout


class ScryptConan(ConanFile):
    name = "scrypt"
    version = "1.3.2"
    description = "Encrypt and decrypt files using the scrypt key derivation function (RFC 7914)"
    license = "BSD-2-Clause"
    homepage = "http://www.tarsnap.com/scrypt.html"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # configure hard-requires OpenSSL (AES_encrypt + openssl/aes.h)
        self.requires("openssl/3.5.8.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--disable-shared")
        tc.generate()
        # Inject openssl dependency cpp_info (include/lib dirs) into configure
        # via CPPFLAGS/LDFLAGS; without AutotoolsDeps, configure's
        # AC_SEARCH_LIBS(AES_encrypt, crypto) cannot locate libcrypto.
        AutotoolsDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # E112/E114 bypass-mktemp（R02 缺陷 2 修复，afflib 3.7.22 同构已验证）：
        # config.status 用 `umask 077 && mktemp -d "./confXXXXXX"` 创建临时目录，
        # 在 CI/受限布局（HMDFS、noexec、TMPDIR=/data/storage/el2/base/cache）下
        # 0700 目录当前进程不可写 → "subs1.awk: Permission denied" →
        # "could not setup config files machinery"。改为普通 mkdir（默认 umask）
        # 使临时目录落位即可写可执行。
        configure_path = os.path.join(self.source_folder, "configure")
        old = """{
  tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&
  test -d "$tmp"
}  ||
{
  tmp=./conf$$-$RANDOM
  (umask 077 && mkdir "$tmp")
} || as_fn_error $? "cannot create a temporary directory in ." "$LINENO" 5
ac_tmp=$tmp"""
        new = """tmp=./conf$$-$RANDOM
mkdir "$tmp"
ac_tmp=$tmp"""
        replace_in_file(self, configure_path, old, new, strict=False)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # CLI tool: only bindir carries the scrypt executable
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []