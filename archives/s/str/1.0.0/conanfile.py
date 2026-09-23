from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.cmake import CMakeToolchain, cmake_layout
import os


class StrConan(ConanFile):
    name = "str"
    version = "1.0.0"
    description = "Single-header string library for microcontrollers"
    license = "AGPL-3.0-or-later"
    homepage = "https://github.com/cesanta/str"
    url = ""
    topics = ("c", "string", "json", "header-only", "microcontroller")

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()

    def package(self):
        copy(self, "str.h", dst=os.path.join(self.package_folder, "include"), src=self.source_folder)
        copy(self, "LICENSE", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "str")
        self.cpp_info.set_property("cmake_target_name", "str::str")
        self.cpp_info.libs = []
