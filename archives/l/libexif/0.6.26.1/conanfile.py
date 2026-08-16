#!/usr/bin/env python3
"""Conan recipe — libexif 0.6.26.1 (Autotools).

EXIF 元数据处理库，用于读取、写入和编辑图像文件的 EXIF 信息。
适配说明：config.guess/config.sub 增加 HarmonyOS 平台识别，
configure 临时目录改为 ${HOME}/tmp 并放宽 umask（E011/HMDFS）。
"""
import os
from pathlib import Path

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibexifConan(ConanFile):
    name = "libexif"
    version = "0.6.26.1"
    description = "EXIF 元数据处理库，用于读取、写入和编辑图像文件的 EXIF 信息"
    license = "LGPL-2.1+"
    homepage = "https://libexif.github.io"
    url = "https://github.com/libexif/libexif"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # Add project-specific configure args here:
        # tc.configure_args.append("--without-bash-malloc")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # E002: configure 临时目录使用 ${HOME}/tmp（补丁已改 configure），需确保目录存在
        home_tmp = Path(os.environ.get("HOME", "/tmp")) / "tmp"
        home_tmp.mkdir(parents=True, exist_ok=True)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # 实际库名为 libexif.a，Conan 自动加 lib 前缀
        self.cpp_info.libs = ["exif"]
        self.cpp_info.set_property("pkg_config_name", "libexif")
