#!/usr/bin/env python3
"""Conan recipe — tsl-hat-trie 0.6.0 (header-only).

HAT-trie: C++11 header-only set/map of strings with prefix search.
Zero runtime dependencies; the only build step is copying headers.
"""
from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout
import os

required_conan_version = ">=2.0"


class TslHatTrieConan(ConanFile):
    name = "tsl-hat-trie"
    version = "0.6.0"
    package_type = "header-library"

    description = "HAT-trie C++ implementation - header-only set/map of strings with prefix search"
    homepage = "https://github.com/Tessil/hat-trie"
    license = "MIT"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"

    exports_sources = "patches/*"

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def package(self):
        # copy() preserves the relative directory structure from src,
        # so dst must be package_folder itself (matches aixlog reference).
        copy(self, "include/tsl/*.h", src=self.source_folder, dst=self.package_folder)
        copy(self, "include/tsl/array-hash/*.h", src=self.source_folder, dst=self.package_folder)
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "tsl_hat_trie")
        self.cpp_info.set_property("cmake_target_name", "tsl::hat_trie")
        self.cpp_info.includedirs = ["include"]
