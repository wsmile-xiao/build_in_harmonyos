#!/usr/bin/env python3
"""Conan recipe — midifile g20200602 (C++11 CMake static library).

Midifile (Craig Stuart Sapp, CCRMA) parses/creates Standard MIDI Files.
CMakeLists builds a static libmidifile + 32 demo CLI tools and has no
install rules; this recipe builds ONLY the library target and installs
headers + archive itself. Upstream CMake declares cmake_minimum_required
2.8 (rejected by CMake 4.x) → CMAKE_POLICY_VERSION_MINIMUM=3.5 (E103/E321
reuse). Upstream ships no test suite (verified: no tests/, no ctest
registration) — consumer read/write roundtrip covers verification (R51).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches


class MidifileConan(ConanFile):
    name = "midifile"
    version = "g20200602"
    description = "C++ library for parsing/creating Standard MIDI Files (CCRMA midifile)"
    license = "MIT"
    homepage = "https://github.com/craigsapp/midifile"
    url = "https://github.com/craigsapp/midifile"
    topics = ("midi", "music", "smf", "cpp11")

    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # upstream min-required 2.8 vs CMake 4.x (E103/E321)
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # only the library target; skip the 32 demo tools
        cmake.build(target="midifile")

    def package(self):
        copy(self, "*.h", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "*.a", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["midifile"]
        self.cpp_info.set_property("cmake_file_name", "midifile")
        self.cpp_info.set_property("cmake_target_name", "midifile::midifile")
