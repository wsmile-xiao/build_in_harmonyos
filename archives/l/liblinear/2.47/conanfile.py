#!/usr/bin/env python3
"""Conan recipe — liblinear 2.47 (upstream v247, Makefile)"""
import os
import shlex

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class LiblinearConan(ConanFile):
    name = "liblinear"
    version = "2.47"
    package_type = "library"
    description = (
        "Library for large linear classification supporting "
        "SVM, logistic regression and linear regression"
    )
    license = "BSD-3-Clause"
    homepage = "https://www.csie.ntu.edu.tw/~cjlin/liblinear/"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cxx = compilers.get("cpp") or "clang++"
        cc = compilers.get("c") or "clang"
        self.run(
            f"make CXX={shlex.quote(cxx)} CC={shlex.quote(cc)} "
            "AR=llvm-ar RANLIB=llvm-ranlib -j1 all lib",
            cwd=self.source_folder,
        )

    def package(self):
        include_dir = os.path.join(self.package_folder, "include")
        lib_dir = os.path.join(self.package_folder, "lib")
        bin_dir = os.path.join(self.package_folder, "bin")
        copy(self, "linear.h", self.source_folder, include_dir)
        copy(self, "liblinear.so*", self.source_folder, lib_dir)
        copy(self, "train", self.source_folder, bin_dir)
        copy(self, "predict", self.source_folder, bin_dir)
        versioned_library = os.path.join(lib_dir, "liblinear.so.5")
        library_link = os.path.join(lib_dir, "liblinear.so")
        if os.path.exists(versioned_library) and not os.path.exists(library_link):
            os.symlink("liblinear.so.5", library_link)

    def package_info(self):
        self.cpp_info.libs = ["linear"]
        self.cpp_info.bindirs = ["bin"]
