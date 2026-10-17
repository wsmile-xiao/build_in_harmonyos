#!/usr/bin/env python3
"""Conan recipe — chntpw 140201（Offline NT Password & Registry Editor，C 工具集）.

上游 http://pogostick.net/~pnh/ntpasswd/（源码经 archive.ubuntu.com pristine
orig.tar.xz 获取，Debian/Ubuntu dsc 双重互证）。raw Makefile 无 configure：
无条件依赖 OpenSSL（chntpw.c 直接 include <openssl/des.h>/<openssl/md4.h>），
Makefile 默认 CFLAGS 强制 -m32 且 LIBS 缺 -lcrypto，全部以 make 变量覆写修正。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class ChntpwConan(ConanFile):
    name = "chntpw"
    version = "140201"
    description = "Offline NT Password & Registry Editor: chntpw/reged/cpnt/samusrgrp/sampasswd CLI tools"
    license = "GPL-2.0-or-later"
    homepage = "https://pogostick.net/~pnh/ntpasswd/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # chntpw.c 无条件 include <openssl/des.h> 与 <openssl/md4.h>（链接 DES_/MD4_）
        self.requires("openssl/1.1.1w")

    def layout(self):
        # raw Makefile 在源码目录原地构建（无 VPATH 支持）
        self.folders.source = "."
        self.folders.build = "."
        self.folders.generators = os.path.join(".", "conan")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        openssl = self.dependencies["openssl"]
        ossl = openssl.package_folder
        # 上游 Makefile 三处不适用默认值，全部命令行覆写（codonw 先例：
        # 命令行变量优先于文件内赋值）：
        #   CFLAGS 默认含 -m32（aarch64 必须去掉）
        #   LIBS 默认只有 -L（缺 -lcrypto，DES_/MD4_ 符号会未定义）
        #   CC 默认 gcc（OHOS 用 clang）
        # 仅构建 5 个动态工具目标，避开需要 -static + libcrypto.a 的 .static 目标
        # （tarball 自带的陈旧 .static 预编译产物保持原样、不入包）
        make_cmd = (
            "make -j1"
            " CC=clang"
            f" CFLAGS='-DUSEOPENSSL -g -I. -I{os.path.join(ossl, 'include')} -Wall'"
            f" OSSLPATH='{ossl}'"
            f" LIBS='-L{os.path.join(ossl, 'lib')} -lcrypto'"
            " chntpw reged cpnt samusrgrp sampasswd"
        )
        self.run(make_cmd, cwd=self.source_folder)

    def package(self):
        src = self.source_folder
        # 上游无 install 目标（写死 /usr/local），按交付清单手动打包
        # （clzip 家族先例）；tarball 内陈旧 .static 预编译产物不入包
        for tool in ("chntpw", "reged", "cpnt", "samusrgrp", "sampasswd"):
            copy(self, tool, src, os.path.join(self.package_folder, "bin"))
        copy(self, "*.txt", src, os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
