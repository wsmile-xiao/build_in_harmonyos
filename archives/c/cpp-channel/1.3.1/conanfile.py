#!/usr/bin/env python3
"""Conan recipe — cpp-channel 1.3.1 (header-only C++11 library).

msd::channel is a thread-safe channel implementation distributed as
header-only sources (include/msd/*.hpp). The upstream CMake project builds
an INTERFACE library (msd_channel) with no compiled artifacts, so the
recipe only stages the headers and license (header-only variant A).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class CppchannelConan(ConanFile):
    name = "cpp-channel"
    version = "1.3.1"
    description = "Thread-safe channel implementation for C++11 (header-only)"
    license = "MIT"
    homepage = "https://github.com/andreiavrammsd/cpp-channel"
    url = ""  # CI fills this

    package_type = "header-library"

    # Header-only: settings kept for structural consistency only.
    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # Header-only: no compiled artifacts, so build() stays empty except for
    # conandata patch application (no-op when patches are empty). R34:
    # real consumer-side verification happens in test_package instead of
    # fabricating build logs.
    def build(self):
        apply_conandata_patches(self)

    def package(self):
        # Use explicit absolute destinations under package_folder: relative
        # "dst=" values resolve against the layout in a way that can place
        # headers under a wrong nested path with basic_layout.
        inc_dir = os.path.join(self.package_folder, "include")
        copy(self, "*.h", src=os.path.join(self.source_folder, "include"),
             dst=inc_dir)
        copy(self, "*.hpp", src=os.path.join(self.source_folder, "include"),
             dst=inc_dir)
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        self.info.clear()          # header-only: single package_id

    def package_info(self):
        # Header-only: headers on include path, no lib/bin dirs.
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
