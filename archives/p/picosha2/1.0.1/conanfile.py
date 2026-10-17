#!/usr/bin/env python3
"""Conan recipe — picosha2 1.0.1 (header-only, no build family A)."""
import os

from conan import ConanFile
from conan.tools.cmake import cmake_layout
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class Picosha2Conan(ConanFile):
    name = "picosha2"
    version = "1.0.1"
    description = "PicoSHA2 - a tiny SHA256 implementation (header-only)"
    license = "MIT"
    homepage = "https://github.com/okdshin/PicoSHA2"
    url = ""  # CI fills this

    package_type = "header-library"   # header-only 库（无需 shared option）

    # 无编译产物 → settings 仅保留结构一致性；package_id 清空见下
    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def export_sources(self):
        export_conandata_patches(self)

    def build(self):
        # header-only: 无编译阶段，仅统一补丁应用入口（R34：不伪造编译日志）
        apply_conandata_patches(self)

    def package(self):
        # header-only 库: 仅复制头文件与许可证
        copy(self, "*.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "*.hpp", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        self.info.clear()          # 无构建依赖 os/compiler → 单一 package_id

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
