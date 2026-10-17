#!/usr/bin/env python3
"""Conan recipe for the pure-Python catkin-pkg setuptools package."""

import os
import sys

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout
import os
import sys

class CatkinPkgConan(ConanFile):
    name = "catkin-pkg"
    version = "1.1.0"
    description = "Standalone Python package metadata and workspace utilities"
    license = "MIT"
    homepage = "https://github.com/ros-infrastructure/catkin_pkg"
    package_type = "library"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("docutils/0.23")
        self.requires("packaging/26.3")
        self.requires("python-dateutil/2.9.0.post0")
        self.requires("pyparsing/3.1.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # The sdist has setup.py and no pyproject.toml.
        target = os.path.join(self.build_folder, "site-packages")
        self.run(f'"{sys.executable}" -m pip install --no-deps --target "{target}" "{self.source_folder}"')

    def package(self):
        staged = os.path.join(self.build_folder, "site-packages")
        site_packages = os.path.join(self.package_folder, "lib", "site-packages")
        copy(self, "*", src=staged, dst=site_packages)
        for bindir in (os.path.join(staged, "bin"), os.path.join(self.build_folder, "bin")):
            if os.path.isdir(bindir):
                copy(self, "*", src=bindir, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        site_packages = os.path.join(self.package_folder, "lib", "site-packages")
        self.buildenv_info.define_path("PYTHONPATH", site_packages)
        self.runenv_info.define_path("PYTHONPATH", site_packages)
        self.buildenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
