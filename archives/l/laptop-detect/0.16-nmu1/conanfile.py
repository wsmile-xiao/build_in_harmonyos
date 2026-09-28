#!/usr/bin/env python3
"""Conan recipe for laptop-detect 0.16-nmu1 (system chassis type checker).

Debian-native POSIX shell script package, no compilation. Debian builds it
by substituting @VERSION@ in laptop-detect.in via sed (debian/rules
override_dh_auto_configure); we replicate that substitution in build() and
install the generated script together with its man page, README and the
BSD-3-Clause license text (shipped in debian/copyright, the upstream has
no standalone LICENSE file).

License: BSD-3-Clause.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout


class LaptopDetectConan(ConanFile):
    name = "laptop-detect"
    version = "0.16-nmu1"
    description = ("Debian system chassis type checker: detects whether the "
                   "machine is a laptop (POSIX sh script, arch-independent)")
    license = "BSD-3-Clause"
    homepage = "https://gitlab.com/debiants/laptop-detect"
    url = ""  # CI fills this

    package_type = "application"

    # 纯脚本包不消费编译设置，但 CI 的 L0p 门禁要求 OHOS profile 四项齐全
    # （缺 compiler/build_type 直接判失败），故声明完整四项——它们只进
    # package_id，build() 不读。
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)  # patches=[] 空操作，预留补丁入口
        # 复刻 Debian 构建方式（debian/rules override_dh_auto_configure）：
        # sed 替换 @VERSION@ 生成最终脚本。锚点防漂移：必须恰好一处。
        with open(os.path.join(self.source_folder, "laptop-detect.in"),
                  encoding="utf-8") as f:
            content = f.read()
        if content.count("@VERSION@") != 1:
            raise ConanInvalidConfiguration(
                "laptop-detect 0.16-nmu1: expected exactly one @VERSION@ "
                "anchor in laptop-detect.in")
        content = content.replace("@VERSION@", self.version)
        out = os.path.join(self.build_folder, "laptop-detect")
        with open(out, "w", encoding="utf-8") as f:
            f.write(content)
        os.chmod(out, 0o755)

    def package(self):
        # 安装布局与 Debian 一致：bin/laptop-detect + 手册页 + README；
        # 许可证文本随 debian/copyright 原样分发（BSD-3-Clause 全文在
        # copyright 内，上游 Debian-native 包无独立 LICENSE 文件）。
        copy(self, "laptop-detect", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"))
        os.chmod(os.path.join(self.package_folder, "bin", "laptop-detect"),
                 0o755)
        copy(self, "laptop-detect.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "README", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc",
                             "laptop-detect"))
        copy(self, "copyright", src=os.path.join(self.source_folder, "debian"),
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
