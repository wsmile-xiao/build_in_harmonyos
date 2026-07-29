#!/usr/bin/env python3
"""Conan recipe for gsan 5.0.0 — TLS certificate subject alternative name scanner."""
import os
from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class GsanConan(ConanFile):
    name = "gsan"
    version = "5.0.0"
    description = "TLS certificate subject alternative name scanner"
    license = "MIT"
    homepage = "https://pypi.org/project/gsan/"
    url = "https://pypi.org/project/gsan/"
    package_type = "application"
    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        copy(self, "LICENSE.md", self.source_folder, os.path.join(self.package_folder, "share", "licenses", "gsan"))
        copy(self, "*.py", os.path.join(self.source_folder, "src", "gsan"), os.path.join(self.package_folder, "lib", "gsan"))
        launcher = os.path.join(self.package_folder, "bin", "gsan")
        os.makedirs(os.path.dirname(launcher), exist_ok=True)
        with open(launcher, "w", encoding="utf-8", newline="\n") as output:
            output.write("#!/bin/sh\nexec \"${PYTHON:-python3}\" -m gsan.main \"$@\"\n")
        os.chmod(launcher, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        module_path = os.path.join(self.package_folder, "lib")
        self.runenv_info.append_path("PATH", os.path.join(self.package_folder, "bin"))
        self.runenv_info.append_path("PYTHONPATH", module_path)
