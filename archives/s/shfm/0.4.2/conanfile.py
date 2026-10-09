#!/usr/bin/env python3
"""Conan recipe for shfm 0.4.2: a file manager written in POSIX shell (nothing is compiled).

Upstream: https://github.com/dylanaraps/shfm (MIT). The 0.4.2 tag archive holds the
single script ``shfm``, ``README``, ``LICENSE`` and a shellcheck-only GitHub workflow;
there is no build system and no test suite.

One portability patch (patches/0001-shfm.patch) fixes the documented cd-on-exit contract
for shells that keep ``main >/dev/tty`` active while the EXIT trap runs (mksh, bash, zsh).
"""
import os
import stat

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class ShfmConan(ConanFile):
    name = "shfm"
    version = "0.4.2"
    description = "File manager written in POSIX shell"
    license = "MIT"
    homepage = "https://github.com/dylanaraps/shfm"
    url = "https://github.com/dylanaraps/shfm"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Nothing to compile; make sure the patched script still parses.
        self.run("sh -n shfm", cwd=self.source_folder)

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        copy(self, "shfm", src=self.source_folder, dst=bindir, keep_path=False)
        program = os.path.join(bindir, "shfm")
        os.chmod(program, os.stat(program).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "README", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc", "shfm"), keep_path=False)

    def package_id(self):
        self.info.clear()  # one script for every os/arch/compiler

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
