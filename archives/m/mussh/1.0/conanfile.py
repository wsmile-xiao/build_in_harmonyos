#!/usr/bin/env python3
"""Conan recipe — mussh 1.0 (MUltihost SSH Wrapper).

mussh is a pure bash script (no build system, no compiled artifacts):
it wraps ssh-agent/ssh-add and fans a command or script out over
multiple hosts via ssh. The package ships bin/mussh as-is (package_id
cleared: the script content is identical across platforms), plus the
man page under res/man/man1 and README/CHANGES as license material
(upstream README declares GPL without a version notice).

Runtime dependencies (ssh, ssh-agent, ssh-add, sed, cat, mktemp,
hostname, awk) are all system commands — there are no Conan
requirements. The tarball ships junk files (.swp, mussh.bak, mussh.spec,
casetest.sh, ...), so package() must cherry-pick the targets instead of
copying the whole source tree.
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class MusshConan(ConanFile):
    name = "mussh"
    version = "1.0"
    description = "MUltihost SSH Wrapper: run a command or script over many hosts via ssh"
    license = "GPL-1.0-or-later"  # upstream README declares GPL without version
    homepage = "http://mussh.sourceforge.net/"
    url = "http://mussh.sourceforge.net/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def package_id(self):
        # script-only package: identical content on every platform
        self.info.clear()

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        # no build system; kept for future patches (zero-patch by default)
        apply_conandata_patches(self)

    def package(self):
        src = self.source_folder
        copy(self, "mussh", src=src, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "mussh.1", src=src,
             dst=os.path.join(self.package_folder, "res", "man", "man1"))
        copy(self, "README", src=src, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "CHANGES", src=src, dst=os.path.join(self.package_folder, "licenses"))
        # conan get() does not guarantee the executable bit
        os.chmod(os.path.join(self.package_folder, "bin", "mussh"), 0o755)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
