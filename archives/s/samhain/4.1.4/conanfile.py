#!/usr/bin/env python3
"""Conan recipe — samhain 4.1.4 (host integrity monitoring / HIDS, pure C, autotools).

Upstream site : https://www.la-samhna.de/samhain/
Source browser: https://trac.la-samhna.de/samhain/browser
License       : GPL-2.0-only (COPYING ships GPLv2 text)

HarmonyOS adaptation summary (per-flag rationale table lives in notes.md):

* config.guess / config.sub patched for the `HarmonyOS` uname (E007 family;
  the bundled patch-autotools-ohos.pl helper only scores 1/5 on these
  2014-era scripts, so the branch is hand-wired to `echo; exit` and
  config.sub gains the `linux-ohos` OS entries).
* c_random.sh gets a sum(1) fallback (the device has no sum(1)): without it
  my_key_*/POS_TF substitute empty values and `#if (POS_TF == 1)` fails to
  compile with "invalid token at start of a preprocessor expression".
* dnmalloc allocator disabled (--disable-dnmalloc): it aborts at runtime with
  `assertion failed: hashval < AMOUNTHASH` on this platform; upstream's own
  testhash.sh also builds with --disable-dnmalloc.
* pthread cancellation shims in src/sh_pthread.c (patch): the OHOS NDK
  exports neither pthread_cancel(), pthread_testcancel() nor
  pthread_setcanceltype(); samhain references them from the mutex macros
  and from sh_pthread_cancel_all()/sh_threaded_module_run().
* src/dnmalloc.c includes <sys/types.h> explicitly for BSD `u_int`
  (OHOS sys/time.h does not provide it transitively).
* src/sh_mounts.c includes <paths.h> for `_PATH_MOUNTED` (same class of
  glibc-transitive-include assumption).
* All daemon / network / database / SMTP configure switches are pinned off:
  the build is local file: mode only (task 10371 pre-lead requirement #1);
  each flag and its reason is recorded in notes.md and in
  manifest.yaml build.configure_options.
"""
import os
import shutil
import stat
import tarfile
from pathlib import Path

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


# Keep in sync with manifest.yaml build.configure_options and notes.md.
CONFIGURE_FLAGS = [
    # ── SMTP ────────────────────────────────────────────────────────────
    "--disable-mail",              # internal SMTP mailer off: no mail egress
    # ── network / daemon surface ───────────────────────────────────────
    "--enable-network=no",         # do not compile client/server mode (root of
                                   # both daemon and socket behaviour; upstream
                                   # default is already no, pinned explicitly)
    "--enable-udp=no",             # no 514/udp listener compile-in
    "--enable-port-check=no",      # port probing is network behaviour, and
                                   # /proc/net/{tcp,udp} is unreadable on OHOS
    "--disable-ipv6",              # IPv6 stack off
    "--disable-encrypt",           # client/server transport encryption off
    "--disable-srp",               # SRP authentication (client/server only) off
    "--enable-db-reload=no",       # SIGHUP database reload is daemon behaviour
    "--disable-message-queue",     # SysV message queue (daemon IPC) off
    # ── external execution surface ──────────────────────────────────────
    "--disable-external-scripts",  # no external script hooks
    "--disable-shellexpand",       # no shell expansion when reading config
    "--without-gpg",               # GnuPG not installed on the device anyway
    # ── network-adjacent compile surfaces ───────────────────────────────
    "--without-prelude",           # Prelude IDS component (network log shipper)
    "--without-libwrap",           # TCP Wrappers compile surface
    # ── platform workaround ─────────────────────────────────────────────
    "--disable-dnmalloc",          # dnmalloc asserts `hashval < AMOUNTHASH`
                                   # at runtime on OHOS; system allocator is
                                   # upstream-sanctioned (testhash.sh uses the
                                   # same flag)
    # ── trusted users (path trust model) ───────────────────────────────
    "--with-trusted=0,2,1000,1006,20001006,20020085",
                                   # HMDFS maps every file owner to the shared
                                   # uid 20001006, directories are group
                                   # writeable under gid 1006 (whose member uid
                                   # 1006 must be trusted as well) and the
                                   # sandbox euid is 20020085 (device-facts
                                   # §一.10).  Upstream default is [0] only, so
                                   # every config/state path check fails with
                                   # "owner ... not in the list of trusted
                                   # users" / "is group writeable" for non-root
                                   # users (upstream runs its own tests as
                                   # root, which is why this never surfaced
                                   # there).
    #
    # --without-database is deliberately ABSENT: upstream configure.ac runs
    # the AC_ARG_WITH(database) action BEFORE testing withval != no, so
    # `--without-database` itself trips the fatal
    #   "With --with-database, --enable-xml-log is required as well."
    # The default is already no database backend; verified in configure
    # output (no mysql/postgresql/oracle/odbc probes executed).
]


