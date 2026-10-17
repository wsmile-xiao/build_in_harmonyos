#!/usr/bin/env python3
"""Conan recipe for libcanberra 0.30.

libcanberra is the XDG Sound Theme / Name event-sound library (the public
API is canberra.h / libcanberra.so).  The OHOS build compiles the minimal
self-contained configuration and ships the shared library plus a real
consumer test that drives the public ca_context_* / ca_proplist_* API.

Why vorbis is optional here
---------------------------
Upstream configure.ac hard-requires the reference audio decoder:

    PKG_CHECK_MODULES(VORBIS, [ vorbisfile ])   # mandatory, no --disable-*

so a stock configure aborts when libvorbisfile is absent.  The OHPCD artifact
repo does not ship vorbis/libogg, so the generated configure is fed the
documented pkg-config bypass variables instead:

    VORBIS_CFLAGS=-DHAVE_VORBIS=0 VORBIS_LIBS=' '

Both values must be non-empty for the bundled pkg.m4 to take the env branch
and never invoke pkg-config (configure.ac lines 586).  HAVE_VORBIS is *not*
defined anywhere in config.h (no AC_DEFINE in configure.ac), so the two
patches that guard the Ogg Vorbis decoder in the library use the C value
``#if HAVE_VORBIS``; the ``-DHAVE_VORBIS=0`` from VORBIS_CFLAGS reaches every
compilation unit via ``libcanberra_la_CFLAGS = $(AM_CFLAGS) $(VORBIS_CFLAGS)``.
If vorbis/libogg are ever published to the repo, flipping to -DHAVE_VORBIS=1
and adding the conan requirements restores the .ogg decode path untouched.

  * patches/0001  wraps the whole read-vorbis.c decoder behind HAVE_VORBIS
                 (it is the only file that includes <vorbis/vorbisfile.h>).
  * patches/0002  guards the vorbis fallback in read-sound-file.c (open retry,
                 close, channel map, s16 read, size); WAV (read-wav.c) is kept.

Why --with-builtin=null
-----------------------
Drivers (pulse/alsa/gstreamer/...) are loadable modules that would need a
libltdl DSO loader plus a runtime plugin dir, none of which apply on OHOS.
``--with-builtin=null`` compiles exactly one driver (null.c) into
libcanberra.so and turns BUILTIN_DSO off, so no dso.c/driver-order.c and no
``$(LIBLTDL)`` link.  The null driver's driver_play() reports completion
synchronously, which is exactly what a headless smoke test needs.  Upstream
null.c forgets driver_playing() (the DSO wrapper provided it in module mode);
patches/0003 adds the missing function so the shared library links with the
``driver_playing`` reference in common.c.

Build notes
-----------
The release tarball's Makefile.am recurses into ``src gtkdoc doc``.  gtkdoc/
would need the gtk-doc toolchain and doc/ is generated documentation, so the
recipe only builds/installs the ``src`` subdirectory and copies the
configure-substituted libcanberra.pc into place itself.  configure is run in
cross-compiling mode with --host=aarch64-linux-ohos under /system/bin/sh,
following the CI-verified libxrender/0.9.12 pattern (native --build == --host
mode tries to *run* conftest binaries that the OHOS sandbox cannot execute).
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


class LibcanberraConan(ConanFile):
    name = "libcanberra"
    version = "0.30"
    description = "XDG Sound Theme and Name event-sound library"
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
                f"libcanberra supports Linux and OHOS, not {self.settings.os}"
            )

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
                self._run_ohos("make -C src -j1")
            else:
                # Keep a plain host path for local recipe debugging.
                args = self._configure_arguments()
                configure = str(Path(self.source_folder, "configure"))
                self.run(f"{shlex.quote(configure)} {' '.join(args)}", cwd=self.build_folder)
                self.run("make -C src -j1", cwd=self.build_folder)

    def package(self):
        environment = self._build_environment()
        with environment.vars(self).apply():
            if str(self.settings.os) == "OHOS":
                destination = shlex.quote(self.package_folder)
                self._run_ohos(f"make -C src install DESTDIR={destination}")
            else:
                self.run("make -C src install DESTDIR=%s" % shlex.quote(self.package_folder),
                         cwd=self.build_folder)
        self._install_pkgconfig()
        copy(
            self,
            "LGPL",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        # Upstream builds libcanberra.so.0 (libtool -version-info 2:5:2); the
        # conan libs entry must match libcanberra.so so CMakeDeps works.
        self.cpp_info.libs = ["canberra"]
        self.cpp_info.set_property("cmake_file_name", "libcanberra")
        self.cpp_info.set_property("cmake_target_name", "libcanberra::libcanberra")
        self.cpp_info.set_property("pkg_config_name", "canberra")
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
            "--disable-gtk3",
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

    def _install_pkgconfig(self):
        pc_source = Path(self.build_folder, "libcanberra.pc")
        if not pc_source.is_file():
            raise ConanException("configure did not produce libcanberra.pc")
        lib_dir = Path(self.package_folder, "lib")
        if not lib_dir.is_dir():
            raise ConanException(f"installed libdir missing: {lib_dir}")
        pc_dir = lib_dir / "pkgconfig"
        pc_dir.mkdir(parents=True, exist_ok=True)
        destination = pc_dir / "libcanberra.pc"
        if not destination.is_file():
            copy(self, "libcanberra.pc", src=str(self.build_folder), dst=str(pc_dir))
        pc_content = destination.read_text(encoding="utf-8")
        pc_content, count = re.subn(
            r"^prefix=.*$",
            "prefix=${pcfiledir}/../..",
            pc_content,
            count=1,
            flags=re.MULTILINE,
        )
        if count != 1:
            raise ConanException("libcanberra.pc has no unique prefix field")
        destination.write_text(pc_content, encoding="utf-8")

        la_path = lib_dir / "libcanberra.la"
        if la_path.is_file():
            la_path.unlink()
