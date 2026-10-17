#!/usr/bin/env python3
"""Conan recipe — tinyfsm 0.3.3 (header-only C++11 FSM library)."""

import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class TinyfsmConan(ConanFile):
    name = "tinyfsm"
    version = "0.3.3"
    description = "TinyFSM is a simple finite state machine library for C++, designed for optimal performance and low memory footprint"
    license = "MIT"
    homepage = "https://digint.ch/tinyfsm"
    url = "https://github.com/digint/tinyfsm"
    topics = ("fsm", "state-machine", "c++", "header-only")

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # header-only: 无源码编译，直接打包头文件
        pass

    def package(self):
        copy(self, "tinyfsm.hpp",
             os.path.join(self.source_folder, "include"),
             os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # header-only: 无链接库，仅供 include
        self.cpp_info.libs = []
        self.cpp_info.set_property("cmake_target_name", "tinyfsm::tinyfsm")