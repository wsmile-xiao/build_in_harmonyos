import os

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches
from conan.tools.layout import basic_layout


class AsyncFutureConan(ConanFile):
    name = "asyncfuture"
    version = "0.4.1"
    description = "Qt-based futures and promises library"
    homepage = "https://github.com/benlau/asyncfuture"
    license = "Apache-2.0"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qt5-qtbase/5.15.2.2")
        self.requires("qt5-qtdeclarative/5.15.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"])

    def build(self):
        # Upstream tests require the unavailable QPM vendor package. The
        # installed header-only package is validated by test_package instead.
        pass

    def package(self):
        copy(self, "asyncfuture.h", self.source_folder,
             os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "asyncfuture")
        self.cpp_info.set_property("cmake_target_name", "asyncfuture::asyncfuture")
