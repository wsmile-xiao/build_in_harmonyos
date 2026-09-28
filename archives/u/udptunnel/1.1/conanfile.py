#!/usr/bin/env python3
"""Conan recipe for udptunnel — tunnels UDP packets over a TCP connection."""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class UdptunnelConan(ConanFile):
    name = "udptunnel"
    version = "1.1"
    description = "udptunnel tunnels UDP packets over a TCP connection"
    license = "BSD-3-Clause"
    homepage = "https://www1.cs.columbia.edu/~lennox/udptunnel/"
    url = "https://www1.cs.columbia.edu/~lennox/udptunnel/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
