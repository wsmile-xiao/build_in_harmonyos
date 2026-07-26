#!/usr/bin/env python3
"""Conan recipe for tkdiff 6.0.

tkdiff is a script-only Tcl/Tk application. The recipe installs the upstream
script and adjusts the shell trampoline away from /bin/sh for HarmonyOS PC.
"""
import os
import stat

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class TkdiffConan(ConanFile):
    name = "tkdiff"
    version = "6.0"
    package_type = "application"
    description = "Tcl/Tk graphical side-by-side diff utility"
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/tkdiff/"
    url = "https://sourceforge.net/projects/tkdiff/"

    settings = "os", "arch"

    def requirements(self):
        self.requires("tk/9.0.3.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        script = os.path.join(self.source_folder, "tkdiff")
        with open(script, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        content = content.replace("#!/bin/sh", "#!/usr/bin/env sh", 1)
        with open(script, "w", encoding="utf-8") as f:
            f.write(content)
        os.chmod(script, os.stat(script).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        doc_dir = os.path.join(self.package_folder, "share", "doc", "tkdiff")
        copy(self, "tkdiff", src=self.source_folder, dst=bin_dir, keep_path=False)
        copy(self, "README.txt", src=self.source_folder, dst=doc_dir, keep_path=False)
        copy(self, "CHANGELOG.txt", src=self.source_folder, dst=doc_dir, keep_path=False)
        copy(self, "LICENSE.txt", src=self.source_folder, dst=doc_dir, keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.runenv_info.append_path("PATH", os.path.join(self.package_folder, "bin"))
