#!/usr/bin/env python3
"""Conan recipe for metalang99 1.13.5 on HarmonyOS PC.

metalang99 is a full-blown C99 preprocessor metaprogramming library
(header-only, zero dependencies). It provides compile-time lists,
tuples, naturals, either/maybe/choice, control flow, and a lazy
functional macro evaluation engine.

Upstream ships a formal CMake test suite (tests/CMakeLists.txt builds
18 test executables whose bodies are _Static_assert checks — a
successful build *is* a passing test, matching upstream's own
scripts/test.sh contract). These are compiled in test_package for
real (R34/L0c/L1).
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class Metalang99Conan(ConanFile):
    name = "metalang99"
    version = "1.13.5"
    package_type = "header-library"
    license = "MIT"
    homepage = "https://github.com/hirrolot/metalang99"
    url = "https://github.com/hirrolot/metalang99"
    description = (
        "Full-blown C99 preprocessor metaprogramming library "
        "(header-only, zero dependencies)"
    )
    topics = ("metaprogramming", "preprocessor", "c99", "header-only")

    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version],
            strip_root=True)

    def build(self):
        # header-only：no compilation (tests run in test_package)
        pass

    def package(self):
        copy(self, "*",
             src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"),
             keep_path=True)
        copy(self, "LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libs = []
