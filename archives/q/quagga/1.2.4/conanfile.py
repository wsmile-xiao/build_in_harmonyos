#!/usr/bin/env python3
"""Conan recipe — quagga 1.2.4 (GNU Quagga routing daemon suite) for OHOS.

GNU Quagga ships zebra (routing information base manager) plus the BGP4+/OSPFv2/
OSPFv3/RIPv1-RIPng/IS-IS/PIM-SM/NHRP daemons, a `vtysh` integrated shell and
`watchquagga`.  This recipe packages the daemon suite plus `watchquagga`; the
optional `vtysh` front-end is switched off (see --disable-vtysh in generate()).

OHOS-specific adaptations (path A = stock minimal build, every optional feature
that needs an external part unavailable on OHOS is switched off with the
*upstream* switch name; see notes.md for the full list):

  - E007: the git-tag tarball ships no `configure` (only configure.ac) and no
    config.guess, so build() bootstraps with `autoreconf -fi` (automake/libtool
    come from tool_requires) and then replaces config.guess with an OHOS-aware
    version emitting `aarch64-unknown-linux-ohos` (`uname -s` returns
    "HarmonyOS", which upstream/GNU config.guess does not recognise).
  - E091: `-D__MUSL__` is required for every zebra/nhrpd translation unit that
    includes both <sys/socket.h> and <linux/netlink.h>/<linux/rtnetlink.h>;
    without it the OHOS sysroot's <linux/socket.h> re-defines
    `struct sockaddr_storage` and clang hard-errors (measured: see notes.md).
  - HMDFS: autoconf's generated configure/config.status run `umask 077`, whose
    0700 temp dirs break on HMDFS -> rewritten to `umask 022`.
  - Runtime identity: `--enable-user/--enable-group/--enable-vty_group` so the
    packaged daemons and the sample-config install hooks do not reference a
    non-existent `quagga` account on OHOS.
  - `--disable-vtysh`: the integrated shell is the only component that needs
    libreadline (`configure.ac:757-761` hard-errors without it) and no termcap
    provider is usable in this sysroot.  Dropping it keeps the daemon suite and
    its netlink face; see generate() and notes.md for the readline publication
    probe.
  - `--disable-nhrpd`: nhrpd is the only component that needs c-ares
    (`configure.ac:1348` PKG_CHECK_MODULES([CARES], [libcares])), which is not
    published on the ohpcd remote either.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.files import (apply_conandata_patches, copy, export_conandata_patches,
                               get, rmdir, save)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class QuaggaConan(ConanFile):
    name = "quagga"
    version = "1.2.4"
    package_type = "application"
    description = ("GNU Quagga routing daemon suite — zebra, bgpd, ospfd, ospf6d, "
                   "ripd, ripngd, isisd, pimd, watchquagga "
                   "(vtysh and nhrpd are not built, see --disable-vtysh "
                   "and --disable-nhrpd in generate())")
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/Quagga/quagga"
    url = "https://github.com/Quagga/quagga"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    # Installed daemons/tools of the stock build (used by package()/test hooks).
    _DAEMONS = ["zebra", "bgpd", "ripd", "ripngd", "ospfd", "ospf6d",
                "isisd", "pimd"]
    # `vtysh` and `nhrpd` are deliberately not listed: neither is built
    # (see --disable-vtysh / --disable-nhrpd in generate()).
    _TOOLS = ["watchquagga"]

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Path A: no external Conan dependencies.  Every optional library face
        # (snmp / libpam / libcap / ossp-uuid(ospfapi) / pcreposix / protobuf /
        # fpm / readline(vtysh) / c-ares(nhrpd)) is disabled by its upstream
        # switch instead of being pulled in -- for readline and c-ares the exact
        # binary probe shows a publication gap, see notes.md.
        pass

    def build_requirements(self):
        # The git-tag tarball has no configure: bootstrap needs automake +
        # libtool (autoconf/autoreconf exist on the host under
        # /data/service/hnp/bin).  Same approach as archives/a/abiword-plugin-*
        # and the 234 merged recipes that tool_requires automake.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)
        # E386 / DRAFT-6487 (HMDFS getcwd storm): the OHOS bash injected by the
        # profile's [buildenv] (CONFIG_SHELL=/data/service/hnp/bin/bash) returns
        # ENOTSUP/EINVAL from getcwd() once the CWD is one level deeper than the
        # conan cache base, so configure dies with
        #   "shell-init: error retrieving current directory: getcwd: cannot
        #    access parent directories" -> "configure: error: working directory
        #    cannot be determined".
        # Keeping the build *in-source* pins every CWD to the depth where pwd
        # still works; the CONFIG_SHELL override below covers config.status.
        self.folders.build = ""
        self.folders.generators = "conan"

    def source(self):
        # conandata.yml carries url + filename + sha256; the codeload URL has no
        # file suffix, so `filename` must be passed explicitly or conan guesses
        # zip and strip_root fails.
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R32: never compare settings.os with == "Linux"
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"quagga supports Linux/OHOS only, not {self.settings.os}")

        tc = AutotoolsToolchain(self)

        # Link-time duplicate symbols (CCLD pimd): `pimd/pimd.h` and
        # `pimd/pim_version.h` declare the daemon's shared globals as *tentative
        # definitions* -- `struct thread_master *master;`,
        # `const char *const PIM_ALL_SYSTEMS;`, `const char * const
        # PIMD_VERSION;`, the `qpim_*` set, 14 objects in all -- i.e. without
        # `extern`, so *every* translation unit that includes the header emits
        # its own strong definition.  C compilers up to GCC 9 defaulted to
        # `-fcommon`, where the linker merges those COMMON symbols into one;
        # clang 15 (the OHOS toolchain) defaults to `-fno-common`, so each
        # definition became a separate `.bss`/`.rodata`/`.data.rel.ro` symbol
        # and `ld.lld` aborted the pimd link with 20 `duplicate symbol` errors
        # before hitting its own error limit (measured, W3 round 7).
        # Restoring the language default this 2018-era code was written against
        # is the complete fix and needs no upstream edit: zebra, bgpd, ripd,
        # ripngd, ospfd, ospf6d and isisd all linked clean without it.
        # Same recipe-level remedy as archives/c/chordii/4.5.3b and
        # archives/a/aris/2.2 (repo convention: tc.extra_cflags).
        tc.extra_cflags.append("-fcommon")

        # R26: internal libraries (libzebra/lib/bgpd/... convenience archives)
        # stay static; no system-name .so is produced that could pollute /lib.
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")

        if self.settings.os == "OHOS":
            # E091: sysroot <linux/socket.h> and musl <sys/socket.h> both define
            # struct sockaddr_storage; the musl guard is what keeps them apart.
            tc.extra_cflags.append("-D__MUSL__")
            # Linux UAPI headers (linux/rtnetlink.h, linux/if_addr.h, ...) needed
            # by zebra/rt_netlink.c and nhrpd/*.
            sysroot = self.conf.get("tools.build:sysroot", default="",
                                    check_type=str)
            if sysroot:
                tc.extra_cflags.append(f"-I{sysroot}/usr/include")
                tc.extra_cflags.append(f"-I{sysroot}/usr/include/aarch64-linux-ohos")
                tc.extra_ldflags.append(f"-L{sysroot}/usr/lib")

        # --- optional faces that cannot be satisfied on OHOS (path A) ---------
        tc.configure_args += [
            # SNMP is left off the way upstream switches it OFF: by not
            # asking for it.  configure.ac:307 only defines
            # --enable-snmp=smux|agentx and the guard at :1356 reads
            # `if test "${enable_snmp}" != ""`, so passing --disable-snmp
            # sets enable_snmp=no (non-empty) and *enters* the SNMP block
            # -> "configure: error: --enable-snmp given but unable to
            # find net-snmp-config" (measured, W3 round 6).
            "--without-libpam",        # no security/pam_appl.h in sysroot
            "--disable-capabilities",  # do not link libcap (cap_set_proc)
            "--disable-doc",           # no texinfo makeinfo in the toolchain
            "--disable-ospfapi",       # needs ossp-uuid + libss
            "--disable-ospfclient",    # links against libospf (ospfapi)
            "--disable-fpm",           # needs json-c
            "--disable-protobuf",      # needs libprotobuf/grpc
            "--disable-pcreposix",     # no libpcreposix
            "--disable-werror",        # clang 15 diagnostics on 2018 code
            # (no --disable-exampledir: `exampledir` does not exist in
            #  configure.ac, so the flag is an autoconf "unrecognized
            #  option" that only prints a warning and does nothing.)
            "--disable-gcc_ultra_verbose",
            "--disable-rusage",
            # vtysh (integrated interactive CLI) needs libreadline + a termcap
            # provider: `configure.ac:757-761` hard-errors when
            # AC_CHECK_LIB(readline, main) fails, and all four tputs probes
            # (termcap/tinfo/curses/ncurses) came back "no" in this sysroot.
            # archives/r/readline ships 8.2/8.3 recipes on origin/main, but the
            # exact-binary probe `conan install --requires=readline/8.3@ohpcd/
            # stable --build=never` reports "Unable to find ... in remotes" (8.2
            # likewise) => a publication gap, not an adaptation gap.
            # vtysh is the optional interactive front-end; the routed daemons
            # (zebra/bgpd/ospfd/...) and their netlink face stay built.
            "--disable-vtysh",
            # nhrpd is the only component that needs c-ares: configure.ac:1348
            # runs PKG_CHECK_MODULES([CARES], [libcares]) whenever nhrpd is
            # enabled and nhrpd/Makefile.am links @CARES_LIBS@.  c-ares 1.34.4/
            # 1.34.5/1.34.6 recipes do exist on origin/main, but the exact-binary
            # probes answer `Unable to find 'c-ares/1.34.6@ohpcd/stable' in
            # remotes` (1.34.5 likewise) => the same publication gap as readline.
            # NHRP (RFC 2332, NBMA overlay) is a niche daemon; the IGP/BGP suite
            # and zebra's netlink face are untouched.
            "--disable-nhrpd",
            # runtime identity: OHOS has no quagga:quagga account
            "--enable-user=root",
            "--enable-group=root",
            "--enable-vty_group=root",
        ]
        # NOTE on CONFIG_SHELL: it must be pinned *on the configure command
        # line* (see build()).  Anything exported from here loses to the profile
        # [buildenv] because conanbuild.sh sources conanautotoolstoolchain.sh
        # *before* conanbuildenv-<id>.sh (measured on this cache layout).
        tc.generate()

    def _write_ohos_config_guess(self):
        """E007: replace config.guess so configure can guess the OHOS triplet."""
        guess = os.path.join(self.source_folder, "config.guess")
        save(self, guess, """#!/bin/sh
