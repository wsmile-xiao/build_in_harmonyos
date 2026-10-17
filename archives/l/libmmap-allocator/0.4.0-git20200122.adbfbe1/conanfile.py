#!/usr/bin/env python3
"""Conan recipe for the mmap_allocator STL file-mapping library."""

import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class LibmmapAllocatorConan(ConanFile):
    name = "libmmap-allocator"
    version = "0.4.0-git20200122.adbfbe1"
    description = "STL allocator and vector implementation backed by memory-mapped files"
    license = "LGPL-2.1"
    homepage = "https://github.com/johannesthoma/mmap_allocator"
    url = "https://github.com/johannesthoma/mmap_allocator"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _toolchain(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cxx = compilers.get("cpp") or "c++"
        cc = compilers.get("c") or "cc"
        ar = compilers.get("ar") or "ar"

        if str(self.settings.os) == "OHOS":
            target = "aarch64" if str(self.settings.arch) == "armv8" else str(self.settings.arch)
            sdk_sysroot = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(cxx))),
                "sysroot",
            )
            sysroot_flag = (
                f" --sysroot={sdk_sysroot}"
                if os.path.isdir(sdk_sysroot)
                else ""
            )
            if "--target=" not in cxx:
                cxx = f"{cxx} --target={target}-linux-ohos{sysroot_flag}"
            if "--target=" not in cc:
                cc = f"{cc} --target={target}-linux-ohos{sysroot_flag}"

        if str(self.settings.build_type) == "Debug":
            optimization = "-O0 -g"
        else:
            optimization = "-O2 -g"
        cxxflags = f"-std=c++17 {optimization} -fPIC"
        cflags = f"-std=c11 {optimization} -fPIC"
        return (
            f'CXX="{cxx}" CC="{cc}" AR="{ar}" '
            f'CXXFLAGS="{cxxflags}" CFLAGS="{cflags}"'
        )

    def _make_command(self):
        # Windows hosts in the local CI image provide mingw32-make, while
        # HarmonyOS/Linux builders provide the usual make executable.
        return "make" if shutil.which("make") else "mingw32-make"

    def build(self):
        apply_conandata_patches(self)
        os.chdir(self.source_folder)
        arguments = self._toolchain()
        make = self._make_command()
        self.run(f"{make} {arguments} -j1 all")
        # test_mmap_fixed is a separate upstream regression target and is
        # compiled even when the build machine cannot execute OHOS binaries.
        self.run(f"{make} {arguments} -j1 test_mmap_fixed")
        if can_run(self):
            self.run(f"{make} {arguments} -j1 test")
            self.run("./test_mmap_fixed")

    def package(self):
        os.chdir(self.source_folder)
        copy(self, "*.h", dst=os.path.join(self.package_folder, "include"), src=self.source_folder)
        copy(self, "README.md", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        if self.options.shared:
            copy(
                self,
                "libmmap_allocator.so",
                dst=os.path.join(self.package_folder, "lib"),
                src=self.source_folder,
            )
        else:
            copy(
                self,
                "libmmap_allocator.a",
                dst=os.path.join(self.package_folder, "lib"),
                src=self.source_folder,
            )

    def package_info(self):
        self.cpp_info.libs = ["mmap_allocator"]
        self.cpp_info.set_property("cmake_file_name", "mmap_allocator")
        self.cpp_info.set_property("cmake_target_name", "mmap_allocator::mmap_allocator")
