import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class AlpacaConan(ConanFile):
    name = "alpaca"
    version = "0.2.1"
    description = "C++17 header-only serialization library"
    license = "MIT"
    homepage = "https://github.com/p-ranav/alpaca"
    url = ""
    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["ALPACA_BUILD_TESTS"] = "ON" if can_run(self) else "OFF"
        tc.variables["ALPACA_BUILD_BENCHMARKS"] = "OFF"
        tc.variables["ALPACA_BUILD_SAMPLES"] = "OFF"
        tc.variables["ALPACA_BUILD_PYTHON_LIB"] = "OFF"
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if can_run(self):
            test_binary = os.path.join(self.build_folder, "test", "tests")
            self.run(f'"{test_binary}"', cwd=self.build_folder)

    def package(self):
        CMake(self).install()
        # The upstream install rule omits include/alpaca/detail/types/*.h;
        # copy the complete public header tree for consumers.
        copy(self, "*.h", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"), keep_path=True)
        copy(self, "LICENSE", dst="licenses", src=self.source_folder)

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.set_property("cmake_file_name", "alpaca")
        self.cpp_info.set_property("cmake_target_name", "alpaca::alpaca")
        self.cpp_info.builddirs.append(os.path.join("lib", "cmake", "alpaca"))
