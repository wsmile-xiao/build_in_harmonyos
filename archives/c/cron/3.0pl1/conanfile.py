#!/usr/bin/env python3
"""Conan recipe for the cron 3.0pl1 command-line tools."""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, chdir, copy, get, export_conandata_patches
from conan.tools.layout import basic_layout


class CronConan(ConanFile):
    name = "cron"
    version = "3.0pl1"
    description = "Vixie cron scheduler and crontab command"
    license = "MIT"
    homepage = "https://www.cron.org/"
    url = "https://github.com/atomgit/build_in_harmonyos"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compiler_executables = self.conf.get("tools.build:compiler_executables", default={})
        cc = compiler_executables.get("c", "clang")
        with chdir(self, self.source_folder):
            self.run(f"make -j1 CC={cc}", env="conanbuild")

    def package(self):
        copy(self, "cron", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "crontab", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "cron.8", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "man", "man8"))
        copy(self, "crontab.1", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "crontab.5", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "man", "man5"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
