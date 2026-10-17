from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get

import os
import shutil


class LibcpuidToolConan(ConanFile):
    name = "libcpuid-tool"
    version = "0.8.0"
    description = "cpuid_tool - command-line CPU identification utility based on libcpuid"
    license = "BSD-2-Clause"
    homepage = "https://github.com/anrieff/libcpuid"
    url = "https://github.com/anrieff/libcpuid"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libcpuid-tool is supported only on Linux/OHOS")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def generate(self):
        toolchain = CMakeToolchain(self)
        # E092: CMake has no OHOS/HarmonyOS platform module.  libcpuid's
        # CMakeLists gates getauxval/_GNU_SOURCE/SONAME generation on
        # CMAKE_SYSTEM_NAME STREQUAL "Linux" and UNIX, so force the Linux
        # platform branch exactly like the historical device adaptation.
        if self.settings.os in ("Linux", "OHOS"):
            toolchain.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            toolchain.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) == "armv8" else str(self.settings.arch)
            )
        # Link cpuid statically so cpuid_tool is a self-contained binary;
        # this package intentionally does not ship or conflict with the
        # published shared libcpuid package.
        toolchain.cache_variables["BUILD_SHARED_LIBS"] = "OFF"
        # The DKMS driver branch installs source files into the absolute
        # /usr/src prefix, which is neither writable nor wanted on OHOS.
        toolchain.cache_variables["LIBCPUID_BUILD_DRIVERS"] = "OFF"
        toolchain.cache_variables["LIBCPUID_ENABLE_DOCS"] = "OFF"
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Tool-only package: drop the library, headers and pkg-config files
        # installed by upstream's catch-all install rules.
        for leftover in ("lib", "include", "share"):
            shutil.rmtree(os.path.join(self.package_folder, leftover), ignore_errors=True)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
