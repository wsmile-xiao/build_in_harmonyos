#!/usr/bin/env python3
"""Conan recipe for tmux-mem-cpu-load — a CPU, RAM, and load monitor for tmux."""

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class TmuxMemCpuLoadConan(ConanFile):
    name = "tmux-mem-cpu-load"
    version = "3.8.3"
    description = "CPU, RAM, and load monitor for use with tmux"
    license = "Apache-2.0"
    homepage = "https://github.com/thewtex/tmux-mem-cpu-load"
    url = "https://github.com/thewtex/tmux-mem-cpu-load"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []