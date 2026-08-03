#!/usr/bin/env python3
"""Conan recipe for packaging the pure-Python PyYAML 6.0.2 library."""

import os
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class PyyamlConan(ConanFile):
    name = "pyyaml"
    version = "6.0.2"
    description = "YAML parser and emitter for Python"
    license = "MIT"
    homepage = "https://pyyaml.org/"
    url = "https://github.com/yaml/pyyaml"

    package_type = "unknown"
    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def configure(self):
        self.settings.rm_safe("os.version")

    def validate(self):
        if sys.version_info < (3, 8):
            raise ConanInvalidConfiguration("PyYAML 6.0.2 requires Python 3.8 or newer")

    def package_id(self):
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        test_dir = os.path.join(self.source_folder, "tests", "legacy_tests")
        test_script = os.path.join(test_dir, "test_all.py")
        tmp_dir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp_dir, exist_ok=True)

        test_env = Environment()
        test_env.define("PYYAML_FORCE_LIBYAML", "0")
        test_env.define("PYTHONDONTWRITEBYTECODE", "1")
        test_env.define("TMPDIR", tmp_dir)
        test_env.define("TMP", tmp_dir)
        test_env.define("TEMP", tmp_dir)
        test_env.prepend_path("PYTHONPATH", os.path.join(self.source_folder, "lib"))
        test_env.prepend_path("PYTHONPATH", test_dir)
        with test_env.vars(self).apply():
            self.run(f'"{sys.executable}" "{test_script}"', cwd=self.source_folder)

    def package(self):
        site_packages = os.path.join(
            self.package_folder,
            "lib",
            "python",
            "site-packages",
        )
        copy(
            self,
            "*.py",
            src=os.path.join(self.source_folder, "lib", "yaml"),
            dst=os.path.join(site_packages, "yaml"),
            keep_path=False,
        )
        copy(
            self,
            "*.py",
            src=os.path.join(self.source_folder, "lib", "_yaml"),
            dst=os.path.join(site_packages, "_yaml"),
            keep_path=False,
        )
        copy(
            self,
            "*",
            src=os.path.join(self.source_folder, "lib", "PyYAML.egg-info"),
            dst=os.path.join(site_packages, "PyYAML-6.0.2.egg-info"),
            keep_path=False,
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        site_packages = os.path.join(
            self.package_folder,
            "lib",
            "python",
            "site-packages",
        )
        self.runenv_info.prepend_path("PYTHONPATH", site_packages)
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
