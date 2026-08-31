#!/usr/bin/env python3
"""Conan recipe for fio — flexible I/O tester.

fio is a tool that spawns a number of threads or processes doing a
particular type of I/O action as specified by the user.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class FioConan(ConanFile):
    name = "fio"
    version = "3.41"
    description = "Flexible I/O tester — benchmark tool for filesystem and disk I/O"
    license = "GPL-2.0"
    homepage = "https://git.kernel.org/pub/scm/linux/kernel/git/axboe/fio.git/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # fio uses a custom configure script (not autoconf),
        # so AutotoolsToolchain is not suitable here.
        pass

    def build(self):
        apply_conandata_patches(self)
        # E165: fio's configure uses #!/bin/sh shebang which doesn't exist on OHOS
        # CONFIG_SHELL is set by Conan profile's [buildenv] section
        # env="conanbuild" ensures Conan profile env vars are applied
        config_shell = shutil.which("bash") or os.environ.get("CONFIG_SHELL", "bash")
        src = self.source_folder
        # fio has no out-of-tree build support — run from source dir
        # R1: minimal args — only --prefix
        self.run(f'{config_shell} ./configure --prefix="{self.package_folder}"', cwd=src, env="conanbuild")
        # R9: always -j1
        self.run("make -j1", cwd=src, env="conanbuild")

    def package(self):
        # make install uses the prefix set during configure
        self.run("make install", cwd=self.source_folder, env="conanbuild")

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
