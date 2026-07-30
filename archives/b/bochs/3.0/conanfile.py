#!/usr/bin/env python3
"""Conan recipe - Bochs 3.0 (Autotools application)."""

import os

from conan import ConanFile
from conan.tools.build import cmd_args_to_string
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    mkdir,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class BochsConan(ConanFile):
    name = "bochs"
    version = "3.0"
    description = "Portable x86 and x86-64 emulator"
    license = "LGPL-2.1-or-later"
    homepage = "https://bochs.sourceforge.io/"
    url = "https://github.com/bochs-emu/Bochs"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    win_bash = True

    _configure_options = (
        "--disable-docbook",
        "--disable-plugins",
        "--disable-readline",
        "--enable-debugger",
        "--enable-x86-64",
        "--with-nogui",
        "--without-sdl",
        "--without-sdl2",
        "--without-term",
        "--without-x",
    )

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    @property
    def _bochs_source(self):
        return os.path.join(self.source_folder, "bochs")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(self._configure_options)
        env = tc.environment()
        if str(self.settings_build.os) == "Windows":
            env.define(
                "MSYS2_ARG_CONV_EXCL",
                ";".join((
                    "--prefix=",
                    "--bindir=",
                    "--sbindir=",
                    "--libdir=",
                    "--includedir=",
                    "--oldincludedir=",
                )),
            )
        tc.generate(env)

    def build(self):
        apply_conandata_patches(self)

        autotools = Autotools(self)
        configure_args = AutotoolsToolchain(self).configure_args
        configure_args.extend(self._configure_options)
        configure_dir = os.path.relpath(
            self._bochs_source, self.build_folder
        ).replace("\\", "/")
        # A relative script path avoids Autoconf splitting a Windows drive path.
        self.run(
            f'"{configure_dir}/configure" '
            f'{cmd_args_to_string(configure_args)}'
        )

        # Bochs 3.0 assumes these generated VPATH directories already exist.
        for relative in (
            os.path.join("cpu", "decoder"),
            os.path.join("cpu", "cpudb", "intel"),
            os.path.join("cpu", "cpudb", "amd"),
        ):
            mkdir(self, os.path.join(self.build_folder, relative))

        autotools.make()

    def package(self):
        Autotools(self).install()

    def package_info(self):
        bxshare = os.path.join(self.package_folder, "share", "bochs")
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.define_path("BXSHARE", bxshare)
        self.buildenv_info.define_path("BXSHARE", bxshare)
