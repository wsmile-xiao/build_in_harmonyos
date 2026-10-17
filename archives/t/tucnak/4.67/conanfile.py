#!/usr/bin/env python3
"""Conan recipe for tucnak 4.67 — amateur radio contest logger (terminal UI).

Why this recipe builds two projects
-----------------------------------
Upstream ships tucnak and its sibling library libzia as two separate release
tarballs that are meant to be unpacked side by side.  tucnak's ``configure.ac``
first probes for an installed ``libzia.pc`` and otherwise looks for a
``../libzia`` *directory*; when it finds one it links
``../libzia/src/.libs/libzia.a`` **statically** and reads flags from
``../libzia/bin/zia-config``.  So both trees are unpacked as siblings and
libzia is configured, built and installed before tucnak's configure runs.

Why glib is a hard requirement
------------------------------
glib is not an optional feature here.  libzia's ``include/zerror.h`` and
``include/zstr.h`` include ``<glib.h>`` with no ``HAVE_GLIB`` guard, and ten
libzia sources include it directly, so a glib-free libzia cannot be built.
``configure`` merely omits glib from its *report* when pkg-config misses it,
then the compile fails later.  tucnak's own glib/gthread probe is genuinely
optional and resolves against the same Conan glib.

One OHOS portability fix
------------------------
libzia's ``configure`` probes the return type of ``strerror_r`` and records the
answer in ``config.h`` as ``Z_STRERROR_R_RETURNS_INT`` — but **no** libzia
source file ever includes ``config.h``; they only read ``include/zconfig.h``.
On glibc that latent bug is invisible, because glibc's ``strerror_r`` returns
``char *``, which is exactly the ``#else`` branch the code falls into.  OHOS
uses the XSI/musl flavour, whose ``strerror_r`` returns ``int``, so
``src/zerror.c`` keeps taking the glibc-only branch and fails to compile:

    zerror.c:190:11: error: incompatible integer to pointer conversion
                   initializing 'char *' with an expression of type 'int'

This recipe therefore passes the exact value configure computed
(``-DZ_STRERROR_R_RETURNS_INT``) instead of including ``config.h`` wholesale,
which keeps the fix scoped to the one stale macro rather than switching on every
other unused ``AC_DEFINE`` in that file.

Generated files: ship what the tarball ships
--------------------------------------------
The 4.67 release tarball already contains the pre-generated
``src/language.{h,inc}`` and ``src/txts.{h,inc}`` with mtimes equal to
their make prerequisites, so an untouched extraction makes ``make`` skip
those rules.  Only ``src/fonts.{h,inc}`` are generated at build time, and
their rule (``../src/fonts.inc:`` -- no prerequisites) execs
``data/font2inc.pl`` by shebang (``#!/usr/bin/perl -w``).  The OHOS device
has no ``/usr/bin/perl`` (platform perl is on ``PATH`` only -- the same
device fact documented in the tor/0.4.9.11 recipe), so ``build()`` runs
``perl font2inc.pl`` from ``PATH`` before ``make``; ``make`` then sees
``src/fonts.inc`` as up to date and skips the rule.

Two temptations to resist (both bit us on the device):

* do not pre-run ``intl/fixlang.pl`` -- it rewrites the ``.lng`` files in
  place, which makes them newer than the shipped ``src/language.inc`` and
  forces ``make`` to re-run the intl rule;
* do not pre-run ``intl/gen-intl`` -- its ``#define T_*`` pipeline uses
  ``cat -n``, which the device ``cat`` does not implement, so it silently
  produces an incomplete ``language.h`` and moves it over the complete
  shipped one, and every ``T_*`` reference then fails to compile
  (build #85454).

tucnak needs neither curses nor gettext
---------------------------------------
tucnak implements its own terminal handling (no ``<curses.h>`` anywhere in
``src/``) and ``intl/`` only ships ``.lng`` language files, so no ncurses or
gettext dependency is pulled in.
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class TucnakConan(ConanFile):
    name = "tucnak"
    version = "4.67"
    description = "Amateur radio contest logging and radio control program (terminal UI)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/Tucnak/tucnak"
    url = ""

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    generators = "PkgConfigDeps", "VirtualBuildEnv"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"tucnak is only supported on Linux/OHOS, got {self.settings.os}"
            )
        if str(self.settings.arch) not in ("armv8", "armv8.3"):
            raise ConanInvalidConfiguration(
                f"tucnak 4.67 targets aarch64/armv8, got {self.settings.arch}"
            )

    def requirements(self):
        self.requires("glib/2.88.0", transitive_headers=True, transitive_libs=True)

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "conanfile.py", src=self.recipe_folder, dst=self.export_sources_folder)

    def layout(self):
        basic_layout(self)

    def source(self):
        sources = self.conan_data["sources"]
        for project in ("libzia", "tucnak"):
            get(
                self,
                **sources[project],
                strip_root=True,
                destination=os.path.join(self.source_folder, project),
            )

    def _host_triplet(self):
        triplets = {
            "armv8": "aarch64-unknown-linux-ohos",
            "armv8.3": "aarch64-unknown-linux-ohos",
        }
        try:
            return triplets[str(self.settings.arch)]
        except KeyError:
            raise ConanInvalidConfiguration(
                f"No autoconf host triplet mapping for OHOS architecture {self.settings.arch}"
            )

    def _tucnak_host_triplet(self):
        """``--host`` spelling for tucnak, which cannot express OHOS.

        tucnak bundles config.sub from 2018-02-22 and rejects any ``-ohos``
        suffix outright:

            Invalid configuration `aarch64-unknown-linux-ohos':
              machine `aarch64-unknown-linux' not recognized

        (libzia bundles a 2019-06-30 config.sub, which does canonicalise it to
        ``aarch64-unknown-linux-gnu-ohos``, so libzia keeps the accurate value.)

        The plain gnu spelling is used for tucnak because its configure.ac
        contains no ``host_os``/``host_cpu`` branching whatsoever, so the value
        is inert -- it only has to satisfy config.sub.  Codegen is unaffected:
        ``CC`` is the OHOS cross compiler and the sysroot is the OHOS one, which
        the packaged ELF confirms.
        """
        return self._host_triplet().replace("-ohos", "")

    def _compiler(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={}) or {}
        cc = compilers.get("c")
        if not cc:
            raise ConanInvalidConfiguration(
                "tools.build:compiler_executables must define the C compiler for tucnak"
            )
        return cc, compilers.get("cpp")

    def _pkg_config_dir(self):
        """Directory holding PkgConfigDeps' rewritten ``.pc`` files.

        ``PKG_CONFIG_LIBDIR`` is what makes this a real cross build: it replaces
        pkg-config's built-in search path, so a stray x86_64 glib installed on
        the build host can never be picked up over the aarch64 Conan one.  Left
        at its default, configure happily compiled libzia against
        ``/usr/include/glib-2.0`` from the host.

        The *generated* copies must be used, not the ones inside the package
        folders: the shipped ``glib-2.0.pc`` has a bare ``prefix=/`` and would
        resolve to ``/lib``.  PkgConfigDeps rewrites prefix/Libs/Cflags and also
        supplies the transitive ``pcre2.pc`` that ``glib-2.0.pc`` Requires.
        """
        return os.path.join(self.build_folder, "conan")

    def _stage_libtool_archives(self):
        """Stage dependency ``.la`` files that libtool can actually use.

        pcre2/10.45 in the registry ships ``libpcre2-8.la`` with
        ``libdir='//lib'`` and ``dependency_libs='-L/storage/Users/currentUser/
        usr/local/lib'`` — leftovers from being built on-device.  libtool sees
        ``$libdir/$linklib`` missing, concludes the library "was moved", and then
        seds the stale path:

            libtool: warning: library '.../libpcre2-8.la' was moved.
            sed: can't read //lib/libpcre2-8.la: No such file or directory
            libtool: error: '//lib/libpcre2-8.la' is not a valid libtool archive

        Corrected copies are written into the build folder and put first on the
        link path, so the Conan cache itself is never mutated.  Returns the
        directory to prepend to ``LDFLAGS``, or ``None`` when nothing needed it.
        """
        staging = os.path.join(self.build_folder, "lt")
        staged = False
        for dep in self.dependencies.host.values():
            for libdir in dep.cpp_info.libdirs:
                directory = os.path.join(dep.package_folder, libdir)
                if not os.path.isdir(directory):
                    continue
                for name in sorted(os.listdir(directory)):
                    if not name.endswith(".la"):
                        continue
                    source = os.path.join(directory, name)
                    with open(source, encoding="utf-8", errors="replace") as handle:
                        content = handle.read()
                    patched = re.sub(
                        r"^libdir='.*'$", "libdir='%s'" % directory, content, flags=re.M
                    )
                    patched = re.sub(
                        r"^dependency_libs='.*'$", "dependency_libs=''", patched, flags=re.M
                    )
                    if patched == content:
                        continue
                    os.makedirs(staging, exist_ok=True)
                    with open(os.path.join(staging, name), "w", encoding="utf-8") as handle:
                        handle.write(patched)
                    staged = True
                    self.output.info(f"Staged corrected libtool archive {name} ({directory})")
        return staging if staged else None

    def _build_env(self):
        """Compiler/flag variables for the autotools run.

        Returned as ``EnvVars`` so it can be used as ``with env.apply():``;
        ``Environment`` itself is not a context manager in this Conan release.
        """
        cc, cxx = self._compiler()
        env = Environment()
        env.define("CC", cc)
        if cxx:
            env.define("CXX", cxx)
        # The OHOS device ships its own bash; the CI profile points at it and
        # the local WSL mirror overrides it with /bin/bash.  Either way
        # configure must not try to run the target bash.
        env.define("CONFIG_SHELL", "/bin/bash")
        env.define("SHELL", "/bin/bash")
        # See the module docstring: configure computed this into config.h,
        # which src/zerror.c never includes.
        env.define("CFLAGS", "-O2 -DZ_STRERROR_R_RETURNS_INT")
        env.define("CPPFLAGS", "-DZ_STRERROR_R_RETURNS_INT")
        pkgconfig_dir = self._pkg_config_dir()
        env.define("PKG_CONFIG_PATH", pkgconfig_dir)
        env.define("PKG_CONFIG_LIBDIR", pkgconfig_dir)
        libtool_dir = self._stage_libtool_archives()
        if libtool_dir:
            env.define("LDFLAGS", f"-L{libtool_dir}")
        return env.vars(self)

    def _make_jobs(self):
        return str(max(1, (os.cpu_count() or 2)))

    def _zia_configure_args(self, prefix):
        return [
            f"--host={self._host_triplet()}",
            "--build=x86_64-pc-linux-gnu",
            f"--prefix={prefix}",
            # Static only.  Building libzia shared would make libtool try to
            # embed its dependencies, but glib and pcre2 ship as plain .a
            # archives with no libtool .la files, which fails with
            # "'//lib/libpcre2-8.la' is not a valid libtool archive".
            # tucnak links ../libzia/src/.libs/libzia.a statically anyway.
            "--enable-static",
            "--disable-shared",
            "--without-sdl",
            "--without-sdl_ttf",
            "--without-png",
            "--without-ftdi",
            "--without-bfd",
        ]

    def _tucnak_configure_args(self):
        # Every hamradio/audio backend is optional upstream and detected with
        # pkg-config.  They are pinned off so the recipe does not depend on
        # whatever happens to be installed on the build host.
        args = [
            f"--host={self._tucnak_host_triplet()}",
            "--build=x86_64-pc-linux-gnu",
            # DESTDIR=package_folder is what actually places the files, so the
            # prefix only decides the path *inside* that staging root.  Leaving
            # it at the autotools default drops everything under
            # usr/local/{bin,share} and breaks the declared bindirs.
            "--prefix=/",
            "--with-pkg=tucnak",
            "--without-gpm",
            "--without-hamlib",
            "--without-fftw3",
            "--without-portaudio",
            "--without-rtlsdr",
            "--without-hidapi",
            "--without-sndfile",
            "--without-alsa",
        ]
        return args

    def build(self):
        apply_conandata_patches(self)
        env = self._build_env()
        jobs = self._make_jobs()
        zia_dir = os.path.join(self.source_folder, "libzia")
        zia_prefix = os.path.join(self.build_folder, "zia")
        tucnak_dir = os.path.join(self.source_folder, "tucnak")
        os.makedirs(zia_prefix, exist_ok=True)

        with env.apply():
            # ---- stage 1: libzia (provides ../libzia/src/.libs/libzia.a) ----
            self.run(
                "./configure " + " ".join(self._zia_configure_args(zia_prefix)),
                cwd=zia_dir,
                env="conanbuild",
            )
            # Build the specific archive instead of `make all`.  libzia's
            # src/Makefile.am declares an unconditional target
            #   libzia-4.67.so.d: libzia.la map2d
            #   ./map2d libzia.so.map libzia-4.67.so.d
            # and bakes "-Wl,-Map,libzia.so.map" into LIBS.  That map only
            # exists when a shared library is linked, so a static-only libzia
            # can never satisfy `make all` -- it dies with
            # "Can't open 'libzia.so.map' for reading".  bin/zia-config and
            # include/zconfig.h are produced by configure, so src/libzia.la is
            # all that is actually needed.
            self.run(
                f"make -j{jobs} -C src libzia.la", cwd=zia_dir, env="conanbuild"
            )

        libzia_a = os.path.join(zia_dir, "src", ".libs", "libzia.a")
        if not os.path.isfile(libzia_a):
            raise ConanException(f"libzia static archive not produced: {libzia_a}")

        with env.apply():
            # ---- stage 2: tucnak, built in-tree so ../libzia resolves ----
            self.run(
                "./configure " + " ".join(self._tucnak_configure_args()),
                cwd=tucnak_dir,
                env="conanbuild",
            )
            # The release tarball ships the generated src/{language,txts}.{h,inc}
            # with mtimes equal to their make prerequisites, so make skips
            # those rules on an untouched extraction.  Only
            # src/fonts.{h,inc} must be generated, and the data rule for
            # ../src/fonts.inc (no prerequisites) execs data/font2inc.pl by
            # shebang (#!/usr/bin/perl -w), which dies on the OHOS device
            # (no /usr/bin/perl; platform perl is on PATH only -- same
            # device fact as documented in the tor/0.4.9.11 recipe).
            # Pre-run the generator with PATH perl so make sees
            # src/fonts.inc as up to date and skips the rule.
            #
            # Do NOT pre-run intl/fixlang.pl (it rewrites the .lng files in
            # place, making them newer than the shipped src/language.inc
            # and forcing make to re-run the intl rule) or intl/gen-intl
            # (its #define T_* pipeline uses `cat -n`, which the device
            # cat does not implement; it would move an incomplete
            # language.h over the complete shipped one -> "use of
            # undeclared identifier 'T_*'", build #85454).
            data_dir = os.path.join(tucnak_dir, "data")
            self.run("perl font2inc.pl", cwd=data_dir, env="conanbuild")
            self.run(f"make -j{jobs}", cwd=tucnak_dir, env="conanbuild")

        binary = os.path.join(tucnak_dir, "src", "tucnak")
        if not os.path.isfile(binary):
            raise ConanException(f"tucnak build output not found: {binary}")
        self.output.info(f"tucnak binary: {binary}")

    def package(self):
        tucnak_dir = os.path.join(self.source_folder, "tucnak")
        env = self._build_env()
        with env.apply():
            self.run(
                f"make install DESTDIR={self.package_folder}",
                cwd=tucnak_dir,
                env="conanbuild",
            )
        installed = os.path.join(self.package_folder, "bin", "tucnak")
        if not os.path.isfile(installed):
            raise ConanException(
                f"tucnak binary not installed to the declared bindir: {installed}"
            )
        self.output.info(f"packaged tucnak: {installed}")

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))