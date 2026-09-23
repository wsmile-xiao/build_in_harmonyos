#!/usr/bin/env python3
"""Conan recipe — xenium 0.0.2 (header-only)

xenium 是 header-only 的 C++ 并发数据结构与内存回收算法库（C++17）。
库本体无第三方依赖；消费方按上游 README 需要 C++17 编译器与 pthread。
"""
import os
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class XeniumConan(ConanFile):
    name = "xenium"
    version = "0.0.2"
    description = "C++ library providing various concurrent data structures and reclamation schemes (header-only)"
    license = "MIT"
    homepage = "https://github.com/mpoeter/xenium"
    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        # R32 平台检测：header-only 库理论平台无关，但仍遵守规程做白名单校验。
        if self.settings.os not in ("Linux", "OHOS", "FreeBSD", "Macos", "Windows"):
            raise ConanInvalidConfiguration(
                "xenium 只支持 Linux/OHOS/FreeBSD/Macos/Windows，当前: {}".format(self.settings.os))

    def validate(self):
        # 上游 README：实现使用 C++17 特性，要求编译器具备足够 C++17 支持。
        if self.settings.get_safe("compiler.cppstd"):
            check_min_cppstd(self, 17)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # header-only：无编译步骤；补丁直接修正随包分发的头文件。
        apply_conandata_patches(self)

    def package(self):
        # 源码 xenium/ 目录即全部公开头文件（含 detail/、impl/、reclamation/ 子目录）。
        # keep_path=True 保留子目录结构，消费方 #include <xenium/...> 依赖该布局。
        copy(
            self,
            "*.hpp",
            src=os.path.join(self.source_folder, "xenium"),
            dst=os.path.join(self.package_folder, "include", "xenium"),
            keep_path=True,
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
