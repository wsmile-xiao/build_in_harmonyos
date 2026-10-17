#!/usr/bin/env python3
"""Conan recipe — bsd-compat-headers 0.7.2 (header-only).

BSD compatibility headers providing sys/cdefs.h, sys/queue.h, and
sys/tree.h for platforms that lack them (e.g. OHOS).
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class BsdCompatHeadersConan(ConanFile):
    name = "bsd-compat-headers"
    version = "0.7.2"
    package_type = "header-library"

    description = "BSD compatibility headers (cdefs, queue, tree) for OHOS"
    homepage = "https://github.com/NeonatoX/bsd-compat-headers"
    license = "BSD-3-Clause"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("bsd", "headers", "queue", "tree", "cdefs", "compatibility")

    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Header-only: verify expected files exist
        for header in ("cdefs.h", "queue.h", "tree.h"):
            path = os.path.join(self.source_folder, header)
            if not os.path.isfile(path):
                raise FileNotFoundError(f"Expected header not found: {path}")

    def package(self):
        # Install headers to include/sys/ so consumers use #include <sys/queue.h>
        sys_dir = os.path.join(self.package_folder, "include", "sys")
        copy(self, "cdefs.h", src=self.source_folder, dst=sys_dir)
        copy(self, "queue.h", src=self.source_folder, dst=sys_dir)
        copy(self, "tree.h", src=self.source_folder, dst=sys_dir)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "bsd-compat-headers")
        self.cpp_info.set_property("cmake_target_name", "bsd-compat-headers::bsd-compat-headers")
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
