#!/usr/bin/env python3
"""Conan recipe — kann 0 (attractivechaos/kann).

kann 是纯 Makefile 的轻量 C 神经网络库：无 configure、无 make install。
Makefile 仅提供对象目标（kautodiff.o / kann.o / kann_extra/kann_data.o）
与示例可执行目标。本配方只打包库与头文件，示例为演示程序不安装。
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class KannConan(ConanFile):
    name = "kann"
    version = "0.0"
    description = "KANN: a standalone lightweight C library for constructing and training artificial neural networks"
    license = "MIT"
    homepage = "https://github.com/attractivechaos/kann"
    url = "https://github.com/attractivechaos/kann"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # 无 configure：不需要 AutotoolsToolchain；编译器由 make CC= 显式传入（R33）
        pass

    def build(self):
        apply_conandata_patches(self)
        # 纯 Makefile 库：basic_layout 下构建目录与源码目录分离，
        # make/ar 必须在源码目录（self.source_folder）内执行（R33）
        self.run("make CC=clang kautodiff.o kann.o kann_extra/kann_data.o", cwd=self.source_folder)
        # 静态归档 libkann.a（R26：默认静态）
        self.run("llvm-ar rcs libkann.a kautodiff.o kann.o kann_extra/kann_data.o", cwd=self.source_folder)

    def package(self):
        copy(self, "kann.h", src=self.source_folder, dst=os.path.join(self.package_folder, "include"))
        copy(self, "kautodiff.h", src=self.source_folder, dst=os.path.join(self.package_folder, "include"))
        copy(self, "kann_data.h", src=os.path.join(self.source_folder, "kann_extra"),
             dst=os.path.join(self.package_folder, "include", "kann_extra"))
        copy(self, "kseq.h", src=os.path.join(self.source_folder, "kann_extra"),
             dst=os.path.join(self.package_folder, "include", "kann_extra"))
        copy(self, "libkann.a", src=self.source_folder, dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "kann")
        self.cpp_info.set_property("cmake_target_name", "kann::kann")
        self.cpp_info.libs = ["kann"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.system_libs = ["pthread", "m", "z"]
        self.cpp_info.bindirs = []
