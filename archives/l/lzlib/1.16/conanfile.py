#!/usr/bin/env python3
"""Conan recipe for lzlib, the LZMA library for the lzip format."""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LzlibConan(ConanFile):
    name = "lzlib"
    version = "1.16"
    description = "LZMA compression library for the lzip format"
    license = "BSD-2-Clause"
    homepage = "https://www.nongnu.org/lzip/lzlib.html"
    url = "https://www.nongnu.org/lzip/lzlib.html"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("lzlib is supported only on Linux/OHOS")

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # The upstream custom configure script defaults CC to gcc.
        tc.configure_args.append(f"CC={self.settings.compiler}")
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        configure_path = os.path.join(self.source_folder, "configure")
        check_path = os.path.join(self.source_folder, "testsuite", "check.sh")
        for path in (configure_path, check_path):
            replace_in_file(
                self, path, "#! /bin/sh", "#! /system/bin/sh", strict=False
            )
            replace_in_file(
                self, path, "#!/bin/sh", "#!/system/bin/sh", strict=False
            )
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        autotools.make(target="check")

    def package(self):
        lib_dir = os.path.join(self.package_folder, "lib")
        include_dir = os.path.join(self.package_folder, "include")
        os.makedirs(lib_dir, exist_ok=True)
        os.makedirs(include_dir, exist_ok=True)
        copy(self, "lzlib.h", src=self.source_folder, dst=include_dir, keep_path=False)

        if self.options.shared:
            shared_lib = os.path.join(self.build_folder, "liblz.so.1")
            if not os.path.isfile(shared_lib):
                raise ConanInvalidConfiguration("lzlib shared library was not produced")
            versioned_name = f"liblz.so.{self.version}"
            for name in (versioned_name, "liblz.so.1", "liblz.so"):
                shutil.copy2(shared_lib, os.path.join(lib_dir, name))
        else:
            copy(self, "liblz.a", src=self.build_folder, dst=lib_dir, keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["lz"]
        self.cpp_info.set_property("cmake_file_name", "lzlib")
        self.cpp_info.set_property("cmake_target_name", "lzlib::lzlib")
