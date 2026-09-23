#!/usr/bin/env python3
"""Conan recipe for libnexstar 0.15."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    mkdir,
    replace_in_file,
    rm,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibnexstarConan(ConanFile):
    name = "libnexstar"
    version = "0.15"
    description = "C library for controlling NexStar-compatible telescope mounts"
    license = "GPL-3.0-only"
    homepage = "https://sourceforge.net/projects/libnexstar/"
    url = "https://sourceforge.net/projects/libnexstar/"
    package_type = "library"
    implements = ["auto_shared_fpic"]

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libnexstar supports Linux and OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def _prepare_config_status_workdir(self):
        if self.settings.os != "OHOS":
            return

        configure = os.path.join(self.source_folder, "configure")
        config_status_workdir = os.path.join(self.build_folder, "config-status-work")
        mkdir(self, config_status_workdir)
        replace_in_file(
            self,
            configure,
            "ac_tmp=$tmp",
            'ac_tmp="{}"'.format(config_status_workdir),
            strict=True,
        )

    def build(self):
        apply_conandata_patches(self)
        # Autoconf 2.69 creates a mode-0700 conf* directory whose HMDFS owner
        # mapping rejects the subsequent subs1.awk write. Keep the upstream
        # secure-temp setup, but direct generated files to a recipe-created
        # work directory with usable inherited permissions (E167).
        self._prepare_config_status_workdir()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # Retain the upstream entry point. The release has no registered
        # check_PROGRAMS/TESTS; test_package automates all seven shipped
        # testcode/example scenarios.
        autotools.make(target="check", args=["-j1"])

    def package(self):
        Autotools(self).install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        rm(self, "*.la", self.package_folder, recursive=True)

    def package_info(self):
        self.cpp_info.libs = ["nexstar"]
        self.cpp_info.system_libs = ["m"]
