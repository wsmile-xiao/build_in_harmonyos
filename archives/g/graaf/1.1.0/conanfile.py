#!/usr/bin/env python3
"""Conan recipe — graaf 1.1.0 (CMake header-only C++20 graph library).

Header-only C++20 graph library (directed/undirected/weighted graphs with
algorithms: BFS/DFS, shortest paths, MST, coloring, clique detection, ...).

Upstream has NO install rules in its CMakeLists (only examples/test/perf
subdirectories), so packaging is done by copying the include/ tree.
Consumers include <graaflib/...> headers directly.

OHOS adaptation: upstream uses std::ranges algorithms (max_element/min_element/
count_if) that the OHOS libc++ (libcxx-ohos, llvm 15 based) does not provide;
patches replace them with the equivalent std:: algorithm calls. The Welsh-Powell
greedy coloring is made deterministic (lowest unused color search independent of
unordered container iteration order), which also fixes a latent incorrectness
where the same color could be assigned to adjacent vertices depending on
neighbor iteration order.
"""
from conan import ConanFile
from conan.tools.cmake import cmake_layout
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.build import cross_building

import os

from conan.errors import ConanInvalidConfiguration


class GraafConan(ConanFile):
    name = "graaf"
    version = "1.1.0"
    description = "A light-weight C++20 graph library"
    license = "MIT"
    homepage = "https://github.com/bobluppes/graaf"
    url = ""  # CI fills this
    topics = ("graph", "graph-algorithms", "header-only", "cpp20")

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # Header-only library: nothing to compile or link.
        pass

    def package(self):
        copy(self, "*.h",
             src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "*.tpp",
             src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE*",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # Header-only: no libraries, no bin dirs
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "graaf")
        self.cpp_info.set_property("cmake_target_name", "graaf::graaf")
        self.cpp_info.set_property("pkg_config_name", "graaf")