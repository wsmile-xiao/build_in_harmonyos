#!/usr/bin/env python3
"""Conan recipe — canlock 3.3.1 (Autotools)."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rm,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class CanlockConan(ConanFile):
    name = "canlock"
    version = "3.3.1"
    description = "RFC 8315 Cancel-Lock library, header parsers, and command-line tools"
    license = "ICU"
    homepage = "https://micha.freeshell.org/libcanlock/"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("canlock is supported only on Linux/OHOS")
        if self.settings.os == "OHOS" and self.settings.arch not in (
            "armv8",
            "x86_64",
        ):
            raise ConanInvalidConfiguration(
                "HarmonyOS PC builds require armv8/aarch64 or x86_64"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        self.tool_requires("bison/3.8.2")
        self.tool_requires("flex/2.6.4")

    def layout(self):
        # Upstream's recursive Automake setup expects generated and source files
        # to share one tree (notably the documentation templates and canlock.h).
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def source(self):
        get(
            self,
            **self.conan_data["sources"][self.version],
            strip_root=True,
        )

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--enable-hp",
            "--enable-pc-files",
            "--enable-legacy-api",
            "--disable-dependency-tracking",
        ])
        if self.options.shared:
            # Upstream's test binaries link the build-tree static archives
            # directly, so keep them available until packaging completes.
            tc.configure_args.extend(["--enable-shared", "--enable-static"])
        else:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        if not cross_building(self):
            autotools.make(target="check", args=["-j1"])
        else:
            self.output.info(
                "Cross build detected; target-side upstream tests are skipped in this build."
            )

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        if self.options.shared:
            rm(self, "*.a", os.path.join(self.package_folder, "lib"))
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "canlock")
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )

        core = self.cpp_info.components["core"]
        core.libs = ["canlock"]
        core.set_property("cmake_target_name", "canlock::canlock")
        core.set_property("pkg_config_name", "libcanlock-3")

        hp = self.cpp_info.components["hp"]
        hp.libs = ["canlock-hp"]
        hp.set_property("cmake_target_name", "canlock::canlock-hp")
        hp.set_property("pkg_config_name", "libcanlock-hp-3")
