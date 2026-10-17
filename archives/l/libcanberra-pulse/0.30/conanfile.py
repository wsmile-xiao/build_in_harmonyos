#!/usr/bin/env python3
"""Conan recipe for libcanberra-pulse 0.30.

libcanberra is the XDG Sound Theme / Name event-sound library (the public API
is canberra.h / libcanberra.so).  archives/l/libcanberra/0.30 builds the
self-contained null driver; THIS recipe is the PulseAudio flavour: the pulse
driver is compiled *into* libcanberra.so (--with-builtin=pulse), so the shared
library actually talks to a PulseAudio server instead of swallowing every
event.  The installed package is the same libcanberra.so.0 with a hard runtime
dependency on the PulseAudio client library.

Why vorbis is optional here
---------------------------
Upstream configure.ac hard-requires the reference audio decoder:

    PKG_CHECK_MODULES(VORBIS, [ vorbisfile ])   # mandatory, no --disable-*

so a stock configure aborts when libvorbisfile is absent.  The OHPCD artifact
repo does not ship vorbis/libogg, so the generated configure is fed the
documented pkg-config bypass variables instead:

    VORBIS_CFLAGS=-DHAVE_VORBIS=0 VORBIS_LIBS=' '

Both values must be non-empty for the bundled pkg.m4 to take the env branch
and never invoke pkg-config (configure.ac line 586).  HAVE_VORBIS is *not*
defined anywhere in config.h (no AC_DEFINE in configure.ac), so the two
patches that guard the Ogg Vorbis decoder use the C value
'#if HAVE_VORBIS'; the -DHAVE_VORBIS=0 from VORBIS_CFLAGS reaches every
compilation unit via libcanberra_la_CFLAGS = $(AM_CFLAGS) $(VORBIS_CFLAGS).
WAV (read-wav.c) decoding is kept.

Why --with-builtin=pulse
------------------------
Drivers are normally loadable modules (libcanberra-pulse.so in the plugin
directory) that need a libltdl DSO loader plus a runtime plugin directory.
With --with-builtin=pulse configure compiles pulse.c straight into
libcanberra.so, forces HAVE_ALSA/HAVE_OSS/HAVE_GSTREAMER/HAVE_NULL to 0, and
leaves BUILTIN_DSO at 0, so no dso.c/driver-order.c and no $(LIBLTDL) link is
needed (patches/0005 stops configure from aborting on the missing libltdl).
pulse.c defines driver_playing(), which common.c calls unconditionally, so no
extra patch is required - unlike the null driver, for which
archives/l/libcanberra/0.30 needs patches/0003.

The pulse dependency is resolved by the same PKG_CHECK_MODULES(PULSE,
[libpulse >= 0.9.11]) that configure.ac uses for the module build.  The
published pulseaudio/17.0.1 package ships lib/pkgconfig/libpulse.pc but the
file records prefix=/ (recipes install into a staging prefix), so
_build_environment() points PKG_CONFIG_PATH at that directory and
PKG_CONFIG_SYSROOT_DIR at the package folder to re-root the -I/-L flags.

AutotoolsDeps aggregates every dependency library into LIBS, and configure
links LIBS into each probe program.  The published PulseAudio libraries carry
no .codesign section, which the OHOS loader refuses to map, so configure dies
with 'cannot run C compiled programs' unless LIBS is emptied for the probes;
the driver flags reach the build through PULSE_CFLAGS/PULSE_LIBS instead.

Build notes
-----------
The release tarball's Makefile.am recurses into 'src gtkdoc doc'.  gtkdoc/
would need the gtk-doc toolchain and doc/ is generated documentation, so the
recipe only builds/installs the 'src' subdirectory and copies the
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


class LibcanberraPulseConan(ConanFile):
    name = "libcanberra-pulse"
    version = "0.30"
    description = ("XDG Sound Theme and Name event-sound library, built with "
                   "the PulseAudio driver compiled in")
    license = "LGPL-2.1-or-later"
    homepage = "http://0pointer.de/lennart/projects/libcanberra/"
    url = "http://0pointer.de/lennart/projects/libcanberra/"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def requirements(self):
        # The built-in pulse driver links libpulse directly, so the library
        # has a hard runtime dependency on the PulseAudio client library.
        self.requires("pulseaudio/17.0.1")

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
        # configure.ac resolves the driver with PKG_CHECK_MODULES(PULSE,
        # [libpulse >= 0.9.11]).  The dependency's .pc files live inside the
        # package folder and record prefix=/ (staging prefix), so point
        # pkg-config at them and re-root their -I/-L flags onto that folder.
        pulseaudio = self.dependencies["pulseaudio"]
        environment.define(
            "PKG_CONFIG_PATH",
            os.path.join(pulseaudio.package_folder, "lib", "pkgconfig"),
        )
        environment.define("PKG_CONFIG_SYSROOT_DIR", pulseaudio.package_folder)
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
            # Compile the PulseAudio driver into libcanberra.so; configure then
            # forces HAVE_ALSA/HAVE_OSS/HAVE_GSTREAMER/HAVE_NULL to 0.
            "--with-builtin=pulse",
            "--enable-pulse",
            "--disable-null",
            "--disable-alsa",
            "--disable-oss",
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
            # AutotoolsDeps aggregates every dependency lib into LIBS and
            # configure links LIBS into *every* probe program.  The published
            # PulseAudio libraries carry no .codesign section and the OHOS
            # loader refuses to map such an object, so the "is the C compiler
            # working?" probe would die with "Error loading shared library
            # libpulse.so.0".  Emptying the autoconf precious variable keeps
            # the probes library-free; the driver flags arrive through
            # PULSE_CFLAGS/PULSE_LIBS instead.
            "LIBS=",
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
