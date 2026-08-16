import os
from conan import ConanFile
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class NanopbConan(ConanFile):
    name = "nanopb"
    version = "0.4.9.1"
    description = "Protocol Buffers with small code size"
    license = "Zlib"
    homepage = "https://github.com/nanopb/nanopb"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_generator": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_generator": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["BUILD_STATIC_LIBS"] = not bool(self.options.shared)
        tc.variables["nanopb_BUILD_RUNTIME"] = True
        tc.variables["nanopb_BUILD_GENERATOR"] = bool(self.options.with_generator)
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(self.options.get_safe("fPIC", True))
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["protobuf-nanopb"]
        self.cpp_info.includedirs = ["include/nanopb"]
        self.cpp_info.set_property("cmake_file_name", "nanopb")
        self.cpp_info.set_property("cmake_target_name", "nanopb::nanopb")
        self.cpp_info.set_property("pkg_config_name", "nanopb")
