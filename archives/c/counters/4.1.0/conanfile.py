from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, get
import os


class CountersConan(ConanFile):
    name = "counters"
    version = "4.1.0"
    description = "C++ performance counters and benchmarking utilities"
    license = "MIT"
    homepage = "https://github.com/lemire/counters"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    exports_sources = "conandata.yml", "patches/*"

    def export_sources(self):
        copy(self, "conandata.yml", dst=".", src=self.recipe_folder)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["COUNTERS_INSTALL"] = True
        tc.variables["COUNTERS_BUILD_TESTS"] = True
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", dst=os.path.join(self.package_folder, "licenses"),
             src=self.source_folder)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Counters")
        self.cpp_info.set_property("cmake_target_name", "Counters::counters")
