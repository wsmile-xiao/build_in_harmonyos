#!/usr/bin/env python3
"""Conan test_package — libcupsfilters 2.2.1.

Verifies that libcupsfilters can be found via pkg-config and that a
test program linking against libcupsfilters compiles and runs.
"""
import os

from conan import ConanFile
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibcupsfiltersTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "build"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # OHOS 平台：显式指定 build/host，绕过 config.guess
        triplet = "aarch64-ohos-linux-gnu"
        tc.configure_args.append(f"--build={triplet}")
        tc.configure_args.append(f"--host={triplet}")
        tc.generate()
        deps = AutotoolsDeps(self)
        deps.generate()

    def build(self):
        # 简单 C 程序，链接 libcupsfilters，验证 API 可用
        cf = self.dependencies["libcupsfilters"].package_folder
        # cups 包提供 cups/raster.h（image.h 依赖）
        cups = self.dependencies["cups"].package_folder
        pdfio = self.dependencies["pdfio"].package_folder
        zlib = self.dependencies["zlib"].package_folder
        lcms2 = self.dependencies["lcms2"].package_folder
        # cups -> openssl + libiconv（tls-openssl.c 引用 EVP_PKEY_new/X509_new/ASN1_*）
        openssl = self.dependencies["openssl"].package_folder
        libiconv = self.dependencies["libiconv"].package_folder
        src = os.path.join(self.source_folder, "test_libcupsfilters.c")
        self.run(
            f"{os.environ.get('CC', 'clang')} "
            f"-o test_libcupsfilters \"{src}\" "
            f"-I{cf}/usr/include "
            f"-I{cups}/usr/include "
            f"-I{lcms2}/usr/include "
            f"-L{cf}/lib "
            f"-L{cups}/lib "
            f"-L{pdfio}/lib "
            f"-L{zlib}/lib "
            f"-L{lcms2}/lib "
            f"-L{openssl}/lib "
            f"-L{libiconv}/lib "
            # 链接顺序：依赖在前，被依赖在后
            # libcupsfilters 依赖 cups/pdfio/lcms2/zlib
            # cups 依赖 openssl/libiconv/zlib
            f"-lcupsfilters -lcups -lcupsimage -lpdfio -llcms2 "
            f"-lssl -lcrypto -liconv -lcharset -lz "
            f"-lpthread -ldl -lm",
            env="conanbuild",
        )

    def test(self):
        # 显式 self.run() 执行测试二进制（L0d 门禁要求）
        self.run(os.path.join(self.build_folder, "test_libcupsfilters"), env="conanrun")
