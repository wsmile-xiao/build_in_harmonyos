#!/usr/bin/env python3
"""Conan recipe — libdwarf 0.11.1.

libdwarf — A library and a set of command-line tools for reading and
writing DWARF2 debugging information.
构建系统：CMake
平台：OHOS aarch64 / Linux / Windows / macOS
依赖：zlib/1.3.1, zstd/1.5.6（与基线 2.1.0 已发布配方一致，ENABLE_DECOMPRESSION 默认 TRUE
      需要 libz/libzstd；两者缺失时上游自动禁用压缩段支持）

对齐基线 archives/l/libdwarf/2.1.0 配方结构；R34：test_package 真实调用 dwarf_* API。
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rmdir,
    rename,
)
from conan.tools.scm import Version


class LibdwarfConan(ConanFile):
    name = "libdwarf"
    version = "0.11.1"
    description = "A library and a set of command-line tools for reading and writing DWARF2"
    license = ("LGPL-2.1-only", "BSD-2-Clause-Views", "GPL-2.0-only")
    homepage = "https://www.prevanders.net/dwarf.html"
    url = ""
    topics = ("debug", "dwarf", "dwarf2", "elf")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_dwarfgen": [True, False],
        "with_dwarfdump": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_dwarfgen": False,
        "with_dwarfdump": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

        if not self.options.with_dwarfgen:
            self.license = (l for l in self.license if l != "BSD-2-Clause-Views")
        if not self.options.with_dwarfdump:
            self.license = (l for l in self.license if l != "GPL-2.0-only")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("zlib/1.3.1")
        self.requires("zstd/1.5.6")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS"] = True
        tc.variables["BUILD_NON_SHARED"] = not self.options.shared
        tc.variables["BUILD_SHARED"] = self.options.shared
        tc.variables["BUILD_DWARFGEN"] = self.options.with_dwarfgen
        tc.variables["BUILD_DWARFDUMP"] = self.options.with_dwarfdump
        tc.variables["BUILD_DWARFEXAMPLE"] = False
        if cross_building(self):
            tc.variables["HAVE_UNUSED_ATTRIBUTE_EXITCODE"] = "0"
            tc.variables["HAVE_UNUSED_ATTRIBUTE_EXITCODE__TRYRUN_OUTPUT"] = ""
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        # 0001-zlib-target-alias 为 OHOS/Conan 环境所需（ohpcd zlib 只声明 zlib::zlib），
        # 故 0.11.1 总是应用 conandata 中的补丁，而非基线只在 <0.9.2/Windows 应用。
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(
            self,
            pattern="COPYING",
            dst=os.path.join(self.package_folder, "licenses"),
            src=os.path.join(self.source_folder, "src", "lib", "libdwarf"),
        )
        rename(
            self,
            os.path.join(self.package_folder, "licenses", "COPYING"),
            os.path.join(self.package_folder, "licenses", "COPYING-libdwarf"),
        )
        if self.options.with_dwarfgen:
            copy(
                self,
                pattern="COPYING",
                dst=os.path.join(self.package_folder, "licenses"),
                src=os.path.join(self.source_folder, "src", "bin", "dwarfgen"),
            )
            rename(
                self,
                os.path.join(self.package_folder, "licenses", "COPYING"),
                os.path.join(self.package_folder, "licenses", "COPYING-dwarfgen"),
            )
        if self.options.with_dwarfdump:
            copy(
                self,
                pattern="GPL.txt",
                dst=os.path.join(self.package_folder, "licenses"),
                src=os.path.join(self.source_folder, "src", "bin", "dwarfdump"),
            )
            rename(
                self,
                os.path.join(self.package_folder, "licenses", "GPL.txt"),
                os.path.join(self.package_folder, "licenses", "COPYING-dwarfdump"),
            )
        copy(
            self,
            pattern="COPYING",
            dst=os.path.join(self.package_folder, "licenses"),
            src=self.source_folder,
        )

        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.libs = ["dwarf"]
        if self.options.with_dwarfgen:
            self.cpp_info.libs.append("dwarfp")
        # For static builds (>= 2.1.0), define LIBDWARF_STATIC=1
        if Version(self.version) >= "2.1.0" and not self.options.shared:
            self.cpp_info.defines = ["LIBDWARF_STATIC=1"]