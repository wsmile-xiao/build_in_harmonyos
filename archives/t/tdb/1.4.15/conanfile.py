#!/usr/bin/env python3
"""Conan recipe — tdb 1.4.15 (Samba waf build system)"""

import os
import shutil
import sys

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class TdbConan(ConanFile):
    name = "tdb"
    version = "1.4.15"
    description = "TDB - the Samba trivial database library"
    license = "LGPL-3.0-or-later"
    url = "https://tdb.samba.org/"
    homepage = "https://tdb.samba.org/"
    topics = ("database", "key-value", "samba")
    package_type = "shared-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def _python3(self):
        python = shutil.which("python3") or shutil.which("python") or sys.executable
        return python.replace("\\", "/")

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder.replace("\\", "/")
        prefix = self.package_folder.replace("\\", "/")
        jobs = self.conf.get("tools.build:jobs", default=2)
        self.run(
            f'cd "{src}" && PYTHON="{self._python3()}" '
            f'./configure --prefix="{prefix}" --disable-python '
            f'&& make -j{jobs} && make test',
            env="conanbuild",
        )

    def package(self):
        src = self.source_folder.replace("\\", "/")
        self.run(f'cd "{src}" && PYTHON="{self._python3()}" make install',
                 env="conanbuild")
        copy(self, "LICENSE", src, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["tdb"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("pkg_config_name", "tdb")
