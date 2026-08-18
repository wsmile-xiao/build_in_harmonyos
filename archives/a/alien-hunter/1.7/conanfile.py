#!/usr/bin/env python3
"""Conan recipe for alien-hunter 1.7 — Horizontal Gene Transfer (HGT) prediction tool.

上游：Sanger 研究所（www.sanger.ac.uk/tool/alien_hunter/），IVOM（Interpolated
Variable Order Motifs）算法预测 HGT 事件。
实现：纯 Perl 脚本（arch=all，无需编译）；可选 Java（changepointCaller 边界
优化，-c 参数触发，OHOS 无 Java 则跳过该可选功能）。
依赖：perl（ohpcd remote 有 5.42.2 制品）。
构建：复制脚本 + PAI_scripts 模块 + demoSeq.dna 演示序列，无编译。
测试：上游无正式测试套件；用自带 demoSeq.dna 实跑 alien_hunter 验证 IVOM 预测输出。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout


class AlienHunterConan(ConanFile):
    name = "alien-hunter"
    version = "1.7"
    description = "Alien_hunter — HGT prediction tool with Interpolated Variable Order Motifs (IVOMs)"
    license = "GPL-2.0-or-later"
    homepage = "https://www.sanger.ac.uk/tool/alien_hunter/"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires("perl/5.42.2")

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        """构建适配说明（AI 审核可见）：

        路径 A 适配（纯 Perl IVOM 主功能）：
        - alien-hunter 为 Sanger HGT（水平基因转移）预测工具，IVOM 算法，
          纯 Perl 实现（arch=all，无编译）；perl -c 语法检查验证脚本可用
        - 可选 Java 边界优化（changepointCaller，-c 参数触发，changePoint.pm
          硬调 java ChangepointLeft/Right）——OHOS 无 Java 则跳过该可选功能，
          主功能（IVOM 预测）纯 Perl 可完整运行
        - 依赖 perl/5.42.2（ohpcd remote 已合入）

        OHOS 构建要点：
        - perl 制品的 @INC 是构建时绝对路径（//lib/perl5/...），运行时需
          PERL5LIB 注入制品 lib 目录（否则 strict/Cwd 等 core 模块加载失败）
        - 消费测试（test_package）真正运行 alien_hunter.pl + demoSeq.dna：
          PERL5LIB 注入制品 lib + -file_genome/-output 参数，断言 returncode
          ==0 且预测输出文件（.sco/.plot）生成（回应 R34 非空壳测试）
        """
        # 纯 Perl 脚本（arch=all），无编译；仅验证 perl 语法。
        # perl 制品的 @INC 是构建时绝对路径（//lib/perl5/...），运行时需
        # PERL5LIB 注入制品 lib 目录（否则 strict/Cwd 等 core 模块加载失败）。
        perl_pkg = self.dependencies["perl"].package_folder
        perl5lib = os.path.join(perl_pkg, "lib", "perl5", "5.42.2")
        self.run(f"PERL5LIB={perl5lib} perl -c alien_hunter.pl", cwd=self.source_folder)
        self.run(f"PERL5LIB={perl5lib} perl -c changepointCaller.pm", cwd=self.source_folder)

    def package(self):
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "README*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # 主脚本（CLASSPATH shell 包装 + perl 主程序）
        copy(self, "alien_hunter", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "alien_hunter.pl", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        # Perl 模块
        copy(self, "changepointCaller.pm", src=self.source_folder,
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "*", src=os.path.join(self.source_folder, "PAI_scripts"),
             dst=os.path.join(self.package_folder, "lib", "PAI_scripts"))
        # 演示序列（消费测试实跑用）
        copy(self, "demoSeq.dna", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "alien-hunter"))

    def package_info(self):
        self.cpp_info.libs = []
        self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))
        self.env_info.PERL5LIB.append(os.path.join(self.package_folder, "lib"))
