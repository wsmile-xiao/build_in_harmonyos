#!/usr/bin/env python3
"""Conan recipe for c-sig 3.8 — libsigc++ 3.8.0.

Package "c-sig" carries upstream libsigc++ 3.8.0 (typesafe callback system
for standard C++).  The built artefacts keep upstream names: shared/static
library libsigc-3.0, headers under include/sigc++-3.0, config header under
lib/sigc++-3.0/include, pkg-config name sigc++-3.0.

libsigc++ 3.8.0 ships Autotools, Meson and CMake build files in parallel;
this recipe uses CMake (same choice as conan-center libsigcpp/3.x.x).

Upstream ships 42 unit tests (tests/test_*.cc) registered with ctest; they
are built and run via cmake.test() whenever the target can run binaries.
"""

import os

from conan import ConanFile
from conan.tools.build import can_run, check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rmdir,
)


class CSigConan(ConanFile):
    name = "c-sig"
    version = "3.8"
    description = "libsigc++ implements a typesafe callback system (signals/slots) for standard C++"
    license = "LGPL-3.0-only"
    homepage = "https://github.com/libsigcplusplus/libsigcplusplus"
    url = "https://github.com/libsigcplusplus/libsigcplusplus"
    topics = ("signal", "slot", "callback", "libsigc++", "c++")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}
    implements = ["auto_shared_fpic"]

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def validate(self):
        check_min_cppstd(self, 17)

    def source(self):
        get(
            self,
            **self.conan_data["sources"],
            destination=self.source_folder,
            strip_root=True,
        )
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: system-name libraries default to static; let patch 0001's
        # add_library() (no SHARED hardcode) pick this up.
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if can_run(self):
            cmake.test()
        else:
            self.output.info(
                "cross-building: 42 upstream tests compiled but cannot run"
            )

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        # Conan CMakeDeps/PkgConfigDeps generate these from cpp_info
        # properties; upstream-generated files would shadow them.
        for dirname in ("cmake", "pkgconfig"):
            rmdir(self, os.path.join(self.package_folder, "lib", dirname))

    def package_info(self):
        self.cpp_info.libs = ["sigc-3.0"]
        # Headers: include/sigc++-3.0/sigc++/*.h plus the generated
        # sigc++config.h under lib/sigc++-3.0/include (upstream layout).
        self.cpp_info.includedirs = [
            os.path.join("include", "sigc++-3.0"),
            os.path.join("lib", "sigc++-3.0", "include"),
        ]
        self.cpp_info.set_property("cmake_file_name", "sigc++-3")
        self.cpp_info.set_property("cmake_target_name", "sigc-3.0")
        self.cpp_info.set_property("pkg_config_name", "sigc++-3.0")
        if not self.options.shared:
            self.cpp_info.defines = ["LIBSIGCXX_STATIC"]