# OHOS-aware config.guess (self-contained; replaces the GNU version copied by
# `autoreconf -i`, which does not recognise `uname -s` == "HarmonyOS").
machine=$(uname -m 2>/dev/null || echo unknown)
system=$(uname -s 2>/dev/null || echo unknown)
case "$system" in
    HarmonyOS|OHOS)
        echo "${machine}-unknown-linux-ohos"
        ;;
    *)
        echo "${machine}-unknown-linux-gnu"
        ;;
esac
exit 0
""")
        os.chmod(guess, 0o755)

    def _fix_hmdfs_umask(self, path):
        """HMDFS: config.status temp dirs created under umask 077 break builds."""
        if not os.path.isfile(path):
            return
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            content = fh.read()
        if "umask 077" in content:
            save(self, path, content.replace("umask 077", "umask 022"))

    def build(self):
        apply_conandata_patches(self)

        # R33: everything below comes from the Conan toolchain, no bare $CC /
        # $CFLAGS shell variables.
        # Step 1: bootstrap autotools (tarball ships only configure.ac).
        if not os.path.isfile(os.path.join(self.source_folder, "configure")):
            ret = self.run("autoreconf -fi", cwd=self.source_folder,
                           env="conanbuild")
            if ret != 0:
                raise ConanException(f"autoreconf -fi failed (rc={ret})")

        # Step 2: E007 must happen *after* autoreconf, which (re)installs the
        # GNU config.guess from automake's data dir.
        self._write_ohos_config_guess()
        self._fix_hmdfs_umask(os.path.join(self.source_folder, "configure"))

        autotools = Autotools(self)
        if self.settings.os == "OHOS":
            # E386 / DRAFT-6487 decisive half of the fix: autoconf's configure
            # re-execs itself under $CONFIG_SHELL, and the OHOS bash injected by
            # the profile [buildenv] cannot getcwd() on HMDFS
            # ("configure: error: working directory cannot be determined").
            # The env script exported from generate() loses to that buildenv
            # script (conanbuild.sh sources the toolchain first), so pin the
            # shell on the command line, where it wins.  The arg list is taken
            # from the generated toolchain conf through Autotools itself, so
            # nothing here is a hand-written flag.
            configure_cmd = os.path.join(self.source_folder, "configure")
            cmd = f'CONFIG_SHELL=/bin/sh "{configure_cmd}" {autotools._configure_args}'
            if self.run(cmd, env="conanbuild", ignore_errors=True) != 0:
                raise ConanException("configure failed (see log above)")
        else:
            autotools.configure()
        self._fix_hmdfs_umask(os.path.join(self.build_folder, "config.status"))

        autotools.make(args=["-j1"])
        # R51/rule4: really run the upstream suite; registered TESTS live in
        # tests/Makefile.am.  Failures must not be silently swallowed.
        autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)
        rmdir(self, os.path.join(self.package_folder, "share", "man"))
        # libtool .la files bake the build-time prefix into the package and
        # mislead downstream consumers of the internal convenience archives.
        for libdir in ("lib", "libexec"):
            path = os.path.join(self.package_folder, libdir)
            if os.path.isdir(path):
                for root, _dirs, files in os.walk(path):
                    for fname in files:
                        if fname.endswith(".la"):
                            os.remove(os.path.join(root, fname))

    def package_info(self):
        # quagga is a daemon suite, not a consumer library: no public headers or
        # import libs are exposed (internal libzebra.a etc. are convenience
        # archives).
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin", "sbin"]
