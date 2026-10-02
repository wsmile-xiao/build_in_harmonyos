#!/usr/bin/env python3
"""Conan recipe for pktstat 1.8.5 — real-time interface traffic viewer.

pktstat watches a network interface with libpcap and continuously displays the
observed packet rate broken down by protocol and port, in a full-screen curses
UI that updates every ``-w`` seconds (upstream calls it a "top-like utility for
network connections usage").

Build surface, read from the v1.8.5 tree (sha256 9a365668...b9cd):

* The tag ships **only** ``configure.ac`` + ``Makefile.am`` — there is no
  generated ``configure`` and no ``configure.in``.  ``build()`` therefore has to
  bootstrap the build system with ``autoreconf -fi`` before ``configure`` exists.
* ``configure.ac:85`` hard-fails without a packet capture library
  (``AC_CHECK_FUNC([pcap_open_live], , AC_MSG_ERROR(...))``) and
  ``configure.ac:87`` hard-fails without a screen library (``initscr``), so
  **libpcap and ncurses are mandatory** runtime requirements, not optionals.
* The BPF programs are not hand-rolled: ``main.c:334`` calls
  ``pcap_compile``/``pcap_setfilter`` and ``struct bpf_program``/``bpf_u_int32``
  come straight from ``<pcap.h>``.  So libpcap is the only packet-filter
  dependency; the ``ether.c``/``ip.c``/``tcp.c``/... files are the *tagging*
  functions (one per DLT), not BPF bytecode.
* ``main.c``/``display.c`` use K&R function definitions and a K&R parameter list
  (``upcall_from_pcap(context, hdr, data) u_char *context;``); that is still
  legal in the compiler's default gnu17 mode, so no source change is needed.

OHOS notes
----------
* ``build()`` does not call ``autotools.configure()`` directly: the ohos-aarch64
  profile ``[buildenv]`` exports ``CONFIG_SHELL=/data/service/hnp/bin/bash`` and
  that bash fails ``getcwd()`` on HMDFS, so autoconf's configure re-execs itself
  through ``$CONFIG_SHELL`` and dies before doing any work (E386).  The unset has
  to happen *inside the same shell command* — a ``generate()``-time
  ``env.unset()`` loses to the runtime re-injection (validated in sword/1.9.0 and
  wmcore/0.0.4).  The configure arguments still come from
  ``Autotools._configure_args``; this recipe appends no compiler switches
  (R1/R33/R49).
* ``autoreconf -fi`` runs the build system's own autotools from the worker, the
  same shape as the 500+ archived recipes in this repository that bootstrap with
  a bare ``autoreconf``.  That is *not* safe on the CI worker: the machine
  image carries autoconf (autoconf_2.72 under the HNP) but no automake, so a
  bare ``autoreconf -fi`` dies with "Can't exec \"aclocal\"" (CI build
  #66008).  Hence ``tool_requires("automake/1.18")``: the registry has an
  OHOS/armv8 automake, the CI worker is itself aarch64 HarmonyOS so that
  binary executes natively, and it drags in the perl the aclocal scripts need.
* Both dependencies ship **static-only** packages in the registry
  (``libpcap/libpcap.a`` and ``ncurses/libncursesw.a``; there is no
  ``libncurses.a`` and no ``libcurses.a``).  ``configure.ac:21`` searches
  ``tgoto`` in ``termlib termcap curses ncurses ocurses`` and ``configure.ac:22``
  searches ``initscr`` in ``curses ncurses ocurses`` — neither short name would
  resolve.  They succeed anyway because ``AutotoolsDeps`` puts the dependency
  ``-l`` closure into ``$LIBS``, and ncurses exports
  ``cpp_info.libs = ["ncursesw", "panelw", "menuw", "formw"]``, so ``-lncursesw``
  is already present when ``AC_SEARCH_LIBS`` runs its link test.  Being fully
  static also means the packaged ELF carries no NEEDED entry for libpcap or
  ncursesw and needs no loader path at runtime.
* ``configure.ac:6`` uses ``AM_CONFIG_HEADER`` and ``configure.ac:26/27/67`` use
  ``AC_HEADER_STDC`` / ``AC_HEADER_TIME`` / ``AC_TYPE_SIGNAL``.  All four are
  obsolete but autoconf 2.71 only *warns* about them (autoupdate is not run), so
  no patch is required.
* Upstream ships **no** test suite and **no** ``check`` target, so ``build()``
  runs only ``make``; the packaged ``test_package/`` carries the assertions.
  See ``test_package/MANIFEST.yml`` for the upstream inventory evidence.
"""
import os

