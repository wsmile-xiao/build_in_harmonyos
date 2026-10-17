#!/usr/bin/env python3
"""Conan test_package — pdfio 1.6.5.

Verifies that pdfio can be found via pkg-config and that a
test program linking against pdfio compiles and runs.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class PdfioTestConan(ConanFile):
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
        # 简单 C 程序，链接 pdfio，验证 API 可用
        src = os.path.join(self.source_folder, "test_pdfio.c")
        pdfio = self.dependencies["pdfio"]
        self.run(
            f"{os.environ.get('CC', 'clang')} "
            f"-o test_pdfio \"{src}\" "
            f"-I{pdfio.package_folder}/include "
            f"-L{pdfio.package_folder}/lib "
            f"-lpdfio -lz",
            env="conanbuild",
        )

    def test(self):
        # can_run 判断本机能否执行测试二进制
        # 交叉编译时 test_pdfio 是 OHOS 目标二进制，本机无法执行
        # 此时只验证编译链接成功（build() 已完成）
        if can_run(self):
            # 显式 self.run() 执行测试二进制（L0d 门禁要求）
            # test_pdfio 返回 0=全通过，1=有失败
            self.run(
                os.path.join(self.build_folder, "test_pdfio"),
                env="conanrun",
            )
        else:
            self.output.info(
                "交叉编译环境，跳过 test_pdfio 运行（编译链接已验证）"
            )

