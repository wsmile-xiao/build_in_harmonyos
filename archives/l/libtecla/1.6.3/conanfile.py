#!/usr/bin/env python3
"""Conan 2.x recipe — libtecla 1.6.3 (Tecla command-line editing library)

A C library providing interactive command-line editing, history recall,
filename completion and wild-card expansion (used by e.g. MySQL clients).
Build system: custom make (configure script + Makefile.in). Produces
STATIC libraries only (libtecla.a, libtecla_r.a) plus the libtecla.h
header; the demo programs are examples and are not installed.

Platform note: libtecla is terminal-oriented (termios, signals); the
library itself builds and links cleanly on OHOS. Its interactive line
editing works on an OHOS terminal; file-completion helpers are pure
readdir/stat based.
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LibteclaConan(ConanFile):
    name = "libtecla"
    version = "1.6.3"
    description = "Interactive command-line editing facilities (Tecla library)"
    license = "X11"
    homepage = "https://sites.astro.caltech.edu/~mcs/tecla/"
    url = "https://sites.astro.caltech.edu/~mcs/tecla/"

    # Static-only library (libtecla.a / libtecla_r.a, no shared build).
    package_type = "static-library"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: settings.os check must use in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libtecla supports Linux and OHOS only, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # The upstream tarball's entries carry a "./" prefix, so conan's
        # strip_root only strips "." and the sources land under
        # <source_folder>/libtecla/. Flatten that nested dir so
        # apply_conandata_patches() (base_path=source_folder) can find
        # config.sub/config.guess at the source root.
        nested_source = os.path.join(self.source_folder, "libtecla")
        if os.path.exists(os.path.join(nested_source, "configure")):
            for entry in os.listdir(nested_source):
                shutil.move(os.path.join(nested_source, entry), self.source_folder)
            os.rmdir(nested_source)

    def build(self):
        apply_conandata_patches(self)
        # The upstream tarball's entries carry a "./" prefix, so conan's
        # strip_root only strips "." and the sources land under
        # <source_folder>/libtecla/. Flattening in source() moves them to the
        # source root, so src resolves to source_folder itself. The bundled
        # 2003-era config.guess/config.sub are patched (0001) to recognize
        # the aarch64-linux-ohos triplet, and the triplets are pinned below
        # so no build-type guess runs.
        src = self._src_root()
        # umask 022: HMDFS rejects 700-mode temp dirs created by the build.
        # Regenerate configure with the modern autoconf: the bundled 2003-era
        # configure emits a config.status whose conf-dir machinery fails on
        # OHOS (Permission denied); the modern autoconf-generated one works
        # (cf. libzmf). Then apply the E046 umask fix to the regenerated
        # configure and build.
        self.run(f"cd {src} && autoconf", env="conanbuild")
        self.run(f"cd {src} && sed -i 's/umask 077/umask 022/g' configure", env="conanbuild")
        # Pin the triplets and force the curses/ncurses/termcap probes to fail:
        # OHOS has no curses.h (getline.c only includes it under
        # USE_TERMINFO/USE_TERMCAP, and falls back to VT100 sequences).
        self.run(
            f"cd {src} && chmod +x configure && umask 022 && "
            "./configure --prefix=/usr --build=aarch64-linux-ohos --host=aarch64-linux-ohos "
            "ac_cv_lib_curses_tigetstr=no ac_cv_lib_ncurses_tigetstr=no "
            "ac_cv_lib_curses_tgetstr=no ac_cv_header_curses_h=no ac_cv_header_term_h=no",
            env="conanbuild",
        )
        # The shared-library link invokes ld.lld directly (configure bakes
        # the command into the Makefile); insert the OHOS sysroot -L so the
        # hardcoded -lc resolves (the clang driver normally adds this path).
        sysroot_libs = glob.glob(
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/sysroot/usr/lib/aarch64-linux-ohos"
        )
        if sysroot_libs:
            self.run(
                f"cd {src} && sed -i 's| -lc | -L{sysroot_libs[0]} -lc |g' Makefile",
                env="conanbuild",
            )
        # Build both the normal and reentrant static libraries, skipping the
        # interactive demo programs (they are examples, not packaged).
        self.run(
            f"cd {src} && make -j2 DEMOS= PROGRAMS= PROGRAMS_R=",
            env="conanbuild",
        )

    def package(self):
        # Static libraries + header (the demo programs are examples only).
        src = self._src_root()
        copy(self, "libtecla.a", src, os.path.join(self.package_folder, "lib"))
        copy(self, "libtecla_r.a", src, os.path.join(self.package_folder, "lib"))
        copy(self, "libtecla.h", src, os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE.TERMS", src, os.path.join(self.package_folder, "licenses"))
        copy(self, "README", src, os.path.join(self.package_folder, "res"))

    def _src_root(self):
        """Locate the directory containing the libtecla sources (configure)."""
        import glob

        cfgs = glob.glob(os.path.join(self.source_folder, "**", "configure"), recursive=True)
        if cfgs:
            return os.path.dirname(cfgs[0])
        return self.source_folder

    def package_info(self):
        # Static libs only (libtecla.a -> -ltecla, libtecla_r.a -> -ltecla_r).
        self.cpp_info.libs = ["tecla", "tecla_r"]
        self.cpp_info.bindirs = []
