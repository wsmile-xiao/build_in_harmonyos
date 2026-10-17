#!/usr/bin/env python3
"""Conan recipe for probcons 1.12 (upstream bare Makefile, four CLI tools).

probcons compiles probcons/compare/project/makegnuplot from a hand-written
Makefile that has no install target and no PREFIX; this recipe builds in
place with the profile toolchain and packages the binaries into <pkg>/bin.
"""

import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class ProbconsConan(ConanFile):
    name = "probcons"
    version = "1.12"
    description = (
        "PROBCONS: probabilistic-consistency based multiple sequence"
        " alignment of protein sequences"
    )
    license = "Public Domain"
    homepage = "http://probcons.stanford.edu/"
    url = "https://deb.debian.org/debian/pool/main/p/probcons/probcons_1.12.orig.tar.gz"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        if self.settings.os not in ("Linux", "OHOS"):
            self.fail("probcons requires a POSIX host (Linux or OHOS)")
        apply_conandata_patches(self)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cxx = compilers.get("cpp", "clang++") if compilers else "clang++"
        # Upstream Makefile hardcodes CXX=g++ and has no install/PREFIX;
        # build the default targets in place and copy them in package().
        self.run("make -j1 CXX={}".format(cxx))

    def package(self):
        for tool in ("probcons", "compare", "project", "makegnuplot"):
            copy(
                self,
                tool,
                src=self.source_folder,
                dst=os.path.join(self.package_folder, "bin"),
            )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
