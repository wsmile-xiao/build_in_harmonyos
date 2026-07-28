from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class ParchiveConan(ConanFile):
    name = "parchive"
    version = "1.1"
    description = "Command-line utility for creating and checking PAR archives"
    license = "GPL-2.0-only"
    url = "https://parchive.sourceforge.net/"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os != "OHOS" or self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("parchive is packaged for OHOS armv8 only")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        AutotoolsToolchain(self).generate()

    def build(self):
        self.run("make", cwd=self.source_folder, env="conanbuild")

    def package(self):
        copy(self, "par", src=self.source_folder, dst=self.package_folder + "/bin")
        copy(self, "COPYING", src=self.source_folder, dst=self.package_folder + "/licenses")

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
