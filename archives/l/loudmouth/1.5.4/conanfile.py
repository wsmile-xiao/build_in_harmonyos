#!/usr/bin/env python3
"""Conan recipe — loudmouth 1.5.4 (Autotools).

loudmouth is a lightweight and easy-to-use C library for programming with
the Jabber/XMPP protocol (an asynchronous client library on top of GLib).

Upstream (maintained MCabber fork):
  https://github.com/mcabber/loudmouth
  tarball: https://mcabber.com/files/loudmouth/loudmouth-1.5.4.tar.bz2

Adaptation notes (see notes.md for the full exploration log):
  * Requires GLib (glib-2.0 + gobject-2.0, pkg-config). The shipped
    `configure`/`aclocal.m4` already embed the AM_PATH_GLIB_2_0 and
    PKG_CHECK_MODULES macros, so no autoreconf is needed — the tarball
    builds out of the box as long as PkgConfigDeps places glib-2.0.pc /
    gobject-2.0.pc on PKG_CONFIG_PATH.
  * SSL is optionally provided by GnuTLS/OpenSSL. configure's default is
    `--with-ssl=gnutls`, which hard-errors when GnuTLS is absent, so the
    OHOS recipe pins `--with-ssl=no` (plaintext subscription is the
    primary use of this library). The optional libidn (IDNA) and
    libasyncns backends are likewise pinned off for a deterministic build.
  * Upstream test suite (tests/): two GLib test programs, test-parser
    (2 cases) and test-data-objects (2 cases), 4 g_test cases in total,
    driven by `make check`. They are executed after the build and their
    per-case results are parsed deterministically (see _run_upstream_tests).
"""

import json
import os
import re
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout

# Audited upstream GLib test-case count (tests/Makefile.am):
#   test-parser        -> /parser/valid_suite, /parser/invalid/suite       (2)
#   test-data-objects  -> /data_objects/auth_paramters, .../connect_params (2)
# Total = 4.  build() refuses to report "passed" unless the run accounts
# for exactly this many cases, so a silent skip cannot fake a green result.
UPSTREAM_TESTS_TOTAL = 4


# Multi-source-capable minimal ``install`` replacement for HPFS/HMDFS.
#
# The HMBS-provided / toybox ``install`` fails with "Error 64" on the
# multi-source form that pre-automake-1.9 generated Makefiles emit for
# install-*HEADERS targets:
#
#     install -c -m 644 file1 file2 ... fileN <destdir>
#
# (loudmouth's install-libloudmouthincludeHEADERS passes all 9 public headers
# in ONE $(INSTALL_DATA) call; single-file installs such as the static lib /
# .pc use the same shim and work fine.)  The fix (same pattern as E596 openfst
# and DRAFT-libnih) is to rewrite ``INSTALL`` in every generated Makefile to
# this shim, which loops per file with plain ``mkdir -p``/``cp -f`` and
# tolerates HMDFS's absent chmod.  It is invoked via ``/bin/sh`` so no exec
# bit / chmod is needed.
_INSTALL_SHIM = r"""#!/bin/sh
# loudmouth multi-source install shim (for HMDFS where GNU install is absent)
set -e
mode=""
dodir=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    -c|-p|-v|-s) shift ;;
    -m) mode="$2"; shift 2 ;;
    -m*) mode="${1#-m}"; shift ;;
    -d) dodir=1; shift ;;
    -*) shift ;;
    *) break ;;
  esac
done
n=0
for a in "$@"; do n=$((n+1)); done
if [ -n "$dodir" ]; then
  for d in "$@"; do mkdir -p "$d"; done
  exit 0
fi
if [ "$n" -lt 1 ]; then
  echo "install: missing file operand" >&2
  exit 1
fi
if [ "$n" -ge 2 ]; then
  dest=""
  i=0
  for a in "$@"; do
    i=$((i+1))
    if [ "$i" -eq "$n" ]; then dest="$a"; fi
  done
  [ -n "$dest" ] || { echo "install: missing destination" >&2; exit 1; }
  if [ -d "$dest" ]; then
    mkdir -p "$dest"
    i=0
    for a in "$@"; do
      i=$((i+1))
      if [ "$i" -lt "$n" ]; then
        cp -f "$a" "$dest/" || exit 1
      fi
    done
  else
    mkdir -p "$(dirname "$dest")"
    cp -f "$1" "$dest" || exit 1
  fi
else
  # single operand: GNU install requires both FILE and DEST; treat as error
  echo "install: missing destination file operand" >&2
  exit 1
fi
[ -z "$mode" ] || true
exit 0
"""


