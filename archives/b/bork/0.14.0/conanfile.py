#!/usr/bin/env python3
"""Conan recipe — bork 0.14.0 (纯 bash 配置管理工具).

bork 是 Bash 配置管理工具（"the Bash-Operated Reconciling Kludge"），纯 bash
脚本（bin/bork 主脚本 + lib/ 模块），无编译无构建系统，无 conan 库依赖
（运行时依赖 bash 3.2 + sed/awk/grep 等 unix 工具）。

适配（参考 boom-completion/bobby 极简脚本包模式）：
- source(): Git.clone（borksh/bork，--depth 1 --branch v0.14.0，git 独立 ssl，
  CI Python 无 SSL 模块时可下载，E372）
- package(): 复制 bin/bork → bin/ + lib/ 模块 → lib/
  （bork 按 BASH_SOURCE 推导 BORK_SOURCE_DIR=<pkg> 并 source <pkg>/lib/.../，
   不读环境变量覆盖，故模块必须落在 <pkg>/lib/）
- test_package: 脚本存在性 + bash -n 语法校验 + 实际执行 bork version
"""
import os

from conan import ConanFile
from conan.tools.files import copy, export_conandata_patches, apply_conandata_patches
from conan.tools.scm import Git


class BorkConan(ConanFile):
    name = "bork"
    version = "0.14.0"
    description = "bork — Bash 配置管理工具（声明式系统配置断言 DSL）"
    license = "MIT"
    homepage = "https://bork.sh/"
    url = ""  # CI fills this

    package_type = "application"

    # OHOS profile 需要全部四项（L0p 门禁）
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        # Git.clone：git 独立 ssl，CI Python 无 SSL 模块时仍可下载（E372 方案）。
        # 浅克隆 + 指定 tag（v0.14.0）——不 checkout 臆造 commit（浅克隆只有
        # HEAD，固定 commit 需深克隆，臆造 commit 报 unable to read tree）。
        git = Git(self)
        git.clone(url=self.conan_data["git_url"],
                  target=".",
                  args=["--depth", "1", "--branch",
                        self.conan_data["git_branch"]])

    def build(self):
        # 纯脚本无编译；应用 conandata 补丁（本包无补丁，G1 完整性要求调用）
        apply_conandata_patches(self)

    def package(self):
        # bin/bork 主脚本 → bin/
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        bin_bork = os.path.join(self.source_folder, "bin", "bork")
        if os.path.isfile(bin_bork):
            copy(self, "bork", src=os.path.dirname(bin_bork),
                 dst=bindir, keep_path=False)
        # lib/ 模块（declarations/helpers/support）→ <pkg>/lib/
        # 【审查修复 2026-09-11】bork 自身按 BASH_SOURCE 推导加载路径：
        #   BORK_SOURCE_DIR = $(cd $(getDir ${BASH_SOURCE[0]})/.. && pwd -P)
        # 即 bin/bork 的上一级 = <pkg>，随后 source $BORK_SOURCE_DIR/lib/{helpers,
        # declarations,support}/*.sh。bork 不读任何环境变量覆盖该路径
        # （无 BORK_HOME 之类），因此模块必须落在 <pkg>/lib/，否则运行时
        # 报 "…/lib/helpers/*.sh: No such file or directory" 而无法工作。
        # 旧实现装到 share/bork/ 与实际加载路径不符，交付包不可用。
        src_lib = os.path.join(self.source_folder, "lib")
        libdir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(src_lib):
            for d in os.listdir(src_lib):
                src_d = os.path.join(src_lib, d)
                if os.path.isdir(src_d):
                    os.makedirs(os.path.join(libdir, d), exist_ok=True)
                    copy(self, "*", src=src_d, dst=os.path.join(libdir, d))
        # 文档（LICENSE）
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.output.info("bork: 纯 bash 配置管理工具，运行时依赖 bash+unix 工具")
        # bork 按 <pkg>/lib/{helpers,declarations,support}/*.sh 加载自身模块
        # （见 package() 注释），故 libdirs 即模块目录；bindirs 为 bin。
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.resdirs = ["lib"]
        self.cpp_info.libs = []
