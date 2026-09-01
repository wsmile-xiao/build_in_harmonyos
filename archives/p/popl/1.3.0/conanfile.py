#!/usr/bin/env python3
import os

from conan import ConanFile
from conan.tools.files import copy, get


class PoplConan(ConanFile):
    name = "popl"
    version = "1.3.0"
    description = "Header-only C++ program options parser library"
    license = "MIT"
    homepage = "https://github.com/badaix/popl"
    url = ""
    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    def package_id(self):
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def package(self):
        copy(self, "popl.hpp", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "popl")
        self.cpp_info.set_property("cmake_target_name", "popl::popl")
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
