#!/usr/bin/env python3
"""Conan recipe - OpenFst 1.8.4."""
import os

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class OpenfstConan(ConanFile):
    name = "openfst"
    version = "1.8.4"
    description = "Library for constructing, combining, optimizing, and searching weighted finite-state transducers"
    license = "Apache-2.0"
    homepage = "https://www.openfst.org/"
    url = "https://www.openfst.org/"

    settings = "os", "compiler", "build_type", "arch"
    package_type = "library"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--enable-bin",
            "--enable-static" if not self.options.shared else "--disable-static",
            "--enable-shared" if self.options.shared else "--disable-shared",
        ])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        Autotools(self).install()

    def package_info(self):
        self.cpp_info.libs = ["fst", "fstscript"]
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        self.runenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
