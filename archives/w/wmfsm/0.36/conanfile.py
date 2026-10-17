#!/usr/bin/env python3
"""Conan recipe for wmfsm 0.36 (Autotools), a Window Maker filesystem dockapp."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class WmfsmConan(ConanFile):
    name = "wmfsm"
    version = "0.36"
    description = "Window Maker dockapp for monitoring mounted filesystem usage"
    license = "GPL-2.0-or-later"
    homepage = "https://www.dockapps.net/wmfsm"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("x11", "dockapp", "filesystem", "monitor")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if str(self.settings.os) != "OHOS":
            raise ConanInvalidConfiguration(
                "wmfsm/0.36 is packaged for HarmonyOS PC (OHOS) only")
        if str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "wmfsm/0.36 requires the HarmonyOS PC armv8 target")

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # The clean CI image provides autoconf but not automake/aclocal.
        self.tool_requires("automake/1.18")

    def requirements(self):
        # Match the X11 dependency track selected by libdockapp/0.7.3.
        self.requires("libdockapp/0.7.3",
                      transitive_headers=True, transitive_libs=True)
        self.requires("libx11/6.4.0",
                      transitive_headers=True, transitive_libs=True)
        self.requires("libxext/6.4.0",
                      transitive_headers=True, transitive_libs=True)
        self.requires("libxpm/3.5.17",
                      transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)])

    def generate(self):
        AutotoolsDeps(self).generate()
        tc = AutotoolsToolchain(self)
        # Upstream's config.guess does not recognize HarmonyOS uname output.
        tc.configure_args.extend([
            "--build=aarch64-unknown-linux-ohos",
            "--host=aarch64-unknown-linux-ohos",
        ])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # The official release ships configure.ac but no generated configure.
        self.run("unset CONFIG_SHELL; autoreconf -i",
                 cwd=self.source_folder, env="conanbuild")
        self._normalise_config_status_umask()
        autotools = Autotools(self)
        self._configure(autotools)
        autotools.make(args=["-j1"])
        # The upstream archive has no registered test cases; still execute
        # Automake's canonical target and keep its empty result in the log.
        autotools.make(target="check", args=["-j1"])

    def _normalise_config_status_umask(self):
        """Avoid HMDFS permission failures in Autoconf's private temp directory."""
        configure = os.path.join(self.source_folder, "configure")
        try:
            with open(configure, "r", encoding="utf-8") as handle:
                contents = handle.read()
        except OSError as error:
            raise ConanInvalidConfiguration(
                "autoreconf did not produce a readable configure script: {}".format(
                    error))

        marker = "umask 077"
        replacements = contents.count(marker)
        if not replacements:
            raise ConanInvalidConfiguration(
                "generated configure script has no expected Autoconf umask 077 marker")

        with open(configure, "w", encoding="utf-8") as handle:
            handle.write(contents.replace(marker, "umask 022"))
        self.output.info(
            "Normalized {} Autoconf umask 077 marker(s) for HMDFS".format(
                replacements))

    def _dependency_libdirs(self):
        """Return existing lib directories for the complete host dependency graph."""
        found = []
        seen = set()
        for _, dep in self.dependencies.host.items():
            base = dep.package_folder or ""
            for entry in dep.cpp_info.libdirs:
                path = entry if os.path.isabs(entry) else os.path.join(base, entry)
                if os.path.isdir(path) and path not in seen:
                    found.append(path)
                    seen.add(path)
        return found

    def _configure(self, autotools):
        """Unset the HMDFS-incompatible CONFIG_SHELL and run with dependency libs."""
        configure_args = getattr(autotools, "_configure_args", None)
        if configure_args is None:
            self.output.error("Autotools configure arguments are unavailable")
            raise ConanInvalidConfiguration(
                "wmfsm requires the AutotoolsToolchain configure arguments")

        configure = os.path.relpath(
            os.path.join(self.source_folder, "configure"), self.build_folder)
        library_path = ":".join(self._dependency_libdirs())
        self.output.info("configure LD_LIBRARY_PATH=" + library_path)
        self.run(
            "unset CONFIG_SHELL; LD_LIBRARY_PATH=\"" + library_path + "\" "
            + configure + " " + configure_args,
            cwd=self.build_folder,
            env="conanbuild",
        )

    def package(self):
        Autotools(self).install(target="install", args=["-j1"])
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        # This package ships a program, not a C/C++ library.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
