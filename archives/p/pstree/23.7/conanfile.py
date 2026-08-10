#!/usr/bin/env python3
"""Conan recipe — pstree 23.7 (single-file compilation from psmisc).

pstree is a CLI tool that displays running processes as a tree. It is part
of the psmisc suite but can be compiled independently from a single source
file (src/pstree.c).

The full psmisc autotools build requires automake which is not available on
OHOS. Since pstree.c has no exotic dependencies beyond ncurses (wide-char),
we compile it directly:

    clang -DVERSION='"23.7"' -I<ncurses_inc> -o pstree src/pstree.c -lncursesw

OHOS notes:
  - musl libc provides all standard routines (getopt, getpwuid, etc.)
  - SELinux/AppArmor support is disabled by default (not needed on OHOS)
  - statx() is available; if it causes issues, use -DDISABLE_STATX
  - ncurses/6.6 from the OHPCD registry provides libncursesw.a + headers
  - No HAVE_CONFIG_H: we define VERSION directly, skip config.h entirely
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get


class PstreeConan(ConanFile):
    name = "pstree"
    version = "23.7"
    description = "Display a tree of processes (from psmisc)"
    license = "GPL-2.0-only"
    homepage = "https://gitlab.com/psmisc/psmisc"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("pstree", "process", "tree", "psmisc")
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        pass  # No patches needed

    def requirements(self):
        self.requires("ncurses/6.6")

    def validate(self):
        # R32: OHOS must be matched alongside Linux
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"pstree supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        self.folders.root = "src"
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler_c(self):
        # R33: take the compiler from the Conan profile, never from ${CC}
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return executables.get("c") or "clang"

    def build(self):
        cc = self._compiler_c()
        ncurses = self.dependencies["ncurses"]
        inc_dir = ncurses.cpp_info.aggregated_components().includedirs[0]
        lib_dir = ncurses.cpp_info.aggregated_components().libdirs[0]

        cflags = "-O2 -fPIE"
        ldflags = "-pie -Wl,-z,relro,-z,now"
        version_str = '"23.7"'

        self.run(
            f'{cc} {cflags} -DVERSION=\\"{version_str}\\" '
            f'-I"{inc_dir}" '
            f'-o pstree src/pstree.c '
            f'{ldflags} '
            f'-L"{lib_dir}" -lncursesw',
            cwd=self.source_folder,
        )

    def package(self):
        copy(self, "pstree", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        os.chmod(os.path.join(self.package_folder, "bin", "pstree"), 0o755)

    def package_info(self):
        self.cpp_info.libs = []  # pstree is a CLI tool, it ships no library
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
