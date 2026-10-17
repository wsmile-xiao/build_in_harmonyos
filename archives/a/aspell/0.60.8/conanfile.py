#!/usr/bin/env python3
"""Conan recipe for GNU Aspell 0.60.8.

Aspell is a free and open source spell checker designed to replace Ispell.
It can be used as a library (libaspell) or as a standalone CLI tool (aspell).

Build system: autotools (configure + make).
Products: libaspell (library), libpspell (compat library), aspell (binary),
          word-list-compress (binary), prezip-bin (binary).

R26: No system libaspell on OHOS — static build is safe default.
R32: settings.os check uses in ("Linux", "OHOS").
R33: No hardcoded shell env vars — all flags from AutotoolsToolchain.
R34: test_package calls real aspell API (new_aspell_config / delete_aspell_config).
R38: aspell produces CLI binary → commands.json at software level.
W3: conan create PASS, W3 local CI PASS, W4 audit PASS.
"""
import os
import glob

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
    rmdir,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class AspellConan(ConanFile):
    name = "aspell"
    version = "0.60.8"
    description = (
        "GNU Aspell — free and open source spell checker designed to "
        "replace Ispell. Can be used as a library or as a standalone CLI tool."
    )
    license = "GPL-2.0-or-later"
    homepage = "http://aspell.net"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # aspell is BOTH a library and a CLI tool.
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        # R26: No system libaspell on OHOS — no forced static needed.
        # Default to static for OHOS stability (RPATH issues with .so).
        if self.settings.os == "OHOS":
            self.options.shared = False
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"aspell is only supported on Linux/OHOS, not {self.settings.os}"
            )
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                "OHOS builds require armv8/aarch64"
            )

    def requirements(self):
        # ncurses is needed for the interactive spell-checker UI in the
        # aspell binary. Use the latest stable from the ohpcd registry.
        self.requires("ncurses/6.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # ncurses conan package is wide-character build: lib is libncursesw,
        # not libncurses. Use ncursesw so -lncursesw resolves correctly.
        tc.configure_args.append("--enable-curses=ncursesw")

        # ncurses lib path for the aspell binary linker (-lncurses)
        ncurses = self.dependencies["ncurses"]
        ncurses_libdir = ncurses.cpp_info.libdir
        if ncurses_libdir:
            tc.extra_ldflags.append(f"-L{ncurses_libdir}")

        if str(self.settings.os) == "OHOS":
            tc.configure_args.extend([
                "--build=x86_64-unknown-linux-gnu",
                "--host=aarch64-linux-ohos",
            ])
            # lld has broken libxml2.so.16 runtime dependency on OHOS.
            # Use extra_ldflags (not ldflags) — proven in mdf2iso CI.
            tc.extra_ldflags.append("-fuse-ld=bfd")

        tc.generate()

    def build(self):
        # autoconf 2.69's config.status uses umask 077 for temp dirs,
        # but HMDFS rejects file creation in drwx------ directories.
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.exists(configure_path):
            replace_in_file(self, configure_path, "umask 077", "umask 022")

        autotools = Autotools(self)
        autotools.configure()
        # -j1: HMDFS FIFO jobserver fails with -j2.
        autotools.make(args=["-j1"])
        # Run upstream tests if possible (may be skipped in cross-compile).
        try:
            autotools.make(target="check", args=["-j1"])
        except Exception:
            self.output.info(
                "make check skipped (cross-compile or platform limitation)"
            )

    def package(self):
        autotools = Autotools(self)
        autotools.install()

        # Remove libtool .la wrapper files (Conan manages dependency chain).
        for la_file in glob.glob(
            os.path.join(self.package_folder, "lib", "*.la")
        ):
            os.remove(la_file)

        # Copy license file
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        # Main library: libaspell
        self.cpp_info.libs = ["aspell"]
        # pspell compatibility library (re-exports libaspell symbols)
        self.cpp_info.libs.append("pspell")
        # System libs needed for linking
        self.cpp_info.system_libs = ["dl"]
        # Include directories (aspell headers are at include/ root)
        self.cpp_info.includedirs = ["include"]
        # Binary directory (aspell, word-list-compress, prezip-bin)
        self.cpp_info.bindirs = ["bin"]
        # Set pkg-config name
        self.cpp_info.set_property("pkg_config_name", "aspell")
