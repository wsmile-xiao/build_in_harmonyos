#!/usr/bin/env python3
"""Conan recipe for GNU cpio 2.15 on HarmonyOS PC."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class CpioConan(ConanFile):
    name = "cpio"
    version = "2.15"
    description = "GNU cpio archive utility"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/cpio/"
    url = "https://ftp.gnu.org/gnu/cpio/"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "cpio is only supported on Linux/OHOS, not " + str(self.settings.os)
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.extra_cflags.append("-fPIC")
        tc.configure_args.extend(["--disable-mt", "--disable-nls"])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # The release tarball carries older GNU triplet helpers.  Patch only
        # the two target-recognition rules needed by the OHOS cross toolchain.
        replace_in_file(
            self,
            os.path.join(self.source_folder, "build-aux", "config.guess"),
            "case $UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:$UNAME_VERSION in\n",
            "case $UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:$UNAME_VERSION in\n"
            "    aarch64:HarmonyOS:*:*)\n"
            "\tGUESS=aarch64-unknown-linux-ohos\n"
            "\t;;\n",
        )
        config_sub = os.path.join(self.source_folder, "build-aux", "config.sub")
        replace_in_file(
            self,
            config_sub,
            "gnu* | android* | bsd*",
            "gnu* | android* | ohos* | bsd*",
        )
        replace_in_file(
            self,
            config_sub,
            "linux-uclibc*- | linux-mlibc*- )",
            "linux-uclibc*- | linux-mlibc*- | linux-ohos*- )",
        )
        autotools = Autotools(self)
        configure_args = []
        if self.settings.os == "OHOS":
            # The generated configure creates HMDFS-hosted files before its
            # host triplet is initialized, so bind the platform-only umask
            # through the child process environment as well.
            os.environ["CPIO_HMDFS_UMASK"] = "022"
            configure_args.append("--host=aarch64-unknown-linux-ohos")
        autotools.configure(args=configure_args)
        # The release tarball contains generated build files; these explicit
        # no-op tool variables keep install independent from worker utilities.
        autotools.make(args=["-j2", "MAKEINFO=true", "AUTOM4TE=true"])

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["MAKEINFO=true", "AUTOM4TE=true"])

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
