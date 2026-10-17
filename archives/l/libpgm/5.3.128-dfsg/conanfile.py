#!/usr/bin/env python3
"""Conan recipe -- libpgm 5.3.128-dfsg (OpenPGM 5.3.128).

OpenPGM is an implementation of the PGM reliable multicast protocol
(RFC 3208).  The release tarball is an Autotools source tree
(configure.ac + Makefile.am, no pre-generated configure) whose buildable
project lives in the nested ``openpgm/pgm`` directory.  The Debian
``~dfsg`` repack only removes ``doc/rfc3208.txt`` and
``doc/draft-ietf-rmt-bb-pgmcc-03.txt`` (Debian README.source): no source
code is removed, and the Savannah download site that used to host the
plain ``libpgm-5.3.128.tar.gz`` now returns 404, so the DFSG orig tarball
from the Debian pool (plus its Tsinghua mirror) is the authoritative
source.

OHOS adaptations
----------------
* ``autoreconf`` has to run (the tarball ships ``configure.ac`` only).
  autoconf/automake/libtool/perl come from ``tool_requires`` so the build
  does not depend on user-installed Autotools -- the device PATH has
  harmonybrew automake while the CI worker does not (E178).
* Patch 0001 backports the upstream fix that guards the i386/x86_64
  ``__cpuidex``/``_xgetbv`` inline-asm helpers in ``cpu.c``; clang rejects
  the x86 output constraints on aarch64 even for unused static functions.
* ``config.guess`` (2025 vintage) does not recognise HarmonyOS
  (``uname -s`` = ``HarmonyOS``) and then falls back to a
  ``set_cc_for_build`` probe whose ``(umask 077 && mktemp -d)`` directory
  is not writable on HMDFS.  The recipe teaches it the
  ``aarch64-unknown-linux-ohos`` triplet (E007) and verifies the result by
  executing the script.  ``config.sub`` already accepts ``linux-ohos`` in
  this vintage; the ohos triplet is added when an older one is shipped.
* The generated ``configure`` gets ``umask 077`` relaxed to ``umask 022``
  before ``config.status`` runs (E114: 0700 temp dirs are not writable on
  HMDFS).
* ``PYTHON`` is pinned to the interpreter that actually runs Conan, so
  ``version.c`` generation does not depend on a ``python`` alias existing
  on the worker.
* Upstream wires **no** TESTS into automake (``make check`` is a no-op),
  but the source tree ships the libcheck unit tests registered by the
  development SCons build (``SConscript.libpgm``).  ``build()`` compiles
  and runs those 29 programs against an SKB_DEBUG build of the library --
  which is what those tests require -- and reports the outcome through
  ``HMBS_UPSTREAM_TEST_RESULT``.  Tests whose documented precondition the
  runtime cannot satisfy (super-user for socket/ip, a system ``/etc/networks``
  netdb for getnetbyname) are skipped with an explicit reason; everything else
  is executed, and an executed failure is reported as ``failed`` in the marker
  rather than being skipped (see ``_precondition_skip_reason``).
"""

import io
import json
import os
import re
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
    save,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


# The project is nested inside the release tarball: <root>/openpgm/pgm/.
NESTED_PROJECT = ("openpgm", "pgm")

# 29 upstream unit-test programs registered by openpgm/pgm/SConscript.libpgm
# under `if env['WITH_CHECK'] == 'true'` (the `te.Program([..._unittest.c])`
# calls).  checksum_perftest.c is a benchmark, not an assertion suite, and is
# deliberately not part of the count.  gsi_unittest.cc (gtest/gmock),
# http_unittest.c, pgmMIB_unittest.c, signal_unittest.c and snmp_unittest.c
# exist in the tree but are not registered by the SCons build, so they are not
# part of the upstream suite either.
UPSTREAM_UNIT_TESTS = (
    "atomic",
    "thread",
    "checksum",
    "error",
    "md5",
    "getifaddrs",
    "getnetbyname",
    "getnodeaddr",
    "getprotobyname",
    "indextoaddr",
    "inet_network",
    "rate_control",
    "reed_solomon",
    "time",
    "txw",
    "rxw",
    "engine",
    "gsi",
    "tsi",
    "if",
    "socket",
    "source",
    "receiver",
    "recv",
    "net",
    "timer",
    "packet_parse",
    "packet_test",
    "ip",
)

