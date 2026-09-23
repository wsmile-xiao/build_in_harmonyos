from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches
import os

class ZpaqfranzConan(ConanFile):
    name = "zpaqfranz"
    version = "63.3"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml", "patches/*.patch"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        self.run("make -f NONWINDOWS/Makefile -j1")

    def package(self):
        copy(self, "zpaqfranz", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
