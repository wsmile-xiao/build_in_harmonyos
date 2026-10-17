#!/usr/bin/env python3
"""Conan recipe — micro-gl 3.20 (CMake, header-only C++11 vector graphics).

micro-gl is a fast, slim, embeddable, headers-only C++11 vector graphics
library: no FPU / GPU / standard library required. Upstream ships only an
INTERFACE CMake target (microgl::microgl) plus the include/microgl headers
tree (which vendors micro-tess and micro-alloc submodules). Nothing is
compiled; the recipe installs the public headers and license.

Version identity: upstream has no git tags and no GitHub releases; the
task-designated version 3.20 is pinned to upstream master HEAD
d7ddab9890ae6b391bc646b7086e695c06260abb (tarball SHA-256
a0a43d4ee828a7f500a98edd29f3b7dbeb877dc9016a62f3bb054aef46ccf5d4).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class MicroGlConan(ConanFile):
    name = "micro-gl"
    version = "3.20"
    description = "Headers-only C++11 CPU vector graphics: no std-lib, no FPU, no GPU required"
    license = "LicenseRef-micro-gl-semi-permissive"
    homepage = "https://github.com/micro-gl/micro-gl"
    url = "https://github.com/micro-gl/micro-gl"

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # header-only, zero dependencies (explicitly no std-lib runtime deps)
        pass

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # header-only: nothing to compile

    def package(self):
        # keep the microgl/ prefix (consumers include <microgl/canvas.h>);
        # "*" matches through subdirectories (math/, pixel_coders/, ...).
        copy(self, "microgl/*",
             os.path.join(self.source_folder, "include"),
             os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE.MD", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # header-only: no libs to link, headers under include/
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "microgl")
        self.cpp_info.set_property("cmake_target_name", "microgl::microgl")