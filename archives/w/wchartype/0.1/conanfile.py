"""Conan recipe candidate for the pure Python wchartype 0.1 module."""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class WchartypeConan(ConanFile):
    name = "wchartype"
    version = "0.1"
    description = "Classify full-width and Asian Unicode characters"
    license = "MIT"
    homepage = "http://ginstrom.com/code/wchartype.html"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "unknown"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def package(self):
        if not copy(self, "wchartype.py", src=self.source_folder,
                    dst=os.path.join(self.package_folder, "lib", "python"),
                    keep_path=False):
            raise ConanException("wchartype source module is missing")
        if not copy(self, "PKG-INFO", src=self.source_folder,
                    dst=os.path.join(self.package_folder, "share", "doc", "wchartype"),
                    keep_path=False):
            raise ConanException("wchartype PKG-INFO is missing")

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.runenv_info.prepend_path("PYTHONPATH",
                                      os.path.join(self.package_folder, "lib", "python"))
