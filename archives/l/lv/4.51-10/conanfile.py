#!/usr/bin/env python3
"""Conan recipe for lv (Leap View) — multi-lingual file viewer/grep tool.

lv is a command-line application built with autotools. The Debian source
tarball has source code in src/ subdirectory, with lv.hlp/lv.1 at the root.

Dependencies: ncurses/tinfo (system libraries from OHOS SDK)
"""
import os
import glob
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches

class LvConan(ConanFile):
    name = "lv"
    version = "4.51-10"
    description = "Powerful multi-lingual file viewer/grep tool"
    license = "GPL-2.0-or-later"
    homepage = "http://www.ff.iij4u.or.jp/~nrt/lv/"
    url = ""

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _find_ncurses_libs(self):
        """Find libtinfo.so.6 and libncurses.so.6 in standard HNP paths.

        HNP (HarmonyOS Native Platform) root is /data/service/hnp on all
        OHOS systems. Search recursively for terminfo shared libraries.
        """
        hnp_root = "/data/service/hnp"
        tinfo = None
        ncurses = None
        for f in glob.glob(os.path.join(hnp_root, "**", "libtinfo.so.6"), recursive=True):
            tinfo = f
            break
        for f in glob.glob(os.path.join(hnp_root, "**", "libncurses.so.6"), recursive=True):
            ncurses = f
            break
        return tinfo, ncurses

    def generate(self):
        """Create libtinfo.so/libncurses.so symlinks for configure detection.

        OHOS SDK ships libtinfo.so.6 (contains tgetstr) and libncurses.so.6
        but without unversioned .so symlinks. configure's AC_CHECK_LIB
        needs libncurses.so or libtinfo.so to pass the link test.
        """
        tinfo, ncurses = self._find_ncurses_libs()
        libdir = os.path.join(self.build_folder, ".termlib")
        os.makedirs(libdir, exist_ok=True)
        if tinfo:
            link = os.path.join(libdir, "libtinfo.so")
            if not os.path.exists(link):
                os.symlink(tinfo, link)
        if ncurses:
            link = os.path.join(libdir, "libncurses.so")
            if not os.path.exists(link):
                os.symlink(ncurses, link)

    def build(self):
        apply_conandata_patches(self)
        src_dir = os.path.join(self.source_folder, "src")
        libdir = os.path.join(self.build_folder, ".termlib")
        prefix = self.package_folder

        # LIBS=-ltinfo makes configure's link test find tgetstr:
        # AC_CHECK_LIB(ncurses, tgetstr) tests -lncurses $LIBS,
        # and tgetstr is in libtinfo, not libncurses on OHOS.
        self.run(
            f'cd {src_dir} && '
            f'LIBS="-ltinfo" '
            f'LDFLAGS="-L{libdir}" '
            f'LIBRARY_PATH="{libdir}:$LIBRARY_PATH" '
            f'./configure --prefix={prefix}'
        )
        self.run(f'cd {src_dir} && make -j1')

    def package(self):
        src_dir = os.path.join(self.source_folder, "src")
        libdir = os.path.join(self.build_folder, ".termlib")
        prefix = self.package_folder

        # Pre-create directories (install-sh doesn't create bindir)
        os.makedirs(os.path.join(prefix, "bin"), exist_ok=True)
        os.makedirs(os.path.join(prefix, "lib", "lv"), exist_ok=True)
        os.makedirs(os.path.join(prefix, "man", "man1"), exist_ok=True)

        self.run(
            f'cd {src_dir} && '
            f'LD_LIBRARY_PATH="{libdir}:$LD_LIBRARY_PATH" '
            f'make install'
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.system_libs = ["ncurses", "tinfo"]
