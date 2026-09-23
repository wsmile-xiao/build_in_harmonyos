#!/usr/bin/env python3
"""Conan recipe — libjpeg9 9f (IJG reference JPEG library, Autotools)"""

import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class Libjpeg9Conan(ConanFile):
    name = "libjpeg9"
    version = "9f"
    description = "IJG reference implementation of the JPEG image codec"
    license = "IJG"
    homepage = "https://www.ijg.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    # R26: libjpeg9 builds libjpeg artifacts that collide with the system
    # libjpeg on HarmonyOS PC. Default to static so the package cannot shadow
    # the system library.
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # AutotoolsToolchain maps the shared/fPIC options to
        # --enable-shared/--disable-shared and --with-pic.
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # Upstream self-test (check-local): encode/decode testimg.* and compare
        # the output against the reference images shipped with the tarball.
        autotools.make(target="check")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "README", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["jpeg"]
        self.cpp_info.bindirs = ["bin"]
