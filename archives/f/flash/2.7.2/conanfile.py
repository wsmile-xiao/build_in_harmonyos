#!/usr/bin/env python3
"""Conan recipe for the Homebrew flash 2.7.2 task."""
import os
import stat

from conan import ConanFile
from conan.tools.files import copy, download
from conan.tools.layout import basic_layout


class FlashConan(ConanFile):
    name = "flash"
    version = "2.7.2"
    package_type = "application"

    description = "Command-line script to flash SD card images of any kind"
    license = "MIT"
    homepage = "https://github.com/hypriot/flash"
    url = "https://github.com/hypriot/flash"
    topics = ("sd-card", "image", "flashing", "shell")

    settings = "os", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        source = self.conan_data["sources"]
        download(self, source["url"], os.path.join(self.source_folder, "flash"), sha256=source["sha256"])

    def build(self):
        self.output.info("flash is a single shell script; no native build step required")

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        doc_dir = os.path.join(self.package_folder, "share", "doc", "flash")
        os.makedirs(bin_dir, exist_ok=True)
        os.makedirs(doc_dir, exist_ok=True)
        copy(self, "flash", src=self.source_folder, dst=bin_dir, keep_path=False)
        script = os.path.join(bin_dir, "flash")
        os.chmod(script, os.stat(script).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

        with open(os.path.join(doc_dir, "README.OHOS.md"), "w", encoding="utf-8") as readme:
            readme.write(
                "# flash 2.7.2\n\n"
                "Packaged from the Homebrew source URL. The script performs destructive disk writes only when\n"
                "a target image and device are supplied; the Conan smoke test is limited to non-destructive\n"
                "`--version` and `--help` paths.\n"
            )

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
