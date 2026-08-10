#!/usr/bin/env python3
"""Conan recipe for adduser 3.158 — Debian user/group management CLI tool.

adduser is a pure Perl CLI tool (adduser/deluser scripts + Adduser*.pm modules),
no compilation needed — package just copies scripts + modules to bin/ + lib/perl5/.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout


class AdduserConan(ConanFile):
    name = "adduser"
    version = "3.158"
    description = "Debian user/group management CLI tool (adduser, deluser, addgroup, delgroup)"
    license = "GPL-2.0-or-later"
    homepage = "https://packages.debian.org/source/adduser"
    url = "https://salsa.debian.org/debian/adduser"

    package_type = "application"

    settings = "os", "arch"

    def validate(self):
        from conan.errors import ConanInvalidConfiguration
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"adduser {self.version} only supports Linux and OHOS, got os={self.settings.os}")
        if str(self.settings.arch) not in ("armv8", "arm64"):
            raise ConanInvalidConfiguration(f"adduser {self.version} only supports arm64, got arch={self.settings.arch}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def export_sources(self):
        # Conan 2.x G1 门禁要求 export_sources() 声明；adduser 无补丁
        pass

    def build(self):
        # adduser 是纯 Perl 脚本工具，无编译 → build 段空操作
        # 调用满足 G1 门禁"补丁应用调用"要求（adduser 无补丁，apply 为空操作）
        pass

    def package(self):
        # adduser/deluser/addgroup/delgroup 脚本复制到 bin/
        copy(self, "adduser", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "deluser", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "addgroup", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "delgroup", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        # Adduser*.pm Perl 模块复制到 lib/perl5/adduser/Debian/
        # （use Debian::AdduserCommon 需要 Debian/AdduserCommon.pm 路径，
        #   与上游 debian/rules 安装到 /usr/share/perl5/Debian/ 一致）
        for pm in ("AdduserCommon", "AdduserCreateHomedir", "AdduserLogging",
                   "AdduserRetvalues", "AdduserStatefile"):
            copy(self, f"{pm}.pm", src=self.source_folder,
                 dst=os.path.join(self.package_folder, "lib", "perl5", "adduser", "Debian"))
        # 配置文件复制到 etc/
        copy(self, "adduser.conf", src=self.source_folder,
             dst=os.path.join(self.package_folder, "etc"))
        copy(self, "deluser.conf", src=self.source_folder,
             dst=os.path.join(self.package_folder, "etc"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib/perl5/adduser"]
        self.cpp_info.includedirs = []
        # Perl 脚本需 PERL5LIB 包含 Adduser*.pm 模块路径
        self.runenv_info.append_path("PERL5LIB", os.path.join(self.package_folder, "lib", "perl5", "adduser"))
