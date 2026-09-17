#!/usr/bin/env python3
"""Conan recipe — dh-sysuser 1.6.0（脚本包，零编译）。

dh-sysuser 是 Debian debhelper 的 dh 序列 addon，在软件包安装/卸载时按
sysusers 配置创建/清理系统用户与组。上游 tarball 为 Debian native 源：
无 Makefile/configure，文件按 debian/dh-sysuser.install 布局安装。

OHOS 侧无 perl 运行时与 Debian::Debhelper::Dh_Lib，本包无法在 OHOS 上
执行；配方仅镜像 Debian 安装布局（脚本 + perl 模块 + 手册页），
test_package 使用包产物内容断言（见 test_package/MANIFEST.yml）。
"""
import os

from conan import ConanFile
from conan.tools.files import chmod, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class DhSysuserConan(ConanFile):
    name = "dh-sysuser"
    version = "1.6.0"
    description = "debhelper addon to create system users and groups (dh-sysuser 1.6.0)"
    license = "GPL-3.0-or-later"
    homepage = "https://salsa.debian.org/debian/dh-sysuser"
    url = "https://salsa.debian.org/debian/dh-sysuser"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 纯脚本包：无编译、无构建系统（上游为 Debian native 包）。
        # conandata 无补丁，apply_conandata_patches 为空操作。
        pass

    def package(self):
        # 镜像 Debian 安装布局（见 debian/dh-sysuser.install）到 Conan 包前缀：
        #   /usr/bin/dh_sysuser、/usr/bin/minsysusers、/usr/bin/sysuser-helper
        #   /usr/share/perl5/Debian/Debhelper/Sequence/sysuser.pm
        #   /usr/share/man/man8/minsysusers.8
        #   /usr/share/debhelper/autoscripts/postinst-*, postrm-sysuser
        bindir = os.path.join(self.package_folder, "bin")
        for name in ("dh_sysuser", "minsysusers", "sysuser-helper"):
            copy(self, name, src=self.source_folder, dst=bindir)
            chmod(self, os.path.join(bindir, name), 0o755)
        copy(self, "sysuser.pm", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "perl5",
                              "Debian", "Debhelper", "Sequence"))
        copy(self, "minsysusers.8", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man8"))
        copy(self, "postinst-sysuser", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "debhelper", "autoscripts"))
        copy(self, "postrm-sysuser", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "debhelper", "autoscripts"))
        copy(self, "postinst-minsysusers", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "debhelper", "autoscripts"))

    def package_info(self):
        # application/CLI：包内无库产物，不声明 cpp_info.libs（r44）
        self.cpp_info.bindirs = ["bin"]