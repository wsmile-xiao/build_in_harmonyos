import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, replace_in_file


class AwsCCalConan(ConanFile):
    name = "aws-c-cal"
    version = "0.9.13"
    description = "AWS SDK for C cryptographic abstraction layer"
    license = "Apache-2.0"
    homepage = "https://github.com/awslabs/aws-c-cal"
    url = "https://github.com/awslabs/aws-c-cal"
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
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        config = os.path.join(self.package_folder, "lib", "cmake", "aws-c-cal", "aws-c-cal-config.cmake")
        if os.path.exists(config):
            replace_in_file(
                self,
                config,
                'if ((NOT WIN32 AND NOT APPLE) OR AWS_USE_LIBCRYPTO_TO_SUPPORT_ED25519_EVERYWHERE)
    if (USE_OPENSSL)
        find_dependency(OpenSSL REQUIRED)
        find_dependency(Threads REQUIRED)
    else()
        find_dependency(crypto)
    endif()
endif()
',
                '',
            )


    def package_info(self):
        self.cpp_info.libs = ['aws-c-cal']
        self.cpp_info.set_property("cmake_file_name", "aws-c-cal")
        self.cpp_info.set_property("cmake_target_name", "AWS::aws-c-cal")
