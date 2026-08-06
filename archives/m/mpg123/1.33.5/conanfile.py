#!/usr/bin/env python3
"""Conan recipe for mpg123 1.33.5 — MPEG Audio Layer 1/2/3 decoder.

Build system: autotools (configure + make).
mpg123 provides:
  - Libraries: libmpg123 (MP3 decoder), libout123 (audio output), libsyn123 (synthesis)
  - Executables: mpg123 (player), mpg123-id3dump, mpg123-strip, out123
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, replace_in_file, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class Mpg123Conan(ConanFile):
    name = "mpg123"
    version = "1.33.5"
    description = "Fast MPEG Audio Layer 1/2/3 decoder and player"
    license = "LGPL-2.1-or-later"
    homepage = "https://www.mpg123.de/"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("mpg123 is adapted for Linux and OHOS only")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.configure_args.append("--disable-modules")
        is_ohos = str(self.settings.os) == "OHOS"
        if is_ohos:
            env = tc.environment()
            cc = shutil.which("clang") or "clang"
            cxx = shutil.which("clang++") or "clang++"
            env.define("CC", cc)
            env.define("CXX", cxx)
            shell = shutil.which("bash") or "/system/bin/sh"
            env.define("CONFIG_SHELL", shell)
            env.define("SHELL", shell)
            tc.generate(env=env)
        else:
            tc.generate()

    def build(self):
        apply_conandata_patches(self)
        if str(self.settings.os) == "OHOS":
            self._patch_ohos()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["mpg123", "out123", "syn123"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]

    def _patch_ohos(self):
        # E165: fix shebang (/bin/sh does not exist on OHOS)
        configure_path = os.path.join(self.source_folder, "configure")
        replace_in_file(self, configure_path, "#! /bin/sh", "#!/system/bin/sh")
        # E110: HMDFS umask 077 restricts temp file creation
        replace_in_file(self, configure_path, "umask 077", "umask 022")
        # E007: config.guess — add HarmonyOS detection before *:NetBSD:*:*)
        cg_path = os.path.join(self.source_folder, "build", "config.guess")
        replace_in_file(self, cg_path,
            "    *:NetBSD:*:*)",
            '    *:HarmonyOS:*:*)\n'
            '\tcase "$UNAME_MACHINE" in\n'
            '\t    aarch64|arm64) MACHINE=aarch64 ;;\n'
            '\t    armv7*|armv8*) MACHINE=arm ;;\n'
            '\t    x86_64|amd64)  MACHINE=x86_64 ;;\n'
            '\t    i?86)         MACHINE=i686 ;;\n'
            '\t    *)            MACHINE="$UNAME_MACHINE" ;;\n'
            '\tesac\n'
            '\techo ${MACHINE}-unknown-linux-ohos\n'
            '\texit ;;\n\n'
            '    *:NetBSD:*:*)')
        # E007: config.sub — add ohos-linux after android-linux block
        cs_path = os.path.join(self.source_folder, "build", "config.sub")
        replace_in_file(self, cs_path,
            "\t\t\tandroid-linux)\n"
            "\t\t\t\tbasic_machine=$field1-unknown\n"
            "\t\t\t\tbasic_os=linux-android\n"
            "\t\t\t\t;;\n"
            "\t\t\t*)",
            "\t\t\tandroid-linux)\n"
            "\t\t\t\tbasic_machine=$field1-unknown\n"
            "\t\t\t\tbasic_os=linux-android\n"
            "\t\t\t\t;;\n"
            "\t\t\tohos-linux)\n"
            "\t\t\t\tbasic_machine=$field1-unknown\n"
            "\t\t\t\tbasic_os=linux-ohos\n"
            "\t\t\t\t;;\n"
            "\t\t\t*)")
        # E007: config.sub — add ohos* to portable OS list
        replace_in_file(self, cs_path,
            "gnu* | android* | bsd*",
            "gnu* | android* | ohos* | bsd*")
        # E007: config.sub — add linux-ohos* to kernel-OS validation
        replace_in_file(self, cs_path,
            "| linux-musl* | linux-relibc* | linux-uclibc* )",
            "| linux-musl* | linux-ohos* | linux-relibc* | linux-uclibc* )")
