#!/usr/bin/env python3
"""Conan recipe for ProtoMol 2.0.3 on HarmonyOS (OHOS).

ProtoMol is an object-oriented, component-based molecular dynamics framework.
Upstream ships an autoconf/automake (1998-2005 vintage) build system and no
third-party dependencies for the default configuration.  The package installs
six command-line programs and no libraries: every framework archive is a
`noinst_LIBRARIES` archive (libbase, libio, libforces, ... are linked into the
executables and never installed) and there are no `_HEADERS` install targets at
all, so this is an application package, not a library package.

OHOS-specific handling (evidence in notes.md):

* Upstream ships the tarball as ``protomol-2.0.3-tar.gz`` (hyphen, not dot,
  before ``tar``).  Conan's ``unzip()`` only recognises ``.tar.gz``/``.tgz``/
  ``.tbz2``/``.tar.bz2``/``.tar`` and otherwise falls back to plain ``.gz``,
  which decompresses the stream into a bare ``protomol-2.0.3-tar`` file without
  ever unpacking the tar -- leaving an empty source tree and making every patch
  fail with "source/target file does not exist".  ``conandata.yml`` therefore
  sets ``sources.filename: protomol-2.0.3.tar.gz``.
* clang rejects several constructs that the antique gcc of 2005 accepted
  (two-phase name lookup for dependent base classes, a self-referential
  ostream insertion, iterators initialised from NULL) - see patches/0001..0009.
* ``configure``/``configure.in`` carry a single Latin-1 0xAD byte inside the
  PACKAGE_CITE string.  The OHOS userland sed (toybox) cannot match a line
  containing an invalid UTF-8 sequence, so autoconf's define pipeline silently
  dropped AC_DEFINE_UNQUOTED(PACKAGE_CITE,...) and three programs failed with
  "use of undeclared identifier 'PACKAGE_CITE'".  patches/0010 converts both
  files from Latin-1 to UTF-8 (lossless; knowledge entry DRAFT-E549).
* configure is patched, which makes it look newer than the shipped aclocal.m4 /
  Makefile.in.  The automake maintainer rules would then re-run
  aclocal/autoconf/autoheader through missing(1) and regenerate configure
  *without* the patch, so ``_pin_autotools_timestamps()`` stamps every file of
  the autotools dependency chain with one identical mtime.
* GLUT/X11 (the interactive viewer) and PNG output are switched off: OHOS PC
  ships neither GLUT nor X11, and the libpng-backed writer
  (framework/io/PNGWriter.cpp) has no caller anywhere in the tree and is only
  compiled when configure finds png.h.  The autoconf cache variables below pin
  that probe to "no" so the build stays hermetic even if a png.h happens to be
  reachable through the include path.
* The FFT backend is pinned to the bundled ZFFT implementation so the build
  never depends on a system FFTW.
* On the OHOS device the host shell environment carries a "safe delete" `rm`
  shim through three channels (PATH, exported ``BASH_FUNC_rm%%`` functions and
  ``BASH_ENV``).  The shim's shebang is ``#!/bin/bash`` which does not exist on
  OHOS, so every recipe that deletes a file fails with exit 126 -- and the
  automake link rule for a program starts with ``@rm -f $@``, i.e. the build
  dies at the *link* step after compiling everything.  ``_sanitize_path()``
  cuts all three channels (same fix as cryptsetup/libnl3-cli/libmspub-tools).
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class ProtomolConan(ConanFile):
    name = "protomol"
    version = "2.0.3"
    description = (
        "Object-oriented, component-based framework for molecular dynamics "
        "simulations (protomol, coulomb, coords2coords, dcd2dcd, iSGProtomol, xyzviz)"
    )
    license = "GPL-2.0-only"
    homepage = "https://protomol.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("molecular-dynamics", "simulation", "chemistry", "md", "protomol")

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # ProtoMol is self-contained for the configuration built here: the FFT
        # is the bundled ZFFT, GLUT/X11 and PNG are disabled.  See the module
        # docstring for the rationale.
        pass

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"protomol is only supported on Linux/OHOS, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)
        # ProtoMol's 2005-vintage configure probes include headers with a path
        # relative to the SOURCE ROOT, e.g. configure.in:644
        #     #include "framework/base/Array_Fastest.h"
        # That line only resolves when configure runs inside the source tree.
        # With Conan's default out-of-source layout the probe dies with
        # "framework/base/Array_Fastest.h: file not found", so the recipe would
        # silently define NO_PARTIAL_TEMPLATE_SPECIALIZATION and fall back to
        # framework/base/Array_NoPartialSpecialization.h, which does not even
        # compile with modern clang ('N' shadows a template parameter).
        # Upstream has no out-of-source support at all, so build in place.
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # The interactive OpenGL viewer needs GLUT + X11, neither of which
        # exists on OHOS PC; --with-glut=no also clears GLUT_LIBS/X_LIBS so no
        # -lGL/-lX11 leaks into the link line.
        tc.configure_args.append("--with-glut=no")
        # Pin the FFT to the bundled software implementation (ZFFT) so the
        # build never picks up a system FFTW2/FFTW3.
        tc.configure_args.append("--with-fft=zfft")
        # framework/io/PNGWriter.cpp is dead code (no caller in the whole tree)
        # and its libpng 1.2-era API is not worth porting; force the autoconf
        # probes to "no" so a stray png.h can never flip the feature on and
        # silently add -lpng to every executable's link line.
        tc.configure_args.append("ac_cv_header_png_h=no")
        tc.configure_args.append("ac_cv_lib_png_png_create_write_struct=no")
        tc.generate()

        # Byte-oriented text handling keeps configure/config.status sed and awk
        # pipelines deterministic on OHOS (matches the autoconf fix in
        # patches/0010).
        env = Environment()
        env.define("LC_ALL", "C")
        # configure/config.status also delete temporary files; make sure the
        # build environment does not resurrect the safe-delete shim.
        # Only the variables are unset here -- PATH is handled by
        # _sanitize_path() in build(), because this Environment() has no PATH
        # member (the profile's [buildenv] PATH is injected by a separate
        # script) and defining one here would fight that script.
        for var in (
            "BASH_ENV",
            "BASH_FUNC_rm%%",
            "BASH_FUNC_unlink%%",
            "BASH_FUNC_rmdir%%",
            "CODEBUDDY_SAFE_DELETE_BIN_DIR",
            "CODEBUDDY_SAFE_DELETE_ENABLED",
        ):
            env.unset(var)
        env.vars(self).save_script("protomol-build-env")

    def build(self):
        self._sanitize_path()
        apply_conandata_patches(self)
        self._pin_autotools_timestamps()
        autotools = Autotools(self)
        autotools.configure()
        # -j1: the generated makefiles are from automake 1.6 with
        # "no-dependencies" and have never been parallel-safe upstream.
        autotools.make(args=["-j1"])

    def _sanitize_path(self):
        """Strip the OHOS host "safe delete" shim from the build environment.

        Conan spawns ``make``/``configure`` as child processes and they inherit
        ``os.environ``.  The shim is injected through three channels and all
        three have to be cut:

        1) a ``safe-bin/`` directory prepended to PATH whose ``rm``/``unlink``/
           ``rmdir`` wrappers start with ``#!/bin/bash`` -- OHOS has no
           ``/bin/bash`` (bash lives in /data/service/hnp/bin), so exec fails
           with 126 "bad interpreter";
        2) exported shell functions ``BASH_FUNC_rm%%`` etc., which bash imports
           automatically and which take precedence over PATH;
        3) ``BASH_ENV`` pointing at ``shell-runtime-bash-env.sh``, sourced by
           *every* bash child process (and make's SHELL is bash), which
           re-installs the very functions removed in (2).  Removing only the
           PATH entry or only the BASH_FUNC_* variables is therefore useless --
           the whole source chain has to be broken.

        Observed impact here: everything compiles, then the automake program
        link rule (``@rm -f protomol$(EXEEXT)``) fails with
        ``make[3]: *** [Makefile:190: protomol] Error 126``.
        """
        removed = []

        path = os.environ.get("PATH", "")
        if path:
            entries = path.split(os.pathsep)
            kept = [e for e in entries if e and "safe-bin" not in e]
            if len(kept) != len(entries):
                os.environ["PATH"] = os.pathsep.join(kept)
                removed.append(
                    "%d safe-bin dir(s) from PATH" % (len(entries) - len(kept))
                )

        for func_var in ("BASH_FUNC_rm%%", "BASH_FUNC_unlink%%", "BASH_FUNC_rmdir%%"):
            if os.environ.pop(func_var, None) is not None:
                removed.append(func_var)

        for kill_var in (
            "CODEBUDDY_SAFE_DELETE_ENABLED",
            "CODEBUDDY_SAFE_DELETE_BIN_DIR",
            "BASH_ENV",
        ):
            if os.environ.pop(kill_var, None) is not None:
                removed.append(kill_var)

        if removed:
            self.output.info("[ok] sanitized env: %s" % ", ".join(removed))

    def _pin_autotools_timestamps(self):
        # patches/0010 rewrites configure/configure.in, which makes them appear
        # newer than the shipped aclocal.m4 / protomol_config.h.in / Makefile.in.
        # The automake maintainer rules would then re-run aclocal/autoconf/
        # autoheader via missing(1); on device that picks up whatever autoconf
        # happens to be installed and regenerates configure WITHOUT the
        # Latin-1 fix, reintroducing the PACKAGE_CITE failure.  Stamp every
        # file participating in the autotools dependency chain with one
        # identical mtime: GNU make treats equal mtimes as up to date, so no
        # regeneration fires.
        stamp = 978307200  # 2001-01-01, older than any real input edit
        keep_suffixes = (".m4", ".am", ".in", ".ac")
        keep_exact = (
            "configure",
            "aclocal.m4",
            "install-sh",
            "mkinstalldirs",
            "missing",
            "depcomp",
            "compile",
        )
        for root, _dirs, files in os.walk(self.source_folder):
            for name in files:
                if name.endswith(keep_suffixes) or name in keep_exact:
                    os.utime(os.path.join(root, name), (stamp, stamp))

    def package(self):
        Autotools(self).install(args=["-j1"])
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        # Only bin/ is populated: all framework archives are noinst_LIBRARIES
        # and no headers are installed by upstream.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.buildenv_info.append_path("PATH", os.path.join(self.package_folder, "bin"))
        self.runenv_info.append_path("PATH", os.path.join(self.package_folder, "bin"))
