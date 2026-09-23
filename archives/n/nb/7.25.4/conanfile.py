#!/usr/bin/env python3
"""Conan recipe for the prebuilt nb 7.25.4 bash script.

nb is a single-file Bash script (~750 KB) distributed by upstream.
No compilation is needed — it is deployed directly as a prebuilt executable.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, save


class NbConan(ConanFile):
    name = "nb"
    version = "7.25.4"
    description = "A command-line notebook, bookmarks, and documentation manager"
    license = "MIT"
    homepage = "https://github.com/xwmx/nb"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("notebook", "cli", "bash", "bookmarks")
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"nb supports Linux/OHOS only, got {self.settings.os}"
            )
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("nb supports OHOS armv8 only")

    def layout(self):
        self.folders.source = "source"
        self.folders.build = "build"
        self.folders.package = "package"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Verify the nb script is present and executable
        nb_script = os.path.join(self.source_folder, "nb")
        if not os.path.isfile(nb_script):
            raise ConanException("nb script not found in source archive")

    def package(self):
        # Copy the nb script to bin/
        bin_dir = os.path.join(self.package_folder, "bin")
        copy(self, "nb", src=self.source_folder, dst=bin_dir, keep_path=False)
        # Ensure executable permission
        nb_path = os.path.join(bin_dir, "nb")
        os.chmod(nb_path, 0o755)
        # Copy LICENSE
        copy(self, "LICENSE", src=self.source_folder, dst=self.package_folder, keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
