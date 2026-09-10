#!/usr/bin/env python3
"""Conan recipe — dehydrated 0.7.2 (pure Bash ACME v2 client).

dehydrated-io/dehydrated: a client for signing certificates with an ACME
server (e.g. Let's Encrypt). Pure Bash application (no C compilation):
a single self-contained script whose runtime deps are bash 4+/curl/openssl/
sed/awk/grep/diff/mktemp/hexdump — all present in the OHOS PC runtime —
so this recipe only packages the script with its license and docs, and
runs syntax + smoke self-checks as verification.
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class DehydratedConan(ConanFile):
    name = "dehydrated"
    version = "0.7.2"
    description = "ACME v2 client (Let's Encrypt etc.) implemented as a single Bash script"
    license = "MIT"
    homepage = "https://dehydrated.io"
    url = "https://github.com/dehydrated-io/dehydrated"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # 纯 Bash 脚本，无编译。自检两步：
        #   1) bash -n 语法自检
        #   2) --version 冒烟：真实执行脚本内置依赖检查（grep/mktemp/diff/sed/
        #      awk/curl/cut/head/tail/hexdump/openssl + sed ERE 可用性），并核对版本输出
        # 注意：OHOS hnp bash 在部分执行上下文 getcwd() 失败导致内置 PWD 未定义
        # （脚本 set -u 下 ${PWD} 引用报错），启动时显式传 PWD=<目录> 规避。
        bash = os.environ.get("BASH") or "/data/service/hnp/bin/bash"
        src = self.source_folder
        self.run('cd "%s" && PWD="%s" "%s" -n dehydrated' % (src, src, bash))
        self.run('cd "%s" && PWD="%s" "%s" dehydrated --version 2>&1 | grep -q "Dehydrated version: %s"'
                 % (src, src, bash, self.version))

    def package(self):
        src = self.source_folder
        # 主脚本 → bin/
        copy(self, "dehydrated", src=src, dst=os.path.join(self.package_folder, "bin"))
        os.chmod(os.path.join(self.package_folder, "bin", "dehydrated"), 0o755)
        # LICENSE → licenses/
        copy(self, "LICENSE", src=src, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        # 文档：README/CHANGELOG + docs/（md 文档、man 页、examples）
        doc = os.path.join(self.package_folder, "share", "doc", "dehydrated")
        copy(self, "README.md", src=src, dst=doc, keep_path=False)
        copy(self, "CHANGELOG", src=src, dst=doc, keep_path=False)
        copy(self, "docs/*.md", src=src, dst=doc, keep_path=False)
        copy(self, "docs/man/*", src=src, dst=os.path.join(doc, "man"), keep_path=False)
        copy(self, "docs/examples/*", src=src, dst=os.path.join(doc, "examples"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