class LoudmouthConan(ConanFile):
    name = "loudmouth"
    version = "1.5.4"
    description = (
        "Lightweight and easy-to-use C library for programming with the "
        "Jabber/XMPP protocol, built on GLib"
    )
    license = "LGPL-2.1"
    homepage = "https://mcabber.com"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/tree/main/archives/l/loudmouth/1.5.4"
    topics = ("xmpp", "jabber", "network", "glib")

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "loudmouth is validated only for Linux and OHOS"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # configure.ac: AM_PATH_GLIB_2_0(2.38.0) + PKG_CHECK_MODULES(LOUDMOUTH,
        # glib-2.0, gobject-2.0).  glib/2.84.0.1 is a shared-only binary in the
        # ohpcd registry and provides the glib-2.0/gobject-2.0 .pc modules.
        #
        # transitive_headers=True/transitive_libs=True is REQUIRED: loudmouth's
        # installed public headers (lm-connection.h, lm-message-node.h, ...)
        # `#include <glib.h>`, i.e. glib's headers are part of loudmouth's
        # *public interface*.  Without transitive_headers, the CMakeDeps-based
        # consumer (test_package) does NOT inject glib's include dirs into the
        # loudmouth::loudmouth INTERFACE_INCLUDE_DIRECTORIES, so compiling any
        # TU that includes a loudmouth header fails with
        #     lm-message-node.h:26: fatal error: 'glib.h' file not found
        # (the main autotools build finds glib.h via pkg-config Cflags, masking
        # the bug; only the CMake consumer hits it).  Every other glib-exposing
        # library in this repo (atk/evince/cairo/... ) requires glib with
        # transitive_headers=True + transitive_libs=True for this reason.
        self.requires(
            "glib/2.84.0.1", transitive_headers=True, transitive_libs=True
        )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            # configure --with-ssl=gnutls is the default and hard-errors when
            # GnuTLS is absent; pin SSL off for a deterministic OHOS build.
            "--with-ssl=no",
            "--with-idn=no",
            "--with-asyncns=no",
            # IDT_COMPILE_WARNINGS defaults to level `error` (adds -Werror)
            # when autogen.sh is present in srcdir.  With the very new glib
            # (2.84) the 2018-era loudmouth code hits GLib deprecation warnings
            # which -Werror turns into hard compile errors (Error 2).  Tell
            # configure not to inject -Werror (Gentoo/OpenWrt do the same via
            # --with-compile-warnings=yes).  Level `no` emits no warning flags.
            "--with-compile-warnings=no",
            "--enable-shared" if self.options.shared else "--disable-shared",
            "--enable-static" if not self.options.shared else "--disable-static",
        ])
        if self.settings.os == "OHOS":
            # The shipped config.guess (2018-02-24) cannot guess the build type
            # on OHOS (UNAME_SYSTEM="HarmonyOS"), so --build must be pinned.
            # BUT passing BOTH --build and --host as the *equal* linux-gnu
            # triplet makes autoconf treat the build as native
            # (cross_compiling=no): configure then *runs* the freshly compiled
            # probe binary, which the OHOS build sandbox cannot execute, and
            # aborts with "cannot run C compiled programs" (proven in the
            # captagent / libofa / libncursesada rounds).
            #
            # Declare --host ALONE (WITHOUT a matching --build): a lone --host
            # sets cross_compiling=maybe, so the run failure flips maybe -> yes
            # and configure skips runtime probes.  config.guess is bypassed by
            # pre-seeding ac_cv_build in build() (see build()).  This is the
            # proven air-quality-sensor / nspr / a52dec triplet pattern.
            host_arg = "--host=aarch64-unknown-linux-gnu"
            if host_arg not in tc.configure_args:
                tc.configure_args.append(host_arg)
            self._inject_libintl(tc)
        tc.generate()
        deps = PkgConfigDeps(self)
        deps.generate()
        AutotoolsDeps(self).generate()

    def _inject_libintl(self, tc):
        """Link the glib-bundled proxy-libintl so executables resolve
        g_libintl_gettext.

        glib (shared-only binary in the ohpcd registry) is built nls=disabled
        but still vendors subprojects/proxy-libintl as lib/libintl.so, whose
        header maps `gettext` -> `g_libintl_gettext` (glib's private rename to
        avoid libc/libintl symbol clashes).  Consumers that include that header
        (e.g. loudmouth's lm-sock.c) therefore emit an undefined
        g_libintl_gettext reference in every object compiled into the static
        libloudmouth-1.a.  A static archive is fine, but the *link of an
        executable against libloudmouth-1.a* (examples/, tools/, tests/) must
        resolve it, and the PkgConfigDeps glib-2.0.pc Libs line does NOT carry
        `-lintl`.

        Following the proven libgtop/2.41.3 pattern: append LDFLAGS (so it lands
        in every Makefile link line, incl. downstream examples/tests), and only
        when the glib package really ships libintl.so (never invent a path).
        The -Wl,-rpath lets conftest / built executables locate libintl.so.8 at
        runtime from glib's private conan-cache libdir.
        """
        if "glib" not in self.dependencies:
            return
        dep = self.dependencies["glib"]
        pf = getattr(dep, "package_folder", None) or ""
        for _l in dep.cpp_info.libdirs:
            libdir = _l if os.path.isabs(_l) else os.path.join(pf, _l)
            if os.path.isdir(libdir) and os.path.exists(os.path.join(libdir, "libintl.so")):
                flag = "LDFLAGS=-L{} -lintl -Wl,-rpath,{}".format(libdir, libdir)
                if flag not in tc.configure_args:
                    tc.configure_args.append(flag)
                break

    def _ohos_shell_env(self):
        """Return {env: value} that forces every configure/config.status/make
        subprocess to use the injected /bin/sh (toybox ash, whose getcwd(2)
        works on HMDFS) instead of the HNP bash, whose getcwd(2) fails on the
        HMDFS build dir and aborts configure with
        "working directory cannot be determined".

        HMBS platform diagnostic [shell_getcwd]: use the injected SHELL=/bin/sh
        and CONFIG_SHELL=/bin/sh; do not hardcode /data/service/hnp/bin/bash.
        PWD is preset so bash/the shell's `pwd` builtin trusts a valid logical
        path instead of calling getcwd(2).
        """
        return {
            "SHELL": "/bin/sh",
            "CONFIG_SHELL": "/bin/sh",
            "PWD": self.build_folder,
        }

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        if self.settings.os == "OHOS":
            # E129/E011: HMDFS sets the setgid bit on new directories; with
            # configure's `umask 077` the config.status temp dirs become
            # drwx--S--- and config.status itself fails to write subs files.
            # Phase the configure with --no-create, patch the umask into the
            # generated config.status, then run it with the repo-shell.
            for key, value in self._ohos_shell_env().items():
                os.environ[key] = value
            # Pre-seed ac_cv_build so AC_CANONICAL_BUILD skips config.guess
            # (which cannot guess the build type on HarmonyOS).  Pairs with the
            # lone --host in generate() (no matching --build), which keeps
            # autoconf in cross-compile mode so the "cannot run C compiled
            # programs" probe is downgraded instead of fatal
            # (air-quality-sensor / nspr / a52dec pattern).
            os.environ["ac_cv_build"] = "aarch64-unknown-linux-gnu"
            # configure.ac enables GSSAPI/SASL (lp: lm-sasl.c) automatically
            # whenever it finds krb5-config on PATH, then compiles
            # `#include <gssapi/gssapi.h>`.  krb5 dev headers are not present on
            # OHOS, so pre-seed the AC_PATH_PROG cache to "no" and force
            # enable_gssapi=no (USE_GSSAPI conditional off).  There is no
            # --without-sasl switch in loudmouth; the krb5-config probe is the
            # only gate.
            os.environ["ac_cv_path_KRB5CONFIG"] = "no"
            autotools.configure(args=["--no-create"])
            config_status = os.path.join(self.build_folder, "config.status")
            if os.path.isfile(config_status):
                with open(config_status, "r", encoding="utf-8", errors="replace") as f:
                    text = f.read()
                if "umask 077" in text:
                    text = text.replace("umask 077", "umask 022")
                    with open(config_status, "w", encoding="utf-8") as f:
                        f.write(text)
            # Run config.status with the same /bin/sh used for configure.
            self.run('"/bin/sh" "%s"' % config_status, cwd=self.build_folder)
        else:
            autotools.configure()
        autotools.make(args=[f"-j{os.cpu_count() or 1}"])

        if can_run(self):
            result = self._run_upstream_tests()
            self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result))
        else:
            self.output.warning(
                "cross build: upstream runtime suite deferred to the OHOS worker"
            )

    def _run_upstream_tests(self):
        """Execute the two upstream GLib test programs and count their
        per-case results deterministically.

        Each program is a standard GLib g_test binary; run directly (no
        gtester wrapper, which is not guaranteed to ship in the OHOS glib
        package).  When built against the modern glib 2.84 shipped for OHOS,
        g_test defaults to emitting **TAP** output, e.g.
            TAP version 14
            # random seed: R02...
            1..2
            ok 1 /data_objects/auth_paramters
            ok 2 /data_objects/connect_parameters
            # End of data_objects tests
        so we count `ok <n> <name>` as passed and `not ok <n> <name>` as
        failed.  As a defensive fallback (older glib / non-default formats) we
        also honour the classic g_test `name: OK` / `name: FAIL` lines, but
        only when no TAP result line was seen, so the two formats never
        double-count the same case.

        The audited total is 4, so a case that is silently skipped (missing
        fixture / early exit / probe-time g_test_skip) cannot be counted as
        passed: the guard below demands discovered == passed + failed == 4.
        """
        tests_dir = os.path.join(self.build_folder, "tests")
        binaries = ["test-parser", "test-data-objects"]
        libdirs = self._test_libdirs()
        env = dict(os.environ)
        env["LD_LIBRARY_PATH"] = os.pathsep.join(libdirs + [env.get("LD_LIBRARY_PATH", "")])

        passed = 0
        failed = 0
        discovered = 0
        saw_tap = False
        lines = []
        for name in binaries:
            path = os.path.join(tests_dir, name)
            if not os.path.isfile(path):
                raise ConanInvalidConfiguration(
                    f"upstream test binary missing after build: {path}"
                )
            try:
                proc = subprocess.run(
                    [path], capture_output=True, text=True, env=env, timeout=300
                )
            except subprocess.TimeoutExpired:
                raise ConanInvalidConfiguration(
                    f"upstream test {name} timed out; cannot certify result"
                )
            out = (proc.stdout or "") + "\n" + (proc.stderr or "")
            bin_tap = False
            for line in out.splitlines():
                stripped = line.strip()
                # TAP result lines: "ok <n> <path>" / "not ok <n> <path>".
                # A bare "ok"/"not ok" (no number) is also valid TAP.
                if stripped == "ok" or stripped.startswith("ok "):
                    bin_tap = True
                    passed += 1
                    discovered += 1
                elif stripped == "not ok" or stripped.startswith("not ok "):
                    bin_tap = True
                    failed += 1
                    discovered += 1
            # Classic g_test fallback only when this binary emitted no TAP
            # result lines (avoids double counting).
            if not bin_tap:
                for line in out.splitlines():
                    if line.endswith(": OK"):
                        passed += 1
                        discovered += 1
                    elif line.endswith(": FAIL") or line.endswith(": ERROR"):
                        failed += 1
                        discovered += 1
            if bin_tap:
                saw_tap = True
            lines.append(f"== {name} exit={proc.returncode} == "
                         f"(format={'TAP' if bin_tap else 'classic'})")
            lines.append(out.strip())

        if discovered != UPSTREAM_TESTS_TOTAL:
            raise ConanInvalidConfiguration(
                "upstream test harness drift: parsed "
                f"{discovered} cases but audited {UPSTREAM_TESTS_TOTAL}; "
                "refusing to certify. Full output:\n" + "\n".join(lines)
            )
        self.output.info(
            f"[upstream-test] {passed}/{UPSTREAM_TESTS_TOTAL} cases passed, "
            f"{failed} failed (tap={saw_tap})"
        )
        return {
            "status": "passed" if failed == 0 else "failed",
            "framework": "gtest_macros",
            "command": "test-parser test-data-objects (upstream GLib TAP tests, "
                       "4 registered cases)",
            "discovered": discovered,
            "executed": discovered,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
        }

    def _test_libdirs(self):
        """glib libdirs (shared-only glib) plus the in-tree loudmouth lib
        dir, so the GLib test binaries can load their shared runtimes."""
        dirs = []
        for _, dep in self.dependencies.items():
            for d in dep.cpp_info.aggregated_components().libdirs:
                if d not in dirs:
                    dirs.append(d)
        # In-tree built library (in case shared loudmouth is in use).
        libdir = os.path.join(self.build_folder, "loudmouth", ".libs")
        if os.path.isdir(libdir) and libdir not in dirs:
            dirs.append(libdir)
        return dirs

    def _patch_install_for_hmfs(self):
        """Rewrite ``INSTALL`` in every generated Makefile to a multi-source
        capable shim.

        Old configure-era automake emits ONE ``$(INSTALL_DATA)`` call with all
        public headers for install-libloudmouthincludeHEADERS:
            install -c -m 644 lm-connection.h ... loudmouth.h <destdir>
        The HMBS/toybox ``install`` returns "Error 64" on such multi-source
        installs (single-file installs of the static lib and .pc are fine), so
        `make install` aborts in package().  Rewriting ``INSTALL`` means
        ``INSTALL_DATA`` / ``INSTALL_PROGRAM`` (which reference ``${INSTALL}``)
        all fall back to our shim that loops per file with plain
        ``mkdir -p``/``cp -f``.  We never pass an INSTALL override on the make
        command line (bash command substitution eats it -> Error 126), see
        E596 / DRAFT-libnih.
        """
        shim = os.path.join(self.build_folder, "hmbs-install-shim.sh")
        if not os.path.isfile(shim):
            with open(shim, "w", encoding="utf-8", newline="\n") as f:
                f.write(_INSTALL_SHIM)
        install_cmd = "/bin/sh " + shim
        patched = 0
        for root, _dirs, files in os.walk(self.build_folder):
            for fn in files:
                if fn != "Makefile":
                    continue
                mk = os.path.join(root, fn)
                with open(mk, "r", encoding="utf-8", errors="replace") as f:
                    txt = f.read()
                new_txt, subs = re.subn(
                    r"(?m)^INSTALL\s*=\s*.*$", "INSTALL = " + install_cmd, txt
                )
                if subs:
                    with open(mk, "w", encoding="utf-8") as f:
                        f.write(new_txt)
                    patched += subs
        self.output.info(
            f"[install-shim] INSTALL -> {install_cmd} (rewrote {patched} line(s))"
        )

    def package(self):
        # Patch INSTALL to a multi-source-capable shim so the 9-header
        # install-libloudmouthincludeHEADERS target no longer hits the
        # HMFS install Error 64 (test_parser / test-data-objects already ran
        # and passed in build(); here we only arrange packaging).
        self._patch_install_for_hmfs()
        Autotools(self).install()
        # Remove libtool metadata so the .la files never leak stale
        # build-time prefix paths into downstream .pc consumers.
        import shutil
        for root, _dirs, files in os.walk(self.package_folder):
            for fn in files:
                if fn.endswith(".la"):
                    os.remove(os.path.join(root, fn))

    def package_info(self):
        # Public headers install to $(includedir)/loudmouth-1.0/loudmouth and
        # the pc Cflags reference -I${includedir}/loudmouth-1.0.
        self.cpp_info.includedirs = ["include/loudmouth-1.0"]
        self.cpp_info.libs = ["loudmouth-1"]
        self.cpp_info.set_property("pkg_config_name", "loudmouth-1")
        self.cpp_info.set_property("cmake_file_name", "loudmouth")
        self.cpp_info.set_property("cmake_target_name", "loudmouth::loudmouth")
        # loudmouth-1.0.pc declares `Requires: glib-2.0` and links gobject-2.0.
        self.cpp_info.requires = ["glib::glib-2.0", "glib::gobject-2.0"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["dl", "pthread", "m"]
        if self.settings.os == "OHOS":
            # On OHOS the static libloudmouth-1.a references g_libintl_gettext
            # from glib's vendored proxy-libintl header mapping.  Consumers
            # linking the static library therefore need -lintl too; glib-2.0.pc
            # does not carry it.  Declare `intl` as a SYSTEM library (NOT in
            # cpp_info.libs): libintl.so is not shipped inside the loudmouth
            # package — it resolves from glib's private libdir through the
            # consumer's linker search path (glib pc's -L).  Previously putting
            # it in cpp_info.libs made the test_package's CMakeDeps demand a
            # `libintl.so` file inside the loudmouth package and abort at
            # configure time with
            #     Library 'intl' not found in package. If 'intl' is a system
            #     library, declare it with 'cpp_info.system_libs' property.
            # CMakeDeps handles system_libs by emitting plain -lintl, which the
            # linker resolves through glib's -L.  Same pattern as libgtop/2.41.3.
            self.cpp_info.system_libs = ["dl", "pthread", "m", "intl"]
            self.cpp_info.libs = ["loudmouth-1"]
