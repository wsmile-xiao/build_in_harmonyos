#!/usr/bin/env python3
"""Conan recipe for unixcw 3.5.1 - Morse code library and tools."""
import os
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class UnixcwConan(ConanFile):
    name = "unixcw"
    version = "3.5.1"
    description = "Morse code library (libcw) and command-line tools (cw, cwgen)"
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/unixcw/"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.configure_args.append("--disable-oss")
        tc.configure_args.append("--disable-alsa")
        tc.configure_args.append("--disable-pulseaudio")
        tc.configure_args.append("--build=aarch64-linux-gnu")
        tc.configure_args.append("--host=aarch64-linux-gnu")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Fix HMDFS umask issue: config.status creates temp dirs with umask 077
        # which produces drwx--S--- on HMDFS, blocking file creation inside.
        # Patch configure to use umask 022 instead.
        replace_in_file(self, os.path.join(self.source_folder, "configure"),
                        "(umask 077 && mktemp",
                        "(umask 022 && mktemp")
        replace_in_file(self, os.path.join(self.source_folder, "configure"),
                        "(umask 077 && mkdir",
                        "(umask 022 && mkdir")
        autotools = Autotools(self)
        autotools.configure()
        # Fix: HAVE_LIBINTL_H is detected but libintl.h is not usable on OHOS
        # Undefine it in config.h after configure to use the gettext fallback
        replace_in_file(self, os.path.join(self.build_folder, "src", "config.h"),
                        "#define HAVE_LIBINTL_H 1",
                        "/* #undef HAVE_LIBINTL_H */")
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["cw"]
        self.cpp_info.includedirs = ["include"]
