#!/usr/bin/env python3
"""Conan recipe for lcdproc 0.5.9 - the LCDproc suite (LCDd server + clients).

Upstream: https://github.com/lcdproc/lcdproc, release v0.5.9 (2017-06-19),
originally distributed via Savannah/freedesktop.  The tarball is a pure
Autotools project that builds the whole suite from one `make`:

  shared/            libLCDstuff.a  - internal convenience library (noinst)
  clients/lcdproc    the `lcdproc`  system-information screen client
  clients/lcdexec    `lcdexec`      - run commands from the LCDd menu
  clients/lcdvc      `lcdvc`        - virtual console
  clients/metar      lcdmetar.pl    (perl, bin_SCRIPTS)
  clients/examples   5 perl scripts (bin_SCRIPTS)
  server/            `LCDd` daemon + 10 driver plugins + libLCDcommands.a
  docs/ scripts/     man pages, sysvinit/debian/rpm init scripts

`make install` deliberately does NOT install libLCDstuff.a (shared/Makefile.am
declares it `noinst_LIBRARIES`), so this package is an application suite, not a
linkable library: package_type = "application" and the binaries are declared in
the software-level commands.json (R38).

Dependency picture (W0, verified per R35 by `conan download <pkg> --only-recipe`
against the ohpcd remote rather than by `conan list`):
  * Mandatory deps: none beyond libc/libdl.  `configure` finishes with
    `LIBS = -ldl`, so the suite cross-compiles standalone.
  * Every heavy integration sits behind an --enable-<x> flag and degrades
    gracefully when the library is absent, so the default driver list
    (bayrad, CFontz, CFontzPacket, curses, CwLnx, glk, lb216, lcdm001, MtxOrb,
    pyramid, text) builds with no external packages.

Feature configuration (deterministic, not "whatever the machine happens to
have"): the optional integrations whose libraries are NOT published to the
ohpcd registry are switched off explicitly, and the driver set itself is
pinned with --enable-drivers=<list>, so that a local build and the on-device
CI worker resolve the *same* drivers.  See notes.md for the full matrix and
for the ncurses analysis.

  NOT published to ohpcd -> --disable-* : libusb(0.1), libusb-1-0, libftdi,
      libhid, libpng, freetype, libX11.
  No configure switch at all (auto-probe only, so they simply degrade when
      absent): glib2, libpango, libgd, libxml2.
  Published but not wired in: ncurses/6.5 ships only libncursesw.a, while
      upstream's LCD_DRIVERS_SELECT probes AC_CHECK_LIB(ncurses, main), so the
      `curses` driver cannot be enabled without editing upstream's m4.  Since
      upstream exposes no --enable/--disable-curses switch, the only way to
      keep the driver set host-independent is --enable-drivers=<list>, which
      is what this recipe does.

OHOS adaptations (patches, registered in conandata.yml):
  * 0001-config-guess-ohos-triplet: E007/E072.  The tarball ships a
    2014-03-23 config.guess that has never heard of HarmonyOS, and
    `--build/--host` is forbidden (it would flip cross_compiling=yes and skip
    every AC_RUN_IFELSE).  The patch adds a `*:HarmonyOS:*:*` uname branch for
    the on-device CI runner plus a compiler-target probe so that a cross build
    reports the same host triple as a native one.
  * 0002-config-sub-linux-ohos: E072.  The 2014-09-11 config.sub rejects
    `aarch64-unknown-linux-ohos` ("machine `aarch64-unknown-linux' not
    recognized") because neither its kernel-OS nor its OS whitelist mentions
    linux-ohos.  The official scripts/patch-autotools-ohos.pl does not match
    this vintage (its android-linux / linux-uclibc anchors are absent), so the
    two whitelist entries are added directly.
  * 0003-iface-extern-definition: clients/lcdproc/iface.h carries a tentative
    definition of the shared `iface[]` table, i.e. a definition in a header.
    GCC used to merge those across translation units via -fcommon; clang >= 11
    defaults to -fno-common, so main.c and iface.c each emitted a strong .bss
    definition and the client failed to link with "duplicate symbol: iface".
  * 0004-configure-umask-022: E011/E114.  The generated configure builds its
    ./confXXXXXX scratch dir under `umask 077`; on HMDFS the process UID differs
    from the mapped owner, so that directory is not writable even by its owner.
  * (no 5th patch) - instead of patching the source, generate() presets
    `ac_cv_mtab_file=/proc/mounts`.  Upstream's AC_FIND_MTAB_FILE picks the
    mount table with `test -f /etc/mtab|/etc/mnttab|/etc/fstab`, a probe of the
    BUILD machine; with none of the three present (the OHOS CI worker) it leaves
    MTAB_FILE undefined and machine_Linux.c:265 fails with
    `#error "Can't find your mounted filesystem table file."`.  Presetting the
    autoconf cache var bypasses the probe and names the target's table.  This is
    a source of build-host dependence that --host/--build could have hidden but
    that E007 forbid_1 correctly disallows us from using.
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LcdprocConan(ConanFile):
    name = "lcdproc"
    version = "0.5.9"
    description = ("LCDproc suite: LCDd daemon with driver plugins, plus the "
                   "lcdproc / lcdexec / lcdvc clients")
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/lcdproc/lcdproc"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # R38: the payload is a runnable suite (LCDd + 3 clients), not a linkable
    # library, so commands.json is declared at the software level.
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os must be matched against ("Linux", "OHOS").
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"lcdproc is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def layout(self):
        # Out-of-tree (VPATH) build works: every Makefile.in uses the standard
        # automake `srcdir` handling and -I$(top_srcdir), so the build folder
        # stays separate from the sources.
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Pin the optional integrations instead of letting configure probe the
        # machine: the libraries below are not published to the ohpcd registry,
        # and leaving them "auto" makes the driver set depend on whatever
        # happens to be installed on the build host.  --disable-libX11 in
        # particular matters: on a Linux build host pkg-config happily resolves
        # the *host* x86_64 x11.pc, which cross-compiling must never pick up.
        for opt in (
            "libusb",        # libusb 0.1 API - not published
            "libusb-1-0",    # only consumed by picolcd/futaba, not in the default driver set
            "libftdi",       # not published
            "libhid",        # not published
            "libpng",        # not published
            "freetype",      # not published
            "libX11",        # not published; also guards against host pkg-config false positives
        ):
            tc.configure_args.append(f"--disable-{opt}")
        # Pin the driver list itself.  Upstream's default is 11 drivers, but
        # `curses` is the one entry with no --enable/--disable switch: it is
        # added only when configure's AC_CHECK_LIB(ncurses, main) succeeds,
        # which depends on what the *build host* happens to have.  Leaving it
        # implicit would make the packaged driver set drift between a Linux
        # build host (ncurses installed -> 11 drivers) and the OHOS CI worker
        # (no ncurses -> 10).  Naming the list explicitly makes the payload
        # identical everywhere.  These are exactly upstream's defaults minus
        # `curses`; nothing else is dropped.
        tc.configure_args.append(
            "--enable-drivers=bayrad,CFontz,CFontzPacket,CwLnx,glk,lb216,"
            "lcdm001,MtxOrb,pyramid,text"
        )
        # ac_cv_mtab_file: AC_FIND_MTAB_FILE (acinclude.m4:638) resolves the mount
        # table with a plain `test -f` on /etc/mtab, /etc/mnttab, /etc/fstab -
        # i.e. it probes the *build* machine, not the target.  When none of the
        # three exists it leaves MTAB_FILE undefined and
        # clients/lcdproc/machine_Linux.c:265 hits
        #   #error "Can't find your mounted filesystem table file."
        # so the client fails to compile.  On an OHOS worker none of the three
        # exists; on a Linux build host /etc/mtab does, which is exactly why
        # this only shows up on CI.  Presetting the autoconf cache variable
        # bypasses the host probe entirely (configure: `if ${ac_cv_mtab_file+:}`
        # short-circuits the body) and names the *target's* table instead.
        # /proc/mounts is where a Linux-kernel target keeps the mount table and
        # its `dev mpoint type ...` lines parse with the existing
        # sscanf("%s %s %s", ...).
        tc.configure_args.append("ac_cv_mtab_file=/proc/mounts")
        # Never pass --build/--host (E007 forbid_1): it would make configure
        # believe it is cross compiling, skip every AC_RUN_IFELSE and bake a
        # wrong config.h.  The patched config.guess resolves the OHOS host.
        tc.configure_args = [
            a for a in tc.configure_args
            if not str(a).startswith("--build=") and not str(a).startswith("--host=")
        ]
        tc.generate()

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        # E074: parallel make needs a jobserver fifo, which HMDFS refuses to
        # create, so the build must run single-job on the OHOS worker.
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # Application payload: no library to link against (libLCDstuff.a is
        # noinst upstream), just the directories the artifacts land in.
        #
        # NOTE on bindirs: upstream's server/Makefile.am uses sbin_PROGRAMS for
        # LCDd, but AutotoolsToolchain._default_configure_install_flags() derives
        # BOTH --bindir and --sbindir from cpp_info.bindirs[0].  Declaring a
        # single "bin" therefore keeps the whole suite - daemon and clients -
        # in one directory, which is also what commands.json addresses.  The
        # FHS split is intentionally not reintroduced by hand-passing
        # --sbindir, so that a consumer only has to put one directory on PATH.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib", "lib/lcdproc"]
        self.cpp_info.resdirs = ["etc", "share/man"]
        self.cpp_info.libs = []
        self.cpp_info.system_libs = ["dl"]
