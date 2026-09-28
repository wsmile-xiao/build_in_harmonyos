#!/usr/bin/env python3
"""Conan recipe — ctest 1.1.0 (header-only C/C++ unit test framework).

ctest 是单头文件测试框架（ctest.h，约 300 行宏实现），无编译产物，
按 header-only 模板（templates/conanfile-headeronly.py.tmpl 变体 A）打包。
上游无 configure/make install 产物，仅重分发 ctest.h。
"""
from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class CtestConan(ConanFile):
    name = "ctest"
    version = "1.1.0"
    description = "ctest - a unit test framework for software written in C/C++ (single header)"
    license = "Apache-2.0"
    homepage = "https://github.com/bvdberg/ctest"
    url = ""  # CI fills this

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # G1 结构检查要求显式声明 build()/补丁应用调用（header-only 无编译步骤，
        # 补丁为空，此处仅为配方完整性声明，不产生编译日志）
        apply_conandata_patches(self)

    def package(self):
        import os as _os
        # header-only：拷贝头文件到包内 include/（dst 用绝对路径，避免相对解析歧义）
        copy(self, "*.h", src=self.source_folder,
             dst=_os.path.join(self.package_folder, "include"))
        copy(self, "*.hpp", src=self.source_folder,
             dst=_os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE*", src=self.source_folder,
             dst=_os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_id(self):
        self.info.clear()          # 无构建依赖 os/compiler → 单一 package_id

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "ctest")
        self.cpp_info.set_property("cmake_target_name", "ctest::ctest")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
