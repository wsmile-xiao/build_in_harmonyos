#!/usr/bin/env python3
"""Conan recipe for the libplist 2.7.0 ``plistutil`` command-line tool."""
import os
import shutil
import stat
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibplistUtilConan(ConanFile):
    name = "libplist-util"
    version = "2.7.0"
    package_type = "application"

    description = "Command-line utility for converting Apple Property List files"
    license = "LGPL-2.1+"
    homepage = "https://libimobiledevice.org/"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libplist-util is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(
            [
                "--without-cython",
                "--with-tools",
                "--with-tests",
                "--enable-static",
                "--disable-shared",
            ]
        )

        if self.settings.os == "OHOS":
            wrapper_dir = Path(self.build_folder) / ".hmos_fix"
            wrapper_dir.mkdir(exist_ok=True)
            wrapper = wrapper_dir / "mktemp"
            wrapper.write_text(
                "#!/bin/sh\n"
                "# HarmonyOS: force autoconf's mkdir fallback for config.status.\n"
                "exit 1\n",
                encoding="utf-8",
            )
            wrapper.chmod(wrapper.stat().st_mode | stat.S_IEXEC)

            # config.guess does not identify HarmonyOS reliably.
            tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
            from conan.tools.env import Environment

            env = Environment()
            env.prepend_path("PATH", str(wrapper_dir))
            env.vars(self).save_script("hmos_env")

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # HMDFS can reject make's parallel jobserver fifo.
        autotools.make(args=["-j1"])
        if can_run(self):
            autotools.make(args=["-j1", "check"])

    def package(self):
        Autotools(self).install()

        # This is the split utility package: do not publish the libplist library
        # or headers that the upstream source also installs for its tool build.
        for relative in ("include", "lib"):
            path = os.path.join(self.package_folder, relative)
            if os.path.isdir(path):
                shutil.rmtree(path)

        bin_dir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bin_dir):
            for entry in os.listdir(bin_dir):
                if entry != "plistutil":
                    path = os.path.join(bin_dir, entry)
                    if os.path.isdir(path) and not os.path.islink(path):
                        shutil.rmtree(path)
                    else:
                        os.remove(path)

        copy(self, "COPYING*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
