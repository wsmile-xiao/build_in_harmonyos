#!/usr/bin/env python3
"""Conan recipe for libao-pulse 1.2.2.

libao is the Xiph cross-platform audio output library.  Its drivers are
``dlopen``-ed plugin modules that live in ``<libdir>/ao/plugins-4/``; this
package is the PulseAudio flavour: it builds ``libao.so`` plus the pulse
output plugin (``lib/ao/plugins-4/libpulse.so``) against the platform
``pulseaudio`` package, and no other driver.

OHOS adaptations
----------------
* The upstream tarball is a *git archive*: it ships ``configure.ac`` and
  ``Makefile.am`` but no ``configure``, so ``build()`` bootstraps the build
  with ``autoreconf -fi``.  ``automake``/``libtool`` are pulled in as
  ``tool_requires`` because the OHOS image only carries the autoconf suite
  under ``/data/service/hnp``, and the installed ``automake``/``aclocal``/
  ``libtoolize`` hard-code absolute paths for ``autoconf``/``autom4te``/
  ``sed`` that do not exist here, which is why ``_prepare_autotools_env()``
  re-points those variables at whatever is on PATH (same pattern as
  ``archives/a/abiword-plugin-clarisworks/3.0.8``).
* ``config.guess`` cannot identify HarmonyOS (``uname -s`` is ``HarmonyOS``)
  and its compiler probe fails under the HMDFS temp dir, so ``--build`` and
  ``--host`` are passed explicitly as ``aarch64-unknown-linux-ohos``; the
  ``config.sub`` that comes with ``libtool/2.5.4`` accepts that triplet.
* The freshly generated ``configure`` is rewritten to drop ``umask 077``
  from config.status' temp-directory creation (E114: HMDFS forces setgid, and
  a 0700 directory ends up as ``drwx--S---``, unwritable even for its owner).
* ``make`` runs with ``-j1`` (E074: the HMDFS jobserver fifo returns EPERM).
* Only the PulseAudio plugin is built.  ``--enable-pulse`` is requested and
  the other opt-out drivers are disabled explicitly; the esd/arts/nas/alsa
  probes need libraries the OHOS artifact repository does not publish, and
  the OSS driver — which configure.ac enables from ``<sys/soundcard.h>``
  alone — is switched off through the autoconf header cache because OHOS has
  no ``/dev/dsp``.  See ``_configure_args()`` and ``notes.md``.
* libao bakes its driver-plugin directory in at configure time
  (``AO_PLUGIN_PATH``), and ``configure --prefix=/`` makes that
  ``/lib/ao/plugins-4`` — correct once the package is merged into the root
  filesystem, but unreachable while the package is still consumed from the
  Conan cache (and ``/lib`` is a read-only symlink to ``/system/lib`` on
  OHOS).  ``patches/0001`` lets the environment override the directory, so
  both the consumer test and cache-based consumers can load
  ``lib/ao/plugins-4/libpulse.so``; with the variable unset the compiled-in
  path is used exactly as before.
* ``configure.ac`` finds the plugin's headers/libraries with
  ``PKG_CHECK_MODULES(PULSE, [libpulse-simple >= 0.9])``.  ``pkg-config``
  cannot see the ``pulseaudio`` package unless ``PKG_CONFIG_PATH`` points at
  its ``lib/pkgconfig``; the installed ``.pc`` files record ``prefix=/`` (the
  recipe installs into a staging prefix), so ``PKG_CONFIG_SYSROOT_DIR`` is set
  to the package folder to re-root their ``-I``/``-L`` flags.  Without this the
  check quietly reports ``PULSE live output: no`` and ``src/plugins/pulse``
  builds nothing at all, which is exactly what the "plugin missing" test
  failure described.
* The pulse plugin links ``libpulse-simple.so.0`` and ``libpulse.so.0`` from
  the ``pulseaudio`` package.  The OHOS loader refuses to map an object that
  carries no platform signature (``.codesign``), and the published
  ``pulseaudio/17.0.1`` binaries have no such section, which is why the
  consumer test in ``test_package/test.sh`` resolves those two names against
  the signed platform client libraries and why the plugin's ``DT_NEEDED``
  entries are asserted instead.  ``notes.md`` keeps the full evidence trail.
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


def _prepare_autotools_env():
    """Point the autotools wrappers at the tools that actually exist here.

    The installed automake/aclocal/libtoolize store absolute paths for
    autoconf/autom4te/sed that are absent from this image (same fix as
    archives/a/abiword-plugin-clarisworks/3.0.8)."""
    for tool, variable in (
        ("autoconf", "AUTOCONF"),
        ("autoheader", "AUTOHEADER"),
        ("autom4te", "AUTOM4TE"),
        ("sed", "SED"),
    ):
        if os.environ.get(variable):
            continue
        path = shutil.which(tool)
        if path:
            os.environ[variable] = path


def _drop_umask_077(conanfile, path):
    """E114: HMDFS forces setgid on directories, so ``umask 077 && mktemp -d``
    yields a ``drwx--S---`` directory that even its owner cannot write to.
    Remove the umask from config.status' temp-directory creation."""
    with open(path, "r", encoding="utf-8") as handle:
        data = handle.read()
    data = data.replace(
        'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
        'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`')
    data = data.replace('(umask 077 && mkdir "$tmp")', 'mkdir "$tmp"')
    if "umask 077" in data:
        raise ConanException(
            "configure still creates temp directories with umask 077")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(data)


