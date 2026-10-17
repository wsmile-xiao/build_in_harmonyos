#!/usr/bin/env python3
"""Conan recipe for align 1.7.5 — text column alignment filter (Perl scripts)."""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AlignConan(ConanFile):
    name = "align"
    version = "1.7.5"
    description = "Align - text column alignment filter (align + width Perl tools)"
    license = "GPL-2.0-or-later"
    homepage = "https://kinzler.com/me/align/"
    url = "https://kinzler.com/me/align/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # align/width 是 Perl 脚本，运行时依赖 perl
        self.requires("perl/5.42.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # align/width 是 Perl 脚本，无需编译。
        # Makefile 仅用 perl 修改 shebang 为实际 perl 路径，这里等效重写。
        # shebang 指向设备标准 perl 路径（/data/service/hnp/bin/perl，cmd-pkgs 安装位），
        # 避免内嵌构建机 Conan cache 绝对路径导致消费端不可运行。
        for script in ("align", "width"):
            path = os.path.join(self.source_folder, script)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            content = content.replace(
                "#!/usr/bin/perl", "#!/data/service/hnp/bin/perl", 1)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

    def package(self):
        # 安装 align + width 两个可执行脚本到 bin/
        for script in ("align", "width"):
            copy(self, script, self.source_folder,
                 os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
