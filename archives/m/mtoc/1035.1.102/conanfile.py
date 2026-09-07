#!/usr/bin/env python3
"""Conan recipe for mtoc 1035.1.102 (CMake wrapper)."""

import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class MtocConan(ConanFile):
    name = "mtoc"
    version = "1035.1.102"
    description = "Mach-O to PE/COFF converter for EFI firmware images"
    license = "APSL-2.0"
    homepage = "https://github.com/apple-oss-distributions/cctools"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "CMakeLists.txt"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(
            self,
            **self.conan_data["sources"][self.version],
            strip_root=True,
        )

        portability_root = os.path.join(self.source_folder, "_cctools_port")
        get(
            self,
            **self.conan_data["portability_sources"][self.version],
            destination=portability_root,
            strip_root=True,
        )
        portability_source = os.path.join(portability_root, "cctools")

        copy(
            self,
            "*",
            src=os.path.join(portability_source, "include", "foreign"),
            dst=os.path.join(self.source_folder, "include", "foreign"),
        )

        # cctools-port stores these ARM host headers as directory symlinks to
        # its architecture-neutral i386 definitions. Materialize the aliases
        # because Conan's source-to-build copy can drop directory symlinks on
        # HarmonyOS filesystems.
        foreign_source = os.path.join(portability_source, "include", "foreign")
        foreign_destination = os.path.join(self.source_folder, "include", "foreign")
        for alias, target in (("arm", "i386"), ("mach/arm", "mach/i386")):
            alias_path = os.path.join(foreign_destination, alias)
            if os.path.islink(alias_path) or os.path.isfile(alias_path):
                os.unlink(alias_path)
            elif os.path.isdir(alias_path):
                shutil.rmtree(alias_path)
            copy(
                self,
                "*",
                src=os.path.join(foreign_source, target),
                dst=alias_path,
            )
        copy(
            self,
            "machine.h",
            src=os.path.join(portability_source, "include", "mach"),
            dst=os.path.join(self.source_folder, "include", "mach"),
        )
        copy(
            self,
            "port.h",
            src=os.path.join(portability_source, "include", "stuff"),
            dst=os.path.join(self.source_folder, "include", "stuff"),
        )
        copy(
            self,
            "port.c",
            src=os.path.join(portability_source, "libstuff"),
            dst=os.path.join(self.source_folder, "libstuff"),
        )

    def generate(self):
        toolchain = CMakeToolchain(self)
        processor = {
            "armv8": "aarch64",
            "x86_64": "x86_64",
        }.get(str(self.settings.arch))
        if processor:
            toolchain.variables["MTOC_TARGET_PROCESSOR"] = processor
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "APPLE_LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        copy(
            self,
            "COPYING",
            src=os.path.join(self.source_folder, "_cctools_port", "cctools"),
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
