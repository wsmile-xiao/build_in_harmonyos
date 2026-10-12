from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout
import os


class SymfpuConan(ConanFile):
    name = "symfpu"
    version = "0.0-git20190517.8fbe139"
    description = "SymFPU IEEE-754 floating-point algorithms over bit-vector backends"
    homepage = "https://github.com/martin-cs/symfpu"
    url = "https://github.com/martin-cs/symfpu"
    license = "BSD-3-Clause"
    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # This upstream snapshot has no build system or test suite.
        # The test_package compiles and runs a concrete backend consumer.

    def package(self):
        include = os.path.join(self.package_folder, "include", "symfpu")
        copy(self, "*.h", src=os.path.join(self.source_folder, "core"),
             dst=os.path.join(include, "core"))
        copy(self, "*.h", src=os.path.join(self.source_folder, "utils"),
             dst=os.path.join(include, "utils"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "symfpu")
        self.cpp_info.set_property("cmake_target_name", "symfpu::symfpu")