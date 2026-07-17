#!/usr/bin/env python3
"""Conan recipe — fvm 4.1.2 (Flutter Version Manager, Dart)."""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class FvmConan(ConanFile):
    name = "fvm"
    version = "4.1.2"
    description = "Manage Flutter SDK versions per project"
    license = "MIT"
    homepage = "https://fvm.app"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Dart project — requires dart-sdk which is not available in OHOS cross-compilation env
        pass

    def package(self):
        pass

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]