#!/usr/bin/env python3
"""Conan recipe for util-macros 1.20.1 — X.org M4 macro package.

This package provides xorg-macros.m4, the essential autotools macro set
for all X.org projects.  It is a pure M4 / pkg-config data package with
no compiled artefacts, so package_type is "build-utility".
"""

import os
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class UtilMacrosConan(ConanFile):
    name = "util-macros"
    version = "1.20.1"
    description = "X.org M4 macros (xorg-macros.m4) — build dependency for all X.org autotools projects"
    license = "X11"
    homepage = "https://gitlab.freedesktop.org/xorg/util/util-macros"
    url = ""

    # util-macros installs only M4 macros and a pkg-config file;
    # it has no architecture-specific artefacts.
    package_type = "build-scripts"

    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        # R32: settings.os must be in ("Linux", "OHOS")
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"util-macros supports Linux and OHOS, not {self.settings.os}"
            )

    def package_id(self):
        # M4 macros and pkg-config metadata are target-independent.
        self.info.clear()

    def layout(self):
        basic_layout(self)

    def source(self):
        # Support offline builds: if UTIL_MACROS_LOCAL_SOURCE points to
        # an extracted source directory, copy from there instead of downloading.
        local_src = os.environ.get("UTIL_MACROS_LOCAL_SOURCE", "")
        if local_src and Path(local_src).is_dir():
            copy(self, "*", local_src, self.source_folder)
        else:
            get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # E002: configure generates config.status with "umask 077" which causes
        # Permission denied on temp files. Patch configure before running it.
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure_path):
            replace_in_file(self, configure_path, "umask 077", "umask 022", strict=False)
            for pattern in ("#! /bin/sh", "#!/bin/sh", "#! /bin/bash", "#!/bin/bash"):
                replace_in_file(self, configure_path, pattern,
                                "#!/data/service/hnp/bin/bash", strict=False)
        autotools = Autotools(self)
        autotools.configure()
        # Also patch config.status after configure generates it
        cs_path = os.path.join(self.build_folder, "config.status")
        if os.path.isfile(cs_path):
            replace_in_file(self, cs_path, "umask 077", "umask 022", strict=False)
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        # util-macros provides no libraries, headers, or binaries.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.resdirs = []

        # Export the aclocal directory so that aclocal / autoreconf can
        # locate xorg-macros.m4 via ACLOCAL_PATH.
        self.cpp_info.builddirs = ["share/aclocal"]
        self.cpp_info.set_property("cmake_variables", {"ACLOCAL_PATH": "share/aclocal"})

        # Also expose via pkg-config for consumers that query it.
        self.cpp_info.set_property("pkg_config_name", "util-macros")

        aclocal_dir = os.path.join(self.package_folder, "share", "aclocal")
        pkgconfig_dir = os.path.join(self.package_folder, "share", "pkgconfig")
        self.buildenv_info.append_path("ACLOCAL_PATH", aclocal_dir)
        self.buildenv_info.append_path("PKG_CONFIG_PATH", pkgconfig_dir)
        self.runenv_info.append_path("ACLOCAL_PATH", aclocal_dir)
        self.runenv_info.append_path("PKG_CONFIG_PATH", pkgconfig_dir)
