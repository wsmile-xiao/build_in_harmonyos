#!/usr/bin/env python3
"""Conan recipe — gemmlowp 0.8.7

gemmlowp: Google low-precision integer matrix multiplication library
(Apache-2.0). Header-only C++11 library plus one compiled source
(eight_bit_int_gemm/eight_bit_int_gemm.cc). Upstream official build
system is Bazel; the CMakeLists.txt shipped in contrib/ (written for
Debian) builds the static eight_bit_int_gemm library and installs all
public headers under include/gemmlowp/, plus a gemmlowp INTERFACE
target and a find_package(gemmlowp CONFIG) export.

This recipe follows the conan-center-index approach: configure with
the contrib/ CMake build script folder, BUILD_TESTING=OFF for the
package build (upstream tests are run separately in W3 and the
ohos-specific test), install via cmake.install().

R26: system-name libraries default to static.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class GemmlowpConan(ConanFile):
    name = "gemmlowp"
    version = "0.8.7"
    description = "Google low-precision integer matrix multiplication (GEMM) library"
    license = "Apache-2.0"
    homepage = "https://github.com/google/gemmlowp"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def validate(self):
        # R32: settings.os check must be in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"gemmlowp/{self.version} is only supported on Linux/OHOS, "
                f"not {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Upstream contrib/CMakeLists.txt sets BUILD_TESTING via include(CTest);
        # disable it for the package build (tests run separately in W3).
        tc.variables["BUILD_TESTING"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # The CMake build entry is contrib/CMakeLists.txt (Debian-written),
        # while headers live at the repository root.
        cmake.configure(build_script_folder=os.path.join(self.source_folder, "contrib"))
        cmake.build()

    def package(self):
        copy(self, "LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        # Remove the cmake export dir (config files regenerated per-package);
        # keep the installed headers + library.
        self.run(f"rm -rf {os.path.join(self.package_folder, 'lib', 'cmake')}")

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "gemmlowp")
        self.cpp_info.set_property("cmake_target_name", "gemmlowp::gemmlowp")

        # Header-only INTERFACE component for the public headers.
        self.cpp_info.components["gemmlowp"].set_property("cmake_target_name", "gemmlowp::gemmlowp")
        self.cpp_info.components["gemmlowp"].includedirs = [
            os.path.join("include", "gemmlowp")]
        self.cpp_info.components["gemmlowp"].requires = ["eight_bit_int_gemm"]

        # The only compiled artifact: eight_bit_int_gemm (legacy interface).
        self.cpp_info.components["eight_bit_int_gemm"].set_property(
            "cmake_target_name", "gemmlowp::eight_bit_int_gemm")
        self.cpp_info.components["eight_bit_int_gemm"].includedirs = [
            os.path.join("include", "gemmlowp")]
        self.cpp_info.components["eight_bit_int_gemm"].libs = ["eight_bit_int_gemm"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.components["eight_bit_int_gemm"].system_libs.append("pthread")
