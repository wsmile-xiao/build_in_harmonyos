#!/usr/bin/env python3
"""Conan recipe — gaia-ecs 1.0.0 (header-only ECS framework).

gaia-ecs 是 header-only 库（CMake INTERFACE library），无编译产物；
配方参考上游自带 pkg/conan/conanfile.py 写法：no_copy_source + 直接打包
single_include/ 头文件，并导出 gaia::gaia CMake target。
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.scm import Version
from conan.tools.build import check_min_cppstd
from conan.tools.files import copy, get, rm, apply_conandata_patches
from conan.tools.layout import basic_layout
import os

required_conan_version = ">=1.52.0"

class GaiaEcsConan(ConanFile):
    name = "gaia-ecs"
    version = "1.0.0"
    license = "MIT"
    package_type = "header-library"
    description = "A simple and powerful entity component system (ECS) written in C++17"
    homepage = "https://github.com/richardbiely/gaia-ecs"
    url = "https://github.com/richardbiely/gaia-ecs"
    topics = ("gamedev", "performance", "entity", "ecs", "dod", "entity-component-system", "cpp17")
    exports_sources = "LICENSE", "single_include/*"
    no_copy_source = True
    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self, src_folder="src")

    def export_sources(self):
        copy(self, "LICENSE", src=self.recipe_folder, dst=self.export_sources_folder)
        copy(self, "single_include/*", src=self.recipe_folder, dst=self.export_sources_folder)

    def package_id(self):
        self.info.clear()

    def validate(self):
        if self.settings.get_safe("compiler.cppstd"):
            check_min_cppstd(self, 17)

        compiler = self.settings.get_safe("compiler")
        compiler_version = self.settings.get_safe("compiler.version")
        minimum_version = {
            "Visual Studio": "16",
            "msvc": "192",
            "gcc": "10",
            "clang": "7.0",
            "apple-clang": "10.0",
        }.get(str(compiler), False)
        if minimum_version and compiler_version and Version(compiler_version) < minimum_version:
            raise ConanInvalidConfiguration(
                f"{self.ref} requires C++17, which your compiler does not support."
            )

    def source(self):
        # 用 get() 兼容预下载机制改写的 url 列表形态（file:// 镜像缓存）。
        src = self.conan_data["sources"][self.version]
        get(self, **src, strip_root=True, excludes=(".github/*", ".vscode/*", ".git/*"))
        filename = os.path.basename(src["url"][0] if isinstance(src["url"], list) else src["url"])
        rm(self, filename, self.source_folder)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "*", src=os.path.join(self.source_folder, "single_include"),
             dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        if self.settings.os in ["FreeBSD", "Linux", "OHOS"]:
            self.cpp_info.system_libs = ["pthread"]

        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "gaia")
        self.cpp_info.set_property("cmake_target_name", "gaia::gaia")