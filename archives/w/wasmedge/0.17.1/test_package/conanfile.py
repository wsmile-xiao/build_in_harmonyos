import os

from conan import ConanFile


class WasmEdgeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["wasmedge"]
        header = os.path.join(dep.package_folder, "include", "wasmedge", "wasmedge.h")
        library_dir = os.path.join(dep.package_folder, "lib")
        if not os.path.exists(header):
            raise Exception("wasmedge public C API header was not packaged")
        if not os.path.isdir(library_dir):
            raise Exception("wasmedge library directory was not packaged")
