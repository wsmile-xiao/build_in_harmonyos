#!/usr/bin/env python3
"""Conan recipe — dumb 2.0.3

DUMB (Dynamic Universal Music Bibliotheque) is a tracker music module
library: pure-C decoding/rendering for IT/XM/S3M/MOD and a dozen more
module formats, plus resampling/LPC helpers and a dumbfile I/O
abstraction. The recipe builds the upstream CMake target with the
platform-irrelevant extras off:
- BUILD_EXAMPLES=OFF (dumbout/dumbplay need argtable2 + SDL2 audio)
- BUILD_ALLEGRO4=OFF (Allegro4 dat bindings; Allegro is not ported)
- USE_SSE=OFF (x86-only; on aarch64 upstream's own check would skip it,
  we make it explicit)
Result: libdumb shared+static with a small res/ set of self-written
module fixtures for the consumer test (no test data ships upstream).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, copy, replace_in_file


class DumbConan(ConanFile):
    name = "dumb"
    version = "2.0.3"
    description = "Tracker music module library (IT/XM/S3M/MOD etc., pure C)"
    license = "Zlib"  # dual-licensed: Zlib OR FreeType; Zlib declared
    homepage = "https://github.com/kode54/dumb"
    url = "https://github.com/kode54/dumb"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "fPIC": [True, False],
        "shared": [True, False],
    }
    default_options = {
        "fPIC": True,
        "shared": True,
    }

    implements = ["auto_shared_fpic"]

    exports_sources = "patches/*"

    def layout(self):
        cmake_layout(self)

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R33: flags/toolchain come from the Conan toolchain.
        tc = CMakeToolchain(self)
        tc.variables["BUILD_EXAMPLES"] = False
        tc.variables["BUILD_ALLEGRO4"] = False
        tc.variables["USE_SSE"] = False
        tc.generate()

    def build(self):
        # upstream declares cmake_minimum_required(3.1); CMake 4.x refuses
        # <3.5 — the standard compatibility shim. Must be an environment
        # variable (or -D on the command line): anything set inside the
        # toolchain only takes effect at project(), after
        # cmake_minimum_required has already failed to parse.
        cmake = CMake(self)
        # CMake.configure() takes no env kwarg in this conan release —
        # push the shim through the build environment instead.
        from conan.tools.env import Environment
        shimen = Environment()
        shimen.define("CMAKE_POLICY_VERSION_MINIMUM", "3.5")
        with shimen.vars(self).apply():
            cmake.configure()
            cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "dumb")
        self.cpp_info.set_property("cmake_target_name", "dumb::dumb")
        self.cpp_info.set_property("pkg_config_name", "dumb")
        self.cpp_info.libs = ["dumb"]
        self.cpp_info.includedirs = ["include"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
