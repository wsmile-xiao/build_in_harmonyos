#!/usr/bin/env python3
"""Conan recipe — cosmic-icon 1.4.0 (icon theme, data-only)."""
from conan import ConanFile
from conan.tools.files import get, copy
import os


class CosmicIconConan(ConanFile):
    name = "cosmic-icon"
    version = "1.4.0"
    license = "CC-BY-SA-4.0"
    author = "pop-os"
    url = "https://github.com/pop-os/cosmic-icons"
    homepage = "https://github.com/pop-os/cosmic-icons"
    description = "Icon theme for the COSMIC Desktop Environment"
    no_copy_source = True
    settings = "os", "arch"

    def package_id(self):
        # 纯数据包，不依赖平台差异，所有配置共享同一包
        self.info.clear()

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        pass

    def package(self):
        copy(self, "*", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "icons", "Cosmic"))

    def package_info(self):
        self.cpp_info.includedirs = []
