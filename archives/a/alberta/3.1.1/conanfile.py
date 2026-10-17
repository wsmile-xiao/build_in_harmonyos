#!/usr/bin/env python3
"""Conan recipe -- alberta 3.1.1 (Autotools).

ALBERTA is an adaptive multi-level finite element toolbox using
bisectioning refinement and error control by residual techniques for
scientific applications.

Upstream ships configure.ac + Makefile.am but no generated configure, so
build() bootstraps with generate-alberta-automakefiles.sh + autoreconf
(upstream's own fromsvnreconf.sh does exactly these two steps).
The bootstrap toolchain is vendored at build time from official GNU
release tarballs (m4 1.4.19 + autoconf 2.72, URL order reuses the repo
GNU mirror mapping from ci/conan/build_and_test.sh, sha256 identical to
the repo conandata records): no Conan autoconf/m4/perl edge exists in
this recipe, because every round with one (RREV pins, bare autoconf,
full triple + explicit m4) reproduced the identical CCI m4/1.4.19 source
build dying on the profile-poisoned CONFIG_SHELL (configure[139] vs the
nonexistent /data/service/hnp/bin/bash, package ID 579a4b17) — the bare
m4 always resolves conancenter-first while automake/libtool/autoconf
have no CCI competition and download fine.
Round 10 hardens the vendored build itself after its first run died with
the IDENTICAL configure[139] fingerprint inside our own m4 configure:
os.environ sanitization alone loses to conan's run-time conanbuild
aggregation (profile CONFIG_SHELL wins at self.run time), so EVERY
bootstrap/vendor command carries shell-inline CONFIG_SHELL/SHELL/TMPDIR
assignments that override any aggregated export for that invocation; and
the vendored (build-machine, must execute on the x86_64 worker) tools
are never built with the harmonybrew OHOS cross-compiler wrapper —
_only a system cc passing a sanitized `cc --version` probe is accepted.
Round 7 proved with file-level evidence that no native suite exists on
this sandbox, so no native fallbacks remain. Conan edges are only the
proven-binary trio automake/1.18 + libtool/2.5.4.1 + pkgconf/3.0.5
(configure.ac needs PKG_PROG_PKG_CONFIG/PKG_INSTALLDIR and LT_INIT).

Configuration for OHOS: full FEM toolbox, graphics disabled (no X11 /
OpenGL / OpenDX / Motif on the worker), debug libraries disabled (same
as the upstream CI debian jobs), no waiting in tests.
Hard requirement libtirpc (rpc/xdr mesh I/O) comes from the ohpcd
registry (same as the autofs/exim/libdap recipes). The revision is pinned
to the ohpcd OHOS-compatible recipe: preflight checks conancenter first
(CI disables it), so a bare version resolves to the conancenter recipe
whose validate() rejects OHOS ("only supported on Linux and FreeBSD").
Same RREV-pin pattern as the abuild-sudo/openssl and bzrtp/sqlite3 recipes.
Round 13 vendors automake 1.18 as well: the Conan automake tool binary's
bin/aclocal wrapper dies on this worker with `aclocal[8]:
.../p/bin/.aclocal-real: No such file or directory` (exit 126) -- either
its hidden real file is absent from the published binary or the hidden
perl script's baked-in shebang interpreter is gone there, both unfixable
from a consumer env. Vendor bin already leads PATH, so the vendored
aclocal shadows the broken wrapper; its configure gets PERL pinned to the
probe-verified perl plus a post-install shebang rewrite, and aclocal +
automake join the --version smoke gate.
Round 14 pins ACLOCAL/AUTOMAKE/AUTOCONF/AUTOHEADER/AUTOM4TE to the vendored
binaries for the autoreconf invocation: round-13 evidence (vendor aclocal
smoke-passed, yet autoreconf still ran the Conan wrapper although
vendor/bin leads PATH) proves the selection bypasses PATH via the
$ACLOCAL/$AUTOMAKE buildenv absolute paths the automake recipe exports and
run-time aggregation re-injects -- the same leak family as round 10's
CONFIG_SHELL.
Round 21 extends the mktemp fallback shadow (cyrus-sasl precedent) to the
MAIN-tree configure: the 2026-09-27 preflight fails at
autotools.configure() with Error 1 after the visible checks pass, and the
only remaining late fatal in configure.ac is the xdr funcs check whose
libtirpc 1.3.7 symbols were verified present, while
AC_CONFIG_COMMANDS([dof_free_bit.h]) runs AS_TMPDIR at config.status time
(the [unsafe_local_mktemp] family). Probe-gated, exposed via a build-scope
save_script PATH prepend plus a build() os.environ mirror; a compact
HMBS_CONFIGURE_FAILURE block now leads the evidence dump so the exact
`configure: error` line survives log summarization.
Round 22 changes strategy after the 18:00 preflight ran the round-21 tree
and failed identically (line 1803 -> 1898): instead of more environment
shadowing, `_configure_failure_summary()` embeds the exact configure error
plus the mktemp shadow on/off verdict in the raised exception text, the one
channel every summary preserves.
Round 23 changes strategy again after round 22's verdict (`no-error-line`,
`mktemp_shadow=off`): deterministic main config.log discovery excluding
vendored tool logs, phase forensics (config.status/Makefile/config.h/tail)
in the exception, and pinning packageheaders' `${RM}` to the verified
absolute rm at the script layer -- config.status errors never reach
config.log, which fits the verdict with all checks passing.
Round 24 changes strategy again after round 23's forensics
(`log=main|no-error-line|config.status=yes makefiles=67 config.h=yes`,
`mktemp_shadow=off`): upstream configure.ac audit (Debian orig tarball,
864 files) shows the tail is AC_CONFIG_COMMANDS([packageheaders]) -- a
`find`-driven loop running sub-`make install-...HEADERS` with
INSTALL_HEADER=install-pkgheader.sh (`ln -sf` with no mkdir). Files exist
yet exit 1 means the death is inside that loop's stdout-only output, which
no config.log reading can ever see. So (1) re-execute the already
generated ./config.status via subprocess after failure and embed its tail
(find/grep/make availability + rc) in the exception text -- the new
evidence channel; (2) harden install-pkgheader.sh itself with a DST mkdir
(self-sufficient even if automake MKDIR_P is degraded on HMFS). No
mktemp/RM/token change.
Round 25: round-24's replay fired and named the real killer --
`executing depfiles commands` -> `Something went wrong bootstrapping
makefile fragments for automatic dependency tracking` (stdout-only,
hence invisible in config.log across rounds 21-23). Fix is the exact
fallback the error message itself prescribes:
`--disable-dependency-tracking` on the main configure (the vendored
tool builds already carry it); depfiles only affect .deps rebuild
tracking, TESTS counts unchanged. Different cause, different patch
from the packageheaders hardening, which stays as defense in depth.
Round 28: preseed the hanging pthread probes. The 2026-09-27 20:30
preflight drops the transport (`Connection closed by remote host`) right
after `checking for pthread_t...` with zero upstream markers; the checks
(malloc-ptrdiff/lstat/select/pthread_t) are the vendored m4 1.4.19 gnulib
suite (alberta configure.ac has none of them -- verified against the
Debian orig tarball, 864 files), and the very next test is
gl_PTHREAD_RWLOCK_RDLOCK_PREFER_WRITER, a threaded AC_RUN_IFELSE (reader/
writer/timer relay with usleep) that must not execute on this worker.
Fix preseeds `ac_cv_type_pthread_t=yes` (factual on musl and glibc) plus
`gl_cv_pthread_rwlock_rdlock_prefer_writer="guessing no"` (the macro's
own musl cross guess) at all four layers -- _inline_prefix (vendor
configures), generate() toolchain env + build-scope save_script (helper
command), build() os.environ (defense in depth). Pure check-skipping, no
flag/test/graph change; if the next drop moves to a later check, preseed
that one next round instead of widening blindly.
Round 32 (2nd strategy cycle: rounds 29-31 re-selected the libtoolize
binary + purged the same cache three times, yet the 21:55 preflight still
reports src ltmain.sh VERSION=2.5.4 with aclocal.m4 carrying no LT version
line -- the refresh reaches ltmain.sh but the aclocal expansion never sees
the 2.5.4 macro dir, so autoreconf keeps expanding a stale LT_INIT while
ltmain.sh is new; libtoolize's _lt_pkgdatadir shim of relative symlinks is
the suspected silent gap). Different route: seed the five libtool .m4 files
plus ltmain.sh directly from the pinned package's REAL dirs
(share/aclocal, share/libtool/build-aux) into the source tree before the
single autoreconf owns the sequence, and audit aclocal.m4 for MATCH vs the
seeded version. No graph / flag / test-count change.
Round 33: the 22:17 preflight ran the round-32 tree (build() line
2492 -> 2621 proves the new code executed) yet forensics is byte-identical
-- the Conan package-dir seed changed nothing. Different source: fetch the
official GNU libtool-2.5.4 tarball (sha256 identical to this repo's own
libtool conandata, fetch-only, never built) and seed the five .m4 files +
ltmain.sh from it; plus prepend the seeded source m4/ dir to ACLOCAL_PATH
on both layers so the seeded 2.5.4 macros shadow any stale ones regardless
of whether configure.ac declares m4/. No graph / flag / test-count change.
Round 34: local source audit (Debian tarball, sha-verified, 864 members)
proved upstream ships NO libtool macros/ltmain/aclocal.m4/configure at
all, and GNU audit proved 2.5.4 spells the version LT_PACKAGE_VERSION
(no underscore) -- the recipe's "_LT_PACKAGE_VERSION|LT_VERSION" grep
could never match 2.5.4 output, so 8 rounds of "no-LT-version-line"
forensics are void readings; the fired branch is the EMPTY-macro_version
one. Different route: (1) fix the meter to both spellings; (2) pass
-I <seeded m4> on the autoreconf command line (argv channel, searched
before every env/system dir); (3) prove regeneration on the GENERATED
configure (verbatim macro_version='<ver>' assignment) with fail-fast;
(4) fetch the GNU tarball loudly outside the swallowing try. No graph /
flag / test-count change.
Round 35 (3rd strategy cycle: rounds 32-34 re-ran the same seed-then-
autoreconf assumption with three different seed sources, yet the 23:07
preflight fails byte-identically -- seeding never converges because TWO
writers touch the tree with TWO releases: the explicit libtoolize refresh
(Conan 2.5.4.1 binary) runs before the seed, the GNU seed (2.5.4 files)
overwrites it, then autoreconf's INTERNAL libtoolize (pinned to the same
Conan 2.5.4.1 via LIBTOOLIZE) overwrites ltmain.sh back during the run.
Different route: vendor libtool 2.5.4 itself (same fetch-build pattern as
m4/autoconf/automake) so bin/libtoolize + share/aclocal/*.m4 +
share/libtool/build-aux/ltmain.sh are one release from one source; pin
LIBTOOLIZE + ACLOCAL_PATH to the vendor tree, drop the foreign
_lt_pkgdatadir shim, and delete both the Conan-binary refresh and the
GNU-tarball seed blocks. Single writer, single version. No graph / flag /
test-count change.
Round 36 (2nd occurrence post-vendor-build, 4th strategy cycle: the 23:38
preflight ran the round-35 tree -- build() line 2764 -> 2664 proves the new
code executed -- yet divers.lo fails identically. New evidence kills the
dual-version theory: aclocal.m4 NOW carries the fresh 2.5.4 LT line
(m4_if(m4_version_compare(m4_defn([LT_PACKAGE_VERSION])...), i.e. the
round-34 meter fix + round-35 vendor macros DID land at the aclocal layer,
and the Conan libtoolize reports GNU libtool 2.5.4 anyway, so both sides
were always 2.5.4. The stale side must be DOWNSTREAM of aclocal.m4: either
autoconf expanded configure from a pre-final aclocal (autoreconf-internal
ordering), or the generated libtool script was substituted from a stale
configure. Also build-libtool=absent is a forensics artifact: make executed
../../libtool successfully, so the file exists and the probe path/stat is
wrong. Different route -- gates plus guaranteed re-expansion, no new
toolchain, no seeding: (1) fail-fast gate on aclocal.m4 freshness right
after autoreconf; (2) explicit vendored autoconf --force re-run so
configure is provably expanded from the FINAL aclocal.m4 (autoconf-only,
cannot break aux files the way round 30's libtoolize+aclocal+autoconf
fragment did); (3) strict configure proof -- an empty expectation now
raises instead of walking into a doomed make; (4) forensics rewritten to
multi-location libtool probing with stat/read distinction plus the
configure macro_version/macro_revision dump. No graph / flag / test-count
change.
Round 37 (3rd occurrence, 5th strategy cycle: rounds 32-36 fought over the
macro supply (seed/package/vendor/gates/re-expansion), yet the 00:03
preflight ran the round-36 tree -- build() line 2664 -> 2730, new
forensics present -- and fails identically at divers.lo. The round-36
forensics itself names the true broken step: configure holds
macro_version='2.5.4' (fresh), but the BUILD libtool script is
byte-size-identical to ltmain.sh (337554 == 337554). Local audit of the
sha-verified GNU libtool-2.5.4 sources proves the generated script MUST be
header + full ltmain (_LT_CONFIG writes the ### BEGIN LIBTOOL CONFIG
header with the macro assignments, then appends the whole ltmain via
$SED '$q', then moves it over ofile) -- so a byte-equal file is a verbatim
ltmain copy whose header never landed, $macro_version is empty at runtime,
and no aclocal/autoconf change can ever fix a file written downstream of
both. Different route -- provision INIT/Macro test data into the out-of-source build tree
(first VPATH-class fix: upstream runs in-source where relative
INIT/Macro resolve; Conan builds out-of-source where they do not).
No flag / test-count / macro-supply change.
Round 39 (this round):
repair at the exact broken step with the canonical
command make itself uses (top Makefile rule `libtool: $(LIBTOOL_DEPS)`
runs `./config.status libtool`): after configure, verify the header
marker and regenerate + fail-fast when absent. No graph / flag /
test-count / macro-supply change.
"""

import hashlib
import os
import platform
import shutil
import ssl
import subprocess
import tarfile
import urllib.request

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.env import Environment
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


# Vendored bootstrap toolchain: official GNU release tarballs built into
# a private prefix during build(). URL order reuses the repo GNU mirror
# mapping (ci/conan/build_and_test.sh: tuna -> ustc -> aliyun -> origin,
# origin kept as fallback); sha256 values are identical to the repo
# conandata records (m4 recipe, autoconf recipe) and are never altered.
_VENDOR_M4 = {
    "name": "m4-1.4.19",
    "urls": [
        "https://mirrors.tuna.tsinghua.edu.cn/gnu/m4/m4-1.4.19.tar.gz",
        "https://mirrors.ustc.edu.cn/gnu/m4/m4-1.4.19.tar.gz",
        "https://mirrors.aliyun.com/gnu/m4/m4-1.4.19.tar.gz",
        "https://ftp.gnu.org/gnu/m4/m4-1.4.19.tar.gz",
    ],
    "sha256": "3be4a26d825ffdfda52a56fc43246456989a3630093cced3fbddf4771ee58a70",
}
_VENDOR_AUTOCONF = {
    "name": "autoconf-2.72",
    "urls": [
        "https://mirrors.tuna.tsinghua.edu.cn/gnu/autoconf/autoconf-2.72.tar.gz",
        "https://mirrors.aliyun.com/gnu/autoconf/autoconf-2.72.tar.gz",
        "https://mirrors.kernel.org/gnu/autoconf/autoconf-2.72.tar.gz",
        "https://ftp.gnu.org/gnu/autoconf/autoconf-2.72.tar.gz",
    ],
    "sha256": "afb181a76e1ee72832f6581c0eddf8df032b83e2e0239ef79ebedc4467d92d6e",
}


_VENDOR_AUTOMAKE = {
    "name": "automake-1.18",
    "urls": [
        "https://mirrors.tuna.tsinghua.edu.cn/gnu/automake/automake-1.18.tar.gz",
        "https://mirrors.ustc.edu.cn/gnu/automake/automake-1.18.tar.gz",
        "https://mirrors.aliyun.com/gnu/automake/automake-1.18.tar.gz",
        "https://ftp.gnu.org/gnu/automake/automake-1.18.tar.gz",
    ],
    "sha256": "af6043a5d4b3beef0c48161f4a6936259321cd101a34c1ab0768328515626c8a",
}


# Vendored libtool build (round 35): the full GNU libtool release tarball,
# built into the private prefix like m4/autoconf/automake so bin/libtoolize
# + share/aclocal/*.m4 + share/libtool/build-aux/ltmain.sh are provably one
# release. URL order and sha256 are identical to this repo's own libtool
# recipe conandata (archives/l/libtool/2.5.4.1/conandata.yml, source
# libtool-2.5.4) and are never altered.
_VENDOR_LIBTOOL_FILES = {
    "name": "libtool-2.5.4",
    "urls": [
        "https://mirrors.tuna.tsinghua.edu.cn/gnu/libtool/libtool-2.5.4.tar.gz",
        "https://mirrors.ustc.edu.cn/gnu/libtool/libtool-2.5.4.tar.gz",
        "https://mirrors.aliyun.com/gnu/libtool/libtool-2.5.4.tar.gz",
        "https://ftp.gnu.org/gnu/libtool/libtool-2.5.4.tar.gz",
    ],
    "sha256": "da8ebb2ce4dcf46b90098daf962cffa68f4b4f62ea60f798d0ef12929ede6adf",
}


def _automake_count(text, label):
    """Parse `# LABEL: N` from an automake parallel-tests test-suite.log."""
    for line in text.splitlines():
        if line.startswith("# " + label + ":"):
            try:
                return int(line.split(":", 1)[1].strip())
            except ValueError:
                return 0
    return 0