from conan import ConanFile, __version__ as conan_version
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class PktstatConan(ConanFile):
    name = "pktstat"
    version = "1.8.5"
    description = ("pktstat: a top-like utility that shows the live packet rate "
                   "of a network interface broken down by protocol and port, "
                   "rendered with ncurses")
    license = "public-domain"
    homepage = "https://github.com/dleonard0/pktstat"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("network", "monitoring", "traffic", "pcap", "ncurses", "top")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        # No patch needs a helper script here, but the export channel is still
        # declared so that a future upstream fix ships as a real patches/ file
        # registered in conandata.yml instead of an in-recipe string substitution
        # (G1/W2 shape requirement).
        export_conandata_patches(self)

    def validate(self):
        # R32: accept the OHOS enum as well as Linux.
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "pktstat is adapted for Linux/OHOS, not " + str(self.settings.os))

    def requirements(self):
        # Both are hard requirements, enforced by AC_MSG_ERROR in configure.ac:
        # pcap_open_live (line 85) and initscr (line 87).  These are the newest
        # OHOS builds published in the registry.
        self.requires("libpcap/1.10.6")
        self.requires("ncurses/6.6")
        # The v1.8.5 tag ships only configure.ac/Makefile.am, so build() has to
        # run autoreconf, and autoreconf insists on aclocal -- which comes from
        # automake.  The CI worker ships autoconf (its HNP carries
        # autoconf_2.72) but **no automake**, so a bare `autoreconf -fi` dies
        # with (CI build #66008):
        #     Can't exec "aclocal": No such file or directory at
        #     /data/service/hnp/autoconf.org/autoconf_2.72/share/autoconf/Autom4te/FileUtils.pm line 299
        #     autoreconf: error: aclocal failed with exit status: 2
        # Pull automake in as a tool requirement instead of relying on the
        # worker.  1.18 is the version the already-merged recipes use
        # (archives/a/abiword-plugin-*/3.0.8), so it is the proven-green one.
        # Both 1.18 and 1.19 still define the obsolete AM_CONFIG_HEADER used by
        # this configure.ac, so the deprecation stays a warning either way.
        self.tool_requires("automake/1.18")

    def layout(self):
        # In-tree build.  autoreconf regenerates configure/Makefile.in inside the
        # source folder, and automake's generated Makefile is VPATH-aware, but
        # keeping build_folder == source_folder keeps the bootstrap, the configure
        # run and the compile in one tree (the shape proven by lft/3.98).
        basic_layout(self, build_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)],
            strip_root=True)

    def generate(self):
        AutotoolsDeps(self).generate()
        AutotoolsToolchain(self).generate()

    def build(self):
        apply_conandata_patches(self)
        self._autoreconf()
        self._fix_configure_umask()
        autotools = Autotools(self)
        self._configure(autotools)
        # Upstream declares no check target and ships 0 test sources (inventory
        # evidence in test_package/MANIFEST.yml), so `make check` would abort the
        # build with "No rule to make target 'check'".
        autotools.make(args=["-j1"])

    def _fix_configure_umask(self):
        """E011/E114: ``umask 077`` in the generated configure breaks HMDFS.

        autoconf's scratch-dir bootstrap is

            tmp=`(umask 077 && mktemp -d "./confXXXXXX")` ...

        On the HarmonyOS filesystem a 0700 directory reads back as 0660 — the
        search bit is lost — so writing into it fails and CI build #66033 died
        with

            ./config.status[742]: can't create ./confEjEJDa/subs1.awk: Permission denied

        Rewriting ``umask 077`` to ``umask 022`` gives 0755, i.e. the directory
        keeps its search bit.  Both occurrences live in ``configure`` and the
        second one is inside the here-doc autoconf 2.72 uses to emit
        ``config.status`` itself, so fixing ``configure`` fixes both binaries
        (measured: 2 hits in configure, and the generated config.status carries
        the same 2).  The single ``umask 077`` in Makefile.in belongs to
        automake's ``distuninstallcheck`` target, which this package never runs,
        so it is deliberately left alone.

        ``configure`` is regenerated by our own ``autoreconf -fi``, so this is
        an in-place rewrite of a build artifact rather than a patch against
        tracked upstream sources (R6; same shape as lft/3.98).  If the literal
        ever disappears the rewrite is skipped with a loud warning instead of
        failing silently.
        """
        path = os.path.join(self.source_folder, "configure")
        with open(path, "r", encoding="utf-8", errors="ignore") as handle:
            text = handle.read()
        hits = text.count("umask 077")
        if not hits:
            self.output.warning("E011: 'umask 077' not found in the generated "
                                "configure - upstream/autoconf changed, and "
                                "config.status may fail to create its scratch "
                                "dir on HMDFS")
            return
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text.replace("umask 077", "umask 022"))
        self.output.info("E011: rewrote %d occurrence(s) of 'umask 077' to "
                         "'umask 022' in the generated configure (covers both "
                         "configure and the config.status it emits)" % hits)

    def _autoreconf(self):
        """Bootstrap configure/Makefile.in: the tag ships only *.ac/*.am.

        ``automake/1.18`` is a tool_requires (see requirements()), which puts its
        ``bin/`` — hence ``aclocal``/``automake`` and the perl they need — on
        PATH for this run.  Nothing automake-supplied is assumed to exist on the
        machine image: the CI worker has autoconf but no automake.
        """
        self.output.info("bootstrapping the build system with autoreconf -fi")
        self.run("autoreconf -fi", cwd=self.source_folder)

    def _configure(self, autotools):
        """Run configure with CONFIG_SHELL removed in the very same command.

        E386 (see module docstring).  Arguments come from
        ``Autotools._configure_args``; nothing compiler- or feature-specific is
        appended here, so no dependency probing has to be pinned by hand.
        """
        base_args = getattr(autotools, "_configure_args", None)
        if base_args is None:
            # Hard error, not a warning: the fallback below is autotools.configure(),
            # which is exactly the path that trips E386, so degrading silently
            # would relocate the failure into configure with an unrelated message.
            # _configure_args is assigned in Autotools.__init__ from the
            # toolchain's configure_args key (measured with Conan 2.29.1).
            raise ConanException(
                "Autotools._configure_args is unavailable on Conan "
                "%s; this recipe needs it to unset CONFIG_SHELL in the same "
                "shell command (E386). Upgrade Conan, or replace this call "
                "with an explicit configure(args=[...]) plus a documented "
                "CONFIG_SHELL workaround." % conan_version)
        cfg_path = os.path.relpath(os.path.join(self.source_folder, "configure"),
                                   self.build_folder)
        # POSIX sh resolves a bare "configure" through $PATH; with the in-tree
        # layout relpath yields exactly that, which dies with
        # "configure: inaccessible or not found" (rc 127).  Force a relative
        # path expression.
        if not os.path.isabs(cfg_path) and not cfg_path.startswith("."):
            cfg_path = "./" + cfg_path
        if not os.path.isabs(cfg_path):
            cfg_path = cfg_path.replace("/./", "/")
        self.run("unset CONFIG_SHELL; " + cfg_path + " " + base_args,
                 cwd=self.build_folder)

    def package(self):
        autotools = Autotools(self)
        autotools.install(target="install", args=["-j1"])
        copy(self, "COPYING",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)
        self._assert_payload()

    def _assert_payload(self):
        """Fail loudly if the expected deliverable did not land.

        A package_type="application" recipe that silently ships an empty bin/
        would still "build green", so the binary and the man page are checked by
        name here rather than only by the consumer test.  This is deliberately a
        hard error, not a warning: pktstat is the whole deliverable of this
        package, so a missing payload means the package is empty, not degraded.
        """
        binary = os.path.join(self.package_folder, "bin", "pktstat")
        if not os.path.isfile(binary):
            raise ConanException("expected payload missing: " + binary)
        man = os.path.join(self.package_folder, "share", "man", "man1",
                           "pktstat.1")
        if not os.path.isfile(man):
            raise ConanException("expected man page missing: " + man)
        self.output.info("payload verified: bin/pktstat + share/man/man1/pktstat.1")

    def package_info(self):
        # A single standalone CLI program; it exports no header and no library.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        # pktstat.1 installs under <pkg>/share/man/man1.
        self.cpp_info.resdirs = ["share"]
