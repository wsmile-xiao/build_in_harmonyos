#!/usr/bin/env python3
"""Conan recipe for openFPGALoader 1.1.1."""
import hashlib
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    load,
)
from conan.tools.gnu import PkgConfigDeps


class OpenfpgaloaderConan(ConanFile):
    name = "openfpgaloader"
    version = "1.1.1"
    description = "Universal command-line FPGA programmer"
    # Verified from the pinned v1.1.1 source archive's root LICENSE file.
    license = "Apache-2.0"
    homepage = "https://github.com/trabucayre/openFPGALoader"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    _license_sha256 = (
        "c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4"
    )

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("openFPGALoader requires a POSIX platform")

    def requirements(self):
        self.requires("zlib/1.3.1")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        license_path = os.path.join(self.source_folder, "LICENSE")
        with open(license_path, "rb") as license_file:
            license_sha256 = hashlib.sha256(license_file.read()).hexdigest()
        if license_sha256 != self._license_sha256:
            raise ConanInvalidConfiguration(
                "Pinned openFPGALoader v1.1.1 LICENSE checksum does not match "
                "the official tag"
            )
        license_text = load(self, license_path)
        if "Apache License" not in license_text or "Version 2.0" not in license_text:
            raise ConanInvalidConfiguration(
                "Pinned openFPGALoader v1.1.1 source is not Apache-2.0"
            )
        apply_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        PkgConfigDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["ENABLE_OPTIM"] = True
        tc.variables["BUILD_STATIC"] = False
        tc.variables["USE_PKGCONFIG"] = True
        tc.variables["LINK_CMAKE_THREADS"] = True
        tc.variables["ENABLE_USB_SCAN"] = False
        tc.variables["ENABLE_CABLE_ALL"] = False
        tc.variables["ENABLE_REMOTEBITBANG"] = True
        tc.variables["ENABLE_XILINX_VIRTUAL_CABLE_CLIENT"] = True
        tc.variables["ENABLE_SVF_JTAG"] = True
        tc.variables["ENABLE_VENDORS_ALL"] = True
        tc.variables["ENABLE_UDEV"] = False
        tc.variables["ENABLE_LIBGPIOD"] = False
        tc.variables["ENABLE_CMSISDAP"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        CMake(self).install()
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
