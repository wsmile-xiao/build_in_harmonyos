import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, load, replace_in_file


def _replace_if_needed(conanfile, path, old, new):
    content = load(conanfile, path)
    if old not in content:
        return
    replace_in_file(conanfile, path, old, new)


class AwsCCommonConan(ConanFile):
    name = "aws-c-common"
    version = "0.12.6"
    description = "AWS SDK for C core primitives and platform abstraction"
    license = "Apache-2.0"
    homepage = "https://github.com/awslabs/aws-c-common"
    url = "https://github.com/awslabs/aws-c-common"
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
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        cmake_lists = os.path.join(self.source_folder, "CMakeLists.txt")
        _replace_if_needed(
            self,
            cmake_lists,
            'project(aws-c-common LANGUAGES C VERSION 0.1.0)',
            '''project(aws-c-common LANGUAGES C VERSION 0.1.0)
find_package(Threads REQUIRED)
if(NOT TARGET Threads::Threads)
    add_library(Threads::Threads INTERFACE IMPORTED)
endif()''',
        )
        _replace_if_needed(
            self,
            cmake_lists,
            'elseif (${CMAKE_SYSTEM_NAME} STREQUAL "Linux")',
            'elseif (${CMAKE_SYSTEM_NAME} STREQUAL "Linux" OR ${CMAKE_SYSTEM_NAME} STREQUAL "HarmonyOS" OR ${CMAKE_SYSTEM_NAME} STREQUAL "OHOS")',
        )
        _replace_if_needed(
            self,
            cmake_lists,
            'if (UNIX AND NOT APPLE AND NOT ${CMAKE_SYSTEM_NAME} MATCHES FreeBSD|OpenBSD)',
            'if ((UNIX OR ${CMAKE_SYSTEM_NAME} STREQUAL "HarmonyOS" OR ${CMAKE_SYSTEM_NAME} STREQUAL "OHOS") AND NOT APPLE AND NOT ${CMAKE_SYSTEM_NAME} MATCHES FreeBSD|OpenBSD)',
        )

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(self.options.get_safe("fPIC", True))
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


    def package_info(self):
        self.cpp_info.libs = ['aws-c-common']
        self.cpp_info.builddirs = ["lib/cmake", "lib/cmake/aws-c-common", "lib/cmake/aws-c-common/modules"]
        self.cpp_info.set_property("cmake_file_name", "aws-c-common")
        self.cpp_info.set_property("cmake_target_name", "AWS::aws-c-common")
