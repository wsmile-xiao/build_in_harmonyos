#!/usr/bin/env python3
"""Conan recipe for lcms (Little CMS) 2.19.1 (Autotools)."""

import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LcmsConan(ConanFile):
    name = "lcms"
    version = "2.19.1"
    description = "Little CMS open source color management engine (lcms2 line)"
    license = "MIT"
    homepage = "https://www.littlecms.com/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.extend(
            ["--without-jpeg", "--without-tiff", "--without-zlib"]
        )
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        autotools.make(target="check", args=["-j1"])

    def package(self):
        package_libdir = os.path.join(self.package_folder, "lib")
        if self.settings.os == "Windows":
            copy(
                self,
                "lcms2*.dll",
                src=os.path.join(self.build_folder, "src", ".libs"),
                dst=os.path.join(self.package_folder, "bin"),
                keep_path=False,
            )
            for pattern in ("*lcms2*.dll.a", "*lcms2*.lib"):
                copy(
                    self,
                    pattern,
                    src=os.path.join(self.build_folder, "src", ".libs"),
                    dst=package_libdir,
                    keep_path=False,
                )
        else:
            built_libdir = os.path.join(self.build_folder, "src", ".libs")
            if not self.options.shared:
                patterns = ("liblcms2.a", "*lcms2*.lib")
            elif self.settings.os == "Macos":
                patterns = ("liblcms2*.dylib",)
            else:
                patterns = ("liblcms2.so*",)
            for pattern in patterns:
                copy(
                    self,
                    pattern,
                    src=built_libdir,
                    dst=package_libdir,
                    keep_path=False,
                )
        copy(
            self,
            "lcms2.h",
            src=os.path.join(self.source_folder, "include"),
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "lcms2_plugin.h",
            src=os.path.join(self.source_folder, "include"),
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "lcms2.pc",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "lib", "pkgconfig"),
        )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["lcms2"]
        self.cpp_info.set_property("cmake_file_name", "lcms2")
        self.cpp_info.set_property("cmake_target_name", "lcms2::lcms2")
        self.cpp_info.set_property("pkg_config_name", "lcms2")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]
