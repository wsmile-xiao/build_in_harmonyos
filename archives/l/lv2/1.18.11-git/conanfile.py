#!/usr/bin/env python3
"""Conan recipe for LV2 1.18.11-git."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, save
from conan.tools.layout import basic_layout


class Lv2Conan(ConanFile):
    name = "lv2"
    version = "1.18.11-git"
    description = "LV2 audio plugin specification headers and data bundles"
    license = "0BSD OR ISC"
    homepage = "https://lv2plug.in/"
    url = ""
    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        pass

    def package(self):
        copy(self, "*.h", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"), keep_path=True)
        copy(self, "*", src=os.path.join(self.source_folder, "lv2"),
             dst=os.path.join(self.package_folder, "lib", "lv2"), keep_path=True)

        pc_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
        os.makedirs(pc_dir, exist_ok=True)
        save(
            self,
            os.path.join(pc_dir, "lv2.pc"),
            "\n".join([
                "prefix=${pcfiledir}/../..",
                "exec_prefix=${prefix}",
                "includedir=${prefix}/include",
                "lv2dir=${prefix}/lib/lv2",
                "",
                "Name: LV2",
                "Version: 1.18.11",
                "Description: An audio plugin interface specification",
                "Cflags: -I${includedir}",
                "",
            ]),
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["lib/lv2"]
        self.cpp_info.set_property("pkg_config_name", "lv2")
