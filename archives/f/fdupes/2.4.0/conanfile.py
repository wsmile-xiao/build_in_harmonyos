#!/usr/bin/env python3
"""Conan recipe for fdupes 2.4.0.

fdupes is a program for identifying or deleting duplicate files
residing within specified sets of directories.

Build system: autotools (configure + make).
Products: fdupes (CLI binary).

Dependencies (no feature trimming):
  - ncurses: interactive curses-based duplicate file management UI
  - pcre2:   32-bit regex support for ncurses commands (pcre2_match_32)
  - sqlite3: hash database caching for faster duplicate detection

R32: settings.os check uses in ("Linux", "OHOS").
R33: No hardcoded shell env vars — all flags from AutotoolsToolchain.
R34: test_package runs fdupes --version and duplicate-file detection.
R38: fdupes produces CLI binary → commands.json at software level.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class FdupesConan(ConanFile):
    name = "fdupes"
    version = "2.4.0"
    description = (
        "fdupes — program for identifying or deleting duplicate files "
        "residing within specified sets of directories."
    )
    license = "MIT"
    homepage = "https://github.com/adrianlopezroche/fdupes"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"fdupes is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def requirements(self):
        # No feature trimming — all optional dependencies are enabled.
        self.requires("ncurses/6.4")
        self.requires("pcre2/10.45.1")
        self.requires("sqlite3/3.49.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)

        # Explicitly add dependency include/lib paths so configure's
        # AC_CHECK_HEADERS and AC_SEARCH_LIBS can find them.
        # AutotoolsToolchain doesn't automatically propagate all deps.
        for dep_name in ("ncurses", "pcre2", "sqlite3"):
            dep = self.dependencies[dep_name]
            incdir = dep.cpp_info.includedir
            libdir = dep.cpp_info.libdir
            if incdir:
                tc.extra_cflags.append(f"-I{incdir}")
                tc.extra_cxxflags.append(f"-I{incdir}")
            if libdir:
                tc.extra_ldflags.append(f"-L{libdir}")

        if str(self.settings.os) == "OHOS":
            tc.configure_args.extend([
                "--build=x86_64-unknown-linux-gnu",
                "--host=aarch64-linux-ohos",
            ])
            tc.extra_ldflags.append("-fuse-ld=bfd")

        tc.generate()

        # Generate pkg-config files so PKG_CHECK_MODULES([NCURSES], [ncursesw])
        # in configure.ac can find the ncursesw package.
        pkg = PkgConfigDeps(self)
        pkg.generate()

    def build(self):
        # autoconf's config.status uses umask 077 for temp dirs,
        # but HMDFS rejects file creation in drwx------ directories.
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.exists(configure_path):
            replace_in_file(self, configure_path, "umask 077", "umask 022")

        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # -j1: HMDFS FIFO jobserver fails with -j2.
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

        # Copy license file
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        # fdupes is a CLI application, not a library.
        self.cpp_info.bindirs = ["bin"]