class LibaoPulseConan(ConanFile):
    name = "libao-pulse"
    version = "1.2.2"
    description = ("libao, the Xiph audio output library, built with the "
                   "PulseAudio output plugin")
    license = "GPL-2.0-or-later"
    homepage = "https://xiph.org/ao/"
    url = "https://gitlab.xiph.org/xiph/libao"
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # The pulse plugin is the whole point of this package; upstream builds
        # every other driver from an optional external library that OHOS does
        # not ship.
        self.requires("pulseaudio/17.0.1")

    def build_requirements(self):
        if str(self.settings.os) == "OHOS":
            # The git archive has no configure script, so autoreconf must run;
            # the image itself only provides the autoconf suite.
            self.tool_requires("automake/1.18")
            self.tool_requires("libtool/2.5.4")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libao-pulse is not supported on {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)],
            strip_root=True)

    def generate(self):
        _prepare_autotools_env()
        AutotoolsDeps(self).generate()
        toolchain = AutotoolsToolchain(self)
        if str(self.settings.os) == "OHOS":
            # config.guess cannot guess HarmonyOS; the library's own target is
            # aarch64-linux-ohos and libtool/2.5.4's config.sub knows the
            # triplet.  --prefix/build/host are the only knobs configure needs.
            toolchain.configure_args.append("--build=aarch64-unknown-linux-ohos")
            toolchain.configure_args.append("--host=aarch64-unknown-linux-ohos")
        toolchain.configure_args.append("--enable-pulse")
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        _prepare_autotools_env()
        self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
        _drop_umask_077(self, os.path.join(self.source_folder, "configure"))
        autotools = Autotools(self)
        with self._pulse_environment().vars(self).apply():
            if str(self.settings.os) == "OHOS":
                autotools.configure(args=self._configure_args())
            else:
                autotools.configure()
            # E074: parallel make trips over the HMDFS jobserver fifo.
            autotools.make(args=["-j1"])

    def _configure_args(self):
        """The configure arguments that make this package the pulse flavour.

        * ``LIBS=`` — AutotoolsDeps aggregates every dependency lib into LIBS
          and configure links LIBS into *every* probe program.  The published
          PulseAudio libraries carry no ``.codesign`` section and the OHOS
          loader refuses to map such an object, so the "is the C compiler
          working?" probe died with "Error loading shared library
          libpulse.so.0".  The pulse flags come from pkg-config instead, which
          never links a probe program, and the probes stay library-free.
        * ``--disable-{esd,arts,nas,alsa}`` — these four drivers are opt-out in
          configure.ac and would otherwise be probed for host libraries; the
          log shows they resolve to "no" anyway, so disabling them only makes
          the build deterministic.
        * ``ac_cv_header_{sys,machine}_soundcard_h=no`` — the OSS driver is
          switched on by the mere presence of ``<sys/soundcard.h>``, which the
          OHOS sysroot ships even though it exposes no ``/dev/dsp``.  Seeding
          the autoconf header cache (the checks honour a pre-set cache
          variable) keeps the package to the PulseAudio plugin alone.
        """
        return [
            "LIBS=",
            "--disable-esd",
            "--disable-arts",
            "--disable-nas",
            "--disable-alsa",
            "ac_cv_header_sys_soundcard_h=no",
            "ac_cv_header_machine_soundcard_h=no",
        ]

    def _pulse_environment(self):
        """Make pkg-config see the PulseAudio dependency.

        ``PKG_CHECK_MODULES(PULSE, [libpulse-simple >= 0.9])`` only succeeds when
        ``pkg-config --exists`` finds ``libpulse-simple.pc``, which lives in the
        ``pulseaudio`` package and not on the default search path.  The installed
        ``.pc`` files were configured with ``prefix=/``, so their ``-I``/``-L``
        flags point at the filesystem root; ``PKG_CONFIG_SYSROOT_DIR`` re-roots
        them onto the package folder in the build cache.  The plugin's
        ``Makefile`` consumes the resulting ``PULSE_CFLAGS``/``PULSE_LIBS``.
        """
        environment = Environment()
        pulseaudio = self.dependencies["pulseaudio"]
        environment.define(
            "PKG_CONFIG_PATH",
            os.path.join(pulseaudio.package_folder, "lib", "pkgconfig"),
        )
        environment.define(
            "PKG_CONFIG_SYSROOT_DIR", pulseaudio.package_folder
        )
        return environment

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # libtool archives bake in build-machine paths and are useless on OHOS.
        for root, _, files in os.walk(self.package_folder):
            for name in files:
                if name.endswith(".la"):
                    os.unlink(os.path.join(root, name))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["ao"]
        self.cpp_info.set_property("cmake_file_name", "ao")
        self.cpp_info.set_property("cmake_target_name", "ao::ao")
        self.cpp_info.set_property("pkg_config_name", "ao")
        pc_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
        self.buildenv_info.append_path("PKG_CONFIG_PATH", pc_dir)
        self.runenv_info.append_path("PKG_CONFIG_PATH", pc_dir)
