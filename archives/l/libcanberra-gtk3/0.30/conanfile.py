#!/usr/bin/env python3
"""Conan recipe for libcanberra-gtk3 0.30.

libcanberra-gtk3 is the GTK3 binding of the XDG Sound Theme / Name
event-sound library.  The OHOS build compiles only the GTK3 targets
against the broadway GTK3 stack (no X11) and ships the GTK3 shared
library, the GTK3 module, the public header and the pkg-config file.
The core libcanberra.so is provided by the libcanberra/0.30 package.

Broadway compatibility
----------------------
Upstream configure.ac hard-requires X11 in the GTK3 pkg-config probe:

    PKG_CHECK_MODULES(GTK3, [ gtk+-3.0 gthread-2.0 glib-2.0 >= 2.32 gdk-3.0 x11 ])

and the GTK3 sources include <gdk/gdkx.h> / <X11/Xatom.h> and call
XGetWindowProperty / GDK_WINDOW_ID / XInternAtom unconditionally.
The ohpcd gtk/3.24.43 package is built broadway-only (gdkconfig.h has
GDK_WINDOWING_X11 undefined), so the stock configure aborts and the
sources do not compile.  patches/0007 removes x11 from the pkg-config
probe (in both configure.ac and the generated configure) and guards
every X11 include and X11-only code path behind #ifdef GDK_WINDOWING_X11:

  * canberra-gtk.c / canberra-gtk-module.c: include guards;
  * window_get_desktop / display_get_desktop / window_is_xembed helpers
    (X11 property queries) are compiled out;
  * the X11-only property sets in ca_gtk_proplist_set_for_screen /
    ca_gtk_proplist_set_for_widget / dispatch_sound_event are guarded;
  * libcanberra-gtk3.pc.in drops -lX11 and uses the published core pc
    name (Requires: canberra gtk+-3.0, Libs: -lcanberra).

Build notes
-----------
The release tarball's src/Makefile.am builds the core libcanberra.la
too.  The recipe builds the core library (needed at link time for the
GTK3 targets) but only packages the GTK3 artifacts, mirroring the
libportal-gtk3 pattern: core libcanberra.so belongs to libcanberra/0.30.
configure is run in OHOS cross mode with --host=aarch64-linux-ohos
under /system/bin/sh, following the CI-verified libcanberra/0.30
pattern (config.guess/config.sub patches, umask 022 rewrite).
"""

import os
import re
import shlex
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import (
    Autotools,
    AutotoolsDeps,
    AutotoolsToolchain,
    PkgConfigDeps,
)
from conan.tools.layout import basic_layout


