#!/usr/bin/env python3
"""Conan recipe for libosmosdr (OsmoSDR userspace driver library).

Cross-compiles the upstream CMake build for OpenHarmony PC (aarch64) and
applies the portability patch that adds libusb return-value checks, so that
processes running without a usable USB stack report "no devices" instead of
dereferencing an uninitialised libusb context.
"""

import os
import re

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get, load, rm, save)


class LibosmosdrConan(ConanFile):
    name = "libosmosdr"
    version = "0.1.8.effcaa7"
    description = ("OsmoSDR userspace driver library for the OsmoSDR, E4000, "
                   "FC0012 and FC0013 based USB DVB-T receivers")
    license = "GPL-2.0-or-later"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    homepage = "https://osmocom.org/projects/sdr/wiki/Libosmosdr"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libusb/1.0.27")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Upstream still declares cmake_minimum_required(VERSION 2.6) and CMake >= 4
        # rejects every policy floor below 3.5. Raise the floor through the documented
        # escape hatch rather than carrying a patch for a one line version bump.
        # Older CMake simply ignores the unused cache entry.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()
        CMakeDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        cmake = CMake(self)
        cmake.install()
        self._keep_requested_linkage()
        self._drop_build_host_paths_from_pkgconfig()

    def package_info(self):
        self.cpp_info.libs = ["osmosdr"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("pkg_config_name", "libosmosdr")

    def _keep_requested_linkage(self):
        # Upstream's CMakeLists installs both osmosdr_shared and osmosdr_static under
        # the same base name. Keep only the variant selected by the `shared` option,
        # otherwise `-losmosdr` may silently resolve to the other one.
        libdir = os.path.join(self.package_folder, "lib")
        if self.options.shared:
            rm(self, "libosmosdr.a", libdir)
        else:
            rm(self, "libosmosdr.so*", libdir)

    def _drop_build_host_paths_from_pkgconfig(self):
        # Upstream already strips the cross-compile include path from libosmosdr.pc,
        # but guards it with `IF(CMAKE_CROSSCOMPILING)`. That flag is false for this
        # native OHOS build, so the conan cache include directory would be baked into
        # the installed .pc and be meaningless on a consumer machine. Drop the absolute
        # -I entries, keeping only the relocatable ${includedir} one.
        pc = os.path.join(self.package_folder, "lib", "pkgconfig", "libosmosdr.pc")
        if not os.path.isfile(pc):
            return
        cleaned = []
        for line in load(self, pc).splitlines():
            if line.startswith("Cflags"):
                line = re.sub(r"\s+-I/[^\s]+", "", line)
            cleaned.append(line)
        save(self, pc, "\n".join(cleaned) + "\n")
