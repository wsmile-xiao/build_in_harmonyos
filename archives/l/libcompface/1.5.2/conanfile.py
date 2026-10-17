#!/usr/bin/env python3
"""Conan recipe for compface 1.5.2 and its libcompface static library."""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.build import can_run
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibcompfaceConan(ConanFile):
    name = "libcompface"
    version = "1.5.2"
    description = "48x48 face image compression library and compface utilities"
    license = "MIT"
    homepage = "https://github.com/SvitloLinux-pkgs/compface"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libcompface supports Linux and OHOS only")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "libcompface 1.5.2 upstream only builds a static library"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)
        # The upstream Makefile has no VPATH support; configure and make
        # must run in the source tree rather than Conan's out-of-source folder.
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(["--enable-static", "--disable-shared"])
        # compface.c and uncompface.c share legacy tentative globals; the
        # combined static library needs common-symbol compatibility.
        tc.extra_cflags.append("-fcommon")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        # The source archive carries install-sh without an executable mode on
        # HMDFS.  Invoke it through the device shell, as the upstream Makefile
        # does not otherwise honor Conan's DESTDIR convention.
        install_sh = os.path.join(self.source_folder, "install-sh")
        install = shlex.quote("/bin/sh %s -c" % install_sh)
        install_data = shlex.quote("/bin/sh %s -c -m 644" % install_sh)
        # The patched Makefile honors DESTDIR; use canonical absolute
        # subdirectories so Conan's package root is not duplicated.
        package_root = self.package_folder
        install_args = [
            "-j1",
            "DESTDIR=%s" % package_root,
            "BINDIR=/bin",
            "LIBDIR=/lib",
            "MANDIR=/man",
            "INCLUDEDIR=/include",
            "INSTALL=%s" % install,
            "INSTALL_PROGRAM=%s" % install,
            "INSTALL_DATA=%s" % install_data,
        ]
        if str(self.settings.os) == "OHOS":
            # The OHOS compiler emits a code-signature section; stripping
            # the installed ELF invalidates it.
            install_args.append("STRIP=:")
        Autotools(self).install(args=install_args)

    def package_info(self):
        self.cpp_info.libs = ["compface"]
        self.cpp_info.bindirs = ["bin"]
