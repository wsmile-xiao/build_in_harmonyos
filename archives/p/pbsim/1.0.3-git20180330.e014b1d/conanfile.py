#!/usr/bin/env python3
"""Conan recipe for PBSIM 1.0.3 (git snapshot e014b1d) - PacBio read simulator.

Upstream is a small C++ autotools project (top-level Makefile.am + src/) with no
pre-generated ``configure`` in the release tarball, so the recipe runs
``autoreconf -i`` before configuring.  There are no third-party dependencies.

The source is the Debian dfsg orig tarball (the task version is the Debian
upstream snapshot ``1.0.3+git20180330.e014b1d``); the tarball is byte-pinned by
sha256.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy, export_conandata_patches,
                               get)
from conan.tools.layout import basic_layout


class PbsimConan(ConanFile):
    name = "pbsim"
    version = "1.0.3-git20180330.e014b1d"
    description = "PBSIM: PacBio read simulator (continuous long read / CCS)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/pfaucon/PBSIM-PacBio-Simulator"
    url = ""

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "pbsim OHOS adaptation is validated on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler(self, name, fallback):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        return executables.get(name) or fallback

    def build(self):
        apply_conandata_patches(self)
        cxx = self._compiler("cpp", "clang++")
        src = os.path.join(self.source_folder, "src")
        opt = "-O2" if str(self.settings.build_type) == "Release" else "-O0 -g"
        out = os.path.join(src, "pbsim")
        # pbsim.cpp only pulls in ../config.h when HAVE_CONFIG_H is defined, so
        # compiling the three C++ translation units directly avoids the
        # autotools config.status machinery entirely (whose awk helper scripts
        # cannot be executed on the OHOS HMDFS sandbox).  There is no
        # third-party code to configure.
        self.run('"{cxx}" {opt} -I"{src}" -o "{out}" "{src}/pbsim.cpp" '
                 '"{src}/helpers.cpp" "{src}/output.cpp" -lm'.format(
                     cxx=cxx, opt=opt, out=out, src=src),
                 cwd=self.source_folder)
        if not os.path.isfile(out):
            raise ConanInvalidConfiguration("build did not produce the 'pbsim' program")

    def package(self):
        copy(self, "pbsim", os.path.join(self.source_folder, "src"),
             os.path.join(self.package_folder, "bin"))
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "README*", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
