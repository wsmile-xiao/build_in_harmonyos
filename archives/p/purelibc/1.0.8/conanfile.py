#!/usr/bin/env python3
"""Conan recipe — purelibc 1.0.8 (glibc overlay library for syscall capture).

purelibc converts libc from a libc+system interfacing library into a libc-only
library: after `_pure_start(pure_syscall, flags)` the libc system calls issued
by the process are routed to the user-supplied `pure_syscall` handler, enabling
process self-virtualization (umview/VirtualSquare style). Upstream builds one
shared library from five C sources and ships no test suite, so the consumer
tests in test_package/ carry the verification (real API calls, assertions,
run on device).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class PurelibcConan(ConanFile):
    name = "purelibc"
    version = "1.0.8"
    description = "glibc overlay library for process self-virtualization (syscall capture)"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/virtualsquare/purelibc"
    url = ""  # CI fills this
    topics = ("syscall", "virtualization", "libc", "overlay")

    package_type = "shared-library"
    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: OHOS must be matched alongside Linux, never `== "Linux"`.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"purelibc not validated for {self.settings.os}"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        CMakeToolchain(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Upstream ships no test suite (N_static = 0): the tarball has no test
        # directory and CMakeLists.txt registers no test target, so there is
        # nothing to run here. Verification is carried by the test_package
        # consumer programs, which exercise the real capture API.

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["purelibc"]
