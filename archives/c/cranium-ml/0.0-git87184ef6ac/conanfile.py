#!/usr/bin/env python3
"""Conan recipe — cranium-ml 0.0-git87184ef6ac (header-only C99)

Cranium 是一个 C99 header-only 人工神经网络库（MIT License, https://github.com/100/Cranium）。
仅分发 src/*.h 头文件（cranium.h 聚合入口 + matrix/layer/network/function/optimizer），
无二进制产物，无需编译；上游测试用 gcc -std=c99 + -lm 编译运行。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class CraniumMlConan(ConanFile):
    name = "cranium-ml"
    version = "0.0-git87184ef6ac"
    description = "A portable, header-only, artificial neural network library written in C99"
    license = "MIT"
    homepage = "https://github.com/100/Cranium"
    url = ""  # CI fills this

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        # R32: 平台判断必须 in ("Linux", "OHOS")，不能 == "Linux"
        if self.settings.os not in ("Linux", "OHOS", "FreeBSD", "Macos", "Windows"):
            raise ConanInvalidConfiguration(
                "cranium-ml 只支持 Linux/OHOS/FreeBSD/Macos/Windows，当前: {}".format(self.settings.os))

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # header-only，无编译单元；仍保留补丁应用入口（当前 patches 为空）
        apply_conandata_patches(self)

    def package(self):
        copy(self, "*.h",
             src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "include", "cranium"))

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libs = []