class SamhainConan(ConanFile):
    name = "samhain"
    version = "4.1.4"
    description = "Samhain host integrity monitoring system (file integrity, local file: logging)"
    license = "GPL-2.0-only"
    homepage = "https://www.la-samhna.de/samhain/"
    url = "https://trac.la-samhna.de/samhain/browser"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # No third-party dependencies: every external library probe in
        # configure.ac is optional and all of its consumers are switched off
        # above (W0 evidence in notes.md).
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        # The official release artifact is a *container*: it holds
        # samhain-4.1.4.tar.gz (the real source tarball) + its PGP signature.
        get(self, **self.conan_data["sources"], strip_root=False)
        inner = os.path.join(self.source_folder, "samhain-4.1.4.tar.gz")
        with tarfile.open(inner, "r:gz") as tf:
            try:
                tf.extractall(self.source_folder, filter="data")
            except TypeError:  # python < 3.12
                tf.extractall(self.source_folder)
        # promote the single top directory (samhain-4.1.4/) and drop the
        # container leftovers so basic_layout sees the source tree at root.
        top = os.path.join(self.source_folder, "samhain-4.1.4")
        if os.path.isdir(top):
            for item in os.listdir(top):
                dst = os.path.join(self.source_folder, item)
                if os.path.exists(dst):
                    shutil.rmtree(dst) if os.path.isdir(dst) else os.remove(dst)
                shutil.move(os.path.join(top, item), dst)
            os.rmdir(top)
        for leftover in ("samhain-4.1.4.tar.gz", "samhain-4.1.4.tar.gz.asc"):
            p = os.path.join(self.source_folder, leftover)
            if os.path.exists(p):
                os.remove(p)

    def generate(self):
        # HarmonyOS hmmac: `mktemp -d` creates directories with broken
        # permissions (umask 077 -> 2700 + owner mapping), so config.status
        # cannot write confXXXX/subs1.awk ("Permission denied").  A mktemp
        # that always fails makes autoconf's AS_TMPDIR fall back to plain
        # mkdir, which works (same fix as the acct recipe).
        wrapper_dir = Path(self.build_folder) / ".hmos_fix"
        wrapper_dir.mkdir(exist_ok=True)
        wrapper = wrapper_dir / "mktemp"
        wrapper.write_text(
            "#!/bin/sh\n"
            "# HarmonyOS hmmac: mktemp -d yields dirs whose perms are unusable.\n"
            "# Fail so autoconf AS_TMPDIR uses the mkdir fallback.\n"
            "exit 1\n"
        )
        wrapper.chmod(wrapper.stat().st_mode | stat.S_IEXEC)

        tc = AutotoolsToolchain(self)  # prefix=/ + DESTDIR=package_folder
        # samhain overrides autoconf's _AC_INIT_PARSE_ARGS (configure.ac:3) and
        # does NOT know the --oldincludedir standard-dir option that conan adds
        # by default -> configure aborts with "unrecognized option".  It also
        # warns that bindir/libdir/includedir are ignored (it only honours
        # sbindir), so drop all four; --sbindir/--prefix stay (binary layout
        # depends on them: prefix=/ + DESTDIR -> package bin/).
        tc.configure_args = [
            a for a in tc.configure_args
            if not a.startswith(("--oldincludedir", "--bindir", "--libdir", "--includedir"))
        ]
        tc.configure_args.extend(CONFIGURE_FLAGS)
        tc.generate()

        env = Environment()
        env.prepend_path("PATH", str(wrapper_dir))
        # SysV semaphore off: OHOS seccomp kills semget (probe rc=159), and
        # with HAVE_SYS_SEM_H defined sh_sem.c calls semget during every
        # `-t init` → SIGSYS.  Feeding the AC_CHECK_HEADERS cache variable
        # makes configure skip the header, so sh_sem.c compiles its upstream
        # `#else` no-op fallback (designed for IPC-less platforms).
        env.define("ac_cv_header_sys_sem_h", "no")
        env.vars(self).save_script("hmos_env")

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()  # DESTDIR=package_folder, flat bin/ etc/ var/ layout

    def package_info(self):
        # conan passes --sbindir=${prefix}/bin, so samhain lands in bin/.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
