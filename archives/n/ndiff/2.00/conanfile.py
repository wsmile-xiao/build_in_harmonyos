#!/usr/bin/env python3
"""Conan recipe for ndiff 2.00.

ndiff is a small C command-line utility for comparing text files while
ignoring numeric differences within configured tolerances. Upstream release
2.00 is the upstream release version; the task platform displays it as 2.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class NdiffConan(ConanFile):
    name = "ndiff"
    version = "2.00"
    description = "Compare text files while ignoring small numeric differences"
    license = "GPL-2.0-or-later"
    homepage = "https://www.math.utah.edu/~beebe/software/ndiff/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("ndiff is supported only on Linux/OHOS")

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1", "LN=cp"])

        check_tmp = os.path.join(self.build_folder, "check-tmp")
        autotools.make(target="check", args=["-j1", f"TMPDIR={check_tmp}", "LN=cp"])

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        man_dir = os.path.join(self.package_folder, "share", "man", "man1")
        os.makedirs(bin_dir, exist_ok=True)
        os.makedirs(man_dir, exist_ok=True)

        binary = os.path.join(self.build_folder, "ndiff")
        packaged_binary = os.path.join(bin_dir, "ndiff")
        versioned_binary = os.path.join(bin_dir, f"ndiff-{self.version}")
        shutil.copy2(binary, packaged_binary)
        shutil.copy2(binary, versioned_binary)
        os.chmod(packaged_binary, 0o755)
        os.chmod(versioned_binary, 0o755)

        shutil.copy2(os.path.join(self.source_folder, "ndiff.man"),
                     os.path.join(man_dir, "ndiff.1"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
