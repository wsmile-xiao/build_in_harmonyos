import os
from conan import ConanFile
from conan.tools.files import get
from conan.tools.layout import basic_layout

class ZsignConan(ConanFile):
    name = "zsign"
    version = "1.0.4"
    description = "Cross-platform iOS code signing tool"
    homepage = "https://github.com/zhlynn/zsign"
    license = "MIT"

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires("openssl/3.3.0")
        self.requires("minizip-ng/4.0.7")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        self.run("make -j$(nproc)")

    def package(self):
        self.run(f"mkdir -p {self.package_folder}/bin")
        self.run(f"cp zsign {self.package_folder}/bin/")

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
