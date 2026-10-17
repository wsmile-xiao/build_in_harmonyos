#!/usr/bin/env python3
"""Conan recipe for the AOSP libldac snapshot from 2025-01-10."""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class LibldacConan(ConanFile):
    name = "libldac"
    version = "aosp-20250110"
    description = "AOSP implementation of the Sony LDAC Bluetooth encoder and ABR controller"
    license = "Apache-2.0"
    homepage = "https://android.googlesource.com/platform/external/libldac"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libldac is supported on Linux and OHOS")
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        source = self.conan_data["sources"]
        destination = os.path.join(self.source_folder, "upstream")
        try:
            get(
                self,
                url=source["url"],
                sha256=source["sha256"],
                destination=destination,
                strip_root=False,
                retry=0,
            )
        except ConanException:
            self.output.warning("Official AOSP archive unavailable; using the pinned read-only mirror")
            get(
                self,
                url=source["mirror_url"],
                sha256=source["mirror_sha256"],
                destination=destination,
                strip_root=True,
            )

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        toolchain.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = self.options.get_safe("fPIC", True)
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(build_script_folder=os.path.join(self.source_folder, "upstream"))
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "NOTICE",
            src=os.path.join(self.source_folder, "upstream"),
            dst=os.path.join(self.package_folder, "licenses"),
        )
        copy(
            self,
            "MODULE_LICENSE_APACHE2",
            src=os.path.join(self.source_folder, "upstream"),
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["ldacBT_abr", "ldacBT_enc"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
