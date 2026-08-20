#!/usr/bin/env python3
"""Conan recipe — libsvm 3.37 (Makefile)"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LibsvmConan(ConanFile):
    name = "libsvm"
    version = "3.37"
    description = "Support Vector Machine library for classification, regression, and distribution estimation"
    license = "BSD-3-Clause"
    homepage = "https://www.csie.ntu.edu.tw/~cjlin/libsvm/"

    settings = "os", "compiler", "build_type", "arch"

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
        # R33: pass compiler directly, not via shell env var
        self.run("make CXX=clang++ -j1 all lib", cwd=self.source_folder)

    def package(self):
        copy(self, "svm.h", self.source_folder, os.path.join(self.package_folder, "include"))
        copy(self, "libsvm.so*", self.source_folder, os.path.join(self.package_folder, "lib"))
        copy(self, "svm-train", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "svm-predict", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "svm-scale", self.source_folder, os.path.join(self.package_folder, "bin"))
        lib_dir = os.path.join(self.package_folder, "lib")
        if os.path.exists(os.path.join(lib_dir, "libsvm.so.4")) and not os.path.exists(os.path.join(lib_dir, "libsvm.so")):
            os.symlink("libsvm.so.4", os.path.join(lib_dir, "libsvm.so"))

    def package_info(self):
        self.cpp_info.libs = ["svm"]
        self.cpp_info.bindirs = ["bin"]