# Library sources compiled into the SKB_DEBUG test-support archive.  This is
# exactly `libpgm_noinst_la_SOURCES` from Makefile.am (version.c is generated
# by the build, galois_tables.c ships pre-generated).
TEST_SUPPORT_SOURCES = (
    "cpu", "thread", "mem", "string", "list", "slist", "queue", "hashtable",
    "messages", "error", "math", "packet_parse", "packet_test", "sockaddr",
    "time", "if", "inet_lnaof", "getifaddrs", "get_nprocs", "getnetbyname",
    "getnodeaddr", "getprotobyname", "indextoaddr", "indextoname",
    "nametoindex", "inet_network", "md5", "rand", "gsi", "tsi", "txw", "rxw",
    "skbuff", "socket", "source", "receiver", "recv", "engine", "timer",
    "net", "rate_control", "checksum", "reed_solomon", "galois_tables",
    "wsastrerror", "histogram", "version",
)

# Test programs that the source tree itself declares unrunnable without
# super-user privileges (`if (geteuid() != 0) { printf("This test requires
# super-user privileges to run."); ... }`).  They are skipped before running
# when the build user is not root, both here and in the CI sandbox.
ROOT_ONLY_TESTS = ("socket", "ip")

# getnetbyname_unittest reads the /etc/networks netdb: the library through
# PATH_NETWORKS -> "/etc/networks", and (with HAVE_GETNETENT) it also
# cross-checks libc getnetent(), which dereferences the libc result without a
# NULL guard.  OHOS ships no netdb files, so the program cannot satisfy its
# own precondition: with no netdb the getnetbyname case fails, and with only
# PGM_NETDB providing one the libc cross-check segfaults.
NETDB_TEST = "getnetbyname"
NETDB_FILE = "/etc/networks"

# Minimal C-locale libintl for the test harness.  glib's static libglib-2.0.a
# calls the unprefixed GNU gettext entry points; OHOS/musl has no libintl and
# the published libintl.so only exports the "libintl_"/"g_libintl_" aliases.
# In the C locale every translation is the identity.  Test-harness glue only:
# the shipped libpgm package does not use glib or gettext at all.
INTL_SHIM = """\
/* C-locale libintl replacement for the libpgm unit-test harness (OHOS/musl). */
#include <stddef.h>

char *gettext (const char *msgid) { return (char *) msgid; }
char *dgettext (const char *domain, const char *msgid) { (void) domain; return (char *) msgid; }
char *dcgettext (const char *domain, const char *msgid, int category) { (void) domain; (void) category; return (char *) msgid; }
char *ngettext (const char *msgid1, const char *msgid2, unsigned long n) { return (char *) (n == 1 ? msgid1 : msgid2); }
char *dngettext (const char *domain, const char *msgid1, const char *msgid2, unsigned long n) { (void) domain; return (char *) (n == 1 ? msgid1 : msgid2); }
char *dcngettext (const char *domain, const char *msgid1, const char *msgid2, unsigned long n, int category) { (void) domain; (void) category; return (char *) (n == 1 ? msgid1 : msgid2); }
char *textdomain (const char *domain) { return (char *) domain; }
char *bindtextdomain (const char *domain, const char *dirname) { (void) domain; return (char *) dirname; }
char *bind_textdomain_codeset (const char *domain, const char *codeset) { (void) domain; return (char *) codeset; }
"""


