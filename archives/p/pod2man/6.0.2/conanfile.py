#!/usr/bin/env python3
"""Conan recipe — pod2man (podlators) 6.0.2 (ExtUtils::MakeMaker).

Pure Perl module producing command-line tools (pod2man, pod2text).
No binary artifacts; no static linking needed (R26 N/A for pure Perl).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class Pod2manConan(ConanFile):
    name = "pod2man"
    version = "6.0.2"
    description = "Convert POD format to man page and plain text"
    license = "Artistic-1.0-Perl OR GPL-1.0-or-later"
    homepage = "https://www.eyrie.org/~eagle/software/podlators/"
    url = ""

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        self.folders.source = "."
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        self.run("perl Makefile.PL", env="conanrun")
        self.run("make", env="conanrun")

    def package(self):
        copy(self, "*.pm", src=os.path.join(self.build_folder, "blib", "lib"),
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "pod2man", src=os.path.join(self.build_folder, "blib", "script"),
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "pod2text", src=os.path.join(self.build_folder, "blib", "script"),
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
