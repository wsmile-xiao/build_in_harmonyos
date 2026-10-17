#!/usr/bin/env python3
"""Conan recipe — rbenv-bundle-exec 1.0.0 (custom, pure Bash plugin)"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class RbenvBundleExecConan(ConanFile):
    name = "rbenv-bundle-exec"
    version = "1.0.0"
    description = "rbenv plugin to automatically run bundle exec when needed"
    license = "MIT"
    homepage = "https://github.com/maljub01/rbenv-bundle-exec"
    url = "https://github.com/maljub01/rbenv-bundle-exec"
    package_type = "application"

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        self.output.info("Pure Bash plugin; no native build step required")

    def package(self):
        plugin_dir = os.path.join(self.package_folder, "share", "rbenv-bundle-exec")
        copy(self, "etc/rbenv.d/exec/*", src=self.source_folder, dst=plugin_dir)
        copy(self, "README.md", src=self.source_folder, dst=plugin_dir)
        copy(self, "LICENSE", src=self.source_folder, dst=plugin_dir)

    def package_id(self):
        self.info.clear()

    def package_info(self):
        plugin_dir = os.path.join(self.package_folder, "share", "rbenv-bundle-exec")
        self.runenv_info.define("RBENV_BUNDLE_EXEC_DIR", plugin_dir)