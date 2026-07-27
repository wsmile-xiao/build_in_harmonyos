#!/usr/bin/env python3
"""Conan recipe for mcpp 2.7.2 (Autotools)."""

import os
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class McppConan(ConanFile):
    name = "mcpp"
    version = "2.7.2"
    description = "Alternative C/C++ preprocessor"
    license = "BSD-2-Clause"
    homepage = "https://mcpp.sourceforge.net/"
    url = "https://sourceforge.net/projects/mcpp/"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _validate_library_modes(self):
        configure = os.path.join(self.source_folder, "configure")
        try:
            result = subprocess.run(
                [configure, "--help"],
                check=True,
                capture_output=True,
                text=True,
            )
        except OSError as error:
            raise ConanInvalidConfiguration(
                f"unable to execute mcpp configure --help: {error}"
            ) from error
        except subprocess.CalledProcessError as error:
            detail = f"exit code {error.returncode}"
            if error.stderr:
                detail += ": " + error.stderr.strip()
            raise ConanInvalidConfiguration(
                "mcpp configure --help failed with " + detail
            ) from error

        # Autoconf provides --disable-* as the inverse of each --enable-* option.
        required_options = ("--enable-shared", "--enable-static")
        missing_options = [
            option for option in required_options if option not in result.stdout
        ]
        if missing_options:
            raise ConanInvalidConfiguration(
                "mcpp configure does not support: " + ", ".join(missing_options)
            )

    def generate(self):
        self._validate_library_modes()
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--enable-mcpplib")
        library_args = (
            ("--enable-shared", "--disable-static")
            if self.options.shared
            else ("--disable-shared", "--enable-static")
        )
        tc.configure_args.extend(arg for arg in library_args if arg not in tc.configure_args)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["mcpp"]
        self.cpp_info.bindirs = ["bin"]
