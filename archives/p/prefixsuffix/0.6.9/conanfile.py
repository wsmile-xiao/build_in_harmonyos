import os

from conan import ConanFile
from conan.tools.files import copy
from conan.tools.layout import basic_layout


class PrefixsuffixConan(ConanFile):
    name = "prefixsuffix"
    version = "0.6.9"
    description = "Failed OHOS adaptation record for prefixsuffix"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/murraycu/prefixsuffix"
    package_type = "application"

    settings = "os", "arch"
    exports_sources = "manifest.yaml", "notes.md"

    def layout(self):
        basic_layout(self)

    def build(self):
        manifest = os.path.join(self.source_folder, "manifest.yaml")
        notes = os.path.join(self.source_folder, "notes.md")
        if not os.path.isfile(manifest) or not os.path.isfile(notes):
            raise RuntimeError("failed adaptation record is incomplete")

    def package(self):
        destination = os.path.join(self.package_folder, "share", "prefixsuffix")
        copy(self, "manifest.yaml", src=self.source_folder, dst=destination)
        copy(self, "notes.md", src=self.source_folder, dst=destination)

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
