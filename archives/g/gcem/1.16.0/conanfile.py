#!/usr/bin/env python3
"""Conan recipe — gcem 1.16.0 (header-only C++11 compile-time math library)."""

import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class GcemConan(ConanFile):
    name = "gcem"
    version = "1.16.0"
    description = "A C++ compile-time math library using generalized constant expressions (header-only)"
    license = "Apache-2.0"
    homepage = "https://github.com/kthohr/gcem"
    url = "https://github.com/kthohr/gcem"
    topics = ("math", "constexpr", "header-only", "c++", "cpp")

    package_type = "header-library"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # header-only：无编译步骤；应用 conandata 声明的补丁（当前 patches 为空）
        apply_conandata_patches(self)

    def package(self):
        copy(self, "*.hpp",
             os.path.join(self.source_folder, "include"),
             os.path.join(self.package_folder, "include"))
        # 子目录头文件（gcem_incl/）
        copy(self, "*",
             os.path.join(self.source_folder, "include", "gcem_incl"),
             os.path.join(self.package_folder, "include", "gcem_incl"))
        copy(self, "LICENSE*", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []