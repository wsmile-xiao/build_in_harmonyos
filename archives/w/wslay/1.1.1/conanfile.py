#!/usr/bin/env python3
"""Conan recipe for wslay 1.1.1, a WebSocket protocol library."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class WslayConan(ConanFile):
    name = "wslay"
    version = "1.1.1"
    description = "C library implementing the WebSocket protocol"
    license = "MIT"
    homepage = "https://github.com/tatsuhiro-t/wslay"
    url = "https://github.com/tatsuhiro-t/wslay"

    package_type = "library"
    required_conan_version = ">=2.0"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"wslay supports Linux and OHOS targets, got {self.settings.os}"
            )
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # Upstream's CUnit suite is optional and must not become a consumer
        # dependency of the installed WebSocket library.
        self.test_requires("cunit/2.1-3")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
        else:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])
            if self.options.fPIC:
                tc.extra_cflags.append("-fPIC")

        # configure.ac detects CUnit with AC_CHECK_LIB rather than pkg-config.
        # Pass the test-only package's paths explicitly, without exporting them
        # to consumers through package_info().
        cunit = self.dependencies["cunit"]
        for directory in cunit.cpp_info.includedirs:
            tc.extra_cflags.append(
                "-I" + os.path.join(str(cunit.package_folder), directory)
            )
        for directory in cunit.cpp_info.libdirs:
            tc.extra_ldflags.append(
                "-L" + os.path.join(str(cunit.package_folder), directory)
            )
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["wslay"]
        self.cpp_info.set_property("cmake_file_name", "wslay")
        self.cpp_info.set_property("cmake_target_name", "wslay::wslay")
        self.cpp_info.set_property("pkg_config_name", "libwslay")
