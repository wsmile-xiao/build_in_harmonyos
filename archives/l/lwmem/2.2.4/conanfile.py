#!/usr/bin/env python3
"""Conan recipe — lwmem 2.2.4 (lightweight dynamic memory manager, MIT).

Upstream is a CMake library: the root CMakeLists only builds the test suite
when configured as top-level project, and adds the library via
`add_subdirectory(lwmem)` otherwise. `lwmem/CMakeLists.txt` includes
`library.cmake` which registers two targets: `lwmem` (C core) and
`lwmem_cpp` (C++ extension). The upstream test suite hard-codes the win32
system port (`LWMEM_SYS_PORT "win32"` + `#include "windows.h"` in every
test's lwmem_opts.h) — not usable on OHOS; the recipe therefore builds the
library directory itself with the default (OS=0, no system port) options,
which is the portable embedded configuration.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class LwmemConan(ConanFile):
    name = "lwmem"
    version = "2.2.4"
    description = "Lightweight dynamic memory manager optimized for embedded systems (MIT)"
    license = "MIT"
    homepage = "https://github.com/MaJerle/lwmem"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("memory", "heap", "malloc", "embedded", "allocator")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("lwmem is supported only on Linux/OHOS")

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Build the library subdirectory directly: the top-level CMakeLists
        # only builds tests, the library targets live in lwmem/.
        cmake = CMake(self)
        cmake.configure(build_script_folder="lwmem")
        cmake.build()

    def package(self):
        # lwmem has no install rules; copy libs and headers manually.
        copy(self, "liblwmem*.a", self.build_folder,
             os.path.join(self.package_folder, "lib"))
        copy(self, "*.h", os.path.join(self.source_folder, "lwmem", "src", "include"),
             os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["lwmem_cpp", "lwmem"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "lwmem")
        self.cpp_info.set_property("cmake_target_name", "lwmem::lwmem")
