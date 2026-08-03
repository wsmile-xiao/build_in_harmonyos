#!/usr/bin/env python3
"""Conan recipe for httpstat 1.3.2."""

import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class HttpstatConan(ConanFile):
    name = "httpstat"
    version = "1.3.2"
    package_type = "application"

    description = "Curl statistics made simple"
    license = "MIT"
    homepage = "https://github.com/reorx/httpstat"
    url = "https://github.com/reorx/httpstat"
    topics = ("curl", "http", "network", "timing")

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        python = os.environ.get("PYTHON", "python3")
        script = os.path.join(self.source_folder, "httpstat.py")
        self.run(f'"{python}" "{script}" --version')

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        licenses_dir = os.path.join(self.package_folder, "licenses")

        copy(self, "httpstat.py", self.source_folder, bin_dir)
        copy(self, "LICENSE", self.source_folder, licenses_dir)

        source_script = os.path.join(bin_dir, "httpstat.py")
        packaged_script = os.path.join(bin_dir, "httpstat")
        os.replace(source_script, packaged_script)
        os.chmod(packaged_script, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
