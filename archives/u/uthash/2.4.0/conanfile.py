import os

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class UthashConan(ConanFile):
    name = "uthash"
    version = "2.4.0"
    description = "Hash table and linked list implementation for C structures (header-only)"
    license = "BSD-1-Clause"
    homepage = "https://github.com/troydhanson/uthash"
    url = "https://github.com/troydhanson/uthash"

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        copy(self, "*.h", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = []
