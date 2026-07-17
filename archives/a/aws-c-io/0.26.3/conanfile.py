import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, replace_in_file


class AwsCIoConan(ConanFile):
    name = "aws-c-io"
    version = "0.26.3"
    description = "AWS SDK for C asynchronous IO primitives"
    license = "Apache-2.0"
    homepage = "https://github.com/awslabs/aws-c-io"
    url = "https://github.com/awslabs/aws-c-io"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def requirements(self):
        self.requires("aws-c-common/0.12.6")
        self.requires("aws-c-cal/0.9.13")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(self.options.get_safe("fPIC", True))
        tc.variables["BYO_CRYPTO"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake_lists = os.path.join(self.source_folder, "CMakeLists.txt")
        replace_in_file(
            self,
            cmake_lists,
            'elseif (CMAKE_SYSTEM_NAME STREQUAL "Linux" OR CMAKE_SYSTEM_NAME STREQUAL "Android")',
            'elseif (CMAKE_SYSTEM_NAME STREQUAL "Linux" OR CMAKE_SYSTEM_NAME STREQUAL "Android" OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS" OR CMAKE_SYSTEM_NAME STREQUAL "OHOS")',
        )
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        config = os.path.join(self.package_folder, "lib", "cmake", "aws-c-io", "aws-c-io-config.cmake")
        if os.path.exists(config):
            replace_in_file(
                self,
                config,
                '''if (UNIX AND NOT APPLE AND NOT BYO_CRYPTO)
    find_dependency(s2n)
endif()

''',
                '',
            )


    def package_info(self):
        self.cpp_info.libs = ['aws-c-io']
        self.cpp_info.set_property("cmake_file_name", "aws-c-io")
        self.cpp_info.set_property("cmake_target_name", "AWS::aws-c-io")
