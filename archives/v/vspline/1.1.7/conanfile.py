#!/usr/bin/env python3
"""Conan recipe for vspline - header-only b-spline library.

vspline is a header-only C++ template library: there are no shared or
static libraries to build. The package simply exports the headers and
propagates its vigra dependency.
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class VsplineConan(ConanFile):
    name = "vspline"
    version = "1.1.7"
    description = "generic C++ code for creation and evaluation of uniform b-splines"
    license = "MIT"
    homepage = "https://bitbucket.org/kfj/vspline"
    url = "https://bitbucket.org/kfj/vspline"

    package_type = "header-library"
    no_copy_source = True

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("vigra/1.12.4")

    def source(self):
        # R39: official upstream source (bitbucket is the project's official host)
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # header-only: nothing to build
        pass

    def package(self):
        copy(self, "*.h", src=self.source_folder, dst=os.path.join(self.package_folder, "include", "vspline"))
        copy(self, "*.h", src=os.path.join(self.source_folder, "opt"), dst=os.path.join(self.package_folder, "include", "vspline", "opt"))
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        # vspline uses std::thread; on Linux/OHOS it needs pthread
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
