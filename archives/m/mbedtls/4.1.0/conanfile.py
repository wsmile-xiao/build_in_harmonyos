from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, export_conandata_patches, apply_conandata_patches, rmdir
import os


class MbedtlsConan(ConanFile):
    name = "mbedtls"
    version = "4.1.0"
    description = "mbedTLS is an open source and commercial SSL/TLS library by Arm"
    license = "Apache-2.0"
    homepage = "https://github.com/Mbed-TLS/mbedtls"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
    }
    default_options = {
        "shared": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["ENABLE_PROGRAMS"] = False
        tc.variables["ENABLE_TESTING"] = False
        tc.variables["MBEDTLS_FATAL_WARNINGS"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["mbedtls", "mbedx509", "tfpsacrypto"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