class LibcanberraGtk3Conan(ConanFile):
    name = "libcanberra-gtk3"
    version = "0.30"
    description = "GTK3 bindings for the XDG Sound Theme and Name event-sound library"
    license = "LGPL-2.1-or-later"
    homepage = "http://0pointer.de/lennart/projects/libcanberra/"
    url = "http://0pointer.de/lennart/projects/libcanberra/"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libcanberra-gtk3 supports Linux and OHOS, not {self.settings.os}"
            )

    def requirements(self):
        self.requires("libcanberra/0.30", transitive_headers=True, transitive_libs=True)
        self.requires("gtk/3.24.43", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(
            self,
            **self.conan_data["sources"][str(self.version)],
            strip_root=True,
        )

    def generate(self):
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()
        self._autotools_toolchain().generate()

    def build(self):
        apply_conandata_patches(self)
        environment = self._build_environment()
        with environment.vars(self).apply():
            if str(self.settings.os) == "OHOS":
                self._generate_ohos_configure()
                self._configure_ohos()
                self._run_ohos(
                    "make -C src libcanberra.la libcanberra-gtk3.la "
                    "libcanberra-gtk3-module.la -j1"
                )
            else:
                args = self._configure_arguments()
                configure = str(Path(self.source_folder, "configure"))
                self.run(f"{shlex.quote(configure)} {' '.join(args)}", cwd=self.build_folder)
                self.run(
                    "make -C src libcanberra.la libcanberra-gtk3.la "
                    "libcanberra-gtk3-module.la -j1",
                    cwd=self.build_folder,
                )

    def package(self):
        self._install_library()
        self._install_module()
        self._install_header()
        self._install_pkgconfig()
        copy(
            self,
            "LGPL",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["canberra-gtk3"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("cmake_file_name", "libcanberra-gtk3")
        self.cpp_info.set_property("cmake_target_name", "libcanberra-gtk3::libcanberra-gtk3")
        self.cpp_info.set_property("pkg_config_name", "libcanberra-gtk3")
        pc_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
        self.buildenv_info.append_path("PKG_CONFIG_PATH", pc_dir)
        self.runenv_info.append_path("PKG_CONFIG_PATH", pc_dir)

    def _build_environment(self):
        temporary = Path(self.build_folder, ".tmp")
        temporary.mkdir(parents=True, exist_ok=True)
        environment = Environment()
        environment.define_path("TMPDIR", str(temporary))
        # Both variables must be non-empty to take pkg.m4's env bypass branch
        # and never probe pkg-config for the mandatory vorbisfile dependency.
        environment.define("VORBIS_CFLAGS", "-DHAVE_VORBIS=0")
        environment.define("VORBIS_LIBS", " ")
        if str(self.settings.os) == "OHOS":
            environment.define("MKDIR_P", "/system/bin/mkdir -p")
        return environment

    def _autotools_toolchain(self):
        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.extend(
            argument
            for argument in self._configure_arguments()
            if argument not in toolchain.configure_args
        )
        return toolchain

    def _configure_arguments(self):
        library_args = (
            ("--enable-shared", "--disable-static")
            if self.options.shared
            else ("--disable-shared", "--enable-static")
        )
        return list(library_args) + [
            "--with-builtin=null",
            "--disable-alsa",
            "--disable-oss",
            "--disable-pulse",
            "--disable-gstreamer",
            "--disable-udev",
            "--disable-gtk",
            "--enable-gtk3",
            "--disable-tdb",
            "--disable-lynx",
            "--disable-gtk-doc",
            "--with-systemdsystemunitdir=no",
        ]

    def _configure_ohos(self):
        shell = "/system/bin/sh"
        if not os.path.isfile(shell):
            raise ConanInvalidConfiguration(f"OHOS configure shell is missing: {shell}")
        configure = self._ohos_configure_path()
        configure_args = [
            f"--srcdir={self.source_folder}",
            "--host=aarch64-linux-ohos",
            *self._autotools_toolchain().configure_args,
        ]
        arguments = " ".join(shlex.quote(argument) for argument in configure_args)
        self._run_ohos(f'"{shell}" "{configure}" {arguments}')

    def _generate_ohos_configure(self):
        upstream = Path(self.source_folder, "configure")
        if not upstream.is_file():
            raise ConanException(f"configure script is missing: {upstream}")
        generated = self._ohos_configure_path()
        content = upstream.read_text(encoding="utf-8")
        needle = "umask 077"
        if content.count(needle) != 2:
            raise ConanException("configure umask contract changed")
        generated.parent.mkdir(parents=True, exist_ok=True)
        generated.write_text(
            content.replace(needle, "umask 022"),
            encoding="utf-8",
            newline="\n",
        )

    def _ohos_configure_path(self):
        return Path(self.build_folder, "configure-ohos")

    def _run_ohos(self, command):
        shell = "/system/bin/sh"
        prefix = f"export SHELL={shell} CONFIG_SHELL={shell}; "
        self.run(prefix + command, cwd=self.build_folder, env="conanbuild")

    def _install_library(self):
        """Copy libcanberra-gtk3.so.0.1.9 and create real-copy aliases.

        The upstream libtool version-info 1:9:1 yields soname
        libcanberra-gtk3.so.0 and real file libcanberra-gtk3.so.0.1.9.
        Real copies (not symlinks) follow the gtk/libportal-gtk3 OHOS
        pattern: HMDFS does not reliably support symlinks for dev aliases.
        """
        libs = os.path.join(self.build_folder, "src", ".libs")
        real = os.path.join(libs, "libcanberra-gtk3.so.0.1.9")
        if not os.path.isfile(real):
            raise ConanException(f"built GTK3 library missing: {real}")
        libdir = Path(self.package_folder, "lib")
        libdir.mkdir(parents=True, exist_ok=True)
        destination = libdir / "libcanberra-gtk3.so.0.1.9"
        copy(self, "libcanberra-gtk3.so.0.1.9", src=libs, dst=str(libdir))
        for alias in ("libcanberra-gtk3.so.0", "libcanberra-gtk3.so"):
            alias_path = libdir / alias
            if alias_path.exists() or alias_path.is_symlink():
                alias_path.unlink()
            alias_path.write_bytes(destination.read_bytes())

    def _install_module(self):
        """Copy the GTK3 module and its unversioned compatibility name."""
        libs = os.path.join(self.build_folder, "src", ".libs")
        real = os.path.join(libs, "libcanberra-gtk3-module.so")
        if not os.path.isfile(real):
            raise ConanException(f"built GTK3 module missing: {real}")
        module_dir = Path(self.package_folder, "lib", "gtk-3.0", "modules")
        module_dir.mkdir(parents=True, exist_ok=True)
        copy(self, "libcanberra-gtk3-module.so", src=libs, dst=str(module_dir))
        compatibility = module_dir / "libcanberra-gtk-module.so"
        if compatibility.exists() or compatibility.is_symlink():
            compatibility.unlink()
        compatibility.write_bytes((module_dir / "libcanberra-gtk3-module.so").read_bytes())

    def _install_header(self):
        copy(
            self,
            "canberra-gtk.h",
            src=os.path.join(self.source_folder, "src"),
            dst=os.path.join(self.package_folder, "include"),
            keep_path=False,
        )

    def _install_pkgconfig(self):
        pc_source = Path(self.build_folder, "libcanberra-gtk3.pc")
        if not pc_source.is_file():
            raise ConanException("configure did not produce libcanberra-gtk3.pc")
        pc_dir = Path(self.package_folder, "lib", "pkgconfig")
        pc_dir.mkdir(parents=True, exist_ok=True)
        destination = pc_dir / "libcanberra-gtk3.pc"
        copy(self, "libcanberra-gtk3.pc", src=self.build_folder, dst=str(pc_dir))
        pc_content = destination.read_text(encoding="utf-8")
        pc_content, count = re.subn(
            r"^prefix=.*$",
            "prefix=${pcfiledir}/../..",
            pc_content,
            count=1,
            flags=re.MULTILINE,
        )
        if count != 1:
            raise ConanException("libcanberra-gtk3.pc has no unique prefix field")
        destination.write_text(pc_content, encoding="utf-8")
