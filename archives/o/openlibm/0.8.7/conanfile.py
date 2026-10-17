#!/usr/bin/env python3
"""Conan recipe for openlibm 0.8.7 — Makefile-based build system."""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class OpenlibmConan(ConanFile):
    name = "openlibm"
    version = "0.8.7"
    description = "High quality system independent, portable, open source libm implementation"
    license = "MIT"
    homepage = "https://github.com/JuliaMath/openlibm"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        src = self.conan_data["sources"]
        try:
            get(self, **src, strip_root=True)
        except Exception:
            url = src["url"]
            if isinstance(url, list):
                url = url[0]
            mirror_url = "https://gh-proxy.com/" + url
            get(self, url=mirror_url, sha256=src["sha256"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        if self.options.shared:
            self.run("make USECLANG=1 -j1", cwd=self.source_folder)
        else:
            self.run("make USECLANG=1 libopenlibm.a -j1", cwd=self.source_folder)

    def package(self):
        if self.options.shared:
            self.run(f"make USECLANG=1 install DESTDIR={self.package_folder} prefix=",
                     cwd=self.source_folder)
        else:
            self.run(f"make USECLANG=1 install-static install-headers install-pkgconfig "
                     f"DESTDIR={self.package_folder} prefix=",
                     cwd=self.source_folder)

    def package_info(self):
        self.cpp_info.libs = ["openlibm"]
        self.cpp_info.includedirs = ["include/openlibm"]
        self.cpp_info.set_property("cmake_file_name", "openlibm")
        self.cpp_info.set_property("cmake_target_name", "openlibm::openlibm")
