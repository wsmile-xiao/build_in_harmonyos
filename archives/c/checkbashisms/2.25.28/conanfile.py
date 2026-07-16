#!/usr/bin/env python3
"""Conan recipe for checkbashisms 2.25.28."""

import os
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class CheckbashismsConan(ConanFile):
    name = "checkbashisms"
    version = "2.25.28"
    package_type = "application"

    description = "Check for bashisms in /bin/sh scripts"
    license = "GPL-2.0"
    homepage = "https://salsa.debian.org/debian/devscripts"
    url = "https://salsa.debian.org/debian/devscripts"
    topics = ("shell", "bash", "lint", "devscripts")

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        self.folders.build = "."
        self.folders.source = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        src_dir = self.source_folder
        scripts_dir = os.path.join(src_dir, "scripts")

        # 创建版本文件
        version_file = os.path.join(src_dir, "version")
        with open(version_file, "w") as f:
            f.write(f"{self.version}\n")

        # 替换版本号占位符并生成可执行脚本
        pl_file = os.path.join(scripts_dir, "checkbashisms.pl")
        out_file = os.path.join(scripts_dir, "checkbashisms")
        with open(pl_file, "r") as f:
            content = f.read()
        content = content.replace("###VERSION###", self.version)
        with open(out_file, "w") as f:
            f.write(content)
        os.chmod(out_file, 0o755)

        # 运行上游测试（需要 shunit2，失败不影响构建）
        self.run("make check", ignore_errors=True)

    def package(self):
        scripts_dir = os.path.join(self.source_folder, "scripts")
        bin_dir = os.path.join(self.package_folder, "bin")
        man_dir = os.path.join(self.package_folder, "share", "man", "man1")

        copy(self, "checkbashisms", scripts_dir, bin_dir)
        os.chmod(os.path.join(bin_dir, "checkbashisms"), 0o755)

        man_src = os.path.join(scripts_dir, "checkbashisms.1")
        if os.path.exists(man_src):
            copy(self, "checkbashisms.1", scripts_dir, man_dir)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []