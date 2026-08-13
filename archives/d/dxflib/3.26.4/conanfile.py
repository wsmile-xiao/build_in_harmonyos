#!/usr/bin/env python3
"""Conan recipe — dxflib 3.26.4.

DXF file parser/writer library (zero dependencies, C++).
Build: manual (upstream uses qmake .pro; OHOS has no qmake, so compile
the 2 source files directly with clang++).
"""
from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout
import os

required_conan_version = ">=2.0"


class DxflibConan(ConanFile):
    name = "dxflib"
    version = "3.26.4"
    package_type = "library"

    description = "DXF file parser/writer library (zero deps)"
    homepage = "https://qcad.org/en/dxflib-downloads"
    license = "GPL-2.0-or-later"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    exports_sources = "patches/*"

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        # 上游用 qmake（dxflib.pro：TEMPLATE=lib, CONFIG-=qt）。
        # OHOS 无 qmake，手动编译 2 个实现源文件（dxflib.pro SOURCES）。
        src = self.source_folder
        bld = self.build_folder
        fpic = "-fPIC" if self.options.fPIC else ""
        self.run(f"cd {src} && clang++ -std=c++11 {fpic} -O2 "
                 f"-DDXFLIB_LIBRARY -I{src}/src -c src/dl_dxf.cpp "
                 f"-o {bld}/dl_dxf.o")
        self.run(f"cd {src} && clang++ -std=c++11 {fpic} -O2 "
                 f"-DDXFLIB_LIBRARY -I{src}/src -c src/dl_writer_ascii.cpp "
                 f"-o {bld}/dl_writer_ascii.o")
        self.run(f"llvm-ar rcs {bld}/libdxflib.a {bld}/dl_dxf.o {bld}/dl_writer_ascii.o")

    def package(self):
        bld = self.build_folder
        copy(self, "libdxflib.a", src=bld,
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "*.h", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "include", "dxflib"))
        copy(self, "gpl-2.0greater.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "dxflib")
        self.cpp_info.set_property("cmake_target_name", "dxflib::dxflib")
        self.cpp_info.libs = ["dxflib"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]