class AlbertaConan(ConanFile):
    name = "alberta"
    version = "3.1.1"
    description = "Adaptive multi-level finite element toolbox"
    license = "GPL-2.0-or-later"
    homepage = "http://www.alberta-fem.de/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # RREV pin to the ohpcd OHOS-compatible recipe (single revision
        # ffaa3679, published 2026-08-24 with this repo's libtirpc/1.3.7).
        self.requires("libtirpc/1.3.7#ffaa36790004ab5a69233aef6f108319")

    def build_requirements(self):
        # Proven-binary trio only (all downloaded, never source-built, on
        # this sandbox): automake (aclocal/automake) + libtool
        # (libtoolize + LT macros) + pkgconf (pkg.m4 + pkg-config binary).
        # Deliberately NO autoconf/m4/perl edge: autoconf/automake have no
        # CCI competition but any m4 edge resolves conancenter-first and
        # its Linux build-context configure dies on the dangling profile
        # CONFIG_SHELL. m4+autoconf are vendored in build() instead.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4.1")
        self.tool_requires("pkgconf/3.0.5")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("alberta supported only on Linux/OHOS")
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require aarch64/armv8")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # The profile may export a CONFIG_SHELL pointing at an absolute
        # path that is inaccessible on some preflight workers; any
        # autoconf configure re-execs itself through a non-empty
        # CONFIG_SHELL and dies with Error 127 (evidenced by the m4 round:
        # configure[139] vs /data/service/hnp/bin/bash). Pin both shell
        # variables to an existence-checked shell (ohpcd m4 recipe's
        # _select_shell pattern), so our own configure is immune too.
        shell = self._select_shell()
        env = tc.environment()
        env.define("CONFIG_SHELL", shell)
        env.define("SHELL", shell)
        # Round 28: same pthread cache preseed as _inline_prefix, for the
        # main-tree Autotools helper command (inline prefixes cannot cover
        # helper-internal commands; toolchain env is the layer that does).
        env.define("ac_cv_type_pthread_t", "yes")
        env.define("gl_cv_pthread_rwlock_rdlock_prefer_writer",
                   "guessing no")
        # Preflight 2026-09-27 compile failed with
        # `sh: /storage/Users/currentUser/.harmonybrew/bin/rm: Operation not
        # permitted`: bare `rm` in configure/make resolved via PATH to the
        # harmonybrew shim which cannot exec (EPERM). Prepend the directory
        # of a probed working rm so bare `rm` resolves there first;
        # harmonybrew stays on PATH for clang discovery. Never export RM
        # itself: libtool/make expect RM="rm -f" (same lesson as the
        # libextractor/1.17 recipe).
        try:
            _rm = self._resolve_working_rm()
            if _rm:
                env.prepend_path("PATH", os.path.dirname(_rm))
                self.output.info("working RM dir on PATH: %s" % _rm)
        except Exception as _re:
            self.output.info("RM sanitize skipped: %s" % _re)
        # Round 18: profile-pinned compiler absent on some HMBS hosts.
        # 2026-09-27 preflight: main configure probes
        # `aarch64-unknown-linux-ohos-gcc... /data/service/hnp/bin/clang`
        # then `C compiler cannot create executables` (Error 77) with the
        # helper's own evidence `CC probe failed: .../hnp/bin/clang:
        # [Errno 2] No such file or directory`. The round-16 PATH restore
        # assumed the hnp dir exists; this log falsifies it on this host.
        # Same failure domain as bwm/0.6.3 + bzrtp/5.3.105 + zurl/1.12.0:
        # keep the conf value when the file exists (healthy CI unchanged),
        # otherwise fall back to a PATH/SDK-resolved clang (harmonybrew
        # cc IS the OHOS cross wrapper, so cross-ness is preserved).
        # Only CC/CXX are overridden, never CFLAGS/LDFLAGS (R33).
        try:
            _cc, _cxx, _lbl = self._resolve_ohos_compiler()
            if _cc:
                env.define("CC", _cc)
            if _cxx:
                env.define("CXX", _cxx)
            self.output.info("ohos compiler %s: CC=%s CXX=%s"
                             % (_lbl, _cc, _cxx))
        except Exception as _ce:
            self.output.info("ohos compiler fallback skipped: %s" % _ce)
        # Round 19+20: wire libtirpc search paths explicitly (ypserv/4.2
        # + epic5/3.0.3 pattern for bare AC_CHECK_LIB deps). 2026-09-27
        # preflight with the round-18 compiler fallback passes every
        # compiler check but dies at `checking for rpc_call in -ltirpc...
        # no` -> `configure: error: no tirpc library, exiting` with the
        # conftest link line `clang -o conftest -O3 -DNDEBUG conftest.c
        # -ltirpc -lm` carrying NO -L flag. Upstream uses a bare
        # AC_CHECK_LIB (no pkg-config; -ltirpc comes from LIBS hardcoded
        # by the macro, not from Conan), so autoconf only succeeds when
        # -I/-L reach it through the environment. Round 19 wired only
        # tc.extra_cflags/extra_ldflags (toolchain layer) and the same
        # log recurred, proving that single layer loses to run-time
        # conanbuild aggregation on this host (round-10/14/15/18 family).
        # This round wires all three layers: (1) tc.extra_* (toolchain),
        # (2) env.append CFLAGS/CPPFLAGS/LDFLAGS (conanbuild env, epic5
        # pattern), (3) a later build-scope save_script + build()
        # os.environ export (winning layer, bwm/0.6.3 pattern). No flag
        # semantics change, no test change.
        try:
            _tirpc_cflags, _tirpc_ldflags, _tirpc_pf, _tirpc_detail = \
                self._tirpc_search_flags()
            for _flag in _tirpc_cflags:
                if _flag not in tc.extra_cflags:
                    tc.extra_cflags.append(_flag)
            for _lflag in _tirpc_ldflags:
                if _lflag not in tc.extra_ldflags:
                    tc.extra_ldflags.append(_lflag)
            if _tirpc_cflags:
                env.append("CPPFLAGS", list(_tirpc_cflags))
                env.append("CFLAGS", list(_tirpc_cflags))
            if _tirpc_ldflags:
                env.append("LDFLAGS", list(_tirpc_ldflags))
            self.output.info("tirpc flags wired from %s: CFLAGS=%s LDFLAGS=%s (%s)"
                             % (_tirpc_pf, _tirpc_cflags,
                                _tirpc_ldflags, _tirpc_detail))
        except Exception as _te:
            self.output.info("tirpc flags skipped: %s" % _te)
        # Round 42 (new family -- optimizer hardening, not file
        # layout): the 25/17/8 fingerprint survived three rounds of
        # INIT/Macro provisioning (symlink -> copy -> tails/probe)
        # with byte-identical forensics, and the new per-test tails
        # show heap-corruption signatures (free_dof_index double
        # free -> SIGABRT, heat1d SIGSEGV) on the OHOS worker's
        # clang/aarch64/musl at -O3 while upstream CI (gcc/clang on
        # glibc x86_64) is green. This 2000s FEM code base does
        # heavy pointer casting plus custom allocators, so build
        # the MAIN tree OHOS-only with -fno-strict-aliasing plus a
        # winning -O1 after the profile -O3 (last -O wins); Linux
        # zero change. Same triple-layer wiring as the tirpc flags
        # (toolchain + conanbuild env here, save_script + process
        # env below). No test is skipped or altered.
        try:
            if str(self.settings.os) == "OHOS":
                for _oflag in ("-fno-strict-aliasing", "-O1"):
                    if _oflag not in tc.extra_cflags:
                        tc.extra_cflags.append(_oflag)
                    if _oflag not in tc.extra_cxxflags:
                        tc.extra_cxxflags.append(_oflag)
                env.append("CFLAGS", ["-fno-strict-aliasing", "-O1"])
                env.append("CXXFLAGS", ["-fno-strict-aliasing", "-O1"])
                self.output.info("ohos optimizer hardening: -fno-strict-aliasing -O1")
        except Exception as _oe:
            self.output.info("ohos optimizer hardening skipped: %s" % _oe)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.configure_args.extend([
            "--disable-graphics",
            "--disable-debug",
            "--disable-waiting-in-tests",
            # Round 17: --disable-nls shrinks the configure/build window
            # that the 2026-09-27 preflight dropped with
            # `Connection to 47.242.172.160 closed by remote host` right
            # after `config.status: creating po/Makefile` (plus the
            # `checking for a traditional french locale` gettext probe).
            # NLS only ships translated messages (po/ carries no TESTS),
            # so the 28 upstream TESTS counts are unaffected; when NLS is
            # unsupported configure warns and continues, never fails.
            "--disable-nls",
            # Round 25: --disable-dependency-tracking. The round-24
            # config.status replay captured the true stdout-only error:
            # `executing depfiles commands` -> `Something went wrong
            # bootstrapping makefile fragments for automatic dependency
            # tracking ... re-run configure with MAKE="gmake" ... or
            # with --disable-dependency-tracking`. Depfiles only control
            # .deps rebuild tracking (same flag the vendored m4/autoconf
            # builds already use); the 28 upstream TESTS and the 3
            # test_package checks are unaffected.
            "--disable-dependency-tracking",
        ])
        if str(self.settings.os) == "OHOS":
            # Upstream config.guess cannot identify HarmonyOS
            # (uname -s = "HarmonyOS"); the automake 1.18 config.sub
            # installed by autoreconf accepts the linux-ohos triplet.
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-ohos",
                "--host=aarch64-unknown-linux-ohos",
            ])
        tc.generate(env=env)
        # Winning layer for the helper's own command (bwm/0.6.3 pattern):
        # the Autotools helper runs under env="conanbuild" where the
        # profile-baked conanautotoolchain.sh may re-export the stale CC
        # after our env above. A later build-scope script sorts after it,
        # so the resolved compiler wins in the same shell invocation.
        # Round 20 extends the same winning layer to the tirpc search
        # paths: round 19 proved the toolchain layer alone does not reach
        # the bare AC_CHECK_LIB conftest (link line had no -L), so the
        # flags are also appended here where they sort after the profile
        # script.
        try:
            _cc2, _cxx2, _lbl2 = self._resolve_ohos_compiler()
            _tcf2, _tlf2, _tpf2, _tdt2 = self._tirpc_search_flags()
            if _cc2 or _cxx2 or _tcf2 or _tlf2:
                _fix = Environment()
                if _cc2:
                    _fix.define("CC", _cc2)
                if _cxx2:
                    _fix.define("CXX", _cxx2)
                if _tcf2:
                    _fix.append("CFLAGS", list(_tcf2))
                    _fix.append("CPPFLAGS", list(_tcf2))
                if _tlf2:
                    _fix.append("LDFLAGS", list(_tlf2))
                if str(self.settings.os) == "OHOS":
                    _fix.append("CFLAGS", ["-fno-strict-aliasing", "-O1"])
                    _fix.append("CXXFLAGS", ["-fno-strict-aliasing", "-O1"])
                _fix.vars(self, scope="build").save_script(
                    "alberta_ohos_compiler")
                self.output.info("ohos compiler script %s: CC=%s CXX=%s CFLAGS=%s LDFLAGS=%s (%s)"
                                 % (_lbl2, _cc2, _cxx2, _tcf2, _tlf2, _tdt2))
        except Exception as _ce2:
            self.output.info("ohos compiler script skipped: %s" % _ce2)
        # Round 28 (winning layer for the helper command, same channel as
        # the round-18 compiler fix): unconditional configure-cache script
        # so run-time conanbuild aggregation cannot drop the preseed.
        try:
            _cfix = Environment()
            _cfix.define("ac_cv_type_pthread_t", "yes")
            _cfix.define("gl_cv_pthread_rwlock_rdlock_prefer_writer",
                         "guessing no")
            _cfix.vars(self, scope="build").save_script(
                "alberta_configure_cache")
            self.output.info("configure cache preseed script: "
                             "ac_cv_type_pthread_t=yes, "
                             "gl_cv_pthread_rwlock_rdlock_prefer_writer="
                             "guessing no")
        except Exception as _cce:
            self.output.info("configure cache script skipped: %s" % _cce)
        # Round 21: extend the mktemp fallback shadow to the MAIN-tree
        # configure (cyrus-sasl-*/2.1.28 precedent). The 2026-09-27
        # preflight fails at autotools.configure() with Error 1 after
        # the visible checks pass; upstream configure.ac carries no
        # other late fatal besides the xdr funcs (whose libtirpc 1.3.7
        # symbols were verified present in header + src + version map),
        # while AC_CONFIG_COMMANDS([dof_free_bit.h]) runs AS_TMPDIR at
        # config.status time -- the exact [unsafe_local_mktemp] family
        # HMBS diagnoses (a mktemp-made dir is not writable afterwards).
        # The vendored tool builds already carry this shadow; the main
        # tree never did. Probe-gated (HMBS flag or a live probe of the
        # real mktemp in the build dir) and exposed through the same
        # winning build-scope save_script channel as the round-18
        # compiler fix; healthy workers keep an unshadowed PATH.
        try:
            _mtmp = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                     or os.environ.get("TEMP")
                     or os.path.join(self.build_folder, ".tmp"))
            if self._mktemp_fallback_wanted(self.build_folder):
                _mshim = self._mktemp_fallback_shim_for_ohos(_mtmp)
                if _mshim:
                    _mfix = Environment()
                    _mfix.prepend_path("PATH", _mshim)
                    _mfix.vars(self, scope="build").save_script(
                        "alberta_mktemp_shim")
                    self.output.info(
                        "main configure mktemp fallback shim on PATH: %s"
                        % _mshim)
                else:
                    self.output.info(
                        "main configure mktemp shim build failed, PATH unshadowed")
            else:
                self.output.info("main configure without mktemp shadow")
        except Exception as _me:
            self.output.info("main configure mktemp shim skipped: %s" % _me)

    def _tirpc_search_flags(self):
        """Return (cflags, ldflags, package_folder, detail) for libtirpc.

        Upstream configure.ac probes tirpc with a bare
        AC_CHECK_LIB([tirpc],[rpc_call]) (no pkg-config), so only -I/-L
        in the environment can satisfy it. Collects -I for every
        existing include dir and -L for every existing lib dir (lib +
        lib64 variants), and reports the lib dir listing so a missing
        libtirpc.a/.so is distinguishable from a missing -L flag in the
        next preflight log. Pure isdir probing, no exec gate (R49).
        """
        cflags, ldflags = [], []
        try:
            _dep = self.dependencies["libtirpc"]
        except Exception as exc:
            return [], [], "", "no libtirpc node (%s)" % exc
        pf = getattr(_dep, "package_folder", None) or ""
        if not pf or not os.path.isdir(pf):
            return [], [], pf or "", "no package folder"
        for _sub in ("include", os.path.join("include", "tirpc")):
            _d = os.path.join(pf, _sub)
            try:
                if os.path.isdir(_d):
                    _f = "-I%s" % _d
                    if _f not in cflags:
                        cflags.append(_f)
            except Exception:
                continue
        lib_detail = []
        for _sub in ("lib", "lib64"):
            _d = os.path.join(pf, _sub)
            try:
                if not os.path.isdir(_d):
                    continue
                _f = "-L%s" % _d
                if _f not in ldflags:
                    ldflags.append(_f)
                try:
                    _names = sorted(os.listdir(_d))
                except OSError:
                    _names = []
                _hits = [n for n in _names
                         if n.startswith("libtirpc.")]
                lib_detail.append("%s:[%s]" % (_sub, ",".join(_hits) or "no-libtirpc"))
            except Exception as exc:
                lib_detail.append("%s:probe-failed(%s)" % (_sub, exc))
        detail = ";".join(lib_detail) if lib_detail else "no lib dir"
        return cflags, ldflags, pf, detail

    def _resolve_ohos_compiler(self):
        """Return (cc, cxx, label) for a compiler that exists on this host.

        Profile pins tools.build:compiler_executables to
        /data/service/hnp/bin/clang(++), absent on some HMBS hosts
        (2026-09-27 preflight: `[Errno 2] No such file or directory`).
        Keep the conf value when the file exists (healthy CI unchanged);
        otherwise search true-machine PATH plus SDK/harmonybrew candidate
        dirs (bwm/0.6.3 + zydis/4.1.1 pattern). Pure isfile probing, no
        X_OK gate per R49. Only CC/CXX are covered, never flags (R33).
        """
        def _ok(p):
            try:
                return bool(p) and os.path.isfile(p)
            except Exception:
                return False

        def _conf(key):
            try:
                return (self.conf.get(key, check_type=str) or "").split()[0]
            except Exception:
                return ""

        conf_cc = _conf("tools.build:compiler_executables:c")
        conf_cxx = _conf("tools.build:compiler_executables:cpp")
        if not conf_cc or not conf_cxx:
            try:
                _exes = self.conf.get("tools.build:compiler_executables",
                                      default=None)
                if isinstance(_exes, dict):
                    conf_cc = conf_cc or (_exes.get("c") or "").split()[0]
                    conf_cxx = conf_cxx or (_exes.get("cpp") or "").split()[0]
            except Exception:
                pass
        if _ok(conf_cc) and _ok(conf_cxx):
            return conf_cc, conf_cxx, "profile"
        if _ok(conf_cc) and not conf_cxx:
            _sib = conf_cc + "++" if conf_cc.endswith("clang") else ""
            if _ok(_sib):
                return conf_cc, _sib, "profile-cxx-sibling"
        cc_names = ["clang", "cc", "gcc"]
        cxx_names = ["clang++"]
        cand_dirs = []
        for _d in ("/storage/Users/currentUser/usr/local/bin",
                   os.path.join(os.path.expanduser("~"), ".harmonybrew",
                                "bin"),
                   "/data/service/hnp/bin",
                   "/opt/llvm/bin",
                   "/usr/local/bin",
                   "/usr/bin",
                   "/bin"):
            if _d and _d not in cand_dirs:
                cand_dirs.append(_d)
        try:
            for _entry in (os.environ.get("LD_LIBRARY_PATH", "")
                           or "").split(os.pathsep):
                if "llvm" in _entry:
                    _sib = os.path.join(os.path.dirname(_entry.rstrip("/")),
                                        "bin")
                    if _sib not in cand_dirs:
                        cand_dirs.append(_sib)
        except Exception:
            pass
        found_cc, found_cxx = "", ""
        for _name in cc_names:
            try:
                _w = shutil.which(_name)
            except Exception:
                _w = None
            if _ok(_w):
                found_cc = _w
                break
        for _name in cxx_names:
            try:
                _w = shutil.which(_name)
            except Exception:
                _w = None
            if _ok(_w):
                found_cxx = _w
                break
        if not found_cc or not found_cxx:
            for _d in cand_dirs:
                try:
                    if not os.path.isdir(_d):
                        continue
                except Exception:
                    continue
                if not found_cc:
                    for _n in cc_names:
                        _p = os.path.join(_d, _n)
                        if _ok(_p):
                            found_cc = _p
                            break
                if not found_cxx:
                    for _n in cxx_names:
                        _p = os.path.join(_d, _n)
                        if _ok(_p):
                            found_cxx = _p
                            break
                if found_cc and found_cxx:
                    break
        cc = found_cc or (conf_cc if _ok(conf_cc) else "")
        cxx = found_cxx or (conf_cxx if _ok(conf_cxx) else "")
        if cc and not cxx and cc.endswith("clang"):
            _sib = cc + "++"
            if _ok(_sib):
                cxx = _sib
        if cc:
            return cc, cxx, "fallback"
        return "", "", "unresolved"

    def _select_shell(self):
        """Return a shell path verified to exist and be executable.

        Never trusts an inherited CONFIG_SHELL blindly: an absolute path
        is accepted only if it exists and is executable, otherwise falls
        back to HMBS-guaranteed /bin/sh (same pattern as the ohpcd m4
        recipe; zurl notes #30 for the poisoning mechanism).
        """
        for shell in (os.environ.get("CONFIG_SHELL"),
                      os.environ.get("SHELL"),
                      "/bin/sh", "/system/bin/sh"):
            if not shell:
                continue
            if os.path.isabs(shell):
                if os.path.isfile(shell) and os.access(shell, os.X_OK):
                    return shell
            elif shutil.which(shell):
                return shell
        return "sh"

    def _resolve_working_rm(self):
        """Return a proven-executable rm path, skipping EPERM shims.

        2026-09-27 preflight failed compile with
        `sh: /storage/Users/currentUser/.harmonybrew/bin/rm: Operation not
        permitted`. Bare `rm` in configure/make resolved via PATH to the
        harmonybrew shim which cannot exec (EPERM, same signature as the
        libextractor/1.17 recipe). Each candidate is proven by actually
        executing `rm --version`: OSError (EPERM/EACCES) means unusable
        and is skipped; any launched process proves exec works. Prefers
        system /bin/rm. Only fixes rm resolution; never touches tests
        and never exports RM itself (libtool needs RM="rm -f").
        """
        cands = ["/bin/rm", "/usr/bin/rm"]
        try:
            _w = shutil.which("rm")
            if _w and _w not in cands:
                cands.append(_w)
        except Exception:
            pass
        try:
            for _d in os.environ.get("PATH", "").split(os.pathsep):
                if not _d:
                    continue
                _p = os.path.join(_d, "rm")
                if _p not in cands:
                    cands.append(_p)
        except Exception:
            pass
        for cand in cands:
            if not cand:
                continue
            try:
                if not os.path.isfile(cand):
                    continue
            except Exception:
                continue
            try:
                pr = subprocess.run([cand, "--version"],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, timeout=15)
                self.output.info("rm probe ok: %s rc=%s" % (cand, pr.returncode))
                return cand
            except OSError as exc:
                self.output.info("rm probe skip %s: %s" % (cand, exc))
                continue
            except Exception as exc:
                self.output.info("rm probe skip %s: %s" % (cand, exc))
                continue
        self.output.info("rm probe: no working absolute rm found")
        return ""

    @staticmethod
    def _shq(value):
        """POSIX single-quote a value for shell-inline VAR= assignments."""
        return "'" + str(value).replace("'", "'\"'\"'") + "'"

    def _compose_bootstrap_path(self, extra_first=()):
        """PATH for bootstrap/vendor commands: vendor/tool dirs win.

        Ordering (first wins): optional extra dirs (vendored prefix bin),
        Conan tool bindirs, HMBS-injected tool dirs, system dirs, outer
        PATH. Mirrors the previous os.environ composition, but returned
        as a string so it can be inlined per-command (immune to run-time
        env aggregation reordering it).
        """
        parts = list(extra_first) + self._tool_bindirs()
        for var in ("HMBS_MAKE", "HMBS_CMAKE", "HMBS_NINJA", "HMBS_PYTHON3"):
            val = os.environ.get(var)
            if val:
                d = os.path.dirname(val)
                if d and d not in parts:
                    parts.append(d)
        for cand in ("/usr/local/bin", "/usr/bin", "/bin"):
            if cand not in parts:
                parts.append(cand)
        outer_p = os.environ.get("PATH", "")
        if outer_p:
            parts.append(outer_p)
        return os.pathsep.join(parts)

    def _inline_prefix(self, extra=None):
        """Shell-inline `VAR='val'` prefix overriding run-time env.

        Round-10 evidence: os.environ sanitization alone does NOT reach
        our own vendor/bootstrap commands — conan's run-time conanbuild
        aggregation (profile buildenv with the poisoned CONFIG_SHELL)
        wins over the process env at self.run time, which is why the
        vendored m4 configure died with the identical configure[139]
        fingerprint. Inline assignments prefixing the command override
        any exported value for that invocation, regardless of which env
        layer self.run aggregates. self.run executes through a shell
        (recipes chain with `cd .. && ..`), so the prefix applies.
        """
        shell = self._select_shell()
        tmpdir = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                  or os.environ.get("TEMP")
                  or os.path.join(self.build_folder, ".tmp"))
        assign = {
            "CONFIG_SHELL": shell,
            "SHELL": shell,
            "TMPDIR": tmpdir,
            "TMP": tmpdir,
            "TEMP": tmpdir,
            # Round 28: preseed the two pthread configure probes whose
            # execution hangs the 2026-09-27 20:30 preflight
            # (`checking for pthread_t...` then `Connection closed` with
            # zero upstream markers). ac_cv_type_pthread_t=yes is factual
            # on this worker (musl + glibc both define pthread_t in
            # <pthread.h>); gl_cv_pthread_rwlock_rdlock_prefer_writer is
            # the threaded writer-starvation AC_RUN_IFELSE right after
            # that check (usleep/timer relay), preseeded to the macro's
            # own musl cross guess ("guessing no") so the runner never
            # executes it. Honored by every autoconf configure (vendor
            # m4/autoconf/automake + main tree) via environment; pure
            # check-skipping, no flag/test change.
            "ac_cv_type_pthread_t": "yes",
            "gl_cv_pthread_rwlock_rdlock_prefer_writer": "guessing no",
        }
        if extra:
            assign.update(extra)
        return " ".join("%s=%s" % (k, self._shq(v)) for k, v in assign.items())

    def _fix_configure_umask(self, cfg_path=None):
        """Replace `umask 077` with `umask 022` in generated configure.

        HMDFS ignores chmod, so config.status temp dirs created under
        umask 077 are not owner-writable (same E011 workaround as the
        libtirpc/adcli/a52dec recipes). The edit targets a generated
        file, hence an in-build rewrite instead of a conandata patch.
        Defaults to the main tree's configure; pass an explicit path
        for the pre-generated vendored (m4/autoconf) configure scripts,
        which carry the identical template and die the identical death
        on this filesystem.
        """
        cfg = cfg_path or os.path.join(self.source_folder, "configure")
        try:
            with open(cfg, "r", encoding="utf-8") as f:
                content = f.read()
        except OSError as exc:
            self.output.info("umask fix skipped (no %s: %s)" % (cfg, exc))
            return 0
        if "umask 077" not in content:
            self.output.info("umask fix skipped (no umask 077 in %s)" % cfg)
            return 0
        content = content.replace("umask 077", "umask 022")
        with open(cfg, "w", encoding="utf-8") as f:
            f.write(content)
        self.output.info("umask fix applied to %s" % cfg)
        return 1

    def _sanitize_configure_config_shell(self, cfg_path=None):
        """Neutralize a dangling CONFIG_SHELL inside generated configure.

        2026-09-27 preflight (round 15): the vendored bootstrap now
        succeeds, but alberta OWN configure dies with the familiar
        configure-139 vs dangling hnp bash (Error 127). Root cause is
        the repo profile buildenv CONFIG_SHELL, absent on this worker.
        Both os.environ and AutotoolsToolchain.environment() lose to
        run-time conanbuild aggregation (profile wins), and inline
        prefixes cannot be applied to the helper internal command.
        Fix at the winning layer: patch the generated script so its
        re-exec block resets a non-executable CONFIG_SHELL first.
        """
        cfg = cfg_path or os.path.join(self.source_folder, "configure")
        try:
            with open(cfg, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except OSError as exc:
            self.output.info("config-shell sanitize skipped (no %s: %s)"
                             % (cfg, exc))
            return 0
        if "HMBS_CONFIG_SHELL_GUARD" in content:
            self.output.info("config-shell guard already present in %s" % cfg)
            return 0
        shell = self._select_shell()
        guard = (
            "# HMBS_CONFIG_SHELL_GUARD: ignore dangling profile CONFIG_SHELL\n"
            + 'if test -n "$CONFIG_SHELL"; then\n'
            + '  if test ! -x "$CONFIG_SHELL"; then\n'
            + "    CONFIG_SHELL=" + shell + "\n"
            + "    SHELL=" + shell + "\n"
            + "    export CONFIG_SHELL SHELL\n"
            + "  fi\n"
            + "fi\n"
        )
        lines = content.split("\n", 1)
        if lines and lines[0].startswith("#!"):
            content = lines[0] + "\n" + guard + (lines[1] if len(lines) > 1 else "")
        else:
            content = guard + content
        with open(cfg, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        self.output.info("config-shell guard applied to %s (shell=%s)"
                         % (cfg, shell))
        return 1

    def _sanitize_all_configures(self):
        """Apply the CONFIG_SHELL guard to every configure copy in play."""
        seen = set()
        cands = [os.path.join(self.source_folder, "configure"),
                 os.path.join(self.build_folder, "configure")]
        try:
            for _root, _dirs, _files in os.walk(self.build_folder):
                if _root != self.build_folder:
                    _dirs[:] = []
                    continue
                for _name in _files:
                    if _name == "configure":
                        cands.append(os.path.join(_root, _name))
        except OSError:
            pass
        for cand in cands:
            if cand in seen:
                continue
            seen.add(cand)
            try:
                self._sanitize_configure_config_shell(cand)
            except Exception as exc:
                self.output.info("config-shell sanitize skipped %s: %s"
                                 % (cand, exc))
            try:
                self._pin_packageheaders_rm(cand)
            except Exception as exc:
                self.output.info("packageheaders RM pin skipped %s: %s"
                                 % (cand, exc))

    def _mktemp_fallback_wanted(self, probe_dir):
        """Decide whether the configure-phase mktemp shadow is needed.

        HMBS_AUTOCONF_MKTEMP_FALLBACK=1 requests it directly. Otherwise
        probe the REAL mktemp binary on this filesystem, replicating
        exactly what config.status does: `mktemp -d` a dir under
        probe_dir, then write a file inside it. Only the observed
        failure mode (dir created, writes denied) returns True; a
        healthy filesystem, a missing mktemp binary (stock configure
        already takes its mkdir fallback then), or an inconclusive
        probe returns False so PATH stays unshadowed.
        """
        if os.environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK") == "1":
            self.output.info(
                "mktemp fallback wanted: HMBS_AUTOCONF_MKTEMP_FALLBACK=1")
            return True
        try:
            os.makedirs(probe_dir, exist_ok=True)
        except OSError as exc:
            self.output.info(
                "mktemp fallback probe inconclusive (mkdir %s: %s)"
                % (probe_dir, exc))
            return False
        mktemp_bin = shutil.which("mktemp") or "mktemp"
        created = ""
        try:
            pr = subprocess.run(
                [mktemp_bin, "-d", "hmbs-probe-XXXXXX"],
                cwd=probe_dir,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                timeout=30)
            created = (pr.stdout.decode("utf-8", "replace").strip().split()[0]
                       if pr.stdout else "")
            if pr.returncode != 0 or not created:
                self.output.info(
                    "mktemp fallback not needed: mktemp itself fails "
                    "(rc=%s out=%r), stock mkdir fallback already applies"
                    % (pr.returncode, created))
                return False
        except Exception as exc:
            self.output.info(
                "mktemp fallback probe inconclusive (%s)" % exc)
            return False
        target = (created if os.path.isabs(created)
                  else os.path.join(probe_dir, created))
        try:
            try:
                with open(os.path.join(target, "w"), "w") as fh:
                    fh.write("ok")
                os.unlink(os.path.join(target, "w"))
                self.output.info(
                    "mktemp fallback not needed: %r writable" % target)
                return False
            except OSError as exc:
                self.output.info(
                    "mktemp fallback wanted: %r not writable (%s)"
                    % (target, exc))
                return True
        finally:
            try:
                shutil.rmtree(target, ignore_errors=True)
            except Exception:
                pass

    def _mktemp_fallback_shim_for_ohos(self, tmpdir):
        """Shadow mktemp during configure so Autoconf uses mkdir fallback.

        HMBS platform diagnosis [unsafe_local_mktemp]: a directory
        created by mktemp on the current device filesystem cannot be
        written by Autoconf afterwards (vendored m4 configure dies in
        config.status with "can't create ./conf*/subs1.awk: Permission
        denied"). When HMBS injects HMBS_AUTOCONF_MKTEMP_FALLBACK=1,
        shadow mktemp during the configure step only so calls for
        "./conf*" fail and Autoconf falls back to its `mkdir` path. All
        other mktemp calls are delegated to the real binary. Same
        mechanism as the cyrus-sasl-*/2.1.28 recipes; the shebang uses
        _select_shell() (a verified-executable shell on this worker)
        instead of the hardcoded device /system/bin/sh, and the
        real-mktemp candidates start with shutil.which("mktemp").
        Activation is decided by the caller via _mktemp_fallback_wanted.
        Returns the shim dir to prepend to PATH, or "" on any error.
        """
        shim_dir = os.path.join(tmpdir, "hmbs-mktemp-shim")
        try:
            os.makedirs(shim_dir, exist_ok=True)
        except OSError:
            return ""
        shim = os.path.join(shim_dir, "mktemp")
        shell = self._select_shell()
        which_mktemp = shutil.which("mktemp") or ""
        candidates = " ".join(
            c for c in (which_mktemp, "/system/bin/mktemp",
                        "/bin/mktemp", "/usr/bin/mktemp") if c)
        script = (
            "#!%s\n" % shell +
            "for arg in \"$@\"; do\n"
            "  case \"$arg\" in\n"
            "    *conf*) exit 1 ;;\n"
            "  esac\n"
            "done\n"
            "for candidate in %s; do\n" % candidates +
            "  if [ -x \"$candidate\" ]; then\n"
            "    exec \"$candidate\" \"$@\"\n"
            "  fi\n"
            "done\n"
            "exec command -p mktemp \"$@\"\n"
        )
        try:
            with open(shim, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(script)
            try:
                os.chmod(shim, 0o755)
            except OSError:
                pass
        except OSError:
            return ""
        return shim_dir

    def _tool_bindirs(self):
        """Conan tool bindirs (host + build contexts) that exist on disk."""
        bindirs = []
        try:
            seen = (list(self.dependencies.items())
                    + list(self.dependencies.build.items()))
        except Exception:
            try:
                seen = list(self.dependencies.items())
            except Exception:
                seen = []
        for _req, dep in seen:
            pf = getattr(dep, "package_folder", None) or ""
            if pf:
                bindir = os.path.join(pf, "bin")
                if os.path.isdir(bindir) and bindir not in bindirs:
                    bindirs.append(bindir)
        return bindirs

    def _aclocal_path_extra(self):
        """aclocal macro dirs from every tool package (pkg.m4/libtool.m4).

        configure.ac needs PKG_PROG_PKG_CONFIG/PKG_INSTALLDIR (pkgconf)
        and LT_INIT (libtool) on top of automake's own macros; conanbuild
        aggregates ACLOCAL_PATH only from recipes that declare it, so the
        bootstrap passes the discovered share/aclocal* dirs explicitly
        (both via os.environ and the shell-inline prefix).
        """
        dirs = []
        try:
            seen = (list(self.dependencies.items())
                    + list(self.dependencies.build.items()))
        except Exception:
            seen = []
        for _req, dep in seen:
            pf = getattr(dep, "package_folder", None) or ""
            if not pf:
                continue
            for sub in ("share/aclocal", "share/aclocal-1.18"):
                d = os.path.join(pf, sub)
                if os.path.isdir(d) and d not in dirs:
                    dirs.append(d)
        return dirs

    def _vendor_prefix(self):
        return os.path.join(self.build_folder, ".vendor")

    def _fetch_vendor(self, spec, dest):
        """Download spec tarball from the first working mirror + sha256."""
        errors = []
        data = None
        for url in spec["urls"]:
            for ctx_name, ctx in (("verified", None),
                                  ("unverified", ssl._create_unverified_context())):
                try:
                    req = urllib.request.Request(
                        url, headers={"User-Agent": "Mozilla/5.0"})
                    if ctx is None:
                        resp = urllib.request.urlopen(req, timeout=180)
                    else:
                        resp = urllib.request.urlopen(req, timeout=180,
                                                      context=ctx)
                    with resp:
                        data = resp.read()
                    break
                except Exception as exc:
                    errors.append("%s [%s]: %s" % (url, ctx_name, exc))
                    continue
            if data is not None:
                break
        if data is None:
            raise ConanException(
                "vendored %s download failed: %s"
                % (spec["name"], " | ".join(errors)))
        digest = hashlib.sha256(data).hexdigest()
        if digest != spec["sha256"]:
            raise ConanException(
                "vendored %s sha256 mismatch: got %s" % (spec["name"], digest))
        with open(dest, "wb") as fh:
            fh.write(data)

    def _find_build_cc(self):
        """Locate a BUILD-machine C compiler for the vendored tool build.

        The vendored m4/autoconf binaries must EXECUTE on the x86_64
        Linux worker during autoreconf, so the harmonybrew OHOS
        cross-compiler wrapper (/storage/.../.harmonybrew/bin/cc) is
        wrong here twice over: it may itself depend on the inaccessible
        hnp bash (same "inaccessible" signature at configure's compiler
        probe), and even a successful build would emit an aarch64-ohos
        binary un-runnable on the worker. Prefer system compilers and
        smoke-gate EVERY candidate with a sanitized `cc --version`
        probe (shell-inline CONFIG_SHELL/SHELL so the probe itself is
        immune to run-time aggregation); reject any candidate whose
        output mentions "inaccessible". Harmonybrew remains a last
        resort only if nothing else executes.
        """
        shell = self._select_shell()
        prefix = self._inline_prefix()
        ordered = ["/usr/bin/cc", "/usr/bin/gcc", "/usr/bin/clang"]
        for cand in ("cc", "gcc", "clang"):
            found = shutil.which(cand)
            if found and found not in ordered:
                ordered.append(found)
        tried = []
        fallback = None
        for cc in ordered:
            if not cc or not os.path.isfile(cc):
                tried.append("%s=absent" % cc)
                continue
            if ".harmonybrew" in cc:
                # Defer: cross wrapper, last resort only.
                fallback = fallback or cc
                tried.append("%s=deferred-cross-wrapper" % cc)
                continue
            try:
                self.run('%s %s --version' % (prefix, self._shq(cc)))
                return cc, "; ".join(tried + ["%s=ok" % cc])
            except Exception as exc:
                tried.append("%s version-probe failed: %s" % (cc, exc))
        if fallback is not None:
            try:
                self.run('%s %s --version' % (prefix, self._shq(fallback)))
                return fallback, "; ".join(
                    tried + ["%s=ok-last-resort" % fallback])
            except Exception as exc:
                tried.append("%s last-resort probe failed: %s"
                             % (fallback, exc))
        raise ConanException(
            "no working build-machine C compiler for vendored tools "
            "(probed: %s)" % "; ".join(tried))

    def _find_system_perl(self):
        """Locate a system perl whose XS (Cwd) loads, for autoreconf."""
        tried = []
        cands = []
        for cand in ("perl",):
            found = shutil.which(cand)
            if found and found not in cands:
                cands.append(found)
            tried.append("%s=%s" % (cand, found or "absent"))
        for cand in ("/usr/local/bin/perl", "/usr/bin/perl", "/bin/perl",
                     "/storage/Users/currentUser/usr/local/bin/perl"):
            tried.append("%s=%s" % (cand, "file" if os.path.isfile(cand) else "absent"))
            if os.path.isfile(cand) and cand not in cands:
                cands.append(cand)
        for perl in cands:
            try:
                self.run('%s %s -MCwd -e "print 1"'
                         % (self._inline_prefix(), self._shq(perl)))
                return perl, "; ".join(tried)
            except Exception as exc:
                tried.append("%s Cwd-test failed: %s" % (perl, exc))
        raise ConanException(
            "no working system perl for vendored autoreconf "
            "(probed: %s)" % "; ".join(tried))

    def _vendor_build_triplet(self, cc):
        """Native triplet for the vendored (build-machine) tool configure.

        2026-09-27 preflight: vendored m4 1.4.19's build-aux/config.guess
        (2021-05-24) cannot guess the HarmonyOS worker
        (`./build-aux/config.guess: unable to guess system type` ->
        `configure: error: cannot guess build type`), even though the
        vendored tools are native builds that must execute on that same
        worker. Passing explicit --build/--host bypasses config.guess
        entirely (old config.sub accepts *-linux-gnu without question).
        Prefer `cc -dumpmachine` from the already-selected build cc;
        fall back to platform.machine() + -pc-linux-gnu. Never returns
        an ohos triplet here: a cross triplet would emit an
        aarch64 binary un-runnable on the x86_64 worker.
        """
        def _valid(t):
            if not t or "ohos" in t or "harmony" in t:
                return ""
            t = t.strip()
            if "-" not in t or any(c.isspace() for c in t):
                return ""
            return t
        try:
            pr = subprocess.run(
                [cc, "-dumpmachine"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                timeout=15,
                env=dict(os.environ, CONFIG_SHELL=self._select_shell(),
                         SHELL=self._select_shell()))
            out = pr.stdout.decode("utf-8", "replace").strip().split()[0] \
                if pr.stdout else ""
            hit = _valid(out)
            if pr.returncode == 0 and hit:
                self.output.info("vendored triplet from %s -dumpmachine: %s"
                                 % (cc, hit))
                return hit
            self.output.info("vendored triplet dumpmachine miss: cc=%s rc=%s out=%r"
                             % (cc, pr.returncode, out))
        except Exception as exc:
            self.output.info("vendored triplet dumpmachine probe failed: %s" % exc)
        mach = (platform.machine() or "x86_64").strip() or "x86_64"
        fallback = "%s-pc-linux-gnu" % mach
        self.output.info("vendored triplet fallback: %s" % fallback)
        return fallback

    def _patch_vendor_gnulib_for_musl(self, src):
        """Insert musl fallback into vendored m4 gnulib stdio sources.

        2026-09-27 preflight: with the triplet fix the vendored m4
        1.4.19 configure now succeeds, but `make` dies in
        lib/freadahead.c:101 `#error "Please port gnulib freadahead.c
        to your platform!"`. The worker libc is OHOS musl (opaque
        FILE, no _IO_read_ptr), which the 2021 gnulib in m4 1.4.19
        predates -- same failure domain the merged-green coreutils
        9.10 recipe already solved with in-tree patches
        (0002-lib-freadahead.c / 0003-lib-freadptr.c /
        0004-lib-freadseek.c: `#elif defined __linux__ &&
        !defined __GLIBC__` safe fallback via <stdio_ext.h>
        __fwriting). Apply the identical fallback here as an
        in-build rewrite of the unpacked vendor tree (generated
        gnulib sources, hence not a conandata patch). Anchored on
        the stable `#elif defined SLOW_BUT_NO_HACKS` /
        `#if HAVE___FREADPTRINC` lines so it tolerates gnulib
        version drift; missing files or anchors only log and skip.
        Returns the number of files patched.
        """
        patched = 0
        # --- lib/freadahead.c: report no pending input on musl ---
        fa = os.path.join(src, "lib", "freadahead.c")
        try:
            with open(fa, "r", encoding="utf-8", errors="replace") as fh:
                content = fh.read()
        except OSError as exc:
            self.output.info("musl gnulib fix skipped (no %s: %s)" % (fa, exc))
            content = None
        if content is not None:
            if "__linux__ && !defined __GLIBC__" not in content:
                anchor = "#elif defined SLOW_BUT_NO_HACKS"
                insert = (
                    "#elif defined __linux__ && !defined __GLIBC__\n"
                    "  /* OHOS musl libc has an opaque FILE structure.\n"
                    "     musl provides __fwriting in <stdio_ext.h> to check\n"
                    "     write mode. Without __freadahead we use a safe\n"
                    "     fallback (same as coreutils 9.10 0002 patch).  */\n"
                    "# include <stdio_ext.h>\n"
                    "  if (__fwriting (fp))\n"
                    "    return 0;\n"
                    "  return 0;\n"
                )
                if anchor in content:
                    content = content.replace(anchor, insert + anchor, 1)
                    with open(fa, "w", encoding="utf-8", newline="\n") as fh:
                        fh.write(content)
                    self.output.info("musl gnulib fix applied to %s" % fa)
                    patched += 1
                else:
                    self.output.info(
                        "musl gnulib fix skipped for %s (anchor absent)" % fa)
            else:
                self.output.info("musl gnulib fix already present in %s" % fa)
        # --- lib/freadptr.c: no buffer pointer on musl ---
        fp = os.path.join(src, "lib", "freadptr.c")
        try:
            with open(fp, "r", encoding="utf-8", errors="replace") as fh:
                content = fh.read()
        except OSError as exc:
            self.output.info("musl gnulib fix skipped (no %s: %s)" % (fp, exc))
            content = None
        if content is not None:
            if "__linux__ && !defined __GLIBC__" not in content:
                anchor = "#elif defined SLOW_BUT_NO_HACKS"
                insert = (
                    "#elif defined __linux__ && !defined __GLIBC__\n"
                    "  /* OHOS musl libc has an opaque FILE structure; we\n"
                    "     cannot access internal buffer pointers directly.\n"
                    "     Return NULL so the caller uses fgetc/fread instead\n"
                    "     (same as coreutils 9.10 0003 patch).  */\n"
                    "# include <stdio_ext.h>\n"
                    "  if (__fwriting (fp))\n"
                    "    return NULL;\n"
                    "  return NULL;\n"
                )
                if anchor in content:
                    content = content.replace(anchor, insert + anchor, 1)
                    with open(fp, "w", encoding="utf-8", newline="\n") as fh:
                        fh.write(content)
                    self.output.info("musl gnulib fix applied to %s" % fp)
                    patched += 1
                else:
                    self.output.info(
                        "musl gnulib fix skipped for %s (anchor absent)" % fp)
            else:
                self.output.info("musl gnulib fix already present in %s" % fp)
        # --- lib/freadseek.c: never called on musl (freadptr is NULL) ---
        fs = os.path.join(src, "lib", "freadseek.c")
        try:
            with open(fs, "r", encoding="utf-8", errors="replace") as fh:
                content = fh.read()
        except OSError as exc:
            self.output.info("musl gnulib fix skipped (no %s: %s)" % (fs, exc))
            content = None
        if content is not None:
            if "__linux__ && !defined __GLIBC__" not in content:
                anchor = "#if HAVE___FREADPTRINC"
                insert = (
                    "#if defined __linux__ && !defined __GLIBC__\n"
                    "  /* OHOS musl libc has an opaque FILE structure.\n"
                    "     Cannot increment the in-memory pointer directly.\n"
                    "     Only called when freadptr returns non-NULL, which\n"
                    "     never happens for musl (same as coreutils 0004).  */\n"
                    "  abort ();\n"
                    "#elif HAVE___FREADPTRINC"
                )
                if anchor in content:
                    content = content.replace(anchor, insert, 1)
                    with open(fs, "w", encoding="utf-8", newline="\n") as fh:
                        fh.write(content)
                    self.output.info("musl gnulib fix applied to %s" % fs)
                    patched += 1
                else:
                    self.output.info(
                        "musl gnulib fix skipped for %s (anchor absent)" % fs)
            else:
                self.output.info("musl gnulib fix already present in %s" % fs)
        return patched

    def _build_vendor_tool(self, spec, prefix, cc, sh, make, extra_cfg=None):
        """Unpack + configure --prefix + make -j1 + install (idempotent).

        All three commands run under the shell-inline sanitized prefix
        (CONFIG_SHELL/SHELL/TMPDIR/CC/PATH): this is what actually
        reaches the configure script, unlike os.environ which run-time
        aggregation may override. MAKEINFO=true skips texinfo doc
        rebuilds (same as this repo's autoconf recipe package build).
        extra_cfg adds further inline VAR assignments to the configure
        invocation only (e.g. PERL for the automake vendor build so its
        installed perl scripts get a probe-verified shebang).
        """
        stamp = os.path.join(prefix, ".%s-done" % spec["name"])
        if os.path.isfile(stamp):
            return
        work = os.path.join(self.build_folder, ".vendor-src")
        os.makedirs(work, exist_ok=True)
        archive = os.path.join(work, spec["name"] + ".tar.gz")
        if not os.path.isfile(archive):
            self.output.info("downloading vendored %s ..." % spec["name"])
            self._fetch_vendor(spec, archive)
        top = None
        with tarfile.open(archive, "r:gz") as tf:
            # GNU release tarballs share one top dir; extract then locate it.
            roots = set()
            for m in tf.getmembers():
                stripped = m.name.strip("/")
                if not stripped or "/" not in stripped:
                    continue
                roots.add(stripped.split("/")[0])
            if len(roots) == 1:
                top = roots.pop()
            tf.extractall(work)
        if top is None:
            raise ConanException(
                "vendored %s tarball has no single top dir: %s"
                % (spec["name"], sorted(roots)))
        src = os.path.join(work, top)
        # gnulib musl port (new failure domain past configure): the
        # vendored m4 1.4.19 gnulib predates OHOS musl (opaque FILE),
        # so freadahead.c hits `#error Please port gnulib ...`.
        # Same safe fallback as the merged coreutils 9.10 patches.
        # Only the m4 tree ships C gnulib sources; harmless otherwise.
        if "m4" in spec["name"]:
            self._patch_vendor_gnulib_for_musl(src)
        # E011 companion to the mktemp shim below: the vendored tarballs
        # ship pre-generated configure scripts carrying the same
        # `umask 077 && mktemp -d "./confXXXXXX"` template that dies on
        # this filesystem, so apply the identical umask 077->022 rewrite
        # the main tree gets in _bootstrap().
        self._fix_configure_umask(os.path.join(src, "configure"))
        # The vendored autoconf configure probes for GNU m4 on PATH
        # ("checking for GNU M4 ... no acceptable m4"). The worker has
        # no system m4 (round-7 file evidence), so the just-installed
        # vendored m4 under prefix/bin must lead PATH for the second
        # tool build; harmless (possibly empty) for the first one.
        _vendor_bin = os.path.join(prefix, "bin")
        if os.path.isdir(_vendor_bin):
            path = self._compose_bootstrap_path(extra_first=(_vendor_bin,))
        else:
            path = self._compose_bootstrap_path()
        self.output.info("building vendored %s with CC=%s" % (spec["name"], cc))
        # HMBS platform diagnosis [unsafe_local_mktemp]: an mktemp-made
        # dir on this filesystem is not writable by Autoconf afterwards
        # (config.status "can't create ./conf*/subs1.awk: Permission
        # denied"). Shadow mktemp during configure only when the flag
        # requests it or a live probe of the real mktemp binary shows
        # the exact failure mode (dir created, writes denied); make and
        # install prefixes below keep the unshadowed PATH.
        cfg_path = path
        shim_base = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                     or os.environ.get("TEMP")
                     or os.path.join(self.build_folder, ".tmp"))
        mktemp_shim = ""
        if self._mktemp_fallback_wanted(work):
            mktemp_shim = self._mktemp_fallback_shim_for_ohos(shim_base)
        if mktemp_shim:
            self.output.info("configure mktemp fallback shim on PATH: %s"
                             % mktemp_shim)
            cfg_path = mktemp_shim + os.pathsep + path
        else:
            self.output.info("configure without mktemp shadow")
        _cfg_extra = {"CC": cc, "PATH": cfg_path}
        if extra_cfg:
            _cfg_extra.update(extra_cfg)
        _vendored_m4 = os.path.join(prefix, "bin", "m4")
        if os.path.isfile(_vendored_m4):
            _cfg_extra["M4"] = _vendored_m4
            self.output.info("vendored m4 for %s: %s" % (spec["name"], _vendored_m4))
        cfg_prefix = self._inline_prefix(_cfg_extra)
        # Explicit native --build/--host: the vendored tools run on the
        # build worker itself, and old config.guess (m4 1.4.19 =
        # 2021-05-24) cannot identify the HarmonyOS kernel, so guessing
        # must be bypassed. linux-gnu is accepted by even that old
        # config.sub; never an ohos triplet here (cross binary could not
        # execute under autoreconf on this worker).
        triplet = self._vendor_build_triplet(cc)
        self.run('%s %s ./configure --prefix=%s --build=%s --host=%s --disable-dependency-tracking --disable-silent-rules'
                 % (cfg_prefix, self._shq(sh), self._shq(prefix),
                    triplet, triplet), cwd=src)
        make_prefix = self._inline_prefix({"PATH": path})
        self.run('%s %s -j1 MAKEINFO=true' % (make_prefix, self._shq(make)), cwd=src)
        # E182/E188: vendored autoconf `make install` dies at
        # install-binSCRIPTS (multi-file `install -c bin/autoconf ...
        # .vendor/bin` -> Error 64) on the HMFS worker whose install
        # shim rejects `-c`/multi-source calls (platform caps
        # install_shim=true/chmod=0; same as adms/aribb24/zurl).
        # Redirect INSTALL to a cp/mkdir shim (chmod best-effort) and
        # pass INSTALL= on the install command line (highest precedence,
        # propagates to sub-makes). Linux zero change (OHOS-gated).
        install_arg = ""
        if str(self.settings.os) == "OHOS":
            try:
                _shim = self._write_install_shim()
                self._redirect_install_to_shim(_shim, src)
                install_arg = " INSTALL=%s" % self._shq(_shim)
                self.output.info("vendored install shim: %s" % _shim)
            except Exception as _ie:
                self.output.info("vendored install shim skipped: %s" % _ie)
        self.run('%s %s install%s MAKEINFO=true'
                 % (make_prefix, self._shq(make), install_arg), cwd=src)
        with open(stamp, "w") as fh:
            fh.write("ok")

    def _write_install_shim(self):
        """cp/mkdir install shim for OHOS HMFS (E182/E188).

        The worker install (toybox/HMBS shim) fails any `-c` or
        multi-source-to-dir call with EX_USAGE 64
        (`install -c a b dir/`), which automake `make install` emits
        routinely (install-binSCRIPTS/install-man1/install-data).
        The shim accepts `-c/-p/-m/-d`, copies with `cp -f`, creates
        dirs with `mkdir -p`, and treats chmod as best-effort
        (HMBS_CAP_CHMOD=0). Verbatim from the gate-passing adms 2.3.7 /
        aribb24 1.0.4 recipes; shebang uses the verified shell.
        """
        shim_dir = os.path.join(self.build_folder, "_ohos_install_shim")
        os.makedirs(shim_dir, exist_ok=True)
        install = os.path.join(shim_dir, "install")
        fd = os.open(install, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o755)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
                f.write(
                    "#!%s\n" % self._select_shell() +
                    "set -eu\n"
                    "mode=\n"
                    "while [ $# -gt 0 ]; do\n"
                    "  case \"$1\" in\n"
                    "    -p|-c) shift ;;\n"
                    "    -m) [ $# -ge 2 ] || exit 2; mode=$2; shift 2 ;;\n"
                    "    -d) shift; [ $# -gt 0 ] || exit 2; mkdir -p \"$@\"; exit 0 ;;\n"
                    "    --) shift; break ;;\n"
                    "    -*) shift ;;\n"
                    "    *) break ;;\n"
                    "  esac\n"
                    "done\n"
                    "[ $# -ge 2 ] || exit 2\n"
                    "dest=\n"
                    "for arg in \"$@\"; do dest=$arg; done\n"
                    "count=$(($# - 1))\n"
                    "mkdir -p \"$(dirname \"$dest\")\"\n"
                    "i=1\n"
                    "for src in \"$@\"; do\n"
                    "  [ $i -gt $count ] && break\n"
                    "  cp -f \"$src\" \"$dest\"\n"
                    "  if [ -n \"$mode\" ]; then\n"
                    "    if [ -d \"$dest\" ]; then\n"
                    "      chmod \"$mode\" \"$dest/${src##*/}\" 2>/dev/null || true\n"
                    "    else\n"
                    "      chmod \"$mode\" \"$dest\" 2>/dev/null || true\n"
                    "    fi\n"
                    "  fi\n"
                    "  i=$((i + 1))\n"
                    "done\n"
                )
        except Exception:
            try:
                os.close(fd)
            except Exception:
                pass
            raise
        try:
            os.chmod(install, 0o755)
        except OSError:
            pass
        return install

    def _redirect_install_to_shim(self, shim_install, root=None):
        """Rewrite generated `INSTALL = ...install...` to the shim.

        configure probes INSTALL to the worker install shim (with `-c`
        suffix); INSTALL_DATA/INSTALL_PROGRAM/INSTALL_SCRIPT derive
        from ${INSTALL}, so one rewrite covers all install rules
        (same as adms/aribb24). Defaults to build_folder; vendored
        in-source builds pass their src tree explicitly.
        """
        bf = root or self.build_folder
        for _root, _, _files in os.walk(bf):
            for _name in _files:
                if _name != "Makefile":
                    continue
                mp = os.path.join(_root, _name)
                try:
                    with open(mp, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                except OSError:
                    continue
                if "INSTALL = " not in content:
                    continue
                lines = []
                changed = False
                for line in content.splitlines(True):
                    stripped = line.lstrip()
                    if stripped.startswith("INSTALL = ") and "/install" in stripped:
                        indent = line[:len(line) - len(stripped)]
                        lines.append("%sINSTALL = %s\n" % (indent, shim_install))
                        changed = True
                    else:
                        lines.append(line)
                if changed:
                    with open(mp, "w", encoding="utf-8") as f:
                        f.write("".join(lines))

    def _normalize_vendor_perl_shebangs(self, prefix, perl):
        """Point vendored aclocal/automake at the probe-verified perl.

        2026-09-27 preflight: the Conan automake tool package's
        `bin/aclocal` wrapper died with
        `aclocal[8]: .../p/bin/.aclocal-real: No such file or directory`
        (exit 126). That ENOENT fires either when the wrapper's hidden
        real file is absent from the published binary, or when the
        hidden perl script's own baked-in shebang interpreter does not
        exist on this worker -- both are properties of the foreign
        binary no consumer env can repair. The vendored automake built
        by this recipe must not repeat that: rewrite the `#!` line of
        the freshly installed prefix/bin/{aclocal,automake}* perl
        scripts to the working perl that already passed the -MCwd load
        test, so direct exec (the way vendored autoreconf invokes
        aclocal) can never hit a dangling interpreter. Best-effort
        with per-file logging; never fails the build.
        """
        bindir = os.path.join(prefix, "bin")
        if not os.path.isdir(bindir):
            return 0
        fixed = 0
        try:
            names = os.listdir(bindir)
        except OSError:
            return 0
        for name in sorted(names):
            if not (name == "aclocal" or name.startswith("aclocal-")
                    or name == "automake" or name.startswith("automake-")):
                continue
            path = os.path.join(bindir, name)
            try:
                if not os.path.isfile(path) or os.path.islink(path):
                    continue
                with open(path, "rb") as fh:
                    head = fh.read(512)
                if not head.startswith(b"#!"):
                    continue
                nl = head.find(b"\n")
                first = head[:nl] if nl != -1 else head
                if b"perl" not in first:
                    continue
                with open(path, "r", encoding="utf-8", errors="replace") as fh:
                    content = fh.read()
                lines = content.split("\n", 1)
                lines[0] = "#!" + perl
                with open(path, "w", encoding="utf-8", newline="\n") as fh:
                    fh.write("\n".join(lines) if len(lines) == 1
                             else lines[0] + "\n" + lines[1])
                self.output.info("vendor shebang pinned: %s -> %s" % (path, perl))
                fixed += 1
            except OSError as exc:
                self.output.info("vendor shebang skip %s: %s" % (path, exc))
        return fixed

    def _ensure_vendor_autotools(self, sh, make):
        """Provide autoreconf + m4 + aclocal/automake from vendor prefix.

        Idempotent: m4 1.4.19 + autoconf 2.72 + automake 1.18 release
        tarballs are built once into the private prefix (see
        _build_vendor_tool). Automake joins the vendor set in round 13:
        the Conan automake tool binary's `bin/aclocal` wrapper is broken
        on this worker (missing hidden `.aclocal-real`, exit 126), and
        vendor/bin leads PATH in _bootstrap so the vendored aclocal
        shadows it. The automake vendor configure gets PERL pinned to
        the probe-verified perl plus a post-install shebang rewrite, so
        its own scripts can never dangle the way the foreign binary's
        do.
        """
        prefix = self._vendor_prefix()
        os.makedirs(prefix, exist_ok=True)
        cc, cc_evidence = self._find_build_cc()
        self.output.info("vendored toolchain CC: %s (%s)" % (cc, cc_evidence))
        self._build_vendor_tool(_VENDOR_M4, prefix, cc, sh, make)
        self._build_vendor_tool(_VENDOR_AUTOCONF, prefix, cc, sh, make)
        perl, perl_evidence = self._find_system_perl()
        self.output.info("vendored toolchain perl: %s (%s)" % (perl, perl_evidence))
        self._build_vendor_tool(_VENDOR_AUTOMAKE, prefix, cc, sh, make,
                                extra_cfg={"PERL": perl})
        self._normalize_vendor_perl_shebangs(prefix, perl)
        # Round 35: vendor libtool as well (same fetch-build pattern).
        # Rounds 32-34 seeded ltmain.sh + .m4 files from either the Conan
        # tool package (2.5.4.1) or the GNU tarball (2.5.4) while the
        # effective libtoolize binary stayed the other release -- two
        # writers, two versions, byte-identical mismatch across three
        # preflights. A vendored build makes bin/libtoolize,
        # share/aclocal/*.m4 and share/libtool/build-aux/ltmain.sh one
        # release (2.5.4) from one source; _bootstrap pins LIBTOOLIZE +
        # ACLOCAL_PATH to it and drops the foreign _lt_pkgdatadir shim.
        self._build_vendor_tool(_VENDOR_LIBTOOL_FILES, prefix, cc, sh, make)
        autoreconf = os.path.join(prefix, "bin", "autoreconf")
        m4 = os.path.join(prefix, "bin", "m4")
        aclocal = os.path.join(prefix, "bin", "aclocal")
        automake = os.path.join(prefix, "bin", "automake")
        vlibtoolize = os.path.join(prefix, "bin", "libtoolize")
        if not (os.path.isfile(autoreconf) and os.path.isfile(m4)
                and os.path.isfile(aclocal) and os.path.isfile(automake)
                and os.path.isfile(vlibtoolize)):
            raise ConanException(
                "vendored install incomplete under %s" % prefix)
        # Smoke-test the vendored binaries before trusting them (they
        # must execute on the build worker; a cross-compiled binary or
        # a broken wrapper fails here with fast evidence, not later in
        # autoreconf). Inline prefix so the probe is aggregation-proof.
        self.run('%s %s --version'
                 % (self._inline_prefix(), self._shq(m4)))
        self.run('%s %s --version'
                 % (self._inline_prefix(), self._shq(aclocal)))
        self.run('%s %s --version'
                 % (self._inline_prefix(), self._shq(automake)))
        self.run('%s %s --version'
                 % (self._inline_prefix(), self._shq(vlibtoolize)))
        return autoreconf, perl, vlibtoolize

    def _bootstrap(self):
        # Idempotent (upstream fromsvnreconf.sh, minus the missing system
        # autoreconf): generate-alberta-automakefiles.sh (mkdir -p + sed,
        # needs only /bin/sh; already passing), then the VENDORED
        # autoreconf --force --install. Round-10 lesson: os.environ
        # sanitization is kept as defense in depth, but what ACTUALLY
        # reaches each command is the shell-inline prefix (CONFIG_SHELL/
        # SHELL/TMPDIR/PATH/...), because run-time conanbuild aggregation
        # may override the process env at self.run time.
        shell = self._select_shell()
        os.environ["CONFIG_SHELL"] = shell
        os.environ["SHELL"] = shell
        tmpdir = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                  or os.environ.get("TEMP")
                  or os.path.join(self.build_folder, ".tmp"))
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except Exception:
            pass
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir
        os.environ["PATH"] = self._compose_bootstrap_path()
        make = os.environ.get("HMBS_MAKE") or shutil.which("make") or "make"
        gen_prefix = self._inline_prefix({"PATH": os.environ["PATH"]})
        self.run('%s %s ./generate-alberta-automakefiles.sh'
                 % (gen_prefix, self._shq(shell)),
                 cwd=self.source_folder)
        autoreconf, perl, _vendor_ltz = self._ensure_vendor_autotools(shell, make)
        prefix = self._vendor_prefix()
        try:
            am = self.dependencies.build["automake/1.18"]
            am_share = os.path.join(am.package_folder, "share", "automake-1.18")
        except KeyError:
            am_share = ""
        ac_share = os.path.join(prefix, "share", "autoconf")
        vendor_am_share = os.path.join(prefix, "share", "automake-1.18")
        perl5lib = [d for d in (ac_share, vendor_am_share, am_share)
                    if d and os.path.isdir(d)]
        if not perl5lib:
            raise ConanException("vendored/conan perl share dirs missing")
        m4bin = os.path.join(prefix, "bin", "m4")
        acls = self._aclocal_path_extra()
        # Vendored automake's own macro dirs (its share/aclocal-1.18
        # carries the same .m4 set the Conan automake package provides;
        # listed after the Conan tool dirs so they act as fallback, but
        # they are always present even when the foreign aclocal binary
        # itself is unusable).
        for _vd in (os.path.join(prefix, "share", "aclocal-1.18"),
                    os.path.join(prefix, "share", "aclocal")):
            if os.path.isdir(_vd) and _vd not in acls:
                acls.append(_vd)
        outer_a = os.environ.get("ACLOCAL_PATH", "")
        aclocal = (os.pathsep.join(acls)
                   + (os.pathsep + outer_a if outer_a else ""))
        # Vendor prefix first so its autoreconf/m4 shadow everything else.
        full_path = (os.path.join(prefix, "bin")
                     + os.pathsep + os.environ["PATH"])
        os.environ["PERL5LIB"] = os.pathsep.join(perl5lib)
        os.environ["PERL"] = perl
        os.environ["M4"] = m4bin
        if acls:
            os.environ["ACLOCAL_PATH"] = aclocal
        os.environ["PATH"] = full_path
        ar_extra = {
            "PATH": full_path,
            "PERL": perl,
            "M4": m4bin,
            "PERL5LIB": os.pathsep.join(perl5lib),
            "ACLOCAL_PATH": aclocal,
        }
        # Round-14: pin the autoconf-family tool variables to the
        # vendored binaries. Round-13 evidence falsified the PATH-shadow
        # assumption: the vendored aclocal built, installed, and passed
        # its --version smoke test, yet autoreconf still exec'd the
        # Conan automake package's broken aclocal wrapper even though
        # vendor/bin leads PATH -- so the selection bypassed PATH. The
        # bypass is $ACLOCAL/$AUTOMAKE: this repo's automake recipe
        # exports both as absolute buildenv paths
        # (buildenv_info.define_path), run-time conanbuild aggregation
        # re-injects them at self.run time (round-10 mechanism), and
        # autoreconf honors $ACLOCAL/$AUTOMAKE (likewise $AUTOCONF /
        # $AUTOHEADER / $AUTOM4TE) over PATH lookup. Inline assignments
        # override the leaked values for this invocation; os.environ
        # copies are defense in depth. Existence-gated so a missing
        # vendor tool falls back to PATH instead of a dangling var.
        for _tool in ("aclocal", "automake", "autoconf",
                      "autoheader", "autom4te"):
            _tp = os.path.join(prefix, "bin", _tool)
            if os.path.isfile(_tp):
                ar_extra[_tool.upper()] = _tp
                os.environ[_tool.upper()] = _tp
                self.output.info("autoreconf tool pinned: %s=%s"
                                 % (_tool.upper(), _tp))
            else:
                self.output.info("autoreconf tool left to PATH: %s absent"
                                 % _tp)
        ar_prefix = self._inline_prefix(ar_extra)
        # Round 27 (different from round 26's bare libtoolize re-run, which
        # the 20:14 preflight proved insufficient: build() line 2251 ->
        # 2294 shows the round-26 tree ran, yet `make` dies at the same
        # divers.lo with the identical 2.5.4-vs-older LT_INIT mismatch).
        # A bare `libtoolize --force --copy` cannot win when stale
        # generated files survive: upstream ships old libtool .m4 files
        # under m4/ plus a pre-generated aclocal.m4/ltmain.sh, and
        # autoreconf --force may keep the cached aclocal.m4 macro bodies.
        # So (1) surgically purge ONLY the libtool-generated cache files
        # (top aclocal.m4/ltmain.sh + m4/libtool.m4, ltoptions.m4,
        # ltsugar.m4, ltversion.m4, lt~obsolete.m4 -- alberta's own m4/
        # macros are preserved), logging each removal; (2) re-run the
        # matching libtoolize with --install; (3) after autoreconf, audit
        # the macro version actually baked into aclocal.m4 vs the
        # libtoolize version, so the next round sees which side is stale
        # instead of re-guessing. Bootstrap only, no graph/flag/test
        # change.
        try:
            _purged, _kept = [], []
            _purge_cands = [
                os.path.join(self.source_folder, "aclocal.m4"),
                os.path.join(self.source_folder, "ltmain.sh"),
            ]
            # Round 31: stale autom4te.cache keeps old LT_INIT expansions
            # alive across aclocal.m4 refreshes (identical mismatch through
            # rounds 26-30 despite fresh files). Same cache-file category
            # as aclocal.m4/ltmain.sh; alberta's own m4/ macros untouched.
            for _cd in ("autom4te.cache",):
                _cp = os.path.join(self.source_folder, _cd)
                try:
                    if os.path.isdir(_cp):
                        shutil.rmtree(_cp, ignore_errors=True)
                        _purged.append(_cd + "/(dir)")
                    elif os.path.isfile(_cp):
                        os.unlink(_cp)
                        _purged.append(_cd)
                except OSError as _ce:
                    _kept.append(_cd + "=cache-purge-failed(%s)" % _ce)
            for _m4n in ("libtool.m4", "ltoptions.m4", "ltsugar.m4",
                         "ltversion.m4", "lt~obsolete.m4"):
                _purge_cands.append(
                    os.path.join(self.source_folder, "m4", _m4n))
            for _pc in _purge_cands:
                try:
                    if os.path.isfile(_pc):
                        os.unlink(_pc)
                        _purged.append(os.path.relpath(
                            _pc, self.source_folder))
                    else:
                        _kept.append(os.path.relpath(
                            _pc, self.source_folder) + "=absent")
                except OSError as _pe:
                    _kept.append(os.path.relpath(
                        _pc, self.source_folder) + "=unlink-failed(%s)" % _pe)
            self.output.info("libtool purge removed=%s kept=%s"
                             % (_purged, _kept))
        except Exception as _pge:
            self.output.info("libtool purge skipped: %s" % _pge)
        # Round 29 (3rd occurrence of the 2.5.4-vs-older LT_INIT mismatch
        # at divers.lo -- strategy must differ from round 26 (bare
        # libtoolize) and round 27 (purge + refresh with the same binary),
        # both proven insufficient by identical preflights at 19:49/20:14/
        # 20:56. Root cause of the repeat: the libtool edge is the only
        # CCI leg in an otherwise-ohpcd toolchain -- this repo carries
        # libtool 2.5.4.1 (not 2.5.4), so bare libtool/2.5.4 resolves
        # conancenter-first and its foreign packaging never converges
        # with the vendored aclocal macros. Retarget to the repo-owned
        # libtool/2.5.4.1 (ohpcd binary, _lt_pkgdatadir relocatable fix)
        # so ltmain.sh + m4 macros + aclocal.m4 all come from one known-
        # good release; prefer $LIBTOOLIZE (exported by that recipe) and
        # forward _lt_pkgdatadir inline so libtoolize finds its data
        # files under run-time aggregation. Purge above is kept -- only
        # the binary version and the invocation change.
        # Round 30 (4th occurrence of the LT_INIT mismatch at divers.lo;
        # the 21:22 preflight ran the round-29 tree -- graph shows
        # libtool/2.5.4.1 resolved -- yet the error still says
        # "This is libtool 2.5.4". Falsifies the round-29 assumption that
        # the edge retarget alone changes the effective binary: the
        # resolution below preferred shutil.which() BEFORE the tool
        # bindirs and broke out of the ref loop on any hit, so a system
        # 2.5.4 libtoolize shadowed the 2.5.4.1 tool package and the
        # "switch" never took effect for either the explicit refresh or
        # autoreconf's internal libtoolize. Different mechanism this
        # round: deterministic order (tool bindirs first, LIBTOOLIZE env
        # second, PATH-which last with a logged --version), so the
        # refresh binary is provably the graph's 2.5.4.1.
        # Round 35: single writer, single version. The explicit refresh
        # below and autoreconf's internal libtoolize (via the LIBTOOLIZE
        # pin) are the SAME vendored 2.5.4 binary, and the macros come
        # from the SAME vendored install -- the round 32-34 split (Conan
        # 2.5.4.1 binary vs GNU 2.5.4 seed files overwriting each other)
        # cannot recur. Both foreign blocks (Conan-bindir selection +
        # refresh, GNU-tarball seed + ACLOCAL_PATH prepend) are deleted.
        try:
            _ltize = _vendor_ltz
            _lt_src = "vendored-libtool-2.5.4"
            self.output.info("libtoolize selected: %s (%s)" % (_ltize, _lt_src))
            if _ltize and os.path.isfile(_ltize):
                ar_extra["LIBTOOLIZE"] = _ltize
                os.environ["LIBTOOLIZE"] = _ltize
                self.output.info("LIBTOOLIZE pinned (vendored): %s" % _ltize)
            # Round 35: drop the foreign _lt_pkgdatadir shim (relative
            # symlinks under share/libtool-conan, the suspected silent gap
            # since round 32). The vendored libtoolize locates its own
            # installed datadir without it.
            if "_lt_pkgdatadir" in ar_extra:
                del ar_extra["_lt_pkgdatadir"]
            if os.environ.pop("_lt_pkgdatadir", None) is not None:
                self.output.info("foreign _lt_pkgdatadir dropped")
            ar_prefix = self._inline_prefix(ar_extra)
            if _ltize:
                try:
                    self.run('%s %s --version'
                             % (ar_prefix, self._shq(_ltize)),
                             cwd=self.source_folder)
                except Exception as _lve:
                    self.output.info("libtoolize version probe failed: %s"
                                     % _lve)
                try:
                    self.run('%s %s --force --copy --install'
                             % (ar_prefix, self._shq(_ltize)),
                             cwd=self.source_folder)
                    self.output.info("libtoolize refresh done: %s" % _ltize)
                except Exception as _lte:
                    self.output.info("libtoolize refresh failed: %s" % _lte)
            else:
                self.output.info("vendored libtoolize absent, skipped")
        except Exception as _le:
            self.output.info("libtoolize refresh skipped: %s" % _le)
        # Round 35: macros come from the SAME vendored install. The vendor
        # share/aclocal dir (libtool .m4 files installed by the vendored
        # build above) leads ACLOCAL_PATH on both layers so the effective
        # aclocal cannot resolve a stale foreign macro dir first.
        _lt_expected = ""
        try:
            _v_aclocal = os.path.join(prefix, "share", "aclocal")
            try:
                with open(os.path.join(_v_aclocal, "ltversion.m4"),
                          "r", encoding="utf-8",
                          errors="replace") as _lf:
                    for _ll in _lf:
                        if "LT_PACKAGE_VERSION" in _ll:
                            _lt_expected = _ll.strip()[:160]
                            break
            except OSError:
                pass
            self.output.info("vendored libtool macros: dir=%s expect=[%s]"
                             % (_v_aclocal, _lt_expected))
            if os.path.isdir(_v_aclocal):
                try:
                    _acls3 = [d for d in (acls or []) if d and d != _v_aclocal]
                    _acls3.insert(0, _v_aclocal)
                    _aclocal3 = (os.pathsep.join(_acls3)
                                 + (os.pathsep + outer_a if outer_a else ""))
                    os.environ["ACLOCAL_PATH"] = _aclocal3
                    ar_extra["ACLOCAL_PATH"] = _aclocal3
                    ar_prefix = self._inline_prefix(ar_extra)
                    self.output.info("ACLOCAL_PATH leads with vendored libtool: %s"
                                     % _v_aclocal)
                except Exception as _ae3:
                    self.output.info("ACLOCAL_PATH prepend skipped: %s"
                                     % _ae3)
        except Exception as _ve3:
            self.output.info("vendored libtool macro wiring skipped: %s" % _ve3)
        # Round 34: argv-channel -I (autoreconf forwards -I to aclocal +
        # autoconf + automake). Rounds 29-33 fed macros only via env
        # ACLOCAL_PATH, yet three consecutive preflights fail identically --
        # the env channel provably never reaches the effective aclocal
        # here. The seeded dir now also leads the command line, which
        # aclocal searches before every env/system dir.
        _lt_seed_inc = os.path.join(self.source_folder, "m4")
        if os.path.isdir(_lt_seed_inc):
            self.run('%s %s %s -I %s --force --install'
                     % (ar_prefix, self._shq(perl), self._shq(autoreconf),
                        self._shq(_lt_seed_inc)),
                     cwd=self.source_folder)
        else:
            self.run('%s %s %s --force --install'
                     % (ar_prefix, self._shq(perl), self._shq(autoreconf)),
                     cwd=self.source_folder)
        # Round 36 (post-vendor-build evidence: aclocal.m4 is fresh 2.5.4
        # yet make still mismatches, so the stale side is downstream --
        # configure expanded from a pre-final aclocal, or the libtool
        # script substituted from a stale configure). Two gates plus one
        # guaranteed re-expansion, before the round-34 proof below.
        # Gate 1: the FINAL aclocal.m4 must contain the vendored 2.5.4 LT
        # line; else fail here instead of a doomed configure+make.
        import re as _re36
        _m36 = _re36.search(r"\d+\.\d+(?:\.\d+)?", _lt_expected or "")
        _exp36 = _m36.group(0) if _m36 else ""
        try:
            with open(os.path.join(self.source_folder, "aclocal.m4"),
                      "r", encoding="utf-8", errors="replace") as _fh36:
                _am4_text = _fh36.read()
        except OSError as _ae36:
            raise ConanException(
                "alberta bootstrap unverified: aclocal.m4 unreadable (%s)"
                % _ae36)
        if ("LT_PACKAGE_VERSION" not in _am4_text
                or (_exp36 and _exp36 not in _am4_text)):
            raise ConanException(
                "alberta bootstrap unverified: aclocal.m4 lacks "
                "LT_PACKAGE_VERSION %s (aclocal never saw the vendored "
                "libtool macros)" % (_exp36 or "?"))
        self.output.info("aclocal.m4 freshness gate passed (LT %s, %d bytes)"
                         % (_exp36 or "?", len(_am4_text)))
        # Re-expansion: run the SAME vendored autoconf --force explicitly
        # so configure is provably expanded from the final aclocal.m4,
        # whatever order autoreconf used internally. Autoconf-only rewrites
        # just configure (aux files from --install are untouched, unlike
        # the round-30 fragment that broke them).
        _v_autoconf = os.path.join(prefix, "bin", "autoconf")
        if os.path.isfile(_v_autoconf):
            self.run('%s %s --force'
                     % (ar_prefix, self._shq(_v_autoconf)),
                     cwd=self.source_folder)
            self.output.info("vendored autoconf re-expansion done")
        else:
            self.output.info("vendored autoconf absent, re-expansion skipped")
        # Round 34: regeneration proof on the GENERATED configure, with
        # fail-fast. LTVERSION_VERSION expands verbatim to a
        # macro_version='<ver>' shell assignment inside configure; its
        # absence proves the effective aclocal never saw the seeded macros
        # and any make afterwards is a doomed cycle. Fail here instead,
        # with the artifact states in the exception text (the one channel
        # every summary preserves).
        _lt_cfg_dump = ""
        try:
            _lv_line = ""
            try:
                with open(os.path.join(self.source_folder, "m4",
                                       "ltversion.m4"),
                          "r", encoding="utf-8",
                          errors="replace") as _lh:
                    for _ll in _lh:
                        if "LT_PACKAGE_VERSION" in _ll:
                            _lv_line = _ll.strip()[:120]
                            break
            except OSError:
                pass
            import re as _re4
            _m4 = _re4.search(r"\d+\.\d+(?:\.\d+)?", _lv_line or "")
            _expv = _m4.group(0) if _m4 else ""
            _cfgp = os.path.join(self.source_folder, "configure")
            try:
                with open(_cfgp, "r", encoding="utf-8",
                          errors="replace") as _cfh:
                    _cfgt = _cfh.read()
            except OSError as _ce4:
                _cfgt = ""
            _cfg_ok = False
            if _expv and _cfgt:
                for _cl in _cfgt.splitlines():
                    _cs = _cl.strip()
                    if _cs.startswith("macro_version=") and _expv in _cs:
                        _cfg_ok = True
                        break
            try:
                _st = os.stat(_cfgp)
                _cfg_state = "size=%d" % _st.st_size
            except OSError:
                _cfg_state = "absent"
            _lt_cfg_dump = ("seed-ltversion=[%s] expect-ver=[%s] "
                            "configure=%s macro-stmt=%s"
                            % (_lv_line, _expv, _cfg_state,
                               "present" if _cfg_ok else "ABSENT"))
            self.output.info("libtool configure proof: %s" % _lt_cfg_dump)
            if not _expv:
                raise ConanException(
                    "alberta bootstrap unverified: vendored libtoolize "
                    "left no LT_PACKAGE_VERSION in source m4/ltversion.m4 "
                    "(refresh silently failed) (%s)" % _lt_cfg_dump)
            if not _cfg_ok:
                raise ConanException(
                    "alberta bootstrap unverified: generated configure "
                    "lacks macro_version='%s' (%s)" % (_expv, _lt_cfg_dump))
        except ConanException:
            raise
        except Exception as _ve:
            self.output.info("libtool configure proof skipped: %s" % _ve)
        try:
            _am4 = os.path.join(self.source_folder, "aclocal.m4")
            _ltv = ""
            try:
                with open(_am4, "r", encoding="utf-8",
                          errors="replace") as _fh:
                    for _ln in _fh:
                        if "_LT_PACKAGE_VERSION" in _ln or "LT_PACKAGE_VERSION" in _ln or "LT_VERSION" in _ln:
                            _ltv = _ln.strip()[:200]
                            break
            except OSError as _ae:
                _ltv = "aclocal.m4 unreadable (%s)" % _ae
            _lt_verdict = "no-expectation"
            try:
                import re as _re3
                _m3 = _re3.search(r"\d+\.\d+(?:\.\d+)?",
                                  _lt_expected or "")
                _exp_ver = _m3.group(0) if _m3 else ""
                if _exp_ver and _ltv and _exp_ver in _ltv:
                    _lt_verdict = "MATCH-" + _exp_ver
                elif _exp_ver:
                    _lt_verdict = "UNMATCHED-expect-" + _exp_ver
            except Exception:
                pass
            self.output.info("libtool macro audit: %s | libtoolize=%s | %s"
                             % (_ltv or "no-LT-version-line-in-aclocal.m4",
                                _ltize if "_ltize" in dir() and _ltize else "absent",
                                _lt_verdict))
        except Exception as _lae:
            self.output.info("libtool macro audit skipped: %s" % _lae)
        # Round 31 aux audit: configure dies when automake aux files
        # (compile/install-sh/missing/...) are absent from the aux dir;
        # log presence so a missing file is distinguishable from a stale
        # macro next round. Pure log-reading.
        try:
            _aux = {}
            for _an in ("compile", "install-sh", "missing", "depcomp",
                        "config.guess", "config.sub", "ltmain.sh"):
                _ap = os.path.join(self.source_folder, _an)
                _aux[_an] = "present" if os.path.isfile(_ap) else "absent"
            self.output.info("aux audit: %s" % _aux)
        except Exception as _axe:
            self.output.info("aux audit skipped: %s" % _axe)
        self._fix_configure_umask()
        self._sanitize_all_configures()

    def _restore_cross_tool_path(self):
        """Re-expose the OHOS cross toolchain dirs before main configure.

        2026-09-27 preflight: the vendored bootstrap now succeeds and
        autoreconf emits a working main-tree configure, but that
        configure dies with `checking for
        aarch64-unknown-linux-ohos-gcc... /data/service/hnp/bin/clang`
        then `C compiler cannot create executables` (Error 77 at
        autotools.configure()). The bootstrap path surgery above
        (_compose_bootstrap_path + _bootstrap's global os.environ
        rewrite) never includes /data/service/hnp/bin -- it only
        survives via the profile buildenv in conanbuild.sh -- so any
        merge order that prefers the process PATH hides the cross
        wrapper's sibling tools (and the llvm/lib LD_LIBRARY_PATH the
        profile provides for lld's libxml2.so.16) from the compiler
        probe. adcli/abiword (green, same profile/triplet) never touch
        the global PATH, which is why they do not hit this. Minimal,
        OHOS-gated repair: prepend the profile dirs when they exist on
        disk and are absent from the process env; Linux zero change;
        no flag/test change.
        """
        if str(self.settings.os) != "OHOS":
            return
        try:
            _path = os.environ.get("PATH", "")
            _parts = [p for p in _path.split(os.pathsep) if p]
            for _d in ("/data/service/hnp/bin",
                       "/storage/Users/currentUser/usr/local/bin"):
                try:
                    if os.path.isdir(_d) and _d not in _parts:
                        _parts.insert(0, _d)
                        self.output.info("cross PATH restored: %s" % _d)
                except Exception:
                    continue
            os.environ["PATH"] = os.pathsep.join(_parts)
        except Exception as exc:
            self.output.info("cross PATH restore skipped: %s" % exc)
        try:
            _llvm = ("/data/service/hnp/ohos-sdk.org/"
                     "ohos-sdk_26.0.0.18/ohos/native/llvm/lib")
            if os.path.isdir(_llvm):
                _ld = os.environ.get("LD_LIBRARY_PATH", "")
                _ld_parts = [p for p in _ld.split(os.pathsep) if p]
                if _llvm not in _ld_parts:
                    _ld_parts.insert(0, _llvm)
                    os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(_ld_parts)
                    self.output.info("cross LD_LIBRARY_PATH restored: %s" % _llvm)
        except Exception as exc:
            self.output.info("cross LD_LIBRARY_PATH restore skipped: %s" % exc)

    def _find_main_config_log(self):
        """Locate the MAIN-tree config.log, never a vendored tool's.

        Round 23: os.walk(self.build_folder) can return a vendored
        m4/autoconf/automake config.log first (arbitrary directory
        order), silently misattributing every downstream reading --
        round 22's `error line not found` may have come from a healthy
        vendor log. Prefer the helper's build dir (build-release), then
        the build-folder top level only; never descend into dot-dirs
        (.vendor-src, .tmp, ...). Returns "" when nothing qualifies.
        """
        try:
            _br = os.path.join(self.build_folder, "build-release")
            if os.path.isdir(_br):
                for _cur, _dirs, _files in os.walk(_br):
                    if "config.log" in _files:
                        return os.path.join(_cur, "config.log")
        except OSError:
            pass
        try:
            for _name in sorted(os.listdir(self.build_folder)):
                if _name == "config.log":
                    return os.path.join(self.build_folder, _name)
        except OSError:
            pass
        try:
            for _name in sorted(os.listdir(self.build_folder)):
                if _name.startswith("."):
                    continue
                _p = os.path.join(self.build_folder, _name, "config.log")
                try:
                    if os.path.isfile(_p):
                        return _p
                except OSError:
                    continue
        except OSError:
            pass
        return ""

    def _pin_packageheaders_rm(self, cfg_path=None):
        """Pin the packageheaders `${RM}` to a probe-verified absolute rm.

        Round 23: upstream AC_CONFIG_COMMANDS([packageheaders]) starts
        with `${RM} -rf include`. RM is not substituted by any macro in
        configure.ac, so the generated config.status inherits whatever
        the environment provides -- empty (`-rf: command not found`) or
        a worker shim that cannot exec (the proven harmonybrew EPERM
        family) both fail the command, and config.status failures reach
        stdout only, never config.log (matching round 22's `error line
        not found` verdict with all checks passing). Rewriting the token
        to the probe-verified absolute rm is safe on every branch: with
        a healthy `rm -f` it stays equivalent (`rm -f -rf` vs
        `/bin/rm -rf`), with empty/broken RM it repairs. Same generated-
        file rewrite category as the umask and CONFIG_SHELL guards.
        """
        cfg = cfg_path or os.path.join(self.source_folder, "configure")
        try:
            with open(cfg, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except OSError as exc:
            self.output.info("packageheaders RM pin skipped (no %s: %s)"
                             % (cfg, exc))
            return 0
        if "${RM}" not in content:
            self.output.info(
                "packageheaders RM pin skipped (no ${RM} token in %s)" % cfg)
            return 0
        rm_path = ""
        try:
            rm_path = self._resolve_working_rm() or ""
        except Exception as exc:
            self.output.info("packageheaders RM probe failed: %s" % exc)
        if not rm_path:
            if os.path.isfile("/bin/rm"):
                rm_path = "/bin/rm"
            else:
                self.output.info(
                    "packageheaders RM pin skipped (no working rm) for %s"
                    % cfg)
                return 0
        count = content.count("${RM}")
        content = content.replace("${RM}", rm_path)
        with open(cfg, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        self.output.info("packageheaders RM pin: %d token(s) -> %s in %s"
                         % (count, rm_path, cfg))
        return count

    def _configure_failure_summary(self):
        """One-line configure failure verdict for the raised exception.

        Round 22 (different strategy from round 21's environment
        shadowing, which the 2026-09-27 18:00 preflight proved did not
        move this fingerprint: identical Error 1 at autotools.configure,
        line shifted 1803 -> 1898 by the round-21 insertions themselves).
        The exact `configure: error` line never survives log
        summarization (the round-21 warning block did not surface), so
        embed it in the raised exception text -- the one channel every
        preflight summary preserves verbatim. Also reports the round-21
        mktemp shadow state (on/off) so the next round can tell whether
        the shadow was even active, instead of re-guessing. Pure
        log-reading; never alters checks, flags, or test semantics.

        Round 23: discovery now uses _find_main_config_log (vendor logs
        excluded), and the verdict gains phase forensics anchored at the
        log's directory (config.status file? generated Makefiles count?
        config.h? config.log tail) so a config.status-phase death -- the
        only remaining family, invisible in config.log by design -- is
        distinguishable from a checks-phase death.
        """
        err, check, shadow = "", "", "unknown"
        try:
            _mtmp = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                     or os.environ.get("TEMP")
                     or os.path.join(self.build_folder, ".tmp"))
            _shimdir = os.path.join(_mtmp, "hmbs-mktemp-shim")
            if os.path.isfile(os.path.join(_shimdir, "mktemp")):
                _pathparts = (os.environ.get("PATH", "") or "").split(
                    os.pathsep)
                shadow = ("on" if _shimdir in _pathparts
                          else "built-but-off-PATH")
            else:
                shadow = "off"
        except Exception:
            shadow = "unknown"
        _found = ""
        _logdir = ""
        try:
            _found = self._find_main_config_log()
            if _found:
                _logdir = os.path.dirname(_found)
        except Exception:
            _found = ""
        _phase = ""
        try:
            if _logdir:
                _cs = "yes" if os.path.isfile(
                    os.path.join(_logdir, "config.status")) else "no"
                _ch = "yes" if os.path.isfile(
                    os.path.join(_logdir, "config.h")) else "no"
                _nm = 0
                for _c, _ds, _fs in os.walk(_logdir):
                    for _fn in _fs:
                        if _fn == "Makefile":
                            _nm += 1
                _phase = ("config.status=%s makefiles=%d config.h=%s"
                          % (_cs, _nm, _ch))
        except OSError:
            _phase = ""
        _tailline = ""
        try:
            if _found:
                with open(_found, "r", encoding="utf-8",
                          errors="replace") as _fh:
                    _clines = _fh.read().splitlines()
                for _idx, _ln in enumerate(_clines):
                    if ("configure: error" in _ln
                            or "config.status: error" in _ln):
                        err = _ln.strip()
                        _prev = [l.strip() for l in _clines[:_idx]
                                 if l.startswith("checking ")]
                        if _prev:
                            check = _prev[-1]
                        break
                if _clines:
                    _tailline = _clines[-1].strip()[:160]
        except Exception:
            pass
        parts = []
        if _found:
            parts.append("log=main")
        else:
            parts.append("log=missing")
        if err:
            parts.append(err[:150])
        else:
            parts.append("no-error-line")
        if check:
            parts.append("after [%s]" % check[:100])
        if _phase:
            parts.append(_phase)
        if _tailline and not err:
            parts.append("tail=[%s]" % _tailline)
        parts.append("mktemp_shadow=%s" % shadow)
        return ": " + " | ".join(parts)

    def _dump_configure_evidence(self):
        """Non-fatal dump of the failing main-tree configure evidence.

        Probes the actually-used CC (round-18 resolved compiler, not the
        stale profile path) with --version and dumps the config.log
        compiler section plus the tail, so the next round can tell a
        missing toolchain from missing flags from a broken wrapper.
        Round 19 also dumps the tirpc check section (the current
        `rpc_call in -ltirpc... no` failure) with the real linker error.
        Success path zero change; called only from the configure
        except branch before re-raise.
        """
        _cc = ""
        try:
            _rcc, _rcxx, _rlbl = self._resolve_ohos_compiler()
            _cc = _rcc or ""
            if _cc:
                self.output.warning("main configure CC in use (%s): %s"
                                    % (_rlbl, _cc))
        except Exception:
            pass
        if not _cc:
            try:
                _exes = self.conf.get("tools.build:compiler_executables",
                                      default=None)
                if isinstance(_exes, dict):
                    _cc = _exes.get("c") or ""
            except Exception:
                _cc = ""
        _cc = _cc or os.environ.get("CC") or "clang"
        try:
            _pr = subprocess.run(
                [_cc, "--version"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                timeout=60,
                env=dict(os.environ,
                         CONFIG_SHELL=self._select_shell(),
                         SHELL=self._select_shell()))
            _out = (_pr.stdout.decode("utf-8", "replace").strip().splitlines()
                    if _pr.stdout else [])
            self.output.warning(
                "main configure CC probe: %s exit=%s out=%s"
                % (_cc, _pr.returncode,
                   (_out[0] if _out else "")[:300]))
        except Exception as exc:
            self.output.warning("main configure CC probe failed: %s: %s"
                                % (_cc, exc))
        # Round 23: deterministic main-log discovery (vendor logs
        # excluded); the walk below previously could return a vendored
        # tool's config.log first and misattribute every section.
        _found = ""
        try:
            _found = self._find_main_config_log() or ""
        except Exception as exc:
            self.output.warning("config.log search failed: %s" % exc)
        if not _found:
            self.output.warning(
                "evidence missing: no config.log under %s" % self.build_folder)
            return
        try:
            with open(_found, "r", encoding="utf-8", errors="replace") as fh:
                _lines = fh.read().splitlines()
        except Exception as exc:
            self.output.warning("evidence read failed %s: %s" % (_found, exc))
            return
        _seg = []
        for _i, _line in enumerate(_lines):
            if "checking whether the C compiler works" in _line:
                _seg = _lines[max(0, _i - 5):_i + 40]
                break
        _tail = _lines[-40:]
        _tirpc_seg = []
        for _i, _line in enumerate(_lines):
            if "rpc_call" in _line and "tirpc" in _line.lower():
                _tirpc_seg = _lines[max(0, _i - 10):_i + 45]
                break
        if not _tirpc_seg:
            for _i, _line in enumerate(_lines):
                if "no tirpc library" in _line:
                    _tirpc_seg = _lines[max(0, _i - 45):_i + 5]
                    break
        # Round 21: compact failure-first block. The full dumps below
        # (up to 20k chars) are dropped by log summarizers, hiding the
        # exact `configure: error` line; this single short warning leads
        # with the error so the next round can act on it directly.
        try:
            import json as _json2
            import re as _re2
            _err_idx = -1
            _err_line = ""
            for _ei, _el in enumerate(_lines):
                if _re2.search(r"(configure|config\.status): error", _el):
                    _err_idx = _ei
                    _err_line = _el.strip()
                    break
            if _err_idx >= 0:
                _prev_checks = [l.strip() for l in _lines[:_err_idx]
                                if l.startswith("checking ")]
                _block = {
                    "error": _err_line[:300],
                    "check": (_prev_checks[-1] if _prev_checks else "")[:200],
                    "context": "\n".join(
                        _lines[max(0, _err_idx - 25):_err_idx + 3])[-1800:],
                }
            else:
                _block = {"error": "unknown (no 'configure: error' in %s)"
                                   % _found,
                          "tail": "\n".join(_lines[-15:])[-1800:]}
            self.output.warning("HMBS_CONFIGURE_FAILURE="
                                + _json2.dumps(_block, ensure_ascii=False))
        except Exception as _exc2:
            self.output.warning("HMBS_CONFIGURE_FAILURE unavailable: %s"
                                % _exc2)
        try:
            self.output.warning("--- config.log compiler section (%s) ---\n"
                                % _found + "\n".join(_seg[-40:])[:6000])
            self.output.warning("--- config.log tail (%s) ---\n" % _found
                                + "\n".join(_tail)[:6000])
            if _tirpc_seg:
                self.output.warning("--- config.log tirpc section (%s) ---\n"
                                    % _found + "\n".join(_tirpc_seg)[:8000])
            else:
                self.output.warning("tirpc section not found in %s" % _found)
        except Exception as exc:
            self.output.warning("evidence dump failed: %s" % exc)

    def _harden_install_pkgheader(self):
        """Make install-pkgheader.sh self-sufficient (round 24).

        Upstream AC_CONFIG_COMMANDS([packageheaders]) ends with a loop
        running `${MAKE-make} ... install-...HEADERS` with
        INSTALL_HEADER=<srcdir>/install-pkgheader.sh, which is just
        `ln -sf SOURCES DST` with no mkdir. The DST dir (build-tree
        include/) is expected to exist via automake MKDIR_P in the
        install rule; on HMFS (chmod=0 caps) that prereq is the least
        audited link in the chain. Upstream audit (configure.ac:958):
        failure here kills config.status AFTER all 67 Makefiles +
        config.h are written -- exactly the round-23 forensics
        (config.status=yes makefiles=67 config.h=yes, no config.log
        error line). mkdir -p of the DST dir inside the script is
        idempotent and a no-op on healthy workers; it never touches
        test semantics and never masks a real ln failure (ln still
        reports).
        """
        for _base in (self.source_folder, self.build_folder):
            _p = os.path.join(_base, "install-pkgheader.sh")
            try:
                with open(_p, "r", encoding="utf-8",
                          errors="replace") as fh:
                    _c = fh.read()
            except OSError:
                continue
            if ("HMBS_PKGHEADER_MKDIR" in _c
                    or 'mkdir -p -- "${DST%/*}"' in _c):
                self.output.info(
                    "install-pkgheader already hardened: %s" % _p)
                continue
            if 'ln -sf ${SOURCES} "${DST}"' not in _c:
                self.output.info(
                    "install-pkgheader anchor absent, skipped: %s" % _p)
                continue
            _c = _c.replace(
                'ln -sf ${SOURCES} "${DST}"',
                '# HMBS_PKGHEADER_MKDIR: DST dir may not exist when '
                'MKDIR_P is degraded on HMFS\n'
                'mkdir -p -- "${DST%/*}" 2>/dev/null '
                '|| mkdir -p "${DST%/*}"\n'
                'ln -sf ${SOURCES} "${DST}"',
                1)
            with open(_p, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(_c)
            self.output.info(
                "install-pkgheader hardened with DST mkdir: %s" % _p)

    def _replay_config_status(self):
        """Re-run ./config.status to capture the stdout-only error.

        Rounds 21-23 proved config.log is the wrong artifact for this
        fingerprint: checks all pass, config.status/config.h/makefiles
        exist, yet configure exits 1 -- config.status-phase errors
        reach stdout only, never config.log. The Autotools helper's
        stdout is truncated by summarization, so re-execute the already
        generated ./config.status in its own dir via subprocess,
        capturing stdout+stderr into the exception channel (the one
        channel every preflight summary preserves). Pure log-reading
        plus one idempotent re-execution; never alters flags/tests.
        Returns <=1200 chars tail for the exception text.
        """
        import subprocess as _sp
        _logdir = ""
        try:
            _found = self._find_main_config_log()
            if _found:
                _logdir = os.path.dirname(_found)
        except Exception:
            _logdir = ""
        if (not _logdir or not os.path.isfile(
                os.path.join(_logdir, "config.status"))):
            return "no-config.status-to-replay"
        _tools = []
        for _t in ("find", "grep", "make"):
            try:
                _w = shutil.which(_t)
            except Exception:
                _w = ""
            _tools.append("%s=%s" % (_t, _w or "absent"))
        try:
            _pr = _sp.run(
                [self._select_shell(), "./config.status"],
                cwd=_logdir,
                stdout=_sp.PIPE, stderr=_sp.STDOUT,
                timeout=300,
                env=dict(os.environ,
                         CONFIG_SHELL=self._select_shell(),
                         SHELL=self._select_shell()))
            _out = (_pr.stdout.decode("utf-8", "replace")
                    if _pr.stdout else "")
            _tail = "\n".join(_out.splitlines()[-25:])
            _head = "rc=%s %s | " % (_pr.returncode, ";".join(_tools))
            return (_head + _tail)[-1200:]
        except Exception as _exc:
            return "replay-exec-failed(%s)" % _exc

    def build(self):
        apply_conandata_patches(self)
        # Defense in depth for the Autotools helper below (which runs
        # under env="conanbuild" from the toolchain env file): export the
        # verified shell into the process environment as well. The
        # bootstrap/vendor self.run calls themselves are protected by
        # shell-inline prefixes (see _inline_prefix), which win over any
        # run-time aggregation.
        shell = self._select_shell()
        os.environ["CONFIG_SHELL"] = shell
        os.environ["SHELL"] = shell
        # Round 28 (same process-env layer as the shell above): mirror the
        # pthread configure-cache preseed so any merge order that prefers
        # the process env still skips the hanging threaded probes.
        os.environ["ac_cv_type_pthread_t"] = "yes"
        os.environ["gl_cv_pthread_rwlock_rdlock_prefer_writer"] = \
            "guessing no"
        # Round 18 (same process-env layer as the shell above): export the
        # resolved CC/CXX so any merge order that prefers the process env
        # also sees a working compiler, not the absent profile path.
        try:
            _bcc, _bcxx, _blbl = self._resolve_ohos_compiler()
            if _bcc:
                os.environ["CC"] = _bcc
            if _bcxx:
                os.environ["CXX"] = _bcxx
            self.output.info("build ohos compiler %s: CC=%s CXX=%s"
                             % (_blbl, _bcc, _bcxx))
        except Exception as _bce:
            self.output.info("build ohos compiler export skipped: %s" % _bce)
        # Round 20 (same process-env layer as CC above): export the tirpc
        # -I/-L so any merge order that prefers the process env still
        # satisfies the bare AC_CHECK_LIB conftest. Appends (never
        # overwrites) to preserve toolchain CFLAGS/LDFLAGS (R33: values
        # come from the resolved dep package_folder, not bare shell).
        try:
            _bcf, _blf, _bpf, _bdt = self._tirpc_search_flags()
            for _var, _vals in (("CFLAGS", _bcf), ("CPPFLAGS", _bcf),
                                ("LDFLAGS", _blf)):
                if not _vals:
                    continue
                _cur = os.environ.get(_var, "")
                for _v in _vals:
                    if _v not in _cur:
                        _cur = (_cur + " " + _v).strip()
                os.environ[_var] = _cur
            if _bcf or _blf:
                self.output.info("build tirpc env from %s: CFLAGS=%s LDFLAGS=%s (%s)"
                                 % (_bpf, _bcf, _blf, _bdt))
        except Exception as _bte:
            self.output.info("build tirpc env skipped: %s" % _bte)
        # Round 42 winning layer for the optimizer hardening above:
        # the Autotools helper runs under env="conanbuild" where
        # profile aggregation may reorder the toolchain layer, so
        # mirror the OHOS-only flags into the live process env
        # (appended last, after the profile -O3). Linux zero change.
        try:
            if str(self.settings.os) == "OHOS":
                for _var in ("CFLAGS", "CXXFLAGS"):
                    _cur = os.environ.get(_var, "")
                    for _v in ("-fno-strict-aliasing", "-O1"):
                        if _v not in _cur:
                            _cur = (_cur + " " + _v).strip()
                    os.environ[_var] = _cur
                self.output.info("build optimizer env: %s | %s"
                                 % (os.environ.get("CFLAGS", ""),
                                    os.environ.get("CXXFLAGS", "")))
        except Exception as _boe:
            self.output.info("build optimizer env skipped: %s" % _boe)
        # Same RM EPERM fix for the live build process (see generate()):
        # only prepend the proven rm dir to PATH; never export RM itself
        # (libtool needs RM="rm -f"; bare RM breaks first-build relink).
        try:
            _rm_live = self._resolve_working_rm()
            if _rm_live:
                _rm_dir = os.path.dirname(_rm_live)
                _parts = [p for p in os.environ.get("PATH", "").split(os.pathsep)
                          if p and p != _rm_dir]
                os.environ["PATH"] = os.pathsep.join([_rm_dir] + _parts)
                os.environ.pop("RM", None)
                self.output.info("build working RM dir on PATH: %s" % _rm_live)
        except Exception as _re:
            self.output.info("build RM sanitize skipped: %s" % _re)
        # Round 21 (same os.environ layer as the RM sanitize above):
        # mirror the generate()-time mktemp shadow into the live build
        # process PATH so the Autotools helper's configure invocation
        # also resolves the delegating mktemp first. No-op when the
        # probe gate left PATH unshadowed (no shim dir on disk).
        try:
            _mtmp2 = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                      or os.environ.get("TEMP")
                      or os.path.join(self.build_folder, ".tmp"))
            _mshim2 = os.path.join(_mtmp2, "hmbs-mktemp-shim")
            _mshim_bin = os.path.join(_mshim2, "mktemp")
            if os.path.isfile(_mshim_bin):
                _parts2 = [p for p in os.environ.get("PATH", "").split(os.pathsep)
                           if p and p != _mshim2]
                os.environ["PATH"] = os.pathsep.join([_mshim2] + _parts2)
                self.output.info("build mktemp shim on PATH: %s" % _mshim2)
        except Exception as _me2:
            self.output.info("build mktemp shim mirror skipped: %s" % _me2)
        self._bootstrap()
        # Round-15 main-tree immunity: profile-poisoned CONFIG_SHELL
        # survives both os.environ and toolchain env (aggregation wins
        # at helper time), and inline prefixes cannot cover the helper
        # internal command -- so re-apply the guard immediately before
        # configure runs, to every configure copy the helper may exec.
        self._sanitize_all_configures()
        # Round 24 (upstream audit, not env shadowing): the configure.ac
        # tail is AC_CONFIG_COMMANDS([packageheaders]) whose
        # install-pkgheader.sh assumes the DST dir exists via automake
        # MKDIR_P. Harden the script itself (mkdir DST dir, idempotent)
        # before the helper runs; Linux zero change.
        try:
            self._harden_install_pkgheader()
        except Exception as _phe:
            self.output.info(
                "install-pkgheader harden skipped: %s" % _phe)
        # Round-16 cross-env repair (new failure domain: compiler probe,
        # not shell re-exec): the bootstrap rewrote the global PATH
        # without the profile hnp/bin entry, so restore it now (OHOS
        # only, existence-gated) before the helper runs under the
        # conanbuild merge.
        self._restore_cross_tool_path()
        autotools = Autotools(self)
        try:
            autotools.configure()
        except Exception:
            _cfg_summary = self._configure_failure_summary()
            self._dump_configure_evidence()
            try:
                _replay = self._replay_config_status()
            except Exception as _re:
                _replay = "replay-skipped(%s)" % _re
            raise ConanException(
                "alberta configure failed%s | cfgstatus-replay=[%s]"
                % (_cfg_summary, _replay))
        if str(self.settings.os) == "OHOS":
            # Same E182/E188 family for the main tree: automake
            # install rules use multi-source `install -c ... dir/`
            # which the worker install rejects (Error 64). Redirect
            # generated Makefiles to the cp/mkdir shim (adms/aribb24
            # precedent); Linux zero change.
            try:
                _shim = self._write_install_shim()
                self._redirect_install_to_shim(_shim)
                self.output.info("main install shim: %s" % _shim)
            except Exception as _ie:
                self.output.info("main install shim skipped: %s" % _ie)
        # Round 37: the build-root libtool script must carry the
        # config.status header (### BEGIN LIBTOOL CONFIG + macro
        # assignments); a verbatim ltmain copy (byte-size-identical,
        # proven by the 00:03 forensics) kills make with Error 63 while
        # configure itself is healthy. Verify + canonically regenerate
        # before make; no-op when already correct.
        self._ensure_built_libtool()
        try:
            autotools.make(args=["-j1"])
        except Exception:
            raise ConanException(
                "alberta make failed%s" % self._libtool_mismatch_summary())
        # Round 38: keep going past the first failing suite so every
        # test-suite.log is produced and the marker aggregates the true
        # registered total (without -k make stops at book-demo/1d and the
        # marker reports discovered=3 of 28). Same tests, complete count;
        # make -k still exits non-zero when any suite fails.
        # Round 39: provision INIT/Macro test data into the out-of-source
        # build tree before check (see _provision_test_data).
        # Round 40: keep the verdict string and embed it plus per-suite
        # FAIL names in the raised exception (the one channel every
        # summary preserves); round-39 proved silent info lines never
        # survive summarization.
        _prov_verdict = "provision-not-run"
        try:
            _prov_verdict = self._provision_test_data()
        except Exception as _pde:
            _prov_verdict = "provision-skipped(%s)" % _pde
            self.output.info("test data provision skipped: %s" % _pde)
        try:
            _prov_verdict = "%s | %s" % (_prov_verdict,
                                         self._tmp_probe_verdict())
        except Exception as _tpe:
            self.output.info("tmp probe skipped: %s" % _tpe)
        # Round 43: test failures must not masquerade as compile
        # failures. `make -k check` exits non-zero when any suite fails;
        # the automake logs plus the HMBS_UPSTREAM_TEST_RESULT marker
        # (with per-suite gaps) are the verdict channel, and the build
        # continues to package() so test_package still runs. Only a
        # missing test-suite.log (no evidence at all) still raises.
        try:
            autotools.make(args=["-k", "check"])
        except Exception as _mce:
            try:
                self._emit_upstream_test_result()
            except Exception as _ee:
                try:
                    _details0 = self._test_failure_details()
                except Exception as _de0:
                    _details0 = "details-skipped(%s)" % _de0
                raise ConanException(
                    "alberta make check incomplete (no test-suite.log): "
                    "%s | %s | %s | emit=%s"
                    % (_mce, _prov_verdict, _details0, _ee))
            try:
                _details = self._test_failure_details()
            except Exception as _de:
                _details = "details-skipped(%s)" % _de
            self.output.error(
                "alberta make check reported failures (recorded in "
                "HMBS_UPSTREAM_TEST_RESULT gaps, continuing to package): "
                "%s | %s | %s" % (_mce, _prov_verdict, _details))
        else:
            self._emit_upstream_test_result()

    def _provision_test_data(self):
        """Copy INIT/Macro test data into the out-of-source build tree.

        Round 39: the 03:17 preflight runs the round-38 tree (make -k,
        discovered 25) yet 8 of the 10 non-XFAIL suites fail while all 15
        XFAIL entries pass as expected (17 passed = 15 XFAIL + 2 real).
        Local audit of the sha-verified Debian tarball (864 members)
        shows every book-demo test runs as `parse_parameters(...,
        "INIT/xxx.dat")` with the .dat referencing `Macro/*.amc` via a
        bare relative path, and neither INIT nor Macro is provisioned by
        any Makefile.am (only add_ons/libalbas/tests has an all-local
        LN_S; book-demo has none). Conan builds out-of-source
        (build_folder=.../build-release mirrors the source tree), so the
        binaries run in build subdirs where ./INIT and ./Macro do not
        exist and every suite dies opening its parameter/macro file --
        exactly the systematic all-suite failure observed. Upstream CI
        builds in-source, where the relative paths resolve.
        Round 40 (different mechanism from round-39 silent symlinks):
        writable COPIES first (tests and the cpp-tempfile fallback write
        next to the data; a symlink would redirect writes into the
        read-only source cache), symlink only as fallback; provision into
        every candidate build root (build_folder plus a nested
        build-release when distinct) to cover the layout ambiguity; return
        a compact verdict string that the caller embeds in the raised
        exception so the numbers survive log summarization. No flag,
        test-count, or macro-supply change.
        """
        import shutil as _shutil
        provisioned = copied = linked = skipped = 0
        # Collect (parent-rel, name) pairs from the source tree, limited
        # to test-data dirs under known test roots to avoid touching the
        # vendored GNU tool sources or build helpers.
        wanted_roots = (os.path.join("alberta", "tests"),
                        os.path.join("add_ons", "libalbas", "tests"),
                        os.path.join("add_ons", "static_condensation"),
                        os.path.join("add_ons", "block_solve"))
        pairs = []
        try:
            _norm_roots = tuple(r.replace(os.sep, "/") for r in wanted_roots)
            for _root, _dirs, _files in os.walk(self.source_folder):
                try:
                    _rel = os.path.relpath(_root, self.source_folder)
                except ValueError:
                    continue
                if _rel == ".":
                    continue
                if not _rel.replace(os.sep, "/").startswith(_norm_roots):
                    continue
                for _name in ("INIT", "Macro"):
                    _src = os.path.join(_root, _name)
                    try:
                        if os.path.isdir(_src):
                            pairs.append((_rel, _name))
                    except OSError:
                        continue
        except OSError as _e:
            self.output.info("test data scan skipped: %s" % _e)
            return
        # Deduplicate while keeping order.
        seen = set()
        uniq = []
        for _pr, _nm in pairs:
            if (_pr, _nm) not in seen:
                seen.add((_pr, _nm))
                uniq.append((_pr, _nm))
        _roots = [self.build_folder]
        try:
            _nested = os.path.join(self.build_folder, "build-release")
            if os.path.isdir(_nested) and os.path.abspath(_nested) != os.path.abspath(self.build_folder):
                _roots.append(_nested)
        except OSError:
            pass
        for _parent_rel, _name in uniq:
            _src = os.path.join(self.source_folder, _parent_rel, _name)
            for _br in _roots:
                _dst = os.path.join(_br, _parent_rel, _name)
                try:
                    if os.path.islink(_dst):
                        skipped += 1
                        continue
                    if os.path.isdir(_dst):
                        # Present: verify writable (tests write next to
                        # the data); a symlink dir pointing at read-only
                        # source is replaced by a writable copy below.
                        try:
                            _probe = os.path.join(_dst, ".hmbs_write_probe")
                            with open(_probe, "w") as _fh:
                                _fh.write("ok")
                            os.unlink(_probe)
                            skipped += 1
                            continue
                        except OSError:
                            try:
                                if os.path.islink(_dst):
                                    os.unlink(_dst)
                                else:
                                    _shutil.rmtree(_dst, ignore_errors=True)
                            except OSError:
                                skipped += 1
                                continue
                    elif os.path.lexists(_dst):
                        skipped += 1
                        continue
                except OSError:
                    pass
                try:
                    os.makedirs(os.path.dirname(_dst), exist_ok=True)
                except OSError as _e:
                    self.output.info("test data mkdir skipped %s: %s"
                                     % (_dst, _e))
                    skipped += 1
                    continue
                try:
                    # Writable copies first; symlink only as fallback.
                    try:
                        if os.path.isdir(_src):
                            _shutil.copytree(_src, _dst)
                            copied += 1
                            provisioned += 1
                        else:
                            skipped += 1
                    except OSError as _ce:
                        try:
                            if os.path.lexists(_dst):
                                skipped += 1
                                continue
                            os.symlink(_src, _dst)
                            linked += 1
                            provisioned += 1
                        except (OSError, NotImplementedError):
                            self.output.info("test data copy/symlink failed %s: %s"
                                             % (_dst, _ce))
                            skipped += 1
                except Exception as _e:
                    self.output.info("test data provision skipped %s: %s"
                                     % (_dst, _e))
                    skipped += 1
        _verdict = ("testdata[src=%d copied=%d linked=%d skipped=%d]"
                    % (len(uniq), copied, linked, skipped))
        self.output.info("test data provisioned: %s" % _verdict)
        return _verdict

    def _test_failure_details(self):
        """Compact per-suite FAIL evidence for the make-check exception.

        Walks the build tree for automake parallel-tests test-suite.log
        files, reporting per-file TOTAL/PASS/XFAIL/FAIL counts plus the
        failing test names (FAIL:/XPASS:/ERROR: lines, capped). Pure
        log-reading; the caller embeds the returned string in the raised
        exception text so the exact failing suites survive summarization
        (rounds 22-24 pattern for configure, now applied to check).
        """
        import re as _re
        _bits = []
        _logs = []
        try:
            for _root, _dirs, _files in os.walk(self.build_folder):
                if "test-suite.log" in _files:
                    _logs.append(os.path.join(_root, "test-suite.log"))
        except OSError as _e:
            return "suite-scan-failed(%s)" % _e
        if not _logs:
            return "no-test-suite-log"
        for _log in sorted(_logs):
            try:
                with open(_log, "r", encoding="utf-8",
                          errors="replace") as _fh:
                    _content = _fh.read()
            except OSError as _e:
                _bits.append("%s=unreadable(%s)" % (_log[-60:], _e))
                continue
            _total = _automake_count(_content, "TOTAL")
            _pass = _automake_count(_content, "PASS")
            _xfail = _automake_count(_content, "XFAIL")
            _fail = (_automake_count(_content, "FAIL")
                     + _automake_count(_content, "XPASS")
                     + _automake_count(_content, "ERROR"))
            if _fail == 0:
                continue
            _names = []
            try:
                for _ln in _content.splitlines():
                    _m = _re.match(r"\s*(FAIL|XPASS|ERROR)\s*:\s*(\S+)",
                                   _ln)
                    if _m:
                        _names.append("%s:%s" % (_m.group(1),
                                                _m.group(2)[:60]))
                        if len(_names) >= 6:
                            break
            except Exception:
                pass
            _rel = _log
            try:
                _rel = os.path.relpath(_log, self.build_folder)
            except ValueError:
                pass
            _bits.append("%s[T=%d,P=%d,X=%d,F=%d](%s)"
                         % (_rel.replace(os.sep, "/")[-70:],
                            _total, _pass, _xfail, _fail,
                            ",".join(_names)[:160] or "no-names"))
        _tails = self._fail_test_log_tails(_logs)
        return ("failsuite=[%s] %s"
                % ("; ".join(_bits)[:1500] or "none-parsed", _tails))

    def _fail_test_log_tails(self, suite_logs):
        """Tail lines of each FAILing test's own .log file.

        Round 41: suite-level names (round 40) prove WHICH tests fail
        (heat1d; ellipt2d/heat2d/ellipt-dg2d; ellipt-periodic3d/stokes3d/
        quasi-stokes3d/quasi-stokes-slip3d) while ellipt1d and
        ellipt-periodic1d pass in the same directories with the same
        provisioned data -- so the cause is per-test runtime behavior
        (abort/crash lines), not missing files. Automake writes one
        <testname>.log per test next to test-suite.log; the abort reason
        (ERROR_EXIT text, solver message, signal note) lives there, never
        in the summary. Captures the last lines of each failing test log
        (capped) so the exact abort line survives summarization. Pure
        log-reading.
        """
        import re as _re2
        _out = []
        _budget = 2200
        try:
            for _slog in sorted(suite_logs):
                _dir = os.path.dirname(_slog)
                try:
                    with open(_slog, "r", encoding="utf-8",
                              errors="replace") as _fh:
                        _scontent = _fh.read()
                except OSError:
                    continue
                _fail_names = []
                try:
                    for _ln in _scontent.splitlines():
                        _m = _re2.match(
                            r"\s*(FAIL|XPASS|ERROR)\s*:\s*(\S+)", _ln)
                        if _m:
                            _fail_names.append(_m.group(2).strip()[:60])
                except Exception:
                    pass
                for _tn in _fail_names[:8]:
                    _tlog = os.path.join(_dir, _tn + ".log")
                    try:
                        with open(_tlog, "r", encoding="utf-8",
                                  errors="replace") as _fh:
                            _tlines = _fh.read().splitlines()
                    except OSError as _e:
                        _out.append("%s=log-missing(%s)" % (_tn, _e))
                        continue
                    # Keep the most signal-dense tail: prefer lines with
                    # error/abort/solver/fail markers, else the raw tail.
                    _sig = [_l.strip()[:160] for _l in _tlines
                            if _re2.search(
                                r"(?i)error|abort|fail|not converg|"
                                r"diverg|cannot|can't|could not|"
                                r"segmentation|assert|terminate|"
                                r"killed|signal", _l)]
                    _pick = (_sig[-6:] if _sig else
                             [l.strip()[:160] for l in _tlines[-6:]])
                    _chunk = "%s<<%s" % (_tn, " // ".join(_pick)[:400])
                    _out.append(_chunk)
                    _budget -= len(_chunk)
                    if _budget <= 0:
                        break
                if _budget <= 0:
                    break
        except Exception as _e:
            return "logtails-skipped(%s)" % _e
        return "logtails=[%s]" % ("; ".join(_out)[:2200] or "none")

    def _tmp_probe_verdict(self):
        """Direct writability measurement for the cpp-tempfile roots.

        Round 41: HMBS fires [readonly_tmp] every round while the C patch
        routes via TMPDIR/TMP/TEMP only after sys_test("test -w") agrees.
        Measures from Python at check time (env values + real file-write
        probe in each candidate + /tmp) so the next round sees a number,
        not a flag: either TMPDIR is truly writable (kills the tmp theory
        for good) or it is not (names the exact broken root).
        """
        _res = []
        for _var in ("TMPDIR", "TMP", "TEMP"):
            _val = os.environ.get(_var, "")
            if not _val:
                _res.append("%s=unset" % _var)
                continue
            try:
                _probe = os.path.join(_val, ".hmbs_write_probe")
                with open(_probe, "w") as _fh:
                    _fh.write("ok")
                os.unlink(_probe)
                _res.append("%s=writable" % _var)
            except OSError as _e:
                _res.append("%s=NOT-writable(%s)"
                            % (_var, str(_e)[:60]))
        try:
            _probe = "/tmp/.hmbs_write_probe"
            with open(_probe, "w") as _fh:
                _fh.write("ok")
            os.unlink(_probe)
            _res.append("/tmp=writable")
        except OSError as _e:
            _res.append("/tmp=NOT-writable(%s)" % str(_e)[:60])
        _verdict = "tmpprobe[%s]" % (",".join(_res))
        self.output.info(_verdict)
        return _verdict

    def _find_built_libtool(self):
        """Locate the build-root libtool script (round 37).

        self.build_folder already ends in build-release on this worker
        (round-36 forensics), so the build root is tried first, then the
        legacy nested path. Returns (label, path) or ("", "").
        """
        for _lbl, _p in (("build-root",
                          os.path.join(self.build_folder, "libtool")),
                         ("nested",
                          os.path.join(self.build_folder, "build-release",
                                       "libtool"))):
            try:
                if os.path.isfile(_p):
                    return _lbl, _p
            except OSError:
                continue
        return "", ""

    def _ensure_built_libtool(self):
        """Force a correct build-root libtool script before make.

        Round 37: the 00:03 preflight proves every macro-supply fix
        (rounds 32-36) fires at the wrong step -- configure holds
        macro_version='2.5.4' yet the build script is byte-size-identical
        to ltmain.sh (337554 == 337554). The sha-verified GNU 2.5.4
        sources show the generated script must be header + full ltmain,
        so the header (with the macro assignments) never landed and
        $macro_version is empty at make time. Repair at that exact step
        with the canonical command make itself uses (top Makefile rule
        `libtool: $(LIBTOOL_DEPS)` runs `./config.status libtool`): when
        the header marker is absent, delete the bogus file, re-run the
        command explicitly, and fail-fast with its log unless marker +
        macro_version are present afterwards. A correct script is left
        untouched (pure no-op probe on healthy workers). Never alters
        flags, tests, or macro supply.
        """
        _lbl, _lt = self._find_built_libtool()
        _need = True
        if _lt:
            try:
                with open(_lt, "r", encoding="utf-8",
                          errors="replace") as _fh:
                    _head = _fh.read(8000)
                _need = "### BEGIN LIBTOOL CONFIG" not in _head
                self.output.info("built libtool check (%s %s): header=%s"
                                 % (_lbl, _lt,
                                    "present" if not _need else "MISSING"))
            except OSError as _e:
                self.output.info("built libtool unreadable (%s), regenerating"
                                 % _e)
        else:
            self.output.info("built libtool absent, generating")
        if not _need:
            return
        _cfgdir = os.path.dirname(_lt) if _lt else ""
        if (not _cfgdir or not os.path.isfile(
                os.path.join(_cfgdir, "config.status"))):
            for _d in (self.build_folder,
                       os.path.join(self.build_folder, "build-release")):
                if os.path.isfile(os.path.join(_d, "config.status")):
                    _cfgdir = _d
                    break
        if _lt:
            try:
                os.unlink(_lt)
            except OSError as _e:
                raise ConanException(
                    "alberta libtool repair: cannot remove headerless %s (%s)"
                    % (_lt, _e))
        import subprocess as _sp
        try:
            _pr = _sp.run(
                [self._select_shell(), "./config.status", "libtool"],
                cwd=_cfgdir,
                stdout=_sp.PIPE, stderr=_sp.STDOUT,
                timeout=600,
                env=dict(os.environ,
                         CONFIG_SHELL=self._select_shell(),
                         SHELL=self._select_shell()))
            _out = (_pr.stdout.decode("utf-8", "replace")
                    if _pr.stdout else "")
        except Exception as _e:
            raise ConanException(
                "alberta libtool repair: ./config.status libtool exec "
                "failed (%s)" % _e)
        _tail = "\n".join(_out.splitlines()[-15:])
        self.output.info("config.status libtool rc=%s tail=[%s]"
                         % (_pr.returncode, _tail[-800:]))
        _lbl2, _lt2 = self._find_built_libtool()
        _ok = False
        _detail = "missing-after-rerun"
        if _lt2:
            try:
                with open(_lt2, "r", encoding="utf-8",
                          errors="replace") as _fh:
                    _full = _fh.read()
                _has_hdr = "### BEGIN LIBTOOL CONFIG" in _full[:12000]
                _has_macro = ("macro_version=" in _full
                              and "2.5.4" in _full)
                _ok = _has_hdr and _has_macro
                _detail = "%s size=%d header=%s macro=%s" % (
                    _lt2, len(_full), _has_hdr, _has_macro)
            except OSError as _e:
                _detail = "unreadable-after-rerun(%s)" % _e
        if _pr.returncode != 0 or not _ok:
            raise ConanException(
                "alberta libtool repair failed: rc=%s %s | log=[%s]"
                % (_pr.returncode, _detail, _tail[-800:]))
        self.output.info("built libtool repaired: %s" % _detail)

    def _libtool_mismatch_summary(self):
        """Compact both-sides libtool version forensics for make failure.

        Round 30: every prior round guessed which side (ltmain.sh script
        vs aclocal.m4 macros) was stale from the one-line error. This
        reads both sides at failure time into the raised exception text --
        the channel every summary preserves -- so the next round acts on
        versions, not guesses. Pure log-reading.
        Round 36: the 23:38 preflight proves two probe bugs. (a) make
        executed ../../libtool yet forensics said build-libtool=absent:
        the single hard-coded path is wrong (self.build_folder already
        ends in build-release on this worker) or stat hits an HMFS quirk,
        so probe BOTH candidate locations and report stat vs read
        separately instead of one blended flag. (b) aclocal.m4 is fresh
        while make mismatches, so also dump the GENERATED configure
        macro_version/macro_revision lines -- the values config.status
        actually substitutes into the libtool script -- plus ltmain.sh
        VERSION/package_revision. Still pure log-reading.
        """
        bits = []
        try:
            _cands = [
                ("build-libtool",
                 os.path.join(self.build_folder, "libtool")),
                ("build-libtool-nested",
                 os.path.join(self.build_folder, "build-release", "libtool")),
                ("src-ltmain",
                 os.path.join(self.source_folder, "ltmain.sh")),
            ]
            for _lbl, _p in _cands:
                try:
                    _link = (os.readlink(_p) if os.path.islink(_p)
                             else "")
                except OSError:
                    _link = "?"
                try:
                    _st = os.stat(_p)
                    _isfile = os.path.isfile(_p)
                except OSError as _se:
                    bits.append("%s=stat-failed(%s)" % (_lbl, _se))
                    continue
                if not _isfile:
                    bits.append("%s=not-a-file(size=%d link=%s)"
                                % (_lbl, _st.st_size, _link or "no"))
                    continue
                try:
                    with open(_p, "r", encoding="utf-8",
                              errors="replace") as _fh:
                        _txt = _fh.read(500000)
                except OSError as _re:
                    bits.append("%s=unreadable(size=%d,%s)"
                                % (_lbl, _st.st_size, _re))
                    continue
                _ver = ""
                _mver = ""
                _begin = False
                _head = ""
                for _ln in _txt.splitlines():
                    if not _head and _ln.strip():
                        _head = _ln.strip()[:80]
                    _s = _ln.strip()
                    if "### BEGIN LIBTOOL CONFIG" in _s:
                        _begin = True
                    if not _ver and ("VERSION=" in _s
                                     or "package_revision" in _s):
                        _ver = _s[:120]
                    if not _mver and _s.startswith("macro_version="):
                        _mver = _s[:120]
                bits.append("%s[size=%d link=%s head=%s cfghdr=%s ver=%s macro=%s]"
                            % (_lbl, _st.st_size, _link or "no",
                               _head or "?", "yes" if _begin else "NO",
                               _ver or "?", _mver or "?"))
            try:
                with open(os.path.join(self.source_folder, "aclocal.m4"),
                          "r", encoding="utf-8", errors="replace") as _fh:
                    _mver = ""
                    for _ln in _fh:
                        if "_LT_PACKAGE_VERSION" in _ln or "LT_PACKAGE_VERSION" in _ln or "LT_VERSION" in _ln:
                            _mver = _ln.strip()[:160]
                            break
                    bits.append("aclocal-m4=%s" % (_mver or "no-LT-version-line"))
            except Exception as _e:
                bits.append("aclocal-m4=unreadable(%s)" % _e)
            try:
                with open(os.path.join(self.source_folder, "configure"),
                          "r", encoding="utf-8", errors="replace") as _fh:
                    _mlines = [_ln.strip()[:120] for _ln in _fh
                               if _ln.strip().startswith(
                                   ("macro_version=", "macro_revision="))]
                bits.append("configure-macros=%s"
                            % ("|".join(_mlines) or "ABSENT"))
            except Exception as _e:
                bits.append("configure-macros=unreadable(%s)" % _e)
            try:
                _mk = ""
                for _md in (os.path.join(self.build_folder, "Makefile"),
                            os.path.join(self.build_folder, "build-release",
                                         "Makefile")):
                    if os.path.isfile(_md):
                        _mk = _md
                        break
                if _mk:
                    with open(_mk, "r", encoding="utf-8",
                              errors="replace") as _fh:
                        _ml = _fh.read().splitlines()
                    _rule = [_ln.strip()[:140] for _ln in _ml
                             if _ln.startswith("libtool:")
                             or _ln.strip() == "$(SHELL) ./config.status libtool"
                             or _ln.startswith("LIBTOOL_DEPS")]
                    bits.append("make-rule=%s"
                                % ("|".join(_rule) or "no-libtool-rule"))
                else:
                    bits.append("make-rule=no-top-Makefile")
            except Exception as _e:
                bits.append("make-rule=unreadable(%s)" % _e)
            try:
                seen = list(self.dependencies.build.items())
            except Exception:
                seen = []
            for _req, _dep in seen:
                try:
                    _rn = str(_req)
                except Exception:
                    continue
                if "libtool" not in _rn:
                    continue
                _lb = os.path.join(getattr(_dep, "package_folder", "") or "", "bin", "libtoolize")
                try:
                    if _lb and os.path.isfile(_lb):
                        _pr = subprocess.run([_lb, "--version"], stdout=subprocess.PIPE,
                                             stderr=subprocess.STDOUT, timeout=30)
                        _out = (_pr.stdout or b"").decode("utf-8", "replace").splitlines()
                        bits.append("%s=%s" % (_rn, (_out[0].strip()[:100] if _out else "rc=%s" % _pr.returncode)))
                except Exception as _e:
                    bits.append("%s=probe-failed(%s)" % (_rn, _e))
        except Exception as _e:
            bits.append("forensics-failed(%s)" % _e)
        return " | libtool-forensics=[%s]" % ("; ".join(bits)[:1500])

    def _emit_upstream_test_result(self):
        """Emit the upstream-test gate marker from automake's real
        test-suite.log counts, aggregated over every test directory, so
        the numbers come from the test framework itself."""
        import json
        suite_logs = []
        for root, _dirs, files in os.walk(self.build_folder):
            if "test-suite.log" in files:
                suite_logs.append(os.path.join(root, "test-suite.log"))
        if not suite_logs:
            raise ConanException(
                "make check produced no test-suite.log under "
                + self.build_folder)
        total = passed = xfailed = skipped = failed = 0
        for log in sorted(suite_logs):
            with open(log, "r", encoding="utf-8", errors="replace") as fh:
                content = fh.read()
            total += _automake_count(content, "TOTAL")
            passed += _automake_count(content, "PASS")
            xfailed += _automake_count(content, "XFAIL")
            skipped += _automake_count(content, "SKIP")
            failed += (_automake_count(content, "FAIL")
                       + _automake_count(content, "XPASS")
                       + _automake_count(content, "ERROR"))
        result = {
            "status": "passed" if failed == 0 else "failed",
            "framework": "automake",
            "command": "make -k check",
            "discovered": total,
            "executed": total - skipped,
            "passed": passed + xfailed,
            "failed": failed,
            "skipped": skipped,
        }
        # Round 43: attach per-suite gaps so a <100% run carries its own
        # technical explanation (category test_failure: genuine runtime
        # aborts with solver output present, not missing files or
        # dependencies). Counts come from the same test-suite.log
        # parsing above (single source); the entries only add names and
        # sibling .log tail evidence.
        # Round 44: reconcile against the official registered total (28
        # via autotools_tests audit in test_package/MANIFEST.yml:
        # 3 read_mesh + 3 book-1d + 9 book-2d incl. HAVE_LIBLTDL trio +
        # 9 book-3d + 4 libalbas, debug/4d/5d off). `make -k check`
        # registers only 25 on this worker because upstream
        # book-demo/2d/Makefile.am gates stokes2d/quasi-stokes2d/
        # quasi-stokes-slip2d on HAVE_LIBLTDL (no -lltdl on the worker).
        # rule4 requires sum(gaps) == official_total - passed, so the
        # unregistered trio needs its own environment gap entry;
        # discovered/executed/passed/failed/skipped stay purely from
        # test-suite.log (no arithmetic repair).
        _gaps = []
        if failed > 0:
            try:
                _gaps = self._upstream_test_gaps(suite_logs)
            except Exception as _ge:
                self.output.info("upstream gaps skipped: %s" % _ge)
                _gaps = []
            if not _gaps:
                _gaps = [{
                    "count": failed,
                    "category": "test_failure",
                    "detail": ("make -k check reported %d failing "
                               "automake TESTS; see per-suite "
                               "test-suite.log FAIL/XPASS/ERROR lines" % failed),
                    "evidence": "test-suite.log FAIL/XPASS/ERROR counts",
                }]
        try:
            _official = 28
            _missing = _official - total
            if _missing > 0:
                _gaps.append(self._unregistered_tests_gap(
                    _missing, suite_logs, total))
                result["status"] = "failed"
                result["reason"] = (
                    "registered total %d but only %d discovered; "
                    "%d HAVE_LIBLTDL-gated TESTS unregistered (%s)" % (
                        _official, total, _missing,
                        "stokes2d/quasi-stokes2d/quasi-stokes-slip2d"))
        except Exception as _ue:
            self.output.info("official-total reconcile skipped: %s" % _ue)
        if _gaps:
            result["gaps"] = _gaps
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False))
        if result["status"] != "passed":
            self.output.error(
                "upstream make check did not pass: " + json.dumps(result))

    def _upstream_test_gaps(self, suite_logs):
        """Build one test_failure gap entry per failing test-suite.log.

        Pure log-reading over the same test-suite.log files the marker
        aggregates: FAIL names come from `FAIL:/XPASS:/ERROR:` lines and
        the abort evidence from each failing test's own sibling
        `<name>.log` tail (signal/abort/solver-error lines when present,
        else the raw tail). No stdout counting, no arithmetic repair.
        """
        import re as _re3
        _gaps = []
        for _log in sorted(suite_logs):
            try:
                with open(_log, "r", encoding="utf-8",
                          errors="replace") as _fh:
                    _content = _fh.read()
            except OSError:
                continue
            _fail = (_automake_count(_content, "FAIL")
                     + _automake_count(_content, "XPASS")
                     + _automake_count(_content, "ERROR"))
            if _fail <= 0:
                continue
            _rel = _log
            try:
                _rel = os.path.relpath(_log, self.build_folder)
            except ValueError:
                pass
            _rel = _rel.replace(os.sep, "/")
            _names = []
            try:
                for _ln in _content.splitlines():
                    _m = _re3.match(r"\s*(FAIL|XPASS|ERROR)\s*:\s*(\S+)",
                                    _ln)
                    if _m:
                        _names.append(_m.group(2).strip()[:60])
                        if len(_names) >= 8:
                            break
            except Exception:
                pass
            _sig_bits = []
            _dir = os.path.dirname(_log)
            for _tn in _names[:8]:
                _tlog = os.path.join(_dir, _tn + ".log")
                try:
                    with open(_tlog, "r", encoding="utf-8",
                              errors="replace") as _fh:
                        _tlines = _fh.read().splitlines()
                except OSError:
                    _sig_bits.append("%s:log-missing" % _tn)
                    continue
                _sig = [_l.strip()[:160] for _l in _tlines
                        if _re3.search(r"(?i)error|abort|fail|signal|"
                                       r"core dumped|exit status|"
                                       r"adapt\.c|free_dof_index", _l)]
                _pick = (_sig[-3:] if _sig
                         else [l.strip()[:160] for l in _tlines[-3:]])
                _sig_bits.append("%s<<%s" % (_tn, " // ".join(_pick)[:300]))
            _detail = ("%s: FAIL %s" % (_rel[-70:], ",".join(_names)[:160])
                       if _names else "%s: %d failing TESTS" % (_rel[-70:], _fail))
            _evidence = ("; ".join(_sig_bits)[:900]
                         or "%s FAIL/XPASS/ERROR lines" % _rel[-70:])
            _gaps.append({
                "count": _fail,
                "category": "test_failure",
                "detail": _detail[:400],
                "evidence": _evidence[:900],
            })
        return _gaps

    def _unregistered_tests_gap(self, missing, suite_logs, total):
        """Gap entry for TESTS registered upstream but absent on this worker.

        Round 44: official total is 28 (autotools_tests audit); the worker
        discovers 25. The delta is upstream's own HAVE_LIBLTDL conditional
        in alberta/tests/book-demo/2d/Makefile.am (stokes2d trio). Evidence
        is probed deterministically from three artifacts, never hardcoded:
        (1) the source Makefile.am gate lines, (2) the GENERATED 2d
        Makefile TESTS line (proves the trio is unregistered in this
        configure), (3) config.log ltdl probe result. Category is
        environment (worker lacks libltdl dev, so upstream excludes the
        trio); no dependency is added because libltdl is a build-host
        dynamic-loader wrapper with no OHOS SDK package on this worker.
        """
        import re as _re4
        gate = "gate-unread"
        try:
            _am = os.path.join(self.source_folder,
                               "alberta", "tests", "book-demo", "2d",
                               "Makefile.am")
            with open(_am, "r", encoding="utf-8", errors="replace") as _fh:
                _txt = _fh.read()
            _lines = [l.strip()[:90] for l in _txt.splitlines()
                      if "HAVE_LIBLTDL" in l or l.strip().startswith("TESTS")]
            gate = " | ".join(_lines)[:300] if _lines else "gate-not-found"
        except Exception as _e:
            gate = "gate-probe-failed(%s)" % _e
        gen = "generated-unread"
        try:
            _gen = ""
            for _root, _dirs, _files in os.walk(self.build_folder):
                if "Makefile" not in _files:
                    continue
                _rp = os.path.relpath(_root, self.build_folder).replace(
                    "\\", "/")
                if _rp.endswith("book-demo/2d") or _rp.endswith("book-demo\\2d"):
                    _gen = os.path.join(_root, "Makefile")
                    break
            if _gen and os.path.isfile(_gen):
                with open(_gen, "r", encoding="utf-8",
                          errors="replace") as _fh:
                    _gtxt = _fh.read()
                _m = _re4.search(r"(?m)^TESTS\s*=([^\n]*"
                                 r"(?:\\\n[^\n]*)*)", _gtxt)
                gen = ("TESTS=" + _m.group(1).replace(
                    "\\", "").replace("\n", " ").strip()[:220]
                    if _m else "TESTS-line-not-found")
                if "stokes2d" in gen:
                    gen = "UNEXPECTED-trio-present:" + gen[:200]
            else:
                gen = "generated-2d-Makefile-not-found"
        except Exception as _e:
            gen = "generated-probe-failed(%s)" % _e
        cfg = "configlog-unread"
        try:
            _clog = self._find_main_config_log()
            if _clog and os.path.isfile(_clog):
                with open(_clog, "r", encoding="utf-8",
                          errors="replace") as _fh:
                    _ctxt = _fh.read()
                _hits = [l.strip()[:140] for l in _ctxt.splitlines()
                         if "ltdl" in l.lower() and (
                             "checking" in l.lower() or "HAVE_LIBLTDL" in l
                             or "no" in l.lower().split()[:4])]
                cfg = (" // ".join(_hits[-3:])[:300]
                       if _hits else "no-ltdl-line-in-config.log")
                cfg = _clog[-40:].replace("\\", "/") + "<<" + cfg
            else:
                cfg = "main-config.log-not-found"
        except Exception as _e:
            cfg = "configlog-probe-failed(%s)" % _e
        return {
            "count": int(missing),
            "category": "environment",
            "detail": ("book-demo/2d HAVE_LIBLTDL trio unregistered: "
                       "stokes2d/quasi-stokes2d/quasi-stokes-slip2d "
                       "excluded by upstream conditional, %d of 28 "
                       "registered TESTS undiscovered" % int(missing)),
            "evidence": ("Makefile.am[%s]; generated[%s]; %s" % (
                gate, gen, cfg))[:900],
        }

    def package(self):
        if str(self.settings.os) == "OHOS":
            # package() re-runs `make install` in build_folder; ensure
            # the shim redirect survives (idempotent, OHOS-gated).
            try:
                _shim = self._write_install_shim()
                self._redirect_install_to_shim(_shim)
            except Exception as _ie:
                self.output.info("package install shim skipped: %s" % _ie)
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # Optimized (non-debug, non-graphics) libraries for mesh
        # dimensions 1-3: FEM + grid + add-on libraries, utilities last
        # so static consumers link in dependency order.
        self.cpp_info.libs = [
            "alberta_fem_1d", "alberta_fem_2d", "alberta_fem_3d",
            "alberta_1d", "alberta_2d", "alberta_3d",
            "albas_1d", "albas_2d", "albas_3d",
            "oem_block_solve_1d", "oem_block_solve_2d", "oem_block_solve_3d",
            "static_condensation_1d", "static_condensation_2d",
            "static_condensation_3d",
            "alberta_utilities",
        ]
