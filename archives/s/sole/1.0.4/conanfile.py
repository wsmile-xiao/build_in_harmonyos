#!/usr/bin/env python3
"""Conan recipe — sole 1.0.4 (header-only C++11 UUID library).

Sole is a lightweight header-only C++11 library to generate UUIDs
(versions 0, 1 and 4) with str/base62/pretty serialization and rebuild().
Nothing is compiled: the public headers (sole.hpp, sole.fwd.hpp) are
installed as-is.

Patch 0001: uuid4() used `__thread` for thread-local std::random_device /
std::uniform_int_distribution (non-trivial destructor). Clang 15 rejects
`__thread` for such types ("type of thread-local variable has non-trivial
destruction"); standard C++11 `thread_local` works on every platform.
"""
from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout
import os


class SoleConan(ConanFile):
    name = "sole"
    version = "1.0.4"
    description = "Sole is a lightweight C++11 library to generate universally unique identifiers (UUID v0/v1/v4)"
    license = "Zlib"  # zlib/libpng
    homepage = "https://github.com/r-lyeh/sole"
    url = "https://github.com/r-lyeh/sole"

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
        # 无编译阶段（header-only），仅应用补丁后由 package() 拷贝头文件。
        # 不得伪造编译日志（R34）。
        apply_conandata_patches(self)

    def package(self):
        copy(self, "*.hpp", src=self.source_folder, dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        # 无编译产物，不依赖 os/compiler 二进制差异
        self.info.clear()

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