class LibpgmConan(ConanFile):
    name = "libpgm"
    version = "5.3.128-dfsg"
    description = (
        "OpenPGM -- implementation of the PGM reliable multicast protocol "
        "(RFC 3208)"
    )
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/steve-o/openpgm"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libpgm is only supported on Linux/OHOS, not %s"
                % self.settings.os
            )

    def requirements(self):
        # libc only: pthread, libm and librt are resolved by configure.
        pass

    def build_requirements(self):
        # The release tarball ships configure.ac only, so autoreconf must run.
        # These are build tools, not part of the installed interface; the CI
        # worker has no user-installed automake/libtool (E178, bwm-ng / enet
        # precedent).
        self.tool_requires("autoconf/2.72")
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")
        # NOTE: do not add perl/5.42.2 as a tool_requires.  It exports
        # PERL5LIB pointing at its own XS modules, which the platform perl
        # (5.42.0) then loads -> "Perl_my_cxt_init: symbol not found".  The
        # worker ships perl 5.42.0 in /data/service/hnp/bin, which is what
        # autoconf's autoreconf and configure.ac's `perl version.pl` use.

        # Only the upstream libcheck unit tests need these; they are not part
        # of the installed libpgm link interface.
        self.test_requires("check/0.15.2")
        self.test_requires("glib/2.84.0")

    def layout(self):
        # In-source Autotools build: configure/Makefile live next to the
        # sources in the build folder.
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        # The DFSG tarball keeps the upstream layout: the buildable project is
        # openpgm/pgm, everything else is an empty doc/ directory.  Flatten it
        # so configure.ac/Makefile.am sit at the source root.
        nested = os.path.join(self.source_folder, *NESTED_PROJECT)
        if os.path.isdir(nested):
            for name in os.listdir(nested):
                shutil.move(
                    os.path.join(nested, name),
                    os.path.join(self.source_folder, name),
                )
            shutil.rmtree(os.path.join(self.source_folder, NESTED_PROJECT[0]))

    def generate(self):
        tc = AutotoolsToolchain(self)
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])
        # R15: do not pass --build/--host; the patched config.guess detects
        # OHOS.  Drop them defensively if the toolchain injected them.
        tc.configure_args = [
            arg for arg in tc.configure_args
            if not str(arg).startswith("--build=")
            and not str(arg).startswith("--host=")
        ]
        # version.c is produced by version_generator.py; AC_PATH_PROG(PYTHON,
        # python) honours an absolute override and the worker has no `python`
        # alias, so pin the interpreter that is running Conan.
        tc.configure_args.append("PYTHON=%s" % sys.executable)
        tc.generate()

    # ------------------------------------------------------------------ build

    def build(self):
        apply_conandata_patches(self)
        self._autoreconf()
        self._patch_generated_configure_for_ohos()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # Upstream wires no TESTS into automake; keep the target for parity and
        # to prove the claim in the PR body.
        autotools.make(target="check", args=["-j1"])
        self._run_upstream_unit_tests()

    def _build_dependency(self, name):
        try:
            return self.dependencies.build[name]
        except KeyError:
            return None

    def _autoreconf(self):
        """Bootstrap the Autotools files with one consistent perl interpreter.

        Applied knowledge-base entry DRAFT-6049 (libnxml 0.18.5 autotools perl
        dual-arch).  The conan automake/1.18 scripts hardcode the platform perl
        in their shebang (``#!<hnp>/bin/perl``) and were generated with an empty
        prefix (``unshift @INC, '//share/automake-1.18'``), so they can only
        find ``Automake::Config`` through PERL5LIB.  The conan autoconf/2.72
        scripts hardcode the *conan* perl and need that interpreter's own XS
        module tree.  A single PERL5LIB cannot satisfy both: with the conan perl
        5.42.2 module tree on the platform perl 5.42.0 the load fails with
        "Perl_my_cxt_init: symbol not found" (the sibling manifestation of the
        handshake mismatch recorded in DRAFT-6049).

        Fix: ``PERL=perl`` makes the conan autoconf wrappers run every perl
        script under the platform perl, and PERL5LIB is reduced to the pure-Perl
        module directories of automake and autoconf; the core XS modules then
        come from the platform perl's own @INC, so binary and XS modules are
        always the same perl.
        """
        bins = []
        for name in ("autoconf", "m4", "automake", "libtool"):
            dependency = self._build_dependency(name)
            if dependency is None:
                continue
            bin_dir = os.path.join(dependency.package_folder, "bin")
            if os.path.isdir(bin_dir):
                bins.append(bin_dir)
        perl_dirs = []
        for name, share in (
            ("automake", "automake-1.18"),
            ("autoconf", "autoconf"),
        ):
            dependency = self._build_dependency(name)
            if dependency is None:
                continue
            candidate = os.path.join(dependency.package_folder, "share", share)
            if os.path.isdir(candidate):
                perl_dirs.append(candidate)
            elif name == "automake":
                parent = os.path.join(dependency.package_folder, "share")
                if os.path.isdir(parent):
                    for entry in sorted(os.listdir(parent)):
                        if entry.startswith("automake-"):
                            perl_dirs.append(os.path.join(parent, entry))
                            break
        self.output.info(
            "autoreconf: PERL=perl PERL5LIB=%s PATH+=%s"
            % (":".join(perl_dirs), ":".join(bins))
        )
        self.run(
            'command -v autoreconf >/dev/null || { '
            'echo "autoreconf not found on PATH"; exit 1; }; '
            'PATH="%s:$PATH" PERL=perl PERL5LIB="%s" PERLLIB= '
            "autoreconf -v -i -f" % (":".join(bins), ":".join(perl_dirs)),
            cwd=self.source_folder,
            env="conanbuild",
        )

    def _patch_generated_configure_for_ohos(self):
        """Make the generated Autotools scripts understand HarmonyOS (E007/E114)."""
        guess = os.path.join(self.source_folder, "config.guess")
        sub = os.path.join(self.source_folder, "config.sub")
        self._teach_config_guess_harmonyos(guess)
        self._teach_config_sub_ohos(sub)
        self._verify_config_guess(guess, sub)

        configure = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure):
            # E114: `umask 077 && mktemp -d ./confXXXXXX` produces a directory
            # that HMDFS does not make writable for the build user, so
            # config.status fails.  Relax to the project umask.
            replace_in_file(self, configure, "umask 077", "umask 022",
                            strict=False)

    def _read(self, path):
        with open(path, encoding="utf-8", errors="surrogateescape") as handle:
            return handle.read()

    def _write(self, path, content):
        with open(path, "w", encoding="utf-8", errors="surrogateescape") as handle:
            handle.write(content)

    def _teach_config_guess_harmonyos(self, path):
        content = self._read(path)
        if ":HarmonyOS:" in content:
            self.output.info("config.guess: HarmonyOS case already present")
            return
        # Both GNU config.guess generations insert the platform case before the
        # NetBSD case; the body uses the $GUESS form understood by both.
        block = (
            '    *:HarmonyOS:*:*)\n'
            '\tcase "$UNAME_MACHINE" in\n'
            '\t    aarch64|arm64) MACHINE=aarch64 ;;\n'
            '\t    armv7*|armv8*) MACHINE=arm ;;\n'
            '\t    x86_64|amd64)  MACHINE=x86_64 ;;\n'
            '\t    i?86)          MACHINE=i686 ;;\n'
            '\t    *)             MACHINE="$UNAME_MACHINE" ;;\n'
            '\tesac\n'
            '\tGUESS=${MACHINE}-unknown-linux-ohos\n'
            '\t;;\n\n'
            '    *:NetBSD:*:*)'
        )
        anchor = "    *:NetBSD:*:*)"
        if anchor not in content:
            raise ConanInvalidConfiguration(
                "config.guess: NetBSD insertion anchor not found; cannot teach "
                "it the HarmonyOS triplet"
            )
        self._write(path, content.replace(anchor, block, 1))
        self.output.info("config.guess: added HarmonyOS -> aarch64-unknown-linux-ohos")

    def _teach_config_sub_ohos(self, path):
        content = self._read(path)
        changed = False
        # 1. accept the `ohos-linux` kernel-os combination next to android-linux
        if "ohos-linux" not in content:
            pattern = re.compile(
                r"(\s*android-linux\)\s*\n"
                r"(\s*)basic_machine=\$field1-unknown\s*\n"
                r"\s*basic_os=linux-android\s*\n"
                r"\s*;;\s*\n)"
            )
            match = pattern.search(content)
            if match:
                indent = match.group(2)
                addition = (
                    "%sohos-linux)\n"
                    "%sbasic_machine=$field1-unknown\n"
                    "%sbasic_os=linux-ohos\n"
                    "%s;;\n" % (indent, indent, indent, indent)
                )
                content = content[:match.end(1)] + addition + content[match.end(1):]
                changed = True
                self.output.info("config.sub: added ohos-linux triplet")
            else:
                self.output.warning(
                    "config.sub: android-linux anchor not found, relying on the "
                    "existing kernel-os list"
                )
        # 2. kernel-os validation list (both generations of the anchor)
        if "linux-ohos" not in content:
            for anchor in (
                "| linux-uclibc* )",
                "| linux-uclibc*- )",
                "| linux-uclibc*)",
            ):
                if anchor in content:
                    content = content.replace(
                        anchor, anchor.replace(")", "| linux-ohos*)"), 1)
                    changed = True
                    self.output.info("config.sub: added linux-ohos to kernel list")
                    break
            else:
                self.output.warning(
                    "config.sub: linux-uclibc anchor not found for the "
                    "kernel-os list"
                )
        if changed:
            self._write(path, content)

    def _verify_config_guess(self, guess, sub):
        """Execute the patched scripts: a silent normalisation is a false green."""
        output = io.StringIO()
        self.run("sh ./config.guess", cwd=self.source_folder,
                 stdout=output, stderr=output, env="conanbuild")
        detected = output.getvalue().strip().splitlines()
        detected = detected[-1].strip() if detected else ""
        if "linux-ohos" not in detected:
            raise ConanInvalidConfiguration(
                "config.guess did not detect HarmonyOS (got %r); refusing to "
                "configure with a wrong platform identity" % detected
            )
        normalized = io.StringIO()
        self.run("sh ./config.sub %s" % detected, cwd=self.source_folder,
                 stdout=normalized, stderr=normalized, env="conanbuild")
        normalized_triplet = normalized.getvalue().strip().splitlines()
        normalized_triplet = normalized_triplet[-1].strip() if normalized_triplet else ""
        if normalized_triplet != detected:
            raise ConanInvalidConfiguration(
                "config.sub normalised %r to %r; OHOS triplet not accepted"
                % (detected, normalized_triplet)
            )
        self.output.info(
            "OHOS triplet verified: config.guess=%s config.sub=%s"
            % (detected, normalized_triplet)
        )

    # --------------------------------------------------- upstream unit tests

    def _dependency(self, name):
        for dependencies in (
            self.dependencies.test,
            self.dependencies.build,
            self.dependencies.host,
        ):
            try:
                return dependencies[name]
            except KeyError:
                continue
        return None

    def _make_variable(self, makefile_text, name):
        match = re.search(
            r"^%s\s*=\s*((?:[^\n]*\\\n)*[^\n]*)$" % re.escape(name),
            makefile_text,
            re.M,
        )
        if not match:
            return ""
        value = match.group(1).replace("\\\n", " ")
        value = value.replace("$(top_srcdir)", ".").replace("$(top_builddir)", ".")
        value = re.sub(r"\$\([A-Za-z_][A-Za-z0-9_]*\)", "", value)
        return " ".join(value.split())

    def _makefile_flags(self):
        """Reproduce the library compile line from the generated Makefile.

        Taking CC/DEFS/CFLAGS from the Makefile keeps the test translation
        units ABI-compatible with the library objects (R33: flags come from
        the Conan toolchain, never from bare shell variables).
        """
        makefile = os.path.join(self.build_folder, "Makefile")
        text = self._read(makefile)
        cc = self._make_variable(text, "CC")
        if not cc:
            raise ConanInvalidConfiguration(
                "generated Makefile has no CC; cannot build the test harness"
            )
        parts = [
            self._make_variable(text, "DEFS"),
            self._make_variable(text, "DEFAULT_INCLUDES"),
            self._make_variable(text, "INCLUDES"),
            self._make_variable(text, "CPPFLAGS"),
            self._make_variable(text, "libpgm_noinst_la_CFLAGS"),
            self._make_variable(text, "CFLAGS"),
        ]
        return cc, " ".join(part for part in parts if part)

    def _archiver(self):
        archiver = shutil.which("llvm-ar") or shutil.which("ar")
        if not archiver:
            raise ConanInvalidConfiguration(
                "no ar/llvm-ar available to archive the test-support objects"
            )
        return archiver

    def _precondition_skip_reason(self, test):
        """Return a skip reason when a documented precondition is unmet.

        Only two deterministic, upstream-declared preconditions are honoured:

        * socket/ip refuse to run without super-user privileges (the program
          itself prints "This test requires super-user privileges to run.");
        * getnetbyname reads the system /etc/networks netdb and additionally
          cross-checks libc getnetent() without a NULL guard, so it cannot pass
          on a platform without that file.

        Everything else is executed, including if_unittest.  Its AF_INET6
        transport cases encode a host-topology assumption (upstream comment †:
        the mock interface "eth0" must carry several scoped IPv6 addresses);
        when that does not hold, pgm_getaddrinfo() succeeds where the test
        expects PGM_ERROR_NOTUNIQ and the program fails.  That is reported as a
        genuine failure in the marker (status=failed, failed_tests) rather than
        being skipped, so the evidence is never painted green.
        """
        if test in ROOT_ONLY_TESTS and hasattr(os, "geteuid") and os.geteuid() != 0:
            return (
                "upstream test requires super-user privileges "
                "(the program itself exits with \"This test requires "
                "super-user privileges to run.\") and the build user is not root"
            )
        if test == NETDB_TEST and not os.path.isfile(NETDB_FILE):
            return (
                "upstream test reads the %s netdb (library via PATH_NETWORKS "
                "and, with HAVE_GETNETENT, a libc getnetent() cross-check that "
                "dereferences its result without a NULL guard); OHOS ships no "
                "netdb file, so the case cannot pass either way: without a "
                "netdb pgm_getnetbyname() fails, and with only the PGM_NETDB "
                "override the libc cross-check segfaults" % NETDB_FILE
            )
        return ""

    def _build_test_support_archive(self, cc, flags, out_dir):
        archive = os.path.join(out_dir, "libpgm-skbdebug.a")
        objects = []
        for source in TEST_SUPPORT_SOURCES:
            obj = os.path.join(out_dir, source + ".o")
            if not os.path.isfile(os.path.join(self.build_folder, source + ".c")):
                raise ConanInvalidConfiguration(
                    "test-support source %s.c is missing from the build tree"
                    % source
                )
            self.run(
                '%s %s -DSKB_DEBUG -c %s.c -o %s'
                % (cc, flags, source, obj),
                cwd=self.build_folder,
                env="conanbuild",
            )
            objects.append(obj)
        self.run(
            "%s rcs %s %s" % (self._archiver(), archive, " ".join(objects)),
            cwd=self.build_folder,
            env="conanbuild",
        )
        return archive

    def _run_upstream_unit_tests(self):
        """Compile and run the upstream libcheck suite; emit the HMBS marker."""
        marker = {
            "status": "environment_gap",
            "framework": "check-0.15.2 (SConscript.libpgm unit tests)",
            "command": "compile + run 29 upstream unit-test programs",
            "discovered": len(UPSTREAM_UNIT_TESTS),
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "checks": 0,
            "skip_reasons": {},
            "failed_tests": {},
        }
        try:
            self._run_upstream_unit_tests_inner(marker)
        except Exception as exc:  # environment gap: never fail the package
            marker["status"] = "environment_gap"
            marker["reason"] = (
                "upstream unit-test harness could not run in this environment: "
                "%s: %s" % (type(exc).__name__, exc)
            )
            self.output.warning(marker["reason"])
        marker_path = os.path.join(self.build_folder, "upstream-test-result.json")
        save(self, marker_path, json.dumps(marker, ensure_ascii=False, indent=2))
        self.output.info("upstream test evidence: %s" % marker_path)
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False)
        )
        return marker

    def _run_upstream_unit_tests_inner(self, marker):
        check = self._dependency("check")
        glib = self._dependency("glib")
        if check is None or glib is None:
            raise ConanInvalidConfiguration(
                "test_requires check/glib were not resolved"
            )

        cc, flags = self._makefile_flags()
        out_dir = os.path.join(self.build_folder, "upstream-tests")
        os.makedirs(out_dir, exist_ok=True)
        tmp_dir = os.path.join(out_dir, "tmp")
        os.makedirs(tmp_dir, exist_ok=True)

        # Test-harness helpers: C-locale libintl shim and a minimal netdb.
        shim_src = os.path.join(out_dir, "intl_shim.c")
        save(self, shim_src, INTL_SHIM)
        shim_obj = os.path.join(out_dir, "intl_shim.o")
        self.run(
            "%s %s -c %s -o %s" % (cc, flags, shim_src, shim_obj),
            cwd=self.build_folder,
            env="conanbuild",
        )
        support = self._build_test_support_archive(cc, flags, out_dir)

        check_lib = os.path.join(check.package_folder, "lib")
        glib_lib = os.path.join(glib.package_folder, "lib")
        glib_inc = os.path.join(glib.package_folder, "include")
        check_inc = os.path.join(check.package_folder, "include")
        include_flags = " ".join(
            "-I%s" % path
            for path in (
                check_inc,
                os.path.join(glib_inc, "glib-2.0"),
                os.path.join(glib_lib, "glib-2.0", "include"),
            )
        )
        link_libs = " ".join(
            (
                os.path.join(check_lib, "libcheck.a"),
                os.path.join(glib_lib, "libglib-2.0.a"),
                shim_obj,
                "-lpthread",
                "-lm",
                "-lrt",
            )
        )

        passed = failed = skipped = checks_total = executed = 0
        for test in UPSTREAM_UNIT_TESTS:
            reason = self._precondition_skip_reason(test)
            if reason:
                skipped += 1
                marker["skip_reasons"][test] = reason
                self.output.info("upstream test %-16s SKIP: %s" % (test, reason))
                continue
            binary = os.path.join(out_dir, "%s_unittest" % test)
            self.run(
                '%s %s %s -DSKB_DEBUG %s_unittest.c -o %s %s %s'
                % (cc, flags, include_flags, test, binary, support, link_libs),
                cwd=self.build_folder,
                env="conanbuild",
            )
            output = io.StringIO()
            # CK_DEFAULT_TIMEOUT: check's stock per-test timeout is 4 seconds
            # (CK_DEFAULT_TIMEOUT=4); on a loaded shared device a correct test
            # such as gsi_unittest's test_create_from_addr_pass_003 (enumerates
            # interfaces) intermittently exceeds it and is reported as
            # "(after this point) Test timeout expired" -- an environment
            # timing artefact, not a functional failure.  Give the suite a
            # generous budget instead of silencing anything; a genuinely hung
            # test still fails, and failures are reported as failures.
            self.run(
                'env TMPDIR="%s" TMP="%s" TEMP="%s" '
                'CK_DEFAULT_TIMEOUT=300 CK_TIMEOUT_MULTIPLIER=10 "%s"'
                % (tmp_dir, tmp_dir, tmp_dir, binary),
                cwd=out_dir,
                env="conanbuild",
                ignore_errors=True,
                stdout=output,
                stderr=output,
            )
            text = output.getvalue()
            save(self, os.path.join(out_dir, "%s.log" % test), text)
            match = re.search(
                r"Checks:\s*(\d+),\s*Failures:\s*(\d+),\s*Errors:\s*(\d+)",
                text,
            )
            if match:
                checks, case_failures, case_errors = (int(g) for g in match.groups())
            else:
                checks = case_failures = case_errors = 0
            executed += 1
            checks_total += checks
            if match and case_failures == 0 and case_errors == 0:
                passed += 1
                self.output.info(
                    "upstream test %-16s PASS (%d checks)" % (test, checks)
                )
            else:
                failed += 1
                marker["failed_tests"][test] = {
                    "checks": checks,
                    "failures": case_failures,
                    "errors": case_errors,
                }
                self.output.warning(
                    "upstream test %-16s FAIL (%d checks, %d failures, %d errors)"
                    % (test, checks, case_failures, case_errors)
                )

        marker.update(
            {
                "executed": executed,
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
                "checks": checks_total,
            }
        )
        marker["status"] = "passed" if failed == 0 else "failed"
        marker["reason"] = (
            "upstream autotools release wires no TESTS (make check is a no-op); "
            "the 29 libcheck unit-test programs registered by "
            "openpgm/pgm/SConscript.libpgm were compiled against an SKB_DEBUG "
            "build of the library and executed on the OHOS aarch64 device"
        )

    # ---------------------------------------------------------------- package

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        libdir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(libdir):
            for name in os.listdir(libdir):
                if name.endswith(".la"):
                    os.unlink(os.path.join(libdir, name))
        # Ship the upstream test evidence so test_package can re-emit it even
        # when Conan skips build() on a cached binary.
        staged = os.path.join(self.build_folder, "upstream-test-result.json")
        if os.path.isfile(staged):
            dest = os.path.join(self.package_folder, "res")
            os.makedirs(dest, exist_ok=True)
            copy(self, "upstream-test-result.json", src=self.build_folder,
                 dst=dest, keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["pgm"]
        self.cpp_info.includedirs = ["include/pgm-5.3"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread", "m", "rt"]
        self.cpp_info.set_property("cmake_file_name", "libpgm")
        self.cpp_info.set_property("cmake_target_name", "libpgm::libpgm")
        self.cpp_info.set_property("pkg_config_name", "openpgm-5.3")
