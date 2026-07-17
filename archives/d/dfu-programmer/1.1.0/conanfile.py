#!/usr/bin/env python3
"""Conan recipe - dfu-programmer 1.1.0."""
import os
import shlex

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class DfuProgrammerConan(ConanFile):
    name = "dfu-programmer"
    version = "1.1.0"
    description = "Device firmware update programmer for Atmel chips"
    license = "GPL-2.0-or-later"
    homepage = "https://dfu-programmer.github.io/"
    url = "https://github.com/dfu-programmer/dfu-programmer"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires("libusb/1.0.27")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()
        AutotoolsDeps(self).generate()
        AutotoolsToolchain(self).generate()

    def build(self):
        configure = os.path.join(self.source_folder, "configure")
        bootstrap = os.path.join(self.source_folder, "bootstrap.sh")
        if not os.path.exists(configure) and os.path.exists(bootstrap):
            self.run(f"sh {shlex.quote(bootstrap)}", env="conanbuild")

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        Autotools(self).install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
