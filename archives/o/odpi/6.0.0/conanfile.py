#!/usr/bin/env python3
"""Conan recipe -- odpi 6.0.0 (Oracle Database Programming Interface for C).

Pure Makefile project, no ./configure, no autoconf.
Build: make -> lib/libodpic.so.6.0.0

The upstream Makefile uses $(CC) which defaults to literal "cc" if CC is
unset.  We prefix the make invocation with CC=clang inline (R33).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class OdpiConan(ConanFile):
    name = "odpi"
    version = "6.0.0"
    description = "Oracle Database Programming Interface for C (ODPI-C)"
    license = "UPL-1.0 OR Apache-2.0"
    homepage = "https://github.com/oracle/odpi"
    url = "https://github.com/oracle/odpi"
    topics = ("oracle", "database", "odpi", "dpi", "oci", "c-library")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass

    def build(self):
        apply_conandata_patches(self)
        make_root = os.path.dirname(self.build_folder)
        cmd = (
            f'cd {make_root} && '
            f'CC=clang CFLAGS="-O2 -fPIC" LDFLAGS=-shared LIBS="-ldl -lpthread" '
            f'make -j2'
        )
        self.run(cmd)

    def package(self):
        make_root = os.path.dirname(self.build_folder)
        src_inc = os.path.join(make_root, "include")
        src_embed = os.path.join(make_root, "embed")
        src_lib = os.path.join(make_root, "lib")
        copy(self, "*.h", src=src_inc,
             dst=os.path.join(self.package_folder, "include"),
             keep_path=False)
        copy(self, "*.h", src=src_embed,
             dst=os.path.join(self.package_folder, "include", "odpi", "embed"),
             keep_path=False)
        copy(self, "*.so*", src=src_lib,
             dst=os.path.join(self.package_folder, "lib"),
             keep_path=False)
        copy(self, "*.dylib", src=src_lib,
             dst=os.path.join(self.package_folder, "lib"),
             keep_path=False)
        copy(self, "*.a", src=src_lib,
             dst=os.path.join(self.package_folder, "lib"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["odpic"]
        self.cpp_info.set_property("cmake_file_name", "dpi")
        self.cpp_info.set_property("cmake_target_name", "dpi::odpic")
        self.cpp_info.set_property("cmake_build_modules", [])
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["dl", "pthread"]
