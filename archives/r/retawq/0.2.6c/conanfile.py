#!/usr/bin/env python3
"""Conan recipe — retawq 0.2.6c (custom Makefile).

retawq is an interactive, multi-threaded web browser for text terminals.
Build system: classical Makefile (no autotools/cmake).
Depends on ncurses (conan) + pthreads (system).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class RetawqConan(ConanFile):
    name = "retawq"
    version = "0.2.6c"
    description = "Interactive, multi-threaded web browser for text terminals"
    license = "GPL-2.0-or-later"
    homepage = "https://retawq.sourceforge.net/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("ncurses/6.4")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"retawq supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _get_cc(self):
        comp = self.conf.get("tools.build:compiler_executables", check_type=dict, default={})
        return comp.get("c", "clang") if comp else "clang"

    def _get_ncurses_dirs(self):
        """Get ncurses include and lib directories from conan dependencies."""
        inc_dirs = []
        lib_dirs = []
        for dep in self.dependencies.values():
            for incdir in dep.cpp_info.includedirs:
                inc_dirs.append(incdir)
            for libdir in dep.cpp_info.libdirs:
                lib_dirs.append(libdir)
        return inc_dirs, lib_dirs

    def build(self):
        apply_conandata_patches(self)

        cc = self._get_cc()
        inc_dirs, lib_dirs = self._get_ncurses_dirs()

        cflags = ["-fPIC", "-O2", "-D_REENTRANT", "-D_THREAD_SAFE"]
        for incdir in inc_dirs:
            cflags.append(f"-I{incdir}")

        # ncurses conan package provides libncursesw.a (wide character).
        # The Makefile's tool/tgmode expects -lncurses, so we create a local
        # symlink in the build folder (not in the read-only conan cache).
        local_lib = os.path.join(self.build_folder, "_ncurses_link")
        os.makedirs(local_lib, exist_ok=True)
        for libdir in lib_dirs:
            ncursesw = os.path.join(libdir, "libncursesw.a")
            if os.path.exists(ncursesw):
                local_link = os.path.join(local_lib, "libncurses.a")
                if not os.path.exists(local_link):
                    os.symlink(ncursesw, local_link)

        ldflags = [f"-L{local_lib}"]
        for libdir in lib_dirs:
            ldflags.append(f"-L{libdir}")

        cflags_str = " ".join(cflags)
        ldflags_str = " ".join(ldflags)

        src = self.source_folder

        # Build using classical Makefile
        # 'config' target generates .config header with feature defines
        # 'retawqbin' target compiles and links the binary
        self.run(
            f"make -j1 CC='{cc}' CFLAGS='{cflags_str}' LDFLAGS='{ldflags_str}' config",
            env="conanbuild",
            cwd=src,
        )
        self.run(
            f"make -j1 CC='{cc}' CFLAGS='{cflags_str}' LDFLAGS='{ldflags_str}' retawqbin",
            env="conanbuild",
            cwd=src,
        )

    def package(self):
        src = self.source_folder
        bin_dir = os.path.join(self.package_folder, "bin")
        man_dir = os.path.join(self.package_folder, "man", "man1")
        doc_dir = os.path.join(self.package_folder, "doc", "retawq")
        os.makedirs(bin_dir, exist_ok=True)
        os.makedirs(man_dir, exist_ok=True)
        os.makedirs(doc_dir, exist_ok=True)

        self.run(
            f"make install "
            f"PATH_INSTALL_PREFIX={self.package_folder} "
            f"PATH_INSTALL_BIN={bin_dir} "
            f"PATH_INSTALL_MAN={man_dir} "
            f"PATH_INSTALL_DOC={doc_dir}",
            env="conanbuild",
            cwd=src,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.system_libs = ["pthread"]
