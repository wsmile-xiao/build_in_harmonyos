#!/usr/bin/env python3
"""Conan recipe — pycxx 6.2.3 (header+source library for Python C++ extensions)"""

import os
from conan import ConanFile
from conan.tools.files import copy, download, unzip, apply_conandata_patches, export_conandata_patches

class PyCXXConan(ConanFile):
    name = "pycxx"
    version = "6.2.3"
    description = "PyCXX - Write Python extensions in C++"
    license = "BSD-3-Clause"
    homepage = "https://cxx.sourceforge.net"
    settings = "os", "compiler", "build_type", "arch"
    package_type = "header-library"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        download(self, **self.conan_data["sources"], filename="pycxx-6.2.3.tar.gz")
        unzip(self, "pycxx-6.2.3.tar.gz", strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        copy(self, "*.hxx", src=os.path.join(self.source_folder, "CXX", "CXX"),
             dst=os.path.join(self.package_folder, "include", "CXX"))
        copy(self, "*.h", src=os.path.join(self.source_folder, "CXX", "CXX"),
             dst=os.path.join(self.package_folder, "include", "CXX"))
        for pyver in ("Python2", "Python3"):
            copy(self, "*", src=os.path.join(self.source_folder, "CXX", "CXX", pyver),
                 dst=os.path.join(self.package_folder, "include", "CXX", pyver))
        copy(self, "*.cxx", src=os.path.join(self.source_folder, "CXX", "Src"),
             dst=os.path.join(self.package_folder, "include", "CXX", "Src"))
        copy(self, "*.c", src=os.path.join(self.source_folder, "CXX", "Src"),
             dst=os.path.join(self.package_folder, "include", "CXX", "Src"))
        copy(self, "*", src=os.path.join(self.source_folder, "CXX", "Src", "Python3"),
             dst=os.path.join(self.package_folder, "include", "CXX", "Src", "Python3"))
        copy(self, "COPYRIGHT", src=os.path.join(self.source_folder, "CXX"),
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = []
