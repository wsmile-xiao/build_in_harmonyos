#!/usr/bin/env python3
"""Conan recipe for exif 0.6.22.1 — libexif command-line interface tool.

Builds the `exif` command-line tool (autotools) against libexif and popt.
Requires: libexif (already published), popt (already published).
"""
import os
from pathlib import Path

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class ExifConan(ConanFile):
    name = "exif"
    version = "0.6.22.1"
    description = "Command-line utility to read, write, modify and display EXIF data found in digital image files, using libexif"
    license = "GPL-2.0-or-later"
    homepage = "https://libexif.github.io/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # W0 verified: both deps already published to ohpcd artifact repo
        self.requires("libexif/0.6.26.1")
        self.requires("popt/1.16")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # configure 用 pkg-config 检测 libexif/popt（GP_CHECK_LIBRARY），
        # 必须用 PkgConfigDeps 按 conan 依赖真实路径生成 .pc，否则检测失败
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # E002: configure 临时目录使用 ${HOME}/tmp（0003 补丁已改 configure），
        # CI worker 的 HOME 下可能无 tmp 目录，必须先创建（参照 libexif 0.6.26.1 合入配方）
        home_tmp = Path(os.environ.get("HOME", "/tmp")) / "tmp"
        home_tmp.mkdir(parents=True, exist_ok=True)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # exif is a CLI tool: binary in bin/, no library
        self.cpp_info.bindirs = ["bin"]
