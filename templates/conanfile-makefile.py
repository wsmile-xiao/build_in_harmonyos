#!/usr/bin/env python3
"""Conan recipe template — Makefile project.

Usage: Copy to archives/{letter}/{name}/{version}/conanfile.py
       Replace {name}, {version}, {description} with actual values.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class {Name}Conan(ConanFile):
    name = "{name}"
    version = "{version}"
    description = "{description}"
    license = ""  # TODO: 填写许可证
    homepage = ""  # TODO: 填写主页 URL

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # OHOS: ensure clang is used
        make_env = os.environ.copy()
        make_env.setdefault("CC", "clang")
        make_env.setdefault("CXX", "clang++")
        self.run("make -j1", env=make_env)

    def package(self):
        copy(self, "*", src=self.build_folder, dst=self.package_folder)

    def package_info(self):
        self.cpp_info.libs = ["{name}"]
