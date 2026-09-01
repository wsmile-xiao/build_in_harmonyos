#!/usr/bin/env python3
"""Conan recipe — tinyobjloader 2.0.0rc13 (header-only/custom)."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get


class TinyObjLoaderConan(ConanFile):
    name = "tinyobjloader"
    version = "2.0.0rc13"
    description = "Tiny but powerful single file wavefront obj loader (C++03, STL only)"
    license = "MIT"
    homepage = "https://github.com/tinyobjloader/tinyobjloader"
    url = "https://github.com/tinyobjloader/tinyobjloader"
    topics = ("obj", "loader", "header-only", "3d", "mesh")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [False]}
    default_options = {"shared": False}

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def package(self):
        import conan.tools.files as _f
        _f.copy(self, "tiny_obj_loader.h", src=self.source_folder,
                dst=os.path.join(self.package_folder, "include"))
        _f.copy(self, "LICENSE", src=self.source_folder,
                dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "tinyobjloader")
        self.cpp_info.set_property(
            "cmake_target_name", "tinyobjloader::tinyobjloader"
        )

    def validate(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "tinyobjloader 2.0.0rc13 currently supports only OHOS armv8"
            )

    def package_id(self):
        self.info.clear()
