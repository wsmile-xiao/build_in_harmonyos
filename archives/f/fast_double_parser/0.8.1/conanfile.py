from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class FastDoubleParserConan(ConanFile):
    name = "fast_double_parser"
    version = "0.8.1"
    description = "Fast double parser for C++"
    license = "Apache-2.0 OR BSL-1.0"
    homepage = "https://github.com/lemire/fast_double_parser"
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
        tc.variables["BUILD_TESTING"] = "ON" if can_run(self) else "OFF"
        tc.variables["FAST_DOUBLE_BENCHMARKS"] = "OFF"
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
            cmake.test()

    def package(self):
        CMake(self).install()
        copy(self, "LICENSE", dst="licenses", src=self.source_folder)
        copy(self, "LICENSE.BSL", dst="licenses", src=self.source_folder)

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.set_property("cmake_file_name", "fast_double_parser")
        self.cpp_info.set_property(
            "cmake_target_name", "fast_double_parser::fast_double_parser"
        )
        self.cpp_info.builddirs.append("share/fast_double_parser")
