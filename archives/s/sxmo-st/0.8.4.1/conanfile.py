#!/usr/bin/env python3
"""Conan recipe for sxmo-st 0.8.4.1 — Sxmo terminal emulator for X11.

sxmo-st is a simple terminal emulator (suckless st fork) for the SXMO Linux
mobile environment. It builds with a plain POSIX Makefile against X11, Xft,
fontconfig, and freetype2.

On HarmonyOS, the X11 client libraries are provided by the OHOS-ported
libx11/libxft/fontconfig/freetype/libxrender/xorgproto recipes. The resulting
``st`` binary cannot execute on OHOS (no X11 display server), but the build
produces a functional CLI tool that links against the OHOS X11 client stack.

Upstream has no automated tests (no test directory, no test targets).

Build system: plain POSIX makefile.
"""

import os
import shutil
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class SxmoStConan(ConanFile):
    name = "sxmo-st"
    version = "0.8.4.1"
    description = (
        "St terminal emulator for the Simple X Mobile (Sxmo) environment."
    )
    license = "MIT"
    homepage = "https://git.sr.ht/~mil/sxmo-st"
    url = "https://git.sr.ht/~mil/sxmo-st"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"sxmo-st supports Linux and OHOS, not {self.settings.os}"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libx11/1.8.13", transitive_headers=True)
        self.requires("libxft/2.3.9", transitive_headers=True)
        self.requires("fontconfig/2.18.3", transitive_headers=True)
        self.requires("freetype/2.14.3", transitive_headers=True)
        self.requires("xorgproto/2025.1", transitive_headers=True)
        self.requires("libxrender/0.9.12", transitive_headers=True)

    def build_requirements(self):
        if str(self.settings_build.os) in ("Linux", "OHOS"):
            self.tool_requires("pkgconf/3.0.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"]["0.8.4.1"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        deps = PkgConfigDeps(self)
        deps.set_property("freetype", "pkg_config_name", "freetype2")
        deps.generate()

    def build(self):
        self._rewrite_config_mk()
        self._run_make()

    def package(self):
        self._install_st()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "sxmo-st")
        self.cpp_info.set_property("cmake_target_name", "sxmo-st::sxmo-st")

    # ------------------------------------------------------------------
    # Build internals
    # ------------------------------------------------------------------

    def _dependency_folder(self, name):
        for deps in (
            self.dependencies.host,
            self.dependencies.build,
            self.dependencies.test,
        ):
            try:
                return deps[name].package_folder
            except KeyError:
                continue
        return None

    def _rewrite_config_mk(self):
        """Rewrite config.mk to use conan dependency paths."""
        src_dir = Path(self.source_folder)
        config_mk = src_dir / "config.mk"
        if not config_mk.is_file():
            raise ConanInvalidConfiguration(
                "sxmo-st source missing config.mk"
            )

        libx11_dir = self._dependency_folder("libx11")
        xorgproto_dir = self._dependency_folder("xorgproto")

        # X11 headers are in include/ subdirectory; use -I{include} so
        # #include <X11/Xlib.h> resolves correctly.
        x11_inc = []
        if libx11_dir:
            x11_inc.append(os.path.join(libx11_dir, "include"))
        if xorgproto_dir:
            x11_inc.append(os.path.join(xorgproto_dir, "include"))
        x11_inc_str = " ".join(f"-I{p}" for p in x11_inc) if x11_inc else None
        if not x11_inc_str:
            raise ConanInvalidConfiguration(
                "libx11/xorgproto package folders not found; refusing to "
                "fall back to build-host /usr/include"
            )

        x11_lib = os.path.join(libx11_dir, "lib") if libx11_dir else None
        if not x11_lib:
            raise ConanInvalidConfiguration(
                "libx11 package folder not found; refusing to fall back to "
                "build-host /usr/lib"
            )

        # Collect -I and -L flags from other dependencies.
        # freetype puts headers in include/freetype2/ (Xft.h includes <ft2build.h>).
        # libxrender has X11/extensions/Xrender.h needed by Xft.h.
        extra_inc = []
        extra_lib = []
        for name in ("libxft", "fontconfig", "freetype", "xorgproto", "libxrender"):
            folder = self._dependency_folder(name)
            if not folder:
                continue
            inc = os.path.join(folder, "include")
            lib = os.path.join(folder, "lib")
            if os.path.isdir(inc):
                if name == "freetype":
                    ft2_inc = os.path.join(inc, "freetype2")
                    if os.path.isdir(ft2_inc):
                        extra_inc.append(f"-I{ft2_inc}")
                else:
                    extra_inc.append(f"-I{inc}")
            if os.path.isdir(lib):
                extra_lib.append(f"-L{lib}")

        extra_inc_str = " \\\n                   ".join(extra_inc) if extra_inc else ""
        extra_lib_str = " \\\n                   ".join(extra_lib) if extra_lib else ""

        config_mk.write_text(
            f"""\
# st version
VERSION = 0.8.4.1

# Customize below to fit your system

# paths
PREFIX = {self.package_folder}
MANPREFIX = $(PREFIX)/share/man

X11INC = {x11_inc[0]}
X11LIB = {x11_lib}

# includes and libs
INCS = {x11_inc_str} \\
       {extra_inc_str}
LIBS = -L$(X11LIB) -lm -lrt -lX11 -lutil -lXft -lfontconfig -lfreetype \\
       {extra_lib_str}

# flags
STCPPFLAGS = -DVERSION=\\"$(VERSION)\\" -D_XOPEN_SOURCE=600
STCFLAGS = $(INCS) $(STCPPFLAGS) $(CPPFLAGS) $(CFLAGS)
STLDFLAGS = $(LIBS) $(LDFLAGS)

# compiler and linker
# CC = c99
""",
            encoding="utf-8",
        )

    def _run_make(self):
        """Build sxmo-st using make."""
        src_dir = self.source_folder
        # Override CC to clang (Makefile defaults to c99 which doesn't exist on OHOS)
        # and ensure PKG_CONFIG_PATH includes the dependency pkgconfig dirs.
        pkg_config_paths = []
        for name in ("fontconfig", "freetype", "libx11", "libxft", "xorgproto", "libxrender"):
            folder = self._dependency_folder(name)
            if folder:
                pc_dir = os.path.join(folder, "lib", "pkgconfig")
                if os.path.isdir(pc_dir):
                    pkg_config_paths.append(pc_dir)
        env_vars = f"CC=clang PKG_CONFIG_PATH='{':'.join(pkg_config_paths)}'" if pkg_config_paths else "CC=clang"
        self.run(f"{env_vars} make -C '{src_dir}'")

    def _install_st(self):
        """Install st binary to package bin/."""
        src_dir = Path(self.source_folder)
        bin_dir = Path(self.package_folder) / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        st_src = src_dir / "st"
        if not st_src.is_file():
            # Try make install.
            pkg_config_paths = []
            for name in ("fontconfig", "freetype", "libx11", "libxft", "xorgproto", "libxrender"):
                folder = self._dependency_folder(name)
                if folder:
                    pc_dir = os.path.join(folder, "lib", "pkgconfig")
                    if os.path.isdir(pc_dir):
                        pkg_config_paths.append(pc_dir)
            env_vars = f"CC=clang PKG_CONFIG_PATH='{':'.join(pkg_config_paths)}'" if pkg_config_paths else "CC=clang"
            self.run(f"{env_vars} make -C '{src_dir}' install PREFIX='{self.package_folder}'")
            st_src = src_dir / "st"
        if st_src.is_file():
            dest = bin_dir / "st"
            shutil.copy2(st_src, dest)
            os.chmod(dest, 0o755)
            self.output.info(f"Installed st binary to {dest}")
        else:
            raise ConanInvalidConfiguration(
                "sxmo-st build did not produce 'st' binary."
            )
