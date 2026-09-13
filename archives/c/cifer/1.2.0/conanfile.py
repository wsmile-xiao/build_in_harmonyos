#!/usr/bin/env python3
"""Conan recipe — cifer 1.2.0 (Makefile project).

Cifer is a classical cipher cracking tool (CLI binary).
Builds with make using readline + ncursesw libraries (static, R26).
No upstream tests exist.
"""
import os

from conan import ConanFile
from conan.tools.files import (
    get, copy, apply_conandata_patches,
    export_conandata_patches, save, load,
)
from conan.tools.layout import basic_layout


class CiferConan(ConanFile):
    name = "cifer"
    version = "1.2.0"
    description = "Automating classical cipher cracking in C"
    license = "GPL-3.0-only"
    homepage = "https://code.google.com/archive/p/cifer/"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("readline/8.3")
        self.requires("ncurses/6.6")

    def layout(self):
        basic_layout(self)
        # cifer builds in-source (Makefile in source dir)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Apply Makefile patch (LDFLAGS=-static, -ldl) via conandata
        apply_conandata_patches(self)

    def build(self):
        # R33: Get compiler from Conan conf dict, NEVER from shell env vars
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c", "clang")
        cflags = self.settings.get_safe("cflags") or ""
        # R26: Static link readline+ncurses to avoid polluting system /lib
        ldflags = "-static"
        if self.settings.build_type == "Release":
            ldflags += " -O2"

        # Get dependency paths
        readline_pkg = self.dependencies["readline"].package_folder
        ncurses_pkg = self.dependencies["ncurses"].package_folder
        rl_inc = os.path.join(readline_pkg, "include")
        rl_lib = os.path.join(readline_pkg, "lib")
        nc_inc = os.path.join(ncurses_pkg, "include")
        nc_lib = os.path.join(ncurses_pkg, "lib")
        inc_flags = f"-I{rl_inc} -I{nc_inc}"
        lib_flags = f"-L{rl_lib} -L{nc_lib}"
        # ncurses/6.6 provides libncursesw (wide-char), not libncurses
        link_libs = "-lreadline -lncursesw -lformw -lmenuw -lpanelw -ldl"

        # Fix cifer-dict shebang: OHOS has no /bin/bash, must use /bin/sh
        # Also fix bash-specific syntax for POSIX sh compatibility
        dict_path = os.path.join(self.source_folder, "cifer-dict")
        if os.path.exists(dict_path):
            content = load(self, dict_path)
            content = content.replace("#!/bin/bash\n", "#!/bin/sh\n")
            content = content.replace("let OUTFILEN=$#-1", "OUTFILEN=$(( $# - 1 ))")
            content = content.replace('TMPFILE=/tmp/cifer-dict-tmp', 'TMPFILE="${TMPDIR:-/tmp}/cifer-dict-tmp"')
            content = content.replace('TMPFILE2=/tmp/cifer-dict-tmp2', 'TMPFILE2="${TMPDIR:-/tmp}/cifer-dict-tmp2"')
            save(self, dict_path, content)

        cmd = (f"make CC={cc} CFLAGS='{cflags} {inc_flags}' "
               f"LINKLIBS='{link_libs}' "
               f"LDFLAGS='{ldflags} {lib_flags}' "
               f"-j1")
        self.run(cmd, cwd=self.source_folder)

    def package(self):
        # Copy binaries from build folder (same as source for in-source build)
        copy(self, "cifer", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "cifer-dict", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "*.1", os.path.join(self.source_folder, "manpages"),
             os.path.join(self.package_folder, "share", "man", "man1"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
