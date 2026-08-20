#!/usr/bin/env python3
"""Conan recipe — arttime 2.5.0

CLI application that blends beauty of ASCII/text art with functionality of
clock/timer/pattern-based time manager in terminal.

Build system: install.sh (zsh script — NOT CMake/Autotools/Makefile)
License: Custom (LICENSE_CODE, LICENSE_ART, LICENSE_ADDENDUM_CFLA)
Project type: CLI application (produces shell script executables)

arttime is a pure zsh shell-script application. No compilation is needed.
The install.sh script copies bin/ and share/ files to a prefix directory.
This recipe replicates that behaviour using conan.tools.files.copy(),
avoiding runtime zsh-function dependencies (is-at-least, compinit) that
may be absent on OHOS minimal environments.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    get,
    copy,
    apply_conandata_patches,
    export_conandata_patches,
)
from conan.tools.layout import basic_layout


class ArttimeConan(ConanFile):
    name = "arttime"
    version = "2.5.0"
    description = (
        "CLI application that blends beauty of ASCII/text art with "
        "functionality of clock/timer/pattern-based time manager in terminal"
    )
    license = "Custom (LICENSE_CODE, LICENSE_ART, LICENSE_ADDENDUM_CFLA)"
    homepage = "https://github.com/poetaman/arttime"
    url = ""  # CI fills this

    package_type = "application"

    # CI L0p requires all four standard settings even for shell scripts
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # R27: No Conan-level dependencies.
        # zsh >= 5.7 is a system-level dependency, not a Conan package.
        pass

    def layout(self):
        basic_layout(self)

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"Unsupported OS: {self.settings.os}"
            )

    def source(self):
        # Provide explicit filename with .tar.gz extension so Conan can
        # correctly detect and decompress the tarball — the GitHub API URL
        # has no file extension which causes BadZipFile errors.
        get(
            self,
            **self.conan_data["sources"],
            strip_root=True,
            filename="arttime-2.5.0.tar.gz",
        )

    def build(self):
        # arttime is a pure shell script — no compilation step needed.
        # install.sh would run `zsh ./install.sh -p PREFIX --noupdaterc`,
        # but it depends on zsh autoload functions (is-at-least) that may
        # be absent on OHOS. We replicate the install logic in package()
        # using conan.tools.files.copy() instead.
        apply_conandata_patches(self)
        pass

    def package(self):
        # Copy executables to bin/
        copy(
            self,
            "arttime",
            src=os.path.join(self.source_folder, "bin"),
            dst=os.path.join(self.package_folder, "bin"),
        )
        copy(
            self,
            "artprint",
            src=os.path.join(self.source_folder, "bin"),
            dst=os.path.join(self.package_folder, "bin"),
        )
        # Copy share/ (art files, src, keypoems, doc, man, zsh completions)
        copy(
            self,
            "*",
            src=os.path.join(self.source_folder, "share"),
            dst=os.path.join(self.package_folder, "share"),
        )

    def package_info(self):
        # CLI application — executables in bin/, data in share/
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
