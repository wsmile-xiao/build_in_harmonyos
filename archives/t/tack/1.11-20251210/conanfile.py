#!/usr/bin/env python3
"""Conan recipe - tack 1.11-20251210 (Autotools: configure + make).

tack ("T.A.C.K.", the terminfo action checker) is Thomas Dickey's terminal
diagnostic: it probes a terminal through its terminfo entry and verifies or
rebuilds that entry.  Upstream ships one program (``PROGS = tack$x``) plus one
man page, links against the terminfo/curses API and has **no self-test**
(``Makefile.in``'s ``check:`` target is literally ``@echo "** no self-test
available"``).

Terminal library
----------------
``ncurses/6.6`` from this repo's artifact registry.  That package is a
**static-only wide build** (``ls <pkg>/lib`` -> ``libncursesw.a`` etc., no
``.so``), therefore ``--with-ncursesw`` is required: with the default
``ncurses`` screen name tack's ``CF_WITH_NCURSES_ETC`` asks for ``-lncurses``,
which the package does not provide.

Ambient-toolchain hazard (the real OHOS work here)
--------------------------------------------------
tack's configure resolves the curses flags through an external helper *before*
it ever looks at ``--with-curses-dir``:

    checking pkg-config for ncursesw... no
    Looking for ncursesw-config
    checking for ncursesw-config... ncursesw6-config     <- found on $PATH

The OHOS build hosts carry a harmonybrew ncurses in ``~/usr/local/bin`` /
``~/usr/local/lib``, and its ``ncursesw6-config`` hands configure that tree's
``-I``, ``-L`` **and** ``-Wl,-rpath``.  Because ``ld`` prefers a shared object
found anywhere in the search list over an archive in an earlier ``-L``
directory, the link line silently binds the *host* ``libncursesw.so.6``
instead of the declared conan dependency.  Measured on the build host (this
window, ``~/tmp/uc2/z63-tack/explore/B``):

    NEEDED  Shared library: [libncursesw.so.6]
    RUNPATH [.../.harmonybrew/opt/ncurses/lib:.../ncurs.../p/lib]

which is a green build that cannot run on any machine without that harmonybrew
prefix.  The fix is to leave the probe with nothing to find: autoconf's
``AC_CHECK_PROG`` result is read through the cache variables
``ac_cv_prog_NCURSES_CONFIG`` / ``ac_cv_prog_ac_ct_NCURSES_CONFIG``, so
pre-setting them to empty on the configure command line makes the detection
report ``(cached) no`` and stops tack from consulting *any* host ``*-config``
program.  Flags then come only from ``--with-curses-dir=<conan package>`` plus
the ``AutotoolsDeps`` environment, and the resulting artifact is verified in
``test_package`` (``DT_NEEDED`` must not contain ``libncursesw``).

OHOS platform guards baked into this recipe
-------------------------------------------
* E160/E007 -- ``uname -s`` is ``HarmonyOS``, the shipped ``config.guess``
  (timestamp 2025-07-10) fails with "unable to guess system type" (rc=1).
  Fixed by ``patches/0001-config.guess.patch`` + ``0002-config.sub.patch``
  (generated with the repo's own ``scripts/patch-autotools-ohos.pl``, minus the
  ``__OHOS__`` LIBC-probe hunk).  ``--build``/``--host`` are **not** used: the
  patched guess yields ``aarch64-unknown-linux-ohos`` for both, so configure
  keeps ``checking whether we are cross compiling... no`` and its
  ``AC_RUN_IFELSE`` probes really run.
* E011/E114 -- ``configure`` creates ``config.status``'s scratch directory
  under ``(umask 077 && mktemp -d ...)``; HMDFS normalises that directory so
  ``config.status`` cannot write into it.  It then *still prints* "creating
  Makefile" while the substitution silently fails, leaving a Makefile whose
  ``@...@`` placeholders were never filled in.  ``build()`` rewrites
  ``umask 077`` -> ``umask 022`` in place and reports the hit count
  (3 in this release; a warning is printed when the pattern is gone).
* E386 -- the ``ohos-aarch64`` profile exports
  ``CONFIG_SHELL=/data/service/hnp/bin/bash`` and autoconf re-execs itself
  through it; that bash fails ``getcwd()`` on HMDFS.  The guard therefore lives
  in the same shell command as the invocation (an ``Environment.remove()`` in
  ``generate()`` is re-injected at run time).
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import load_toolchain_args
from conan.tools.files import (apply_conandata_patches, export_conandata_patches,
                               get, load, save)
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain


class TackConan(ConanFile):
    name = "tack"
    version = "1.11-20251210"
    description = ("T.A.C.K. terminfo action checker: probe a terminal through "
                   "its terminfo entry and verify or recreate that entry")
    license = "GPL-2.0-only"
    homepage = "https://invisible-island.net/tack/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # E386: must be part of the same command line that starts configure/make.
    _SH = 'env -u CONFIG_SHELL SHELL=/bin/sh'

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # W0: verified published in the ohpcd registry (see notes.md), bare ref
        # without @user/channel -- the artifact repo publishes bare references.
        # run=True: ncurses 在本 profile 下是**静态**库（shared=False），默认不传递 run 信息，
        # 而 tack 运行期需要 ncurses 包里的 terminfo 数据库（其 package_info 用 runenv_info
        # 定义 TERMINFO/TERMINFO_DIRS）。实测：不传 run 时消费者拿到的是
        # "The terminal database could not be found"，传了 run 才能读到包内 terminfo。
        self.requires("ncurses/6.6", run=True)

    def validate(self):
        # R32: os must be compared with `in (...)`, never `== "Linux"`.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"tack is only wired up for Linux/OHOS, got os={self.settings.os}")

    def layout(self):
        # tack's Makefile.in derives its object directory from
        #   DFT_OBJ_SUBDIR=`pwd|sed -e 's:.*/::'`   ->  MODEL = ../<basename>
        # which only resolves for an in-tree build, so source and build share
        # one folder and the generated files stay in it.
        self.folders.source = "src"
        self.folders.build = "src"
        self.folders.generators = "build-generators"

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        for name in ("configure", "config.guess", "config.sub", "install-sh"):
            path = os.path.join(self.source_folder, name)
            if os.path.isfile(path):
                os.chmod(path, 0o755)

    def _curses_dir(self):
        return self.dependencies["ncurses"].package_folder

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Feature/dependency switches only -- compiler flags come from the
        # toolchain and from AutotoolsDeps below (R1/R33).
        tc.configure_args.append("--with-ncursesw")
        tc.configure_args.append(f"--with-curses-dir={self._curses_dir()}")
        # Empty the AC_CHECK_PROG cache so configure never picks up a host
        # `ncursesw*-config` (harmonybrew) and links the system libncursesw.so.
        tc.configure_args.append("ac_cv_prog_NCURSES_CONFIG=")
        tc.configure_args.append("ac_cv_prog_ac_ct_NCURSES_CONFIG=")
        tc.generate()
        AutotoolsDeps(self).generate()

    def _relax_hmdfs_umask(self):
        """E011/E114: config.status' scratch dir must be readable on HMDFS."""
        configure = os.path.join(self.build_folder, "configure")
        text = load(self, configure)
        hits = text.count("umask 077")
        if not hits:
            self.output.warning(
                "E011/E114 guard: no 'umask 077' left in configure - upstream "
                "changed, config.status may now write a Makefile whose "
                "placeholders were never substituted")
            return
        save(self, configure, text.replace("umask 077", "umask 022"))
        self.output.info(f"UMASK077_RELAXED hits={hits} replacement='umask 022'")

    def build(self):
        apply_conandata_patches(self)
        self._relax_hmdfs_umask()
        # Reuse the argument list the toolchain produced (single source of
        # truth), but launch it with the E386 guard in the same shell command.
        configure_args = load_toolchain_args(self.generators_folder)["configure_args"]
        configure = os.path.join(self.source_folder, "configure")
        self.run(f'{self._SH} "{configure}" {configure_args}', cwd=self.build_folder)
        self.run(f"{self._SH} make -j1", cwd=self.build_folder)

    def package(self):
        # --prefix=/ (AutotoolsToolchain default) + DESTDIR=<package_folder>.
        dest = self.package_folder.replace("\\", "/")
        self.run(f'{self._SH} make install DESTDIR="{dest}"', cwd=self.build_folder)

    def package_info(self):
        # Command-line tool only: no headers, no libraries of its own.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin"))
