#!/usr/bin/env python3
"""Conan recipe — libsvm 3.37.1.1 (upstream 3.37, Makefile)"""
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


class LibsvmConan(ConanFile):
    name = "libsvm"
    version = "3.37.1.1"
    package_type = "library"
    description = (
        "Support Vector Machine library for classification, regression, "
        "and distribution estimation"
    )
    license = "BSD-3-Clause"
    homepage = "https://www.csie.ntu.edu.tw/~cjlin/libsvm/"

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
        self.run(
            f"make CXX={shlex.quote(cxx)} -j1 all lib",
            cwd=self.source_folder,
        )

    def package(self):
        include_dir = os.path.join(self.package_folder, "include")
        lib_dir = os.path.join(self.package_folder, "lib")
        bin_dir = os.path.join(self.package_folder, "bin")
        copy(self, "svm.h", self.source_folder, include_dir)
        copy(self, "libsvm.so*", self.source_folder, lib_dir)
        copy(self, "svm-train", self.source_folder, bin_dir)
        copy(self, "svm-predict", self.source_folder, bin_dir)
        copy(self, "svm-scale", self.source_folder, bin_dir)
        versioned_library = os.path.join(lib_dir, "libsvm.so.4")
        library_link = os.path.join(lib_dir, "libsvm.so")
        if os.path.exists(versioned_library) and not os.path.exists(library_link):
            os.symlink("libsvm.so.4", library_link)

    def package_info(self):
        self.cpp_info.libs = ["svm"]
        self.cpp_info.bindirs = ["bin"]
