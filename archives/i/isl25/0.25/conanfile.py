#!/usr/bin/env python3
"""Conan recipe for isl 0.25 on OpenHarmony."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class IslConan(ConanFile):
    name = "isl25"
    version = "0.25"
    description = "Integer Set Library for polyhedral compilation"
    license = "MIT"
    homepage = "https://libisl.sourceforge.io/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("isl25/0.25 is validated only for Linux and OHOS")

    def requirements(self):
        self.requires("gmp/6.3.0")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        gmp = self.dependencies["gmp"]
        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.append(f"--with-gmp-prefix={gmp.package_folder}")
        if self.options.shared:
            toolchain.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            toolchain.configure_args.extend(["--disable-shared", "--enable-static"])
            if self.options.get_safe("fPIC"):
                toolchain.configure_args.append("--with-pic")
        toolchain.generate()

    def _build_environment(self):
        environment = Environment()
        # ISL's configure probes a native build compiler separately from CC.
        # The OHOS device image provides clang but no gcc or cc executable.
        environment.define("CC_FOR_BUILD", "clang")
        environment.define("BUILD_CC", "clang")
        return environment.vars(self)

    def build(self):
        autotools = Autotools(self)
        with self._build_environment().apply():
            autotools.configure()
            autotools.make(args=["-j1"])
            if can_run(self):
                autotools.make(target="check", args=["-j1"])
            else:
                self.output.info("Skipping make check because this is a cross build")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["isl"]
        self.cpp_info.requires = ["gmp::gmp"]
        self.cpp_info.set_property("cmake_file_name", "isl25")
        self.cpp_info.set_property("cmake_target_name", "isl25::isl25")
        self.cpp_info.set_property("pkg_config_name", "isl")
