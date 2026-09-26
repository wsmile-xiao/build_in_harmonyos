#!/usr/bin/env python3
"""Conan recipe for mpop 1.4.22.

mpop is a POP3 client, not a library: it is a single GNU Autotools C project
that installs two programs (``src/Makefile.am``: ``bin_PROGRAMS = mpop`` plus
``mpopd`` under ``if BUILD_MPOPD``), two manual pages and one Texinfo manual.
The whole build surface was read from the unpacked 1.4.22 tarball:

* ``configure.ac`` resolves dependencies through ``PKG_CHECK_MODULES`` only
  (``gnutls >= 3.7.2`` / ``openssl >= 0.0`` / ``libtls >= 0.0`` for TLS,
  ``libgsasl >= 2.1`` for SASL, ``libidn2 >= 0.0`` for IDN, ``libsecret-1``
  for the GNOME keyring) ⇒ ``PkgConfigDeps`` is mandatory; ``AutotoolsDeps``
  alone does not feed ``PKG_CHECK_MODULES``.
* ``AC_CANONICAL_TARGET`` is present and ``build-aux/`` ships ``config.guess``
  and ``config.sub``, so the ``PLATFORM`` macro (printed by ``mpop --version``)
  comes from the target triplet.
* ``AM_GNU_GETTEXT([external])`` is present, so ``--disable-nls`` matters (see
  the OHOS notes below).
* ``doc/Makefile.am`` uses ``info_TEXINFOS = mpop.texi``; ``build-aux/missing``
  lists ``makeinfo`` among the programs that may be absent, and the device has
  no ``makeinfo`` ⇒ the Texinfo rule is stubbed by ``missing``, which is the
  documented automake behaviour, not a failure.
* Upstream ships **no** test suite at all (see ``test_package/MANIFEST.yml``
  for the measured evidence); the canonical ``make check`` target is still
  executed once so the log records "no tests" instead of silence.
* ``src/base64.h`` (vendored from gnulib) declares ``extern bool
  base64_decode_ctx (...)`` but includes only ``<stddef.h>``, and nothing else
  in the tree pulls in ``<stdbool.h>`` — ``grep -rn "stdbool" src/`` returns
  nothing.  That is only reachable with a C23 compiler, where ``bool`` is a
  keyword; the OHOS toolchain is clang 15.0.4 with ``__STDC_VERSION__
  201710L``, so every translation unit that includes the header dies with
  ``error: unknown type name 'bool'``.  Patch 0003 adds the missing include.

OHOS notes
----------
* ``build()`` does not call ``autotools.configure()`` directly: the
  ohos-aarch64 profile's ``[buildenv]`` injects
  ``CONFIG_SHELL=/data/service/hnp/bin/bash``, and that bash returns ``EPERM``
  from ``getcwd()`` on HMDFS, which makes configure die with "working directory
  cannot be determined" (E386).  The unset therefore happens *inside the same
  shell command*, because Conan sources ``conanbuild.sh`` right before running
  it (a ``generate()``-time ``env.unset()`` loses to that re-injection).  The
  configure arguments are still taken from what ``AutotoolsToolchain`` wrote,
  not hand-assembled here.
* E467: ``AutotoolsDeps`` puts the whole dependency closure into ``$LIBS``, and
  mpop's TLS/IDN closure is shared (``libgnutls.so.30``, ``libidn2.so.0`` ...),
  so autoconf's very first "can we run a C program" probe would be refused by
  the loader and mis-reported as "cannot run C compiled programs".
  ``LD_LIBRARY_PATH`` is therefore inlined for that single run.
* NLS is turned off on purpose.  ``gettext/0.22.5.1`` *is* published, but its
  ``package_info()`` declares ``cpp_info.libs = ["intl", "gettextpo",
  "asprintf", "textstyle"]`` while the package only ships ``libintl``,
  ``libgettextpo``, ``libgettextsrc`` and ``libtextstyle`` — there is **no**
  ``libasprintf`` (measured on the downloaded package folder).  As a host
  requirement that injects a ``-lasprintf`` nobody can resolve into ``$LIBS``,
  which breaks every autoconf program probe at once.  Linking the host-side
  ``.harmonybrew/lib/libintl.so`` instead would be an undeclared system
  library (R36), so ``--disable-nls`` is the honest option: ``src/mpop.c``
  guards all localization behind ``#ifdef ENABLE_NLS`` and the English strings
  are the source strings.
* ``--without-libgsasl``: ``configure.ac`` requires ``libgsasl >= 2.1``, the
  artifact repo only registers ``gsasl/1.8.1`` and that archive directory has no
  ``conanfile.py`` at all, so there is no SASL package to link.  Upstream treats
  libgsasl as optional (missing ⇒ only ``AC_MSG_WARN``), and mpop keeps its
  built-in ``user``/``apop`` mechanisms (``src/md5-apps.c``).
* ``--without-libsecret``: the module is ``libsecret-1``, whose published
  recipe pulls the whole ``glib`` closure for a GNOME keyring back-end.  mpop
  itself degrades gracefully (``AC_MSG_WARN`` + ``libsecret=no``), so this
  recipe pins the option off instead of silently depending on the host.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
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

required_conan_version = ">=2.0"


class MpopConan(ConanFile):
    name = "mpop"
    version = "1.4.22"
    description = (
        "A small POP3 client: retrieves mail from one or more POP3 accounts, "
        "optionally over TLS, and delivers it to a local mail delivery program"
    )
    license = "GPL-3.0-or-later"
    homepage = "https://marlam.de/mpop"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("pop3", "mail", "client", "tls", "gnutls", "idn")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        # R32: platform check must accept the OHOS enum as well as Linux.
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "mpop is adapted for Linux/OHOS, not " + str(self.settings.os))

    def requirements(self):
        # configure.ac asks for exactly two modules that the artifact repo can
        # provide: PKG_CHECK_MODULES([libgnutls], [gnutls >= 3.7.2]) and
        # PKG_CHECK_MODULES([libidn2], [libidn2 >= 0.0]).
        # gnutls is shared here, so the transitive flags are needed both for
        # the header (mtls-gnutls.c includes <gnutls.h>) and for the static
        # helpers it links against.
        self.requires("gnutls/3.8.10",
                      transitive_headers=True, transitive_libs=True)
        self.requires("libidn2/2.3.8",
                      transitive_headers=True, transitive_libs=True)
        # Deliberately NOT required, with the reason recorded in the module
        # docstring and in notes.md:
        #   gsasl  -> configure.ac needs libgsasl >= 2.1, the repo only
        #             registers 1.8.1 and that archive dir has no conanfile.py
        #   gettext-> published, but its cpp_info.libs lists libasprintf which
        #             the package does not ship (probed on the download)
        #   libsecret (libsecret-1) -> would drag the whole glib closure

    def export_sources(self):
        # Ships the two E007 patches (build-aux/config.guess, build-aux/config.sub).
        # The configure umask rewrite stays out of patches/ on purpose, because
        # configure is a generated file of the release tarball.
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)],
            strip_root=True)

    def generate(self):
        # Order mirrors the published libdockapp/0.7.3 recipe: dependency flags
        # first, then the pkg-config .pc files consumed by PKG_CHECK_MODULES,
        # then the toolchain that writes configure_args / CC / CFLAGS.
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        # Feature toggles only; no compiler switch is hand-assembled anywhere
        # (R1/R33/R49), and the resulting list is still consumed through
        # AutotoolsToolchain -> Autotools._configure_args (see _configure()).
        tc.configure_args.extend([
            # Upstream default, pinned explicitly so a host-side OpenSSL can
            # never be picked up by accident.
            "--with-tls=gnutls",
            # See the module docstring: no usable libgsasl >= 2.1 exists.
            "--without-libgsasl",
            # PKG_CHECK_MODULES([libidn2], [libidn2 >= 0.0]) - the option name
            # is --with-libidn (historical), the module is libidn2.
            "--with-libidn",
            # No GNOME keyring back-end on a headless POP3 client.
            "--without-libsecret",
            # Not macOS, but the probe is on by default.
            "--without-macosx-keyring",
            # gettext/0.22.5.1 declares a libasprintf it does not ship.
            "--disable-nls",
        ])
        tc.generate()

    def build(self):
        # E007 lands here: patches/0001 + 0002 teach the vendored GNU helpers
        # build-aux/config.guess and build-aux/config.sub about HarmonyOS, so
        # AC_CANONICAL_TARGET resolves aarch64-unknown-linux-ohos instead of the
        # measured failure
        #
        #   checking build system type... ../build-aux/config.guess[1744]:
        #     can't create $HOME/tmp/cgjmG8gI/dummy.c: Permission denied
        #     （此行只把原文的家目录换成 $HOME 写法，mktemp 文件名与错误文本逐字保留）
        #   ../build-aux/config.guess: unable to guess system type
        #   configure: error: cannot guess build type; you must specify one
        #
        # (uname -s is "HarmonyOS", which the packaged config.guess from
        # 2025-07-10 does not know, so it falls back to compiling a probe - and
        # that probe directory, created with mode 0700, comes back from HMDFS
        # without the search bit: the E011 mechanism hit from inside
        # config.guess instead of from config.status.)
        #
        # The shorter-looking workaround of passing --build/--host explicitly,
        # as a few recipes in this corpus do, is forbidden here: E007 states
        # that a forced cross-compile makes autoconf skip every AC_RUN_IFELSE,
        # and configure.ac has one (the getaddrinfo/AI_IDN probe), so it would
        # silently write a wrong config.h.  See knowledge/doc/E007.md and the
        # iron rule at the top of scripts/patch-autotools-ohos.pl, which is
        # what generated these two patches.
        apply_conandata_patches(self)
        self._fix_configure_umask()
        autotools = Autotools(self)
        self._configure(autotools)
        # MAKEINFO=true: doc/Makefile.am has info_TEXINFOS = mpop.texi and the
        # generated version.texi is newer than the distributed mpop.info, so
        # every recursive target (all, check, install) re-enters the Texinfo
        # rule.  The device has no makeinfo and texinfo/7.3 is registered in
        # archives/t/ but has no conanfile.py, so it cannot be a tool_requires.
        # Overriding MAKEINFO on the make command line is this corpus's own
        # convention (see archives/a/autoconf/2.72 and archives/a/anubis/4.3);
        # the tarball's mpop.info is still installed, only the rebuild is
        # skipped - which is what a release build wants anyway.
        doc_args = ["-j1", "MAKEINFO=true"]
        autotools.make(args=doc_args)
        # 上游 0 个测试（实测见 test_package/MANIFEST.yml），canonical check
        # 目标仍执行一次：让日志留下"没有测试可跑"的原始证据而不是沉默。
        autotools.make(target="check", args=doc_args)

    def _fix_configure_umask(self):
        """E011 / E114: ``umask 077`` in the generated configure breaks HMDFS.

        autoconf 2.69 lets ``config.status`` build its scratch directory with
        ``(umask 077 && mktemp -d "./confXXXXXX")``.  On HMDFS a 0700 directory
        comes back as 0660 (no search bit), so the next
        ``cat >"$ac_tmp/subs1.awk"`` fails with::

            ./config.status: can't create ./conffxDNxi/subs1.awk: Permission denied
            config.status: error: could not setup config files machinery

        Rewriting the literal to ``umask 022`` is the documented prescription
        (E011 rec_approach ``edit-umask-in-configure``) and is applied in place
        inside ``build()`` rather than through ``patches/``, because
        ``configure`` is a generated file of the release tarball (corpus
        convention: 1000+ recipes, gsasl/1.8.1 spells the same R6 rationale out
        with a *patch*, which the spec forbids for generated files).
        """
        path = os.path.join(self.source_folder, "configure")
        with open(path, "r", encoding="utf-8", errors="ignore") as handle:
            text = handle.read()
        hits = text.count("umask 077")
        if not hits:
            self.output.warning("E011: 'umask 077' not found in configure - "
                             "upstream text changed, config.status may fail")
            return
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text.replace("umask 077", "umask 022"))
        self.output.info("E011: rewrote %d occurrence(s) of 'umask 077' "
                         "to 'umask 022' in configure" % hits)

    def _dependency_libdirs(self):
        """Absolute lib directories of the whole host dependency closure."""
        found, seen = [], set()
        for _, dep in self.dependencies.host.items():
            base = dep.package_folder or ""
            for entry in dep.cpp_info.libdirs:
                path = entry if os.path.isabs(entry) else os.path.join(base, entry)
                if os.path.isdir(path) and path not in seen:
                    seen.add(path)
                    found.append(path)
        return found

    def _configure(self, autotools):
        """Run configure with CONFIG_SHELL removed in the very same command.

        E386: the profile ``[buildenv]`` exports
        ``CONFIG_SHELL=/data/service/hnp/bin/bash``, and that bash cannot
        ``getcwd()`` on HMDFS ⇒ configure would die with "working directory
        cannot be determined".  Conan sources ``conanbuild.sh`` immediately
        before the command, so the variable has to go inside the command itself.

        ``LD_LIBRARY_PATH`` is injected for the same run (E467):
        ``AutotoolsDeps`` puts the dependency ``-l`` flags into ``$LIBS``, so
        autoconf's very first program run ("checking whether we are cross
        compiling") links against the shared libgnutls/libidn2 closure and
        would otherwise be refused by the loader, which configure misreports as
        "cannot run C compiled programs".  It also matters for mpop's own
        ``AC_RUN_IFELSE`` getaddrinfo/AI_IDN probe, which really executes a
        target binary here because the build is native.

        Arguments still come from ``AutotoolsToolchain``
        (``Autotools._configure_args``), never from hand-written compiler
        switches (R1/R33/R49).
        """
        base_args = getattr(autotools, "_configure_args", None)
        if base_args is None:
            # 回退路径：现代 autoconf 的 configure 未必读 CONFIG_SHELL；届时若
            # 真中招会照原样报错，但至少不会跳过 make。
            self.output.warning("Autotools._configure_args unavailable, "
                             "falling back to autotools.configure()")
            autotools.configure()
            return
        cfg_path = os.path.relpath(os.path.join(self.source_folder, "configure"),
                                   self.build_folder)
        ldpath = ":".join(self._dependency_libdirs())
        self.output.info("configure LD_LIBRARY_PATH=" + ldpath)
        self.run("unset CONFIG_SHELL; LD_LIBRARY_PATH=\"" + ldpath + "\" "
                 + cfg_path + " " + base_args, cwd=self.build_folder)

    def package(self):
        Autotools(self).install(target="install", args=["-j1", "MAKEINFO=true"])
        copy(self, "COPYING",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        # Two standalone programs: the package exports no header and no library.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        # `make install DESTDIR=<pkg>` with the toolchain's --prefix=/ puts the
        # manual pages under <pkg>/share/man/man1, so `share` is the resource
        # directory (also the home of the Texinfo manual when makeinfo exists).
        self.cpp_info.resdirs = ["share"]
