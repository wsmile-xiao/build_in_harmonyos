#!/usr/bin/env python3
"""Conan recipe for AVRDUDE 8.1."""
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class AvrdudeConan(ConanFile):
    name = "avrdude"
    version = "8.1"
    description = "AVR microcontroller programming utility"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/avrdudes/avrdude"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("avrdude supports Linux and OHOS targets")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_DOC"] = False
        tc.variables["BUILD_SHARED_LIBS"] = False
        tc.variables["HAVE_LINUXGPIO"] = False
        tc.variables["HAVE_LINUXSPI"] = False
        tc.variables["HAVE_PARPORT"] = False
        tc.variables["USE_EXTERNAL_LIBS"] = False
        tc.variables["HAVE_LIBELF"] = False
        tc.variables["HAVE_LIBUSB"] = False
        tc.variables["HAVE_LIBUSB_1_0"] = False
        tc.variables["HAVE_LIBUSB_WIN32"] = False
        tc.variables["HAVE_LIBHIDAPI"] = False
        tc.variables["HAVE_LIBFTDI"] = False
        tc.variables["HAVE_LIBFTDI1"] = False
        tc.variables["HAVE_LIBREADLINE"] = False
        # The built-in POSIX serial backend remains enabled; this only disables
        # the optional libserialport adapter.
        tc.variables["HAVE_LIBSERIALPORT"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        if can_run(self):
            shell = shutil.which("bash") or "/data/service/hnp/bin/bash"
            command = [
                shell,
                os.path.join(self.source_folder, "tools", "test-avrdude"),
                "-v",
                "-t",
                self.build_folder,
                "-e",
                os.path.join(self.build_folder, "src", "avrdude"),
                "-c",
                "-C {}".format(os.path.join(self.build_folder, "src", "avrdude.conf")),
                "-d0",
                "-p",
                "-cdryrun -pm2560",
                "-p",
                "-cdryrun -pavr64du28",
            ]
            self.output.info("Running 2 upstream AVRDUDE dryrun test scenarios")
            quoted_command = " ".join(shlex.quote(arg) for arg in command)
            self.run("printf '\\n\\n' | {}".format(quoted_command))
            self.output.info("Upstream AVRDUDE dryrun tests passed: 2/2 (100%)")
        else:
            self.output.info("Cross-building: upstream AVRDUDE dryrun tests require a runnable target")

    def package(self):
        CMake(self).install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
