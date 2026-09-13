#!/usr/bin/env python3
"""Conan recipe for Coco/R C++ (coco-cpp) 20120102 — compiler generator tool.

Upstream build is a single command (`g++ *.cpp -o Coco`); the Makefile
hardcodes g++, so build() compiles directly with the profile C++ compiler.
The .frame files are runtime inputs to code generation and are packaged
into res/.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class CocoCppConan(ConanFile):
    name = "coco-cpp"
    version = "20120102"
    description = "Coco/R compiler generator (C++ version): generates scanners and parsers from attributed grammars"
    license = "GPL-2.0-or-later"
    homepage = "https://ssw.jku.at/Research/Projects/Coco/"
    url = "https://ssw.jku.at/Research/Projects/Coco/"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "coco-cpp is supported only on Linux/OHOS")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cxx = compilers.get("cpp", "g++")
        sources = " ".join(
            '"%s"' % os.path.join(self.source_folder, name)
            for name in sorted(os.listdir(str(self.source_folder)))
            if name.endswith(".cpp"))
        self.run('"%s" %s -o "%s"' % (
            cxx, sources, os.path.join(str(self.build_folder), "Coco")))

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        resdir = os.path.join(self.package_folder, "res")
        copy(self, "Coco", src=str(self.build_folder), dst=bindir)
        os.rename(os.path.join(bindir, "Coco"), os.path.join(bindir, "cococpp"))
        copy(self, "*.frame", src=str(self.source_folder), dst=resdir)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["res"]
        self.runenv_info.prepend_path("PATH",
                                      os.path.join(self.package_folder, "bin"))
