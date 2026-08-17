#!/usr/bin/env python3
"""Conan recipe for acpica 20251212 — Intel ACPI Component Architecture 工具集。

上游：https://github.com/acpica/acpica tag 20251212（Intel ACPI 工具）
构建：make（generate/unix Makefile，make iasl 等生成各工具）
依赖：flex 2.5.3+ / bison 2.4.1+（iASL 编译器生成需要，本机 /data/service/hnp/bin 可用）
工具：iasl（ASL 编译器/AML 反汇编器）、acpixtract、acpiexec、acpihelp、acpisrc、acpibin
测试：上游 acpitests 套件（ASL 测试文件，单独包）；用 iasl 编译测试 ASL 验证
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout


class AcpicaConan(ConanFile):
    name = "acpica"
    version = "20251212"
    description = "ACPICA — Intel ACPI Component Architecture tools (iASL compiler, etc.)"
    license = "BSD-3-Clause"
    homepage = "https://www.acpica.org/"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # acpica 用 make 构建（generate/unix）；flex/bison 在系统 PATH
        # （/data/service/hnp/bin，本机已确认可用）
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        # acpica Makefile.config 用 -Werror + GCC 专有警告选项（-Wlogical-op/
        # -Wmissing-parameter-type/-Wold-style-declaration），clang 不识别且
        # -Werror 使其致命 → CFLAGS 加 -Wno-error -Wno-unknown-warning-option
        env_prefix = ("CC=/data/service/hnp/bin/clang "
                      "CXX=/data/service/hnp/bin/clang++ "
                      "AR=/data/service/hnp/bin/llvm-ar "
                      "RANLIB=/data/service/hnp/bin/llvm-ranlib "
                      'CFLAGS="-Wno-error -Wno-unknown-warning-option" '
                      f"TMPDIR={tmpdir}")
        # 生成全部工具（iasl/acpixtract/acpiexec/acpihelp/acpisrc/acpibin/acpidump）
        self.run(f"cd {self.source_folder} && {env_prefix} make -j4 "
                 "PROGS=\"iasl acpixtract acpiexec acpihelp acpisrc acpibin acpidump\"",
                 ignore_errors=True)

    def package(self):
        copy(self, "COPYING*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # 生成的二进制在 generate/unix/bin 或 bin/
        src_bins = os.path.join(self.source_folder, "generate", "unix", "bin")
        if not os.path.isdir(src_bins):
            src_bins = os.path.join(self.source_folder, "bin")
        for exe in ("iasl", "acpixtract", "acpiexec", "acpihelp", "acpisrc",
                    "acpibin", "acpidump"):
            copy(self, exe, src=src_bins,
                 dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = []
        self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))
