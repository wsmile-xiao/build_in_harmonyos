#!/usr/bin/env python3
"""Conan recipe — inifile-cpp master (header-only)."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get


class InifileCppConan(ConanFile):
    name = "inifile-cpp"
    version = "master"
    description = "C++ INI file parser and writer (header-only)"
    license = "MIT"
    homepage = "https://github.com/Rookfighter/inifile-cpp"
    url = "https://github.com/Rookfighter/inifile-cpp"
    package_type = "header-library"

    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "inifile-cpp supports Linux and OHOS in this recipe, got %s"
                % self.settings.os
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def package(self):
        copy(
            self,
            "inicpp.h",
            src=os.path.join(self.source_folder, "include"),
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "LICENSE.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
