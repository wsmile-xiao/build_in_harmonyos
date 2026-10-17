#!/usr/bin/env python3
"""Conan recipe for remrun 0.2.5."""

import os
import stat

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, replace_in_file
from conan.tools.layout import basic_layout


class RemrunConan(ConanFile):
    name = "remrun"
    version = "0.2.5"
    description = "Copy a file over SSH to a remote host and execute it"
    license = "BSD-2-Clause"
    homepage = "https://gitlab.com/ppentchev/remrun"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        script = os.path.join(self.source_folder, "remrun.sh")
        replace_in_file(
            self, script, "#!/bin/sh", "#!/usr/bin/env sh", strict=False
        )
        self.run("make SKIP_SHELLCHECK=1 all", cwd=self.source_folder)

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        mandir = os.path.join(self.package_folder, "share", "man", "man1")
        copy(self, "remrun", src=self.source_folder, dst=bindir, keep_path=False)
        copy(self, "remrun.1.gz", src=self.source_folder, dst=mandir, keep_path=False)
        copy(self, "BSD-2-Clause.txt", src=os.path.join(self.source_folder, "LICENSES"),
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        tool = os.path.join(bindir, "remrun")
        os.chmod(tool, os.stat(tool).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libs = []
