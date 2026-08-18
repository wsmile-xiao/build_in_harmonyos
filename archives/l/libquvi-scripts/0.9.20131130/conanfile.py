#!/usr/bin/env python3
"""Conan recipe for libquvi-scripts 0.9.20131130.

libquvi-scripts is a collection of Lua scripts used by libquvi to parse
video links from various websites. This is a pure scripts package — no
binary libraries are produced.

Source: https://repo.or.cz/libquvi-scripts.git (official git hosting)
License: LGPL-2.1-or-later
"""
import os

from conan import ConanFile
from conan.tools.files import (
    get, replace_in_file, save,
    export_conandata_patches, apply_conandata_patches,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibquviScriptsConan(ConanFile):
    name = "libquvi-scripts"
    version = "0.9.20131130"
    description = "Lua scripts for libquvi to parse video links"
    license = "LGPL-2.1-or-later"
    homepage = "https://repo.or.cz/libquvi-scripts.git"

    package_type = "unknown"  # Pure Lua scripts, no binary
    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # automake and libtool are needed for autoreconf (bootstrap)
        # The CI worker may not have them installed
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--without-manual")
        # Note: --without-tests is NOT passed because the AC_ARG_WITH
        # action-if-given triggers PKG_CHECK_MODULES for libquvi even when
        # the value is "no". The default (no flag) correctly skips it.
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # Create VERSION file so gen-ver.sh can detect the version
        # (the source is a git snapshot without .git directory)
        save(self, os.path.join(self.source_folder, "VERSION"),
             "v0.9.20131130")

        # Bootstrap: generate configure script from autotools
        self.run("autoreconf -if", env="conanbuild", cwd=self.source_folder)

        # Fix shebangs for HarmonyOS (E165)
        # /bin/bash -> /data/service/hnp/bin/bash
        # /bin/sh -> /system/bin/sh
        for script_name in ["configure", "config.aux/config.guess",
                            "config.aux/config.sub", "config.aux/install-sh",
                            "config.aux/missing", "bootstrap.sh"]:
            script_path = os.path.join(self.source_folder, script_name)
            if os.path.exists(script_path):
                replace_in_file(self, script_path,
                                "#!/bin/bash",
                                "#!/data/service/hnp/bin/bash",
                                strict=False)
                replace_in_file(self, script_path,
                                "#!/bin/sh",
                                "#!/system/bin/sh",
                                strict=False)

        # Patch config.guess to recognize HarmonyOS platform
        # (autoreconf installs a stock config.guess that doesn't know HarmonyOS)
        config_guess = os.path.join(
            self.source_folder, "config.aux", "config.guess")
        if os.path.exists(config_guess):
            replace_in_file(
                self, config_guess,
                'case $UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:$UNAME_VERSION in\n    *:NetBSD:*:*)',
                'case $UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:$UNAME_VERSION in\n'
                '    *:HarmonyOS:*:*)\n'
                '\tcase "$UNAME_MACHINE" in\n'
                '\t    aarch64|arm64) echo aarch64-unknown-linux-ohos ; exit ;;\n'
                '\t    armv7*|armv8*) echo arm-unknown-linux-ohos ; exit ;;\n'
                '\t    x86_64|amd64)  echo x86_64-unknown-linux-ohos ; exit ;;\n'
                '\t    i?86)         echo i686-unknown-linux-ohos ; exit ;;\n'
                '\t    *)            echo ${UNAME_MACHINE}-unknown-linux-ohos ; exit ;;\n'
                '\tesac\n'
                '\t;;\n'
                '    *:NetBSD:*:*)'
            )

        # Patch configure script to use a fixed temp directory
        # (HMDFS filesystem restricts file creation in mktemp-created subdirs)
        configure = os.path.join(self.source_folder, "configure")
        if os.path.exists(configure):
            replace_in_file(
                self, configure,
                'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&\n  test -d "$tmp"\n}  ||\n{\n  tmp=./conf$$-$RANDOM\n  (umask 077 && mkdir "$tmp")\n} || as_fn_error $? "cannot create a temporary directory in ." "$LINENO" 5',
                'tmp="${TMPDIR:-/tmp}/.confstatus_tmp"\n  rm -rf "$tmp" && mkdir -p "$tmp" && chmod 777 "$tmp"\n} || as_fn_error $? "cannot create a temporary directory" "$LINENO" 5'
            )

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # Pure Lua scripts package — no binary libraries
        # Scripts are installed to share/libquvi-scripts/
        self.cpp_info.resdirs = ["share"]
        # Provide pkg-config file path
        self.cpp_info.set_property("cmake_file_name", "libquvi-scripts")
        self.cpp_info.set_property("pkg_config_name", "libquvi-scripts-0.9")
