#!/usr/bin/env python3
"""Conan recipe — sml 1.1.11 (C++14 header-only State Machine Library).

sml is a header-only C++14 state machine library (boost-ext). No sources
are compiled: the public headers under include/ are installed as-is.

R32 note: no settings.os branch is needed — the OHOS-adapted conan maps
os=OHOS to CMAKE_SYSTEM_NAME=HarmonyOS automatically.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class SmlConan(ConanFile):
    name = "sml"
    version = "1.1.11"
    description = "[Boost::ext].SML: C++14 State Machine Library (header-only)"
    license = "BSL-1.0"
    homepage = "https://github.com/boost-ext/sml"
    url = "https://github.com/boost-ext/sml"  # CI fills this

    package_type = "header-library"

    # 无编译产物 → settings 仅保留结构一致性；package_id 清空见 package_id()
    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # 无编译阶段：header-only，无编译产物（R34：不伪造编译日志）
    def build(self):
        apply_conandata_patches(self)

    def package(self):
        copy(self, "*.hpp",
             src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        self.info.clear()          # 无构建依赖 os/compiler → 单一 package_id

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "sml")
        self.cpp_info.set_property("cmake_target_name", "sml::sml")
