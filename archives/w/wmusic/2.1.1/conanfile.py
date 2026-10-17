#!/usr/bin/env python3
"""Conan recipe for wmusic 2.1.1.

wmusic is a dockapp that remote-controls MPRIS-compatible media players.
It uses autotools and depends on libdockapp, playerctl, and X11.

OHOS adaptation: configure is run with --host=aarch64-linux-ohos in
cross-compiling mode (the native --build==--host mode tries to run conftest
binaries which the OHOS sandbox cannot execute). The build uses
/system/bin/sh and AutotoolsDeps for dependency -I/-L flags (the
conan-home .pc files ship with broken prefix paths that don't resolve).
"""

import os
import shlex
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class WmusicConan(ConanFile):
    name = "wmusic"
    version = "2.1.1"
    description = "Remote-control DockApp for MPRIS-compatible media players"
    license = "GPL-2.0"
    homepage = "https://www.dockapps.net/wmusic"
    url = "https://www.dockapps.net/wmusic"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires(
            "libdockapp/0.7.3",
            transitive_headers=True,
            transitive_libs=True,
        )
        self.requires(
            "playerctl/2.4.1",
            transitive_headers=True,
            transitive_libs=True,
        )

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"wmusic supports Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(
            self,
            **self.conan_data["sources"][str(self.version)],
            strip_root=True,
        )

    def generate(self):
        # PkgConfigDeps sets PKG_CONFIG_PATH to find dependency .pc files
        PkgConfigDeps(self).generate()
        AutotoolsDeps(self).generate()
        AutotoolsToolchain(self).generate()

    def build(self):
        apply_conandata_patches(self)
        if str(self.settings.os) == "OHOS":
            self._generate_ohos_configure()
            self._configure_ohos()
            self._run_ohos("make -j1")
        else:
            from conan.tools.gnu import Autotools
            autotools = Autotools(self)
            autotools.configure()
            autotools.make(args=["-j1"])

    def package(self):
        if str(self.settings.os) == "OHOS":
            destination = shlex.quote(self.package_folder)
            self._run_ohos(f"make -j1 install DESTDIR={destination}")
        else:
            from conan.tools.gnu import Autotools
            Autotools(self).install(args=["-j1"])
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "wmusic")
        self.cpp_info.set_property("cmake_target_name", "wmusic::wmusic")
        self.buildenv_info.append_path("PATH", os.path.join(self.package_folder, "bin"))

    def _configure_ohos(self):
        shell = "/system/bin/sh"
        if not os.path.isfile(shell):
            raise ConanInvalidConfiguration(f"OHOS configure shell is missing: {shell}")
        autotools = AutotoolsToolchain(self)
        arguments = [
            f"--srcdir={self.source_folder}",
            "--host=aarch64-linux-ohos",
            *autotools.configure_args,
        ]
        command = " ".join(shlex.quote(argument) for argument in arguments)
        self._run_ohos(f'"{shell}" "{self._ohos_configure_path()}" {command}')

    def _generate_ohos_configure(self):
        upstream = Path(self.source_folder, "configure")
        if not upstream.is_file():
            raise ConanException(f"configure script is missing: {upstream}")
        content = upstream.read_text(encoding="utf-8")
        if content.count("umask 077") != 2:
            raise ConanException("configure umask contract changed")
        generated = self._ohos_configure_path()
        generated.parent.mkdir(parents=True, exist_ok=True)
        generated.write_text(
            content.replace("umask 077", "umask 022"),
            encoding="utf-8",
            newline="\n",
        )

    def _ohos_configure_path(self):
        return Path(self.build_folder, "configure-ohos")

    def _run_ohos(self, command):
        shell = "/system/bin/sh"
        prefix = f"export SHELL={shell} CONFIG_SHELL={shell}; "
        self.run(prefix + command, cwd=self.build_folder, env="conanbuild")
