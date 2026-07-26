#!/usr/bin/env python3
"""Conan recipe for vimtutor-sequel 1.3.2.

vimtutor-sequel is a shell-based command-line tool that launches an advanced
Vim tutorial. Upstream ships one script plus two data files; there is no
configure or compile step.
"""
import os
import stat

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class VimtutorSequelConan(ConanFile):
    name = "vimtutor-sequel"
    version = "1.3.2"
    package_type = "application"
    description = "Advanced Vim tutor lessons for intermediate Vim users"
    license = "MIT"
    homepage = "https://github.com/micahkepe/vimtutor-sequel"
    url = ""

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # Runtime expects a vim executable to be available in PATH.
        # Keep it as a system/runtime expectation to avoid introducing an
        # unpublished Conan dependency into CI for this script-only package.
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        share_dir = os.path.join(self.package_folder, "share", "vimtutor-sequel")

        copy(self, "vimtutor-sequel.sh", src=self.source_folder, dst=bin_dir)
        copy(self, "vimtutor-sequel.txt", src=self.source_folder, dst=share_dir)
        copy(self, "vimtutor-sequel.vimrc", src=self.source_folder, dst=share_dir)

        script_path = os.path.join(bin_dir, "vimtutor-sequel.sh")
        final_path = os.path.join(bin_dir, "vimtutor-sequel")
        os.replace(script_path, final_path)
        os.chmod(
            final_path,
            os.stat(final_path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH,
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
