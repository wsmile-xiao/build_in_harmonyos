#!/usr/bin/env python3
"""Conan recipe for jpeg-compressor 104 — lossless JPEG encoder/decoder library (jpge/jpgd)."""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class JpegCompressorConan(ConanFile):
    name = "jpeg-compressor"
    version = "104"
    description = "jpeg-compressor: C++ class for JPEG compression (jpge) and decompression (jpgd)"
    license = "Public Domain"
    homepage = "https://github.com/richgel999/jpeg-compressor"
    url = "https://github.com/richgel999/jpeg-compressor"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # jpge.cpp/h 与 jpgd.cpp/h 完全自包含，无任何第三方依赖（R18 预编译包无需查询）
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: 编译器必须从 Conan conf 获取，禁止裸用 shell 环境变量
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = compilers.get("cpp", "clang++") if compilers else "clang++"
        ar = compilers.get("ar", "llvm-ar") if compilers else "llvm-ar"
        ranlib = compilers.get("ranlib", "llvm-ranlib") if compilers else "llvm-ranlib"
        opt = "-g" if str(self.settings.build_type) == "Debug" else "-O2"
        flags = f"{opt} -fPIC"
        build_dir = self.build_folder
        src = self.source_folder
        objs = []
        for cppfile in ("jpge.cpp", "jpgd.cpp"):
            obj = os.path.join(build_dir, cppfile.replace(".cpp", ".o"))
            self.run(f"{cxx} {flags} -c {src}/{cppfile} -o {obj}")
            objs.append(obj)
        if self.options.shared:
            shared_lib = os.path.join(build_dir, "libjpeg_compressor.so")
            self.run(f"{cxx} -shared -fPIC -o {shared_lib} {' '.join(objs)}")
        else:
            static_lib = os.path.join(build_dir, "libjpeg_compressor.a")
            self.run(f"{ar} rcs {static_lib} {' '.join(objs)}")
            self.run(f"{ranlib} {static_lib}")

    def package(self):
        # 源码为 Public Domain，仓库内无 LICENSE 文件，不做 license copy
        copy(self, "jpge.h", self.source_folder, os.path.join(self.package_folder, "include"))
        copy(self, "jpgd.h", self.source_folder, os.path.join(self.package_folder, "include"))
        if self.options.shared:
            copy(self, "libjpeg_compressor.so", self.build_folder,
                 os.path.join(self.package_folder, "lib"))
        else:
            copy(self, "libjpeg_compressor.a", self.build_folder,
                 os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["jpeg_compressor"]