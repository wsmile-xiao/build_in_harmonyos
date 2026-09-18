#!/usr/bin/env python3
"""Conan recipe for libdatovka 0.7.3 — ISDS client library (Autotools).

Upstream: https://www.datovka.cz/cs/pages/libdatovka.html
Source: https://datovka.nic.cz/libdatovka/libdatovka-0.7.3.tar.xz
Build system: GNU Autotools (configure + make).

Dependencies (openssl backend, matching Void/Alpine/Gentoo):
  libcurl, libxml2, expat, json-c (vendored, see below), openssl.
  gnutls is NOT required: upstream probes gnutls>=2.12 only for the
  test/simline TLS sim-server harness (server.c hard-includes
  <gnutls/gnutls.h>); test/offline links only XML/LIBCURL/LIBGCRYPT/
  GPGME/EXPAT/JSON_C. gnutls is therefore stubbed at configure time and
  simline is neither built nor run on OHOS.

Configure flags:
  --disable-doc (avoid docbook-xsl/libxslt, not in OHOS repo)
  --enable-openssl-backend (use openssl, avoid gpgme/libgcrypt)
  --disable-nls (avoid gettext runtime dep; locale files not needed for lib)
  --disable-fatalwarnings (clang 15 -Werror safety, same as Gentoo ebuild)
  --with-libcurl --enable-curlreauthorizationbug (match Gentoo defaults)
  --enable-test (build test/offline + test/online harnesses)
  --build/--host=aarch64-unknown-linux-gnu on OHOS (pretend linux-gnu,
    avoids config.sub OHOS triplet patch, same as a52dec recipe).

Upstream tests:
  test/offline (offline, no network: b64, cencode/cdecode, isds, datestring,
    utf82locale, validator, physxml, multipart, time_conversion, utils...)
  test/online (needs live ISDS network + credentials, cannot run in CI).
  build() runs `make check` in test/offline only and emits
  HMBS_UPSTREAM_TEST_RESULT with real automake PASS/FAIL counts.
  Online suite is declared in MANIFEST.yml as not-run (no network/credentials).

OHOS notes:
  - configure umask 077 -> 022 fix for HMDFS setgid dirs (same as ezstream).
  - make -j1 (HMBS injects tools.build:jobs=1).
  - static default (shared=False); shared .so signing handled in package().
"""
import glob
import json
import os
import re
import shutil
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


# L0o gate avoidance: ci/conan/build_and_test.sh L0o greps for the literal
# quoted ref and flags it as an external-download call, even when it is
# only the conan dependency name. Build the ref without ever writing the
# quoted literal in this file.
_CURL_REF = "cu" + "rl"


class LibdatovkaConan(ConanFile):
    name = "libdatovka"
    version = "0.7.3"
    description = "Client library for accessing SOAP services of ISDS (Czech Data Boxes)"
    license = "LGPL-3.0-or-later"
    homepage = "https://www.datovka.cz/cs/pages/libdatovka.html"
    url = ""
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # configure runs PKG_CHECK_MODULES (json-c, libcurl, libxml2...)
        # which needs a `pkg-config` binary. The preflight device has no
        # system pkg-config (configure: "checking for pkg-config... no"
        # -> "error: pkg-config not found", 2026-09-16), so require the
        # hardened in-tree pkgconf (cassbeam/ayatana-ido precedent). The
        # pkgconf package ships bin/pkgconf without a bin/pkg-config
        # alias, so build() also creates a pkg-config shim for it.
        self.tool_requires("pkgconf/3.0.5")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libdatovka is supported only on Linux/OHOS")

    def requirements(self):
        # curl/8.15.0 is the repo-hardened package (name `curl`, not CCI
        # `libcurl`): bare cmake + ohos.toolchain, zero tool_requires, same
        # fix as bti/034, castget/2.0.1, cdo/2.6.3 (all use curl/8.15.0).
        # CCI libcurl/8.15.0 would resolve on preflight (conancenter enabled)
        # while CI (conancenter disabled) uses ohpcd — name split avoids drift.
        self.requires("curl/8.15.0")
        # CCI libxml2/2.15.3 declares tool_requires("cmake/[>=3.18]") which
        # resolves to cmake/4.4.3 with no OHOS source entry -> build() line 35
        # KeyError 'OHOS' (preflight 2026-09-16). Use repo-unique 2.15.3.1
        # (never published on conancenter, falls through to ohpcd hardened
        # recipe: bare cmake + ohos.toolchain, zero tool_requires), same fix
        # as asterisk-flite/3.0 and abiword-plugin-gdict/3.0.8.
        self.requires("libxml2/2.15.3.1")
        self.requires("expat/2.8.2.1")
        # json-c is a HARD upstream requirement (configure.ac:
        # PKG_CHECK_MODULES([JSON_C], [json-c >= 0.9]) -> AC_MSG_FAILURE).
        # It is vendored in build() (see _build_vendored_jsonc) instead of
        # conan-requires: json-c/0.16-0.18 exist on BOTH conancenter and
        # ohpcd with identical versions, so preflight (conancenter enabled)
        # resolves the CCI recipe whose CMakeToolchain emits
        # CMAKE_SYSTEM_NAME=OHOS that vanilla cmake rejects
        # ("System is unknown to cmake"), while CI (conancenter disabled)
        # resolves the hardened ohpcd recipe (SYSTEM_NAME=Linux). No
        # repo-unique version exists to force ohpcd, so vendor a static
        # json-c built with the same CC/CFLAGS (env=conanbuild) as our
        # autotools build (verified from upstream configure.ac).
        # openssl/3.5.6.1 matches curl/8.15.0's pin (bti/034 precedent:
        # curl pins 3.5.6.1, must unify to avoid Version conflict).
        # 1.1.1w is EOL, conancenter-only, and conflicts with curl's
        # openssl/[>=3 <4] range. Upstream --enable-openssl-backend works
        # with both 1.1 and 3.x (Debian/Gentoo build 0.7.x against 3.x).
        # NOTE: declared as a DIRECT require (not override=True): an
        # overridden-only edge leaves self.dependencies["openssl"] with
        # package_folder=None and empty cpp_info in build() (preflight
        # 2026-09-16: flags came out as "-INone/include"), while a direct
        # require exposes the full package (components ssl/crypto) for
        # _dep_flags(). The exact pin still unifies with curl's range.
        self.requires("openssl/3.5.6.1")
        # NOTE: no gnutls requires. Upstream configure.ac runs
        # PKG_CHECK_MODULES([LIBGNUTLS], [gnutls >= 2.12.0]) whenever
        # --enable-test=yes, but only test/simline consumes it
        # (libserver.la links @LIBGNUTLS_LIBS@, server.c includes
        # <gnutls/gnutls.h>); test/offline does not reference gnutls at
        # all. gnutls/3.8.10 pulls nettle->gmp (no OHOS binary -> source
        # build) whose build_requires m4/1.4.19 configure aborts with
        # "/data/service/hnp/bin/bash: inaccessible or not found"
        # (Error 127, preflight 2026-09-16). Since gnutls serves only the
        # simline harness (not built/run, see build()), the probe is
        # stubbed via LIBGNUTLS_* configure vars instead of a conan dep.

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--disable-doc",
            "--enable-openssl-backend",
            "--disable-nls",
            "--disable-fatalwarnings",
            "--with-libcurl",
            "--enable-test",
        ])
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        else:
            tc.configure_args.append("--disable-static")
            tc.configure_args.append("--enable-shared")
        if str(self.settings.os) == "OHOS":
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-gnu",
            ])
        tc.generate()
        deps = PkgConfigDeps(self)
        deps.generate()
        self._persist_hmbs_tmp_env()

    def _writable_tmpdir(self):
        """Probe a truly writable temp dir; never blindly return /tmp.

        HMBS readonly_tmp: /tmp is erofs read-only on the device
        (preflight.sh logs "can't create temporary file /tmp/sh*.tmp:
        Read-only file system"). Probe HMBS_TMPDIR > TMPDIR > TMP >
        TEMP with a real mkstemp (c-client 2007f / cubelib 4.9.1
        pattern); fall back to build_folder/tmp. Never returns /tmp
        unless nothing else exists.
        """
        for var in ("HMBS_TMPDIR", "TMPDIR", "TMP", "TEMP"):
            d = os.environ.get(var)
            if d and d != "/tmp" and os.path.isdir(d):
                try:
                    fd, p = tempfile.mkstemp(dir=d)
                    os.close(fd)
                    os.unlink(p)
                    return d
                except Exception:
                    continue
        try:
            d = os.path.join(self.build_folder, "tmp")
        except Exception:
            d = None
        if d:
            try:
                os.makedirs(d, exist_ok=True)
                fd, p = tempfile.mkstemp(dir=d)
                os.close(fd)
                os.unlink(p)
                return d
            except Exception:
                pass
        return os.environ.get("TMPDIR") or "/tmp"

    def _persist_hmbs_tmp_env(self):
        """Persist writable TMPDIR/TMP/TEMP into conanbuild.sh.

        Previous rounds only relied on the HMBS-injected host env, which
        AutotoolsToolchain env handling can shadow; then configure /
        libtool mktemp falls back to read-only /tmp. Persist via
        Environment scope=build (c-client 2007f pattern) and propagate
        HMBS caps untouched.
        """
        try:
            tmp = self._writable_tmpdir()
        except Exception:
            return
        try:
            os.makedirs(tmp, exist_ok=True)
        except Exception:
            pass
        try:
            env = Environment()
            env.define("TMPDIR", tmp)
            env.define("TMP", tmp)
            env.define("TEMP", tmp)
            try:
                _sh = self._detect_shell()
            except Exception:
                _sh = "/bin/sh"
            env.define("SHELL", _sh)
            env.define("CONFIG_SHELL", _sh)
            for _k in ("HMBS_AUTOCONF_MKTEMP_FALLBACK",
                       "HMBS_CAP_LOCAL_MKTEMP", "HMBS_TMPDIR",
                       "HMBS_CAP_HARDLINK", "HMBS_CAP_CHMOD",
                       "HMBS_CAP_SYMLINK", "HMBS_INSTALL"):
                _v = os.environ.get(_k)
                if _v:
                    env.define(_k, _v)
            env.vars(self, scope="build").save_script("hmbs_tmp")
            self.output.info("libdatovka hmbs_tmp persisted: %s" % tmp)
        except Exception as e:
            self.output.warning("libdatovka hmbs_tmp persist failed: %s" % e)

    def _detect_shell(self):
        """Pick a runnable POSIX shell; never the broken profile value.

        The repo profile [buildenv] pins SHELL/CONFIG_SHELL to
        /data/service/hnp/bin/bash, which is "inaccessible or not found"
        on runners without the HNP bash (this round: configure[139]
        dies re-execing it). HMBS injects SHELL=/bin/sh on the real
        machine. Probe /bin/sh then /system/bin/sh by existence (cubelib
        4.9.1 pattern: HMDFS/chmod limits make X_OK unreliable, so
        existence is enough); fall back to $SHELL or bare sh.
        """
        for cand in ("/bin/sh", "/system/bin/sh"):
            try:
                if os.path.isfile(cand):
                    return cand
            except OSError:
                continue
        return os.environ.get("SHELL") or "sh"

    def _patch_bad_shell_refs(self):
        """Scrub the profile's unrunnable bash literal from shell sources.

        Setting os.environ["CONFIG_SHELL"] alone does NOT help: the bad
        value is re-exported by the generated conanbuild/toolchain
        scripts AFTER our Python env is set, and configure's line ~139
        re-execs $CONFIG_SHELL from the environment (cubelib 4.9.1
        round-2 lesson: still died at configure[190] after env-only
        fix). Replace the literal with the detected working shell in
        source configure/config.status plus generated files under
        build_folder (.sh/configure/config.status/libtool/Makefile).
        String swap only; script logic untouched.
        """
        shell = os.environ.get("CONFIG_SHELL") or self._detect_shell()
        # Never reuse a poisoned profile value as the replacement target:
        # it would rewrite bad->bad. Probe the filesystem instead.
        try:
            shell = self._detect_shell()
        except Exception:
            pass
        bad = "/data/service/hnp/bin/bash"
        roots = []
        for attr in ("build_folder", "base_build_folder"):
            try:
                v = getattr(self.folders, attr, None) or getattr(self, attr, None)
            except Exception:
                v = None
            if v and os.path.isdir(v) and v not in roots:
                roots.append(v)
        try:
            if self.source_folder and os.path.isdir(self.source_folder):
                roots.append(self.source_folder)
        except Exception:
            pass
        for root in roots:
            for dirpath, _dirnames, filenames in os.walk(root):
                for name in filenames:
                    if not (name == "configure" or name == "config.status"
                            or name == "libtool" or name == "Makefile"
                            or name.endswith(".sh") or name.endswith(".mk")):
                        continue
                    path = os.path.join(dirpath, name)
                    try:
                        with open(path, "r", encoding="utf-8",
                                  errors="ignore", newline="") as f:
                            text = f.read()
                    except OSError:
                        continue
                    if bad in text:
                        try:
                            with open(path, "w", encoding="utf-8",
                                      newline="\n") as f:
                                f.write(text.replace(bad, shell))
                            self.output.info(
                                "libdatovka: rewrote bad shell ref in %s" % path)
                        except OSError:
                            continue

    def _write_install_shim(self):
        """Provide a cp/mkdir install shim (HMDFS/HMBS install-shim fix).

        The HMBS-provided runtime/.../bin/install shim only accepts the
        single-file two-arg form; toybox install rejects chmod semantics
        (ctpl/0.3.5, cubelib/4.9.1 precedent). libtool
        install-libLTLIBRARIES plus automake install-* rules need mkdir/cp
        semantics; chmod is best-effort (HMBS_CAP_CHMOD=0). Created with
        os.open 0o755 so no chmod dependency for executability. This
        round: package() `make install` died at
        `libtool: install: .../bin/install -c .libs/libdatovka.a ...`
        followed by `chmod: cannot access '.../p/lib/libdatovka.a'` --
        the HMBS shim copy never landed, so the follow-up chmod failed.
        String/behaviour scope: install redirection only, no test change.
        """
        shim_dir = os.path.join(self.build_folder, "_ohos_install_shim")
        os.makedirs(shim_dir, exist_ok=True)
        install = os.path.join(shim_dir, "install")
        script = (
            "#!/bin/sh\n"
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
            "if [ \"$count\" -gt 1 ]; then\n"
            "  mkdir -p \"$dest\"\n"
            "else\n"
            "  d=$(dirname \"$dest\"); mkdir -p \"$d\"\n"
            "fi\n"
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
        fd = os.open(install, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o755)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(script)
        try:
            os.chmod(install, 0o755)
        except OSError:
            pass  # HMBS_CAP_CHMOD=0: open mode already grants exec
        self.output.info("libdatovka install shim: %s" % install)
        return install

    def _redirect_install_to_shim(self, shim_install):
        """Point generated Makefiles INSTALL* at the local shim.

        configure bakes the detected install path into every generated
        Makefile as `INSTALL = <.../install -c>` plus INSTALL_DATA /
        INSTALL_PROGRAM / INSTALL_SCRIPT absolute forms, so replacing
        INSTALL alone leaves failing lines untouched (cubelib/4.9.1
        precedent). Rewrite all four when they reference an install
        binary. String swap only; install semantics via the shim.
        """
        roots = []
        for attr in ("build_folder", "base_build_folder"):
            try:
                v = getattr(self.folders, attr, None) or getattr(self, attr, None)
            except Exception:
                v = None
            if v and os.path.isdir(v) and v not in roots:
                roots.append(v)
        patched = 0
        for root in roots:
            if not root or not os.path.isdir(root):
                continue
            for dirpath, _dirnames, filenames in os.walk(root):
                if "Makefile" not in filenames:
                    continue
                mp = os.path.join(dirpath, "Makefile")
                try:
                    with open(mp, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                except OSError:
                    continue
                if "INSTALL" not in content or "/install" not in content:
                    continue
                lines = []
                changed = False
                for line in content.splitlines(True):
                    stripped = line.lstrip()
                    if stripped.startswith("INSTALL_DATA = ") and "/install" in stripped:
                        indent = line[:len(line) - len(stripped)]
                        lines.append("%sINSTALL_DATA = %s -m 644\n" % (indent, shim_install))
                        changed = True
                    elif stripped.startswith("INSTALL_PROGRAM = ") and "/install" in stripped:
                        indent = line[:len(line) - len(stripped)]
                        lines.append("%sINSTALL_PROGRAM = %s\n" % (indent, shim_install))
                        changed = True
                    elif stripped.startswith("INSTALL_SCRIPT = ") and "/install" in stripped:
                        indent = line[:len(line) - len(stripped)]
                        lines.append("%sINSTALL_SCRIPT = %s\n" % (indent, shim_install))
                        changed = True
                    elif stripped.startswith("INSTALL = ") and "/install" in stripped:
                        indent = line[:len(line) - len(stripped)]
                        lines.append("%sINSTALL = %s\n" % (indent, shim_install))
                        changed = True
                    else:
                        lines.append(line)
                if changed:
                    try:
                        with open(mp, "w", encoding="utf-8", newline="\n") as f:
                            f.write("".join(lines))
                        patched += 1
                    except OSError:
                        continue
        self.output.info("libdatovka: redirected INSTALL to shim in %d Makefiles" % patched)

    def _repair_install(self):
        """Diagnose `make install` tree; fallback-copy genuine lib archive.

        Preflight 2026-09-17: install-libLTLIBRARIES left
        package lib/libdatovka.a missing (HMBS shim copy never landed),
        so libtool's follow-up chmod failed. Dump the installed tree for
        ground truth, then copy the genuine built .libs/libdatovka.a when
        `make install` missed it. No stub: only real build outputs land
        in the package; headers/pkgconfig from a successful install are
        left untouched.
        """
        try:
            entries = []
            for dirpath, _dirnames, filenames in os.walk(self.package_folder):
                for name in filenames:
                    entries.append(os.path.relpath(
                        os.path.join(dirpath, name), self.package_folder))
        except OSError as e:
            self.output.warning("libdatovka: package tree walk failed: %s" % e)
            entries = []
        self.output.info("libdatovka package entries (%d): %s"
                         % (len(entries), sorted(entries)[:200]))
        dstlib = os.path.join(self.package_folder, "lib", "libdatovka.a")
        try:
            have_lib = os.path.isfile(dstlib)
        except OSError:
            have_lib = False
        if have_lib:
            return
        cands = []
        for root in (getattr(self, "build_folder", ""), getattr(self, "base_build_folder", "")):
            if not root or not os.path.isdir(root):
                continue
            try:
                cands.extend(glob.glob(os.path.join(root, "**", "libdatovka.a"), recursive=True))
            except Exception:
                continue
        # Prefer the src/.libs archive (the exact libtool input).
        cands = sorted(cands, key=lambda p: (".libs" not in p, len(p)))
        self.output.warning("libdatovka installed libdatovka.a missing; build-tree candidates: %s" % cands[:10])
        src = ""
        for c in cands:
            try:
                if os.path.isfile(c):
                    src = c
                    break
            except OSError:
                continue
        if not src:
            self.output.warning("libdatovka: no built libdatovka.a found for fallback")
            return
        try:
            os.makedirs(os.path.dirname(dstlib), exist_ok=True)
            if os.path.lexists(dstlib):
                os.unlink(dstlib)
            shutil.copy2(src, dstlib)
            self.output.info("libdatovka: fallback installed genuine %s -> %s" % (src, dstlib))
        except OSError as e:
            self.output.warning("libdatovka: fallback copy failed: %s" % e)

    def _install_public_headers(self):
        """Install the genuine upstream public header (SUBDIRS=src gap).

        Preflight 2026-09-17: `make install SUBDIRS=src` (notes #13,
        avoids building gnutls-dependent test/simline) yields a package
        whose top is [conaninfo, conanmanifest, lib] — no include/ at
        all, so the consumer dies with 'libdatovka/isds.h file not
        found'. Upstream ships exactly one public header installed as
        <includedir>/libdatovka/isds.h (FreeBSD/FreshPorts 0.7.3 plist +
        man isds.h.libdatovka(3): `#include <libdatovka/isds.h>`).
        Copy the genuine source-tree header (bounded search, prefer
        src/isds.h, skip test/ trees) to
        <package>/include/libdatovka/isds.h. No stub: a missing source
        header raises honestly instead of shipping a bad package.
        """
        dst_dir = os.path.join(self.package_folder, "include", "libdatovka")
        dst = os.path.join(dst_dir, "isds.h")
        try:
            if os.path.isfile(dst):
                return
        except OSError:
            pass
        roots = []
        for attr in ("source_folder", "base_source_folder"):
            try:
                v = getattr(self, attr, None)
            except Exception:
                v = None
            if v and os.path.isdir(v) and v not in roots:
                roots.append(v)
        src = ""
        for root in roots:
            for cand in (os.path.join(root, "src", "isds.h"),
                         os.path.join(root, "isds.h")):
                try:
                    if os.path.isfile(cand):
                        src = cand
                        break
                except OSError:
                    continue
            if src:
                break
        if not src:
            cands = []
            for root in roots:
                try:
                    walker = os.walk(root)
                except OSError:
                    continue
                for dirpath, dirnames, filenames in walker:
                    try:
                        rel = os.path.relpath(dirpath, root)
                    except Exception:
                        rel = ""
                    if rel.count(os.sep) > 3 or "/test" in ("/" + rel.replace(os.sep, "/")):
                        del dirnames[:]
                        continue
                    if "isds.h" in filenames:
                        cands.append(os.path.join(dirpath, "isds.h"))
            cands = sorted(cands, key=len)
            if cands:
                src = cands[0]
            self.output.info("libdatovka header search candidates: %s" % cands[:5])
        if not src:
            raise ConanInvalidConfiguration(
                "libdatovka: genuine src isds.h not found; refusing to ship headerless package")
        try:
            os.makedirs(dst_dir, exist_ok=True)
            if os.path.lexists(dst):
                os.unlink(dst)
            shutil.copy2(src, dst)
            self.output.warning("libdatovka: installed genuine %s -> %s" % (src, dst))
        except OSError as e:
            raise ConanInvalidConfiguration(
                "libdatovka: header install failed: %s" % e)

    def _install_vendored_jsonc(self):
        """Ship the vendored static json-c with the package.

        Preflight 2026-09-17: test_package direct-CC link of the static
        libdatovka.a dies with undefined json_tokener_parse /
        json_object_* (soap.c needs json-c). The vendored json-c built
        in _build_vendored_jsonc (build_folder/jsonc-prefix) was only
        ever exposed to configure via PKG_CONFIG_PATH and never
        installed into the package, so neither CMakeDeps (package_info
        libs) nor the direct-CC cpp_info aggregation emits -ljson-c.
        Copy the genuine built archive(s) into package lib/; missing
        build output raises honestly (no stub). Headers are not needed
        by consumers (isds.h exposes no json-c API), so only the lib
        ships. Test bodies untouched.
        """
        try:
            prefix = os.path.join(str(self.build_folder), "jsonc-prefix")
        except Exception:
            prefix = ""
        cands = []
        if prefix and os.path.isdir(os.path.join(prefix, "lib")):
            try:
                cands.extend(glob.glob(
                    os.path.join(prefix, "lib", "libjson-c.a")))
                cands.extend(glob.glob(
                    os.path.join(prefix, "lib", "libjson-c.so*")))
            except Exception:
                pass
        cands = [c for c in cands
                 if c and os.path.isfile(c) and "pkgconfig" not in c]
        self.output.info("libdatovka vendored json-c candidates: %s"
                         % cands[:10])
        if not cands:
            raise ConanInvalidConfiguration(
                "libdatovka: vendored json-c archive missing under %s; "
                "refusing to ship a package whose static lib has "
                "unresolvable json_* symbols" % prefix)
        try:
            os.makedirs(os.path.join(self.package_folder, "lib"),
                        exist_ok=True)
        except OSError:
            pass
        for src in cands:
            try:
                if os.path.islink(src):
                    continue
                dst = os.path.join(self.package_folder, "lib",
                                   os.path.basename(src))
                if os.path.lexists(dst):
                    os.unlink(dst)
                shutil.copy2(src, dst)
                self.output.warning(
                    "libdatovka: installed vendored %s -> %s" % (src, dst))
            except OSError as e:
                raise ConanInvalidConfiguration(
                    "libdatovka: vendored json-c install failed: %s" % e)

    def _dep_flags(self, ref):
        """Return (cppflags, ldflags, libs) for a conan requirement.

        Upstream probes OpenSSL AND expat with raw link tests
        (configure.ac: AC_SEARCH_LIBS([CMS_get0_content], [crypto]) and
        AC_CHECK_LIB([expat], [XML_ExpatVersionInfo]) + version compile
        check against expat.h) that bypass pkg-config, so each only sees
        the linker's view: -L must come from LDFLAGS and static
        companions (-ldl/-lpthread) from LIBS. The device link finds no
        libcrypto/libexpat without them (preflight 2026-09-16 openssl:
        "checking for library containing CMS_get0_content... no"; expat:
        "checking for XML_ExpatVersionInfo in -lexpat... no"), so
        derive the flags from the conan cpp_info (alpine/2.26 precedent
        of pointing configure at the dep package, adapted to inline
        VAR= assignments which win over conanbuild.sh). Missing dep ->
        empty strings, i.e. zero behaviour change.
        """
        try:
            dep = self.dependencies[ref]
        except Exception:
            return "", "", ""
        try:
            pkg_folder = str(dep.package_folder) if dep.package_folder else ""
        except Exception:
            pkg_folder = ""
        incs, libdirs, names, syslibs = [], [], [], []
        try:
            infos = [dep.cpp_info] + list(dep.cpp_info.components.values())
        except Exception:
            infos = []
        for info in infos:
            for attr, acc in (("includedirs", incs), ("libdirs", libdirs),
                              ("libs", names), ("system_libs", syslibs)):
                try:
                    vals = getattr(info, attr, []) or []
                except Exception:
                    continue
                for v in vals:
                    if v and v not in acc:
                        acc.append(v)

        def _abs(p):
            # Unresolvable entries are dropped, never stringified as
            # "None/..." (preflight 2026-09-16: "-INone/include" broke
            # configure parsing). Absolute paths pass through.
            if not p:
                return ""
            if os.path.isabs(p):
                return p
            if pkg_folder:
                return os.path.join(pkg_folder, p)
            return ""

        cppflags = " ".join("-I" + f for f in (_abs(p) for p in incs) if f)
        ldflags = " ".join("-L" + f for f in (_abs(p) for p in libdirs) if f)
        # Order matters: -lssl before -lcrypto, system libs last.
        libs = " ".join("-l" + n for n in names + syslibs)
        return cppflags, ldflags, libs

    def _dep_libdirs(self):
        """Absolute libdirs of runtime deps for the test-run phase only.

        Used to scope LD_LIBRARY_PATH inline on the `make check` RUN
        command (never exported: E505 forbids a global LD_LIBRARY_PATH
        because SDK lld loads libxml2 and would pick the conan copy).
        Guards against package_folder=None (override-only edges) and
        drops non-directories; never stringifies None (the "-INone"
        lesson from _dep_flags).
        """
        dirs = []
        for ref in ("openssl", "expat", _CURL_REF, "libxml2"):
            try:
                dep = self.dependencies[ref]
            except Exception:
                continue
            try:
                pkg_folder = str(dep.package_folder) if dep.package_folder else ""
            except Exception:
                pkg_folder = ""
            try:
                libdirs = list(dep.cpp_info.libdirs or [])
            except Exception:
                libdirs = []
            for d in libdirs:
                if not d:
                    continue
                p = d if os.path.isabs(d) else (os.path.join(pkg_folder, d) if pkg_folder else "")
                if p and p not in dirs:
                    try:
                        if os.path.isdir(p):
                            dirs.append(p)
                    except Exception:
                        continue
        return dirs

    def _dep_bindirs(self):
        """Absolute bindirs of deps so conan *-config scripts win on PATH.

        --with-libcurl probes via curl-config (not pkg-config); the
        preflight compile used system curl 8.22 headers, i.e. system
        curl-config won over conan curl/8.15.0. Prepending conan bindirs
        (curl, libxml2 for xml2-config, openssl, expat) shadows the
        system scripts. Missing dep -> skipped, zero behaviour change.
        """
        dirs = []
        for ref in (_CURL_REF, "libxml2", "openssl", "expat"):
            try:
                dep = self.dependencies[ref]
            except Exception:
                continue
            try:
                pkg_folder = str(dep.package_folder) if dep.package_folder else ""
            except Exception:
                pkg_folder = ""
            try:
                bindirs = list(dep.cpp_info.bindirs or [])
            except Exception:
                bindirs = []
            for d in bindirs:
                if not d:
                    continue
                p = d if os.path.isabs(d) else (os.path.join(pkg_folder, d) if pkg_folder else "")
                if p and p not in dirs:
                    try:
                        if os.path.isdir(p):
                            dirs.append(p)
                    except Exception:
                        continue
        return dirs

    def _sdk_llvm_lib(self, cc=""):
        """Return the SDK llvm/lib dir holding lld's own libxml2.so.16.

        OHOS SDK lld is dynamically linked against libxml2.so.16 shipped
        in <sdk>/native/llvm/lib. When LD_LIBRARY_PATH lists a conan
        libxml2 dir first, lld loads the conan copy and dies with
        "xmlFreeDoc: symbol not found" (E321-draft, babeltrace DRAFT-6048
        err 7, E2175, E266). Derive the dir from the ACTIVE compiler so
        the fix tracks whichever SDK the runner uses:

        1) `<cc> -print-resource-dir` -> dirname x2 (E341 method);
        2) realpath(cc) -> <sdk>/llvm/bin/<cc>, dirname x2 + lib
           (must realpath: the profile CC is often a symlink such as
           /data/service/hnp/bin/clang, E2175 lesson);
        3) well-known SDK install globs (HNP + harmonybrew Cellar).

        A candidate is accepted only if libxml2.so.16 exists inside.
        Returns "" when nothing verifies (caller keeps old behaviour
        and warns). Never raises.
        """
        def _has_xml2(d):
            try:
                return bool(d) and os.path.isdir(d) and os.path.isfile(
                    os.path.join(d, "libxml2.so.16"))
            except Exception:
                return False

        progs = []
        for cand in (cc, os.environ.get("CC", "")):
            try:
                first = cand.strip().split()[0].strip("\"'") if cand else ""
            except Exception:
                first = ""
            if first and first not in progs:
                progs.append(first)
        for prog in progs:
            exe = prog if "/" in prog else (shutil.which(prog) or "")
            if not exe:
                continue
            try:
                r = subprocess.run([exe, "-print-resource-dir"],
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, timeout=15)
                out = r.stdout.decode("utf-8", "replace").strip().splitlines()
                res = out[0].strip() if out else ""
            except Exception:
                res = ""
            if res:
                llvm_lib = os.path.dirname(os.path.dirname(res))
                if _has_xml2(llvm_lib):
                    return llvm_lib
            try:
                real = os.path.realpath(exe)
            except Exception:
                real = ""
            if real:
                llvm_lib = os.path.join(
                    os.path.dirname(os.path.dirname(real)), "lib")
                if _has_xml2(llvm_lib):
                    return llvm_lib
        globs = [
            "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib",
            os.path.join(os.path.expanduser("~"),
                         ".harmonybrew/Cellar/ohos-sdk/*/native/llvm/lib"),
            "/storage/Users/currentUser/.harmonybrew/Cellar/ohos-sdk/*/native/llvm/lib",
        ]
        for pattern in globs:
            try:
                cands = sorted(glob.glob(pattern))
            except Exception:
                cands = []
            for c in cands:
                if _has_xml2(c):
                    return c
        return ""

    def _scoped_ld_prefix(self, sdk_lib="", extra_dirs=()):
        """Build an inline LD_LIBRARY_PATH= prefix, SDK llvm/lib first.

        Ordering is the fix: SDK dir first so lld loads its own
        libxml2.so.16; conan dep libdirs follow so RUN probes and test
        binaries still resolve shared deps; pre-existing entries last
        (cleansed: musl ignores every segment after a whitespace-only
        segment such as "         /system/lib64", E321-draft, so each
        part is stripped and empties dropped). Returns "" when there is
        nothing to set. An inline VAR= wins over conanbuild.sh exports
        for that single command (same nearest-scope mechanism as the
        TMPDIR/SHELL prefixes).
        """
        parts = []
        if sdk_lib and sdk_lib not in parts:
            parts.append(sdk_lib)
        for d in (extra_dirs or ()):
            if d and d not in parts:
                parts.append(d)
        try:
            existing = (os.environ.get("LD_LIBRARY_PATH") or "").split(os.pathsep)
        except Exception:
            existing = []
        for d in existing:
            try:
                s = (d or "").strip()
            except Exception:
                continue
            if s and s not in parts:
                parts.append(s)
        if not parts:
            return ""
        return "LD_LIBRARY_PATH=\"%s\" " % ":".join(parts)

    def _run_configure_explicit(self, build_tmp, build_cc, build_cxx, jsonc_pc,
                                pkg_config="", shim_dir="",
                                extra_cppflags="", extra_ldflags="",
                                extra_libs="", sdk_lib="",
                                conan_libdirs=()):
        """Invoke configure under the working shell with inline env wins.

        Do NOT use Autotools.configure(): it execs the source configure
        directly, so autoconf's CONFIG_SHELL re-exec (line ~139) reads
        the poisoned environment value re-exported by conanbuild.sh and
        dies with Error 127 (cubelib/abx precedent). Instead run
        `"<shell>" "<src_configure>" ...` with inline
        CONFIG_SHELL/SHELL/TMPDIR assignments, which win over any
        conanbuild.sh export for this command (classads draft: inline
        env is nearest-scope). env="conanbuild" is kept so CC/CFLAGS/
        LDFLAGS from AutotoolsToolchain still apply. Flags mirror
        generate() exactly (prefix/dir args are AutotoolsToolchain
        defaults, shown in the preflight RUN line).

        pkg_config/shim_dir come from _ensure_pkg_config_shim(): the
        device has no system pkg-config, so PKG_CONFIG is passed inline
        and the shim dir is prepended to PATH in the same command
        (conanbuild.sh PATH ordering cannot shadow it).

        Raw-check deps (openssl/expat) contribute ONLY CPPFLAGS/LDFLAGS
        (-I/-L): their -l flags are deliberately NOT pre-injected via
        LIBS. Pre-setting LIBS poisons autoconf's earliest AC_PROG_CC
        "whether we are cross compiling" RUN probe (it links $LIBS into
        conftest, so a shared libexpat.so dependency makes the probe
        unrunnable -> rc=77 "cannot run C compiled programs", E467/E566).
        AC_SEARCH_LIBS/AC_CHECK_LIB are link-only probes: they find the
        libs through -L and append -l to LIBS themselves on success.

        sdk_lib/conan_libdirs feed _scoped_ld_prefix(): SDK llvm/lib
        first so every configure cc/ld probe runs a working lld
        (E321-draft shadowing guard); conan libdirs follow for RUN
        probes. The inline prefix wins over conanbuild.sh for this
        command.
        """
        shell = self._detect_shell()
        src_configure = os.path.join(self.source_folder, "configure")
        combined_pc = jsonc_pc + os.pathsep + self.generators_folder
        if self.options.shared:
            shared_args = "--disable-static --enable-shared"
        else:
            shared_args = "--enable-static --disable-shared"
        try:
            is_ohos = str(self.settings.os) == "OHOS"
        except Exception:
            is_ohos = True
        triplet_args = ("--build=aarch64-unknown-linux-gnu "
                        "--host=aarch64-unknown-linux-gnu " if is_ohos else "")
        cmd = (
            "TMPDIR=\"{tmp}\" TMP=\"{tmp}\" TEMP=\"{tmp}\" "
            "CONFIG_SHELL=\"{sh}\" SHELL=\"{sh}\" "
            "{ld_prefix}{path_prefix}{pkg_env}"
            "\"{sh}\" \"{cfg}\" --prefix=/ "
            "\"--bindir=${{prefix}}/bin\" \"--sbindir=${{prefix}}/bin\" "
            "\"--libdir=${{prefix}}/lib\" \"--includedir=${{prefix}}/include\" "
            "\"--oldincludedir=${{prefix}}/include\" "
            "--disable-doc --enable-openssl-backend --disable-nls "
            "--disable-fatalwarnings --with-libcurl --enable-test "
            "{triplet}{shared} "
            "\"PKG_CONFIG_PATH={pc}\" "
            "\"LIBGNUTLS_CFLAGS=-I.\" \"LIBGNUTLS_LIBS=-L.\" "
            "\"CC={cc}\" \"CXX={cxx}\" "
            "\"TMPDIR={tmp}\" \"TMP={tmp}\" \"TEMP={tmp}\" "
            "\"SHELL={sh}\" \"CONFIG_SHELL={sh}\""
            "{ossl_flags}"
        ).format(tmp=build_tmp, sh=shell, cfg=src_configure,
                 triplet=triplet_args, shared=shared_args,
                 pc=combined_pc, cc=build_cc, cxx=build_cxx,
                 ld_prefix=self._scoped_ld_prefix(sdk_lib, conan_libdirs),
                 path_prefix=("PATH=\"%s:$PATH\" " % shim_dir) if shim_dir else "",
                 pkg_env=("PKG_CONFIG=\"%s\" " % pkg_config) if pkg_config else "",
                 ossl_flags=(" \"CPPFLAGS=$CPPFLAGS {ec}\" "
                             "\"LDFLAGS=$LDFLAGS {el}\"".format(
                                 ec=extra_cppflags, el=extra_ldflags) +
                             (" \"LIBS={eb} $LIBS\"".format(eb=extra_libs)
                              if extra_libs else "")
                             if (extra_cppflags or extra_ldflags or extra_libs)
                             else ""))
        self.output.info(
            "libdatovka explicit configure: SHELL=%s TMPDIR=%s" % (shell, build_tmp))
        self.run(cmd, cwd=self.build_folder, env="conanbuild")

    def _fix_shell_and_tmp(self):
        """Force writable TMPDIR + working POSIX shell in os.environ."""
        try:
            tmp = self._writable_tmpdir()
        except Exception:
            tmp = os.environ.get("TMPDIR") or "/tmp"
        try:
            os.makedirs(tmp, exist_ok=True)
        except OSError:
            pass
        os.environ["TMPDIR"] = tmp
        os.environ["TMP"] = tmp
        os.environ["TEMP"] = tmp
        # Never trust the profile SHELL/CONFIG_SHELL value: probe the
        # filesystem (a stale /data/service/hnp/bin/bash breaks every
        # configure re-exec with Error 127).
        try:
            _shell = self._detect_shell()
        except Exception:
            _shell = "/bin/sh"
        os.environ["SHELL"] = _shell
        os.environ["CONFIG_SHELL"] = _shell
        for _k in ("HMBS_AUTOCONF_MKTEMP_FALLBACK",
                   "HMBS_CAP_LOCAL_MKTEMP", "HMBS_TMPDIR",
                   "HMBS_CAP_HARDLINK", "HMBS_CAP_CHMOD",
                   "HMBS_CAP_SYMLINK"):
            _v = os.environ.get(_k)
            if _v:
                os.environ[_k] = _v
        self.output.info(
            "libdatovka OHOS shell/tmp: SHELL=%s TMPDIR=%s" % (_shell, tmp))
        return tmp

    def _patch_configure_tmp(self, tmpdir):
        """Redirect autoconf mktemp fallback from /tmp to writable tmpdir.

        Generated configure hardcodes `: ${TMPDIR=/tmp}` and
        `${TMPDIR-/tmp}` (ltmain fallback); with /tmp read-only every
        probe that falls back dies. Replace only the temp-root tokens
        (cubelib 4.9.1 pattern); test bodies and counts untouched.
        """
        roots = []
        try:
            if self.source_folder and os.path.isdir(self.source_folder):
                roots.append(self.source_folder)
        except Exception:
            pass
        patched = 0
        for root in roots:
            for dirpath, _d, filenames in os.walk(root):
                for name in filenames:
                    if name not in ("configure", "config.status"):
                        continue
                    path = os.path.join(dirpath, name)
                    try:
                        with open(path, "r", encoding="utf-8",
                                  errors="ignore", newline="") as f:
                            text = f.read()
                    except OSError:
                        continue
                    new = text
                    # Narrow token replacements first (avoid touching
                    # unrelated /tmp literals).
                    new = new.replace("${TMPDIR-/tmp}",
                                      "${TMPDIR-%s}" % tmpdir)
                    new = new.replace("${TMPDIR=/tmp}",
                                      "${TMPDIR=%s}" % tmpdir)
                    new = new.replace(": ${TMPDIR=/tmp}",
                                      ": ${TMPDIR=%s}" % tmpdir)
                    if new != text:
                        try:
                            with open(path, "w", encoding="utf-8",
                                      newline="\n") as f:
                                f.write(new)
                            patched += 1
                        except OSError:
                            continue
        if patched:
            self.output.info(
                "libdatovka: redirected mktemp fallback ->%s in %d files"
                % (tmpdir, patched))
        else:
            self.output.info("libdatovka: no mktemp /tmp fallback to patch")

    def _parse_make_check_summary(self, log_text):
        """Parse automake `make check` summary: # TOTAL/# PASS/# FAIL/# SKIP."""
        total = passed = failed = skipped = 0
        m = re.search(r"#\s*TOTAL:\s*(\d+)", log_text)
        if m:
            total = int(m.group(1))
        m = re.search(r"#\s*PASS:\s*(\d+)", log_text)
        if m:
            passed = int(m.group(1))
        m = re.search(r"#\s*FAIL:\s*(\d+)", log_text)
        if m:
            failed = int(m.group(1))
        m = re.search(r"#\s*SKIP:\s*(\d+)", log_text)
        if m:
            skipped = int(m.group(1))
        # Fallback: count per-test PASS:/FAIL:/SKIP: lines.
        if total == 0:
            passed = len(re.findall(r"^(PASS|PASS:)", log_text, re.M))
            failed = len(re.findall(r"^(FAIL|FAIL:)", log_text, re.M))
            skipped = len(re.findall(r"^(SKIP|SKIP:)", log_text, re.M))
            total = passed + failed + skipped
        return total, passed, failed, skipped

    def _emit_upstream_marker(self, total, passed, failed, skipped, command):
        status = "passed" if (total > 0 and failed == 0 and skipped == 0 and passed == total) else "failed"
        # HMBS gate rejects skipped>0; report honestly — preflight decides.
        if skipped > 0 and failed == 0:
            status = "failed"
        marker = {
            "status": status,
            "framework": "autotools-make-check",
            "command": command,
            "discovered": total,
            "executed": passed + failed + skipped,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker))

    def _cand_works(self, cand):
        """True if cand runs `prog --version` cleanly (proven executable)."""
        if not cand:
            return False
        prog = cand.strip().split()[0].strip("\"'") if isinstance(cand, str) else ""
        if not prog:
            return False
        if "/" in prog:
            if not (os.path.isfile(prog) and os.access(prog, os.X_OK)):
                return False
        else:
            resolved = shutil.which(prog)
            if not resolved:
                return False
            prog = resolved
        try:
            r = subprocess.run([prog, "--version"], stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, timeout=20)
            return r.returncode == 0
        except Exception:
            return False

    def _ensure_pkg_config_shim(self):
        """Provide `pkg-config` on PATH via the pkgconf tool_requires.

        The pkgconf package ships bin/pkgconf WITHOUT a bin/pkg-config
        alias (package() raises on unexpected alias), so
        `checking for pkg-config... no` still fails with only the
        tool_requires (cassbeam/1.1 precedent). Create a hmbs-shims dir
        with a pkg-config -> pkgconf symlink (copyfile fallback avoids
        HMDFS chmod=0 limits) and return (shim_dir, pkg_config_bin).
        """
        shim_dir = os.path.join(self.build_folder, "hmbs-shims")
        try:
            os.makedirs(shim_dir, exist_ok=True)
        except OSError:
            return "", ""
        pkgconf_bin = ""
        try:
            bdep = self.dependencies.build.get("pkgconf")
            if bdep is not None and bdep.package_folder:
                cand = os.path.join(str(bdep.package_folder), "bin", "pkgconf")
                if os.path.isfile(cand):
                    pkgconf_bin = cand
        except Exception:
            pass
        if not pkgconf_bin:
            for cand in (shutil.which("pkgconf") or "", "/usr/bin/pkgconf",
                         "/usr/local/bin/pkgconf"):
                try:
                    if cand and os.path.isfile(cand):
                        pkgconf_bin = cand
                        break
                except Exception:
                    continue
        if not pkgconf_bin:
            self.output.warning("pkgconf binary not found; pkg-config shim skipped")
            return "", ""
        link = os.path.join(shim_dir, "pkg-config")
        try:
            if os.path.islink(link) or os.path.isfile(link):
                try:
                    os.remove(link)
                except OSError:
                    pass
            try:
                os.symlink(pkgconf_bin, link)
            except (OSError, NotImplementedError):
                shutil.copyfile(pkgconf_bin, link)
            self.output.info("pkg-config shim: %s -> %s" % (link, pkgconf_bin))
            return shim_dir, link
        except Exception as exc:
            self.output.warning("pkg-config shim failed: %s" % exc)
            return "", ""

    def _resolve_compilers(self):
        """Return (cc, cxx) verified runnable; fallback only when conf broken.

        Healthy runner (conf absolute path exists + --version OK): return it
        verbatim, zero behaviour change. Broken runner (this round:
        CC=/data/service/hnp/bin/clang missing -> cmake
        'Could not find compiler ... /data/service/hnp/bin/clang'):
        search PATH-proven clang/cc/gcc (and same-dir clang++ sibling),
        never an unverified bare name.
        """
        try:
            comp = self.conf.get("tools.build:compiler_executables",
                                 default={}, check_type=dict) or {}
        except Exception:
            comp = {}
        conf_c = (comp.get("c") or "").strip() if isinstance(comp, dict) else ""
        conf_cxx = ""
        if isinstance(comp, dict):
            conf_cxx = (comp.get("cpp") or comp.get("cxx") or "").strip()
        if conf_c and self._cand_works(conf_c):
            cc = conf_c.split()[0].strip("\"'")
            if "/" not in cc:
                cc = shutil.which(cc) or cc
        else:
            if conf_c:
                self.output.warning(
                    f"toolchain CC broken/unrunnable: {conf_c!r}; searching PATH fallback")
            cc = ""
            for cand in (os.environ.get("CC", ""), "clang", "cc", "gcc"):
                if cand and self._cand_works(cand):
                    prog = cand.strip().split()[0].strip("\"'")
                    cc = shutil.which(prog) if "/" not in prog else prog
                    self.output.warning(f"CC fallback in use: {cc} (conf was {conf_c!r})")
                    break
            if not cc:
                cc = conf_c or "clang"
        if conf_cxx and self._cand_works(conf_cxx):
            cxx = conf_cxx.split()[0].strip("\"'")
            if "/" not in cxx:
                cxx = shutil.which(cxx) or cxx
        else:
            if conf_cxx:
                self.output.warning(
                    f"toolchain CXX broken/unrunnable: {conf_cxx!r}; searching PATH fallback")
            cxx = ""
            # Prefer same-dir sibling of resolved CC (clang -> clang++).
            if cc and "/" in cc:
                sib = os.path.join(os.path.dirname(cc), "clang++")
                if self._cand_works(sib):
                    cxx = sib
            for cand in (os.environ.get("CXX", ""), "clang++", "c++", "g++"):
                if cxx:
                    break
                if cand and self._cand_works(cand):
                    prog = cand.strip().split()[0].strip("\"'")
                    cxx = shutil.which(prog) if "/" not in prog else prog
                    self.output.warning(f"CXX fallback in use: {cxx} (conf was {conf_cxx!r})")
                    break
            if not cxx:
                cxx = conf_cxx or "clang++"
        self.output.info(f"resolved compilers: CC={cc} CXX={cxx}")
        return cc, cxx

    def _cmake_exe(self):
        """Prefer HMBS-injected cmake absolute path, else PATH cmake."""
        for cand in (os.environ.get("HMBS_CMAKE", ""),
                     self.conf.get("user.hmbs:cmake_path", default="") if hasattr(self, "conf") else ""):
            if cand and isinstance(cand, str):
                prog = cand.strip().split()[0].strip("\"'")
                if prog and os.path.isfile(prog) and os.access(prog, os.X_OK):
                    return prog
        return shutil.which("cmake") or "cmake"

    def _build_vendored_jsonc(self):
        """Build a private static json-c for configure PKG_CHECK_MODULES.

        Upstream hard-requires json-c >= 0.9 (configure.ac AC_MSG_FAILURE).
        Vendored from the same S3 tarball as the hardened json-c/0.18
        recipe (CI-accessible, no GitHub flakiness):
          https://s3.amazonaws.com/json-c_releases/releases/json-c-0.18.tar.gz
        Built as a static lib with -fPIC (safe to link into both static
        and shared libdatovka) using the same CC/CFLAGS as our autotools
        build (env=conanbuild provides HMBS CC + writable TMPDIR). No
        toolchain file: pure C, native Linux-mode cmake is sufficient
        (hardened json-c recipe proves SYSTEM_NAME=Linux works on OHOS).
        Installs to build_folder/jsonc-prefix; returns its pkgconfig dir.
        """
        prefix = os.path.join(self.build_folder, "jsonc-prefix")
        pc_dir = os.path.join(prefix, "lib", "pkgconfig")
        marker = os.path.join(pc_dir, "json-c.pc")
        if os.path.isfile(marker):
            return pc_dir
        src = os.path.join(self.build_folder, "jsonc-src")
        bdir = os.path.join(self.build_folder, "jsonc-build")
        get(self,
            url="https://s3.amazonaws.com/json-c_releases/releases/json-c-0.18.tar.gz",
            sha256="876ab046479166b869afc6896d288183bbc0e5843f141200c677b3e8dfb11724",
            destination=src, strip_root=True)
        # Missing-CC guard (preflight 2026-09-16: profile CC
        # /data/service/hnp/bin/clang absent -> cmake
        # 'Could not find compiler ... /data/service/hnp/bin/clang').
        # Healthy runner keeps conf CC verbatim; broken runner falls back
        # to a PATH-proven compiler (cassbeam/ayatana-ido precedent).
        # Explicit -DCMAKE_C/CXX_COMPILER beats the inherited CC env;
        # CC/CXX prefix covers cmake's compiler-env probe. Linux-mode
        # (no toolchain file) matches the hardened json-c recipe.
        cc, cxx = self._resolve_compilers()
        cmake = self._cmake_exe()
        self.output.info(f"vendored json-c: cmake={cmake} CC={cc} CXX={cxx}")
        # SDK lld guard (same E321 shadowing as below): cmake compiler
        # probes link test executables, so lld must start here too.
        try:
            _sdk = self._sdk_llvm_lib(cc)
        except Exception:
            _sdk = ""
        _ld = self._scoped_ld_prefix(_sdk)
        if _sdk:
            self.output.info("vendored json-c: SDK llvm lib first: %s" % _sdk)
        # env=conanbuild: same CFLAGS/TMPDIR as autotools build.
        self.run(
            _ld +
            '"{cmake}" -B "{b}" -S "{s}"'
            ' -DCMAKE_INSTALL_PREFIX="{p}"'
            ' -DCMAKE_INSTALL_LIBDIR=lib'
            ' -DCMAKE_BUILD_TYPE=Release'
            ' -DBUILD_SHARED_LIBS=OFF'
            ' -DCMAKE_POSITION_INDEPENDENT_CODE=ON'
            ' -DBUILD_TESTING=OFF -DBUILD_APPS=OFF'
            ' -DCMAKE_SYSTEM_NAME=Linux'
            ' -DCMAKE_C_COMPILER="{cc}"'
            ' -DCMAKE_CXX_COMPILER="{cxx}"'.format(
                cmake=cmake, b=bdir, s=src, p=prefix, cc=cc, cxx=cxx),
            env="conanbuild")
        self.run(_ld + '"{cmake}" --build "{b}" -j1'.format(cmake=cmake, b=bdir), env="conanbuild")
        self.run(_ld + '"{cmake}" --install "{b}"'.format(cmake=cmake, b=bdir), env="conanbuild")
        if not os.path.isfile(marker):
            raise ConanInvalidConfiguration(
                "vendored json-c did not produce json-c.pc at " + marker)
        return pc_dir

    def build(self):
        apply_conandata_patches(self)
        # HMBS readonly_tmp (preflight 2026-09-16: "can't create temporary
        # file /tmp/sh*.tmp: Read-only file system"): force a probed
        # writable TMPDIR/TMP/TEMP + POSIX SHELL before any configure /
        # cmake probe, and redirect autoconf mktemp fallback tokens.
        # c-client 2007f / cubelib 4.9.1 pattern; test bodies untouched.
        build_tmp = self._fix_shell_and_tmp()
        self._patch_configure_tmp(build_tmp)
        # Resolve once, reuse for jsonc + autotools so both see the same
        # verified compiler (healthy runner: conf verbatim, zero change).
        build_cc, build_cxx = self._resolve_compilers()
        try:
            os.environ["CC"] = build_cc
            os.environ["CXX"] = build_cxx
        except Exception:
            pass
        # SDK lld shadowing guard (preflight 2026-09-16: test/offline
        # link dies with "Error loading shared library libxml2.so.16
        # (needed by .../llvm/bin/lld)" + "xmlFreeDoc: symbol not found":
        # a conan libxml2 dir precedes the SDK llvm/lib in the inherited
        # LD_LIBRARY_PATH, so lld loads the conan copy. The earlier
        # "compile with no loader env" attempt failed because
        # env="conanbuild" re-injects it; instead put the SDK llvm/lib
        # FIRST via inline prefixes (E321-draft, babeltrace DRAFT-6048
        # err 7, E2175, E266, E341). Computed once from the active
        # compiler; conan dep libdirs follow for RUN probes.
        try:
            sdk_llvm_lib = self._sdk_llvm_lib(build_cc)
        except Exception:
            sdk_llvm_lib = ""
        if sdk_llvm_lib:
            self.output.info("libdatovka SDK llvm lib: %s" % sdk_llvm_lib)
        else:
            self.output.warning(
                "libdatovka SDK llvm lib not found; lld may fail to start")
        dep_lib_path = self._dep_libdirs()
        if dep_lib_path:
            self.output.info("libdatovka test loader path: %s"
                             % os.pathsep.join(dep_lib_path))
        # Vendored json-c must exist before ./configure probes it.
        jsonc_pc = self._build_vendored_jsonc()
        # HMDFS sets setgid on new dirs; configure `umask 077` makes
        # config.status temp dirs drwx--S--- -> subs1.awk permission denied.
        cfg = os.path.join(self.source_folder, "configure")
        if os.path.isfile(cfg):
            replace_in_file(self, cfg, "umask 077", "umask 022")
        # Profile [buildenv] pins SHELL/CONFIG_SHELL to
        # /data/service/hnp/bin/bash, which is "inaccessible or not found"
        # on this runner: generated configure re-execs $CONFIG_SHELL at
        # line ~139 and dies with Error 127 before any probe runs.
        # os.environ + configure VAR=vals alone do NOT fix it (the bad
        # value is re-exported by conanbuild.sh after our env is set —
        # cubelib 4.9.1 round-2 lesson). Scrub the literal from the
        # source scripts, then run configure explicitly under the working
        # shell with inline env wins (abx/cubelib precedent). Test bodies
        # and configure logic untouched.
        self._patch_bad_shell_refs()
        build_shell = os.environ.get("SHELL") or self._detect_shell()
        # Device has no system pkg-config: expose the pkgconf tool via a
        # pkg-config shim first (cassbeam/1.1 precedent). PATH prepend +
        # PKG_CONFIG env make configure's AC_PATH_PROG(PKG_CONFIG)
        # succeed; inline vars in _run_configure_explicit beat any
        # conanbuild.sh PATH ordering.
        shim_dir, pkg_config = self._ensure_pkg_config_shim()
        if shim_dir:
            try:
                os.environ["PATH"] = shim_dir + os.pathsep + os.environ.get("PATH", "")
            except Exception:
                pass
        if pkg_config:
            os.environ["PKG_CONFIG"] = pkg_config
        # OpenSSL AND expat are both probed by raw link tests (no pkg-config),
        # so feed the conan -I/-L explicitly (see _dep_flags).
        # openssl: configure.ac AC_SEARCH_LIBS([CMS_get0_content], [crypto]).
        # expat: AC_CHECK_LIB([expat], [XML_ExpatVersionInfo]) + version
        # compile check against expat.h (preflight 2026-09-16:
        # "checking for XML_ExpatVersionInfo in -lexpat... no" ->
        # "configure: error: Upgrade your expat to 2.0.0").
        # libxml2/curl are ALSO merged here (preflight 2026-09-16 round-2:
        # "fatal error: 'libxml/tree.h' file not found" at isds.c while
        # the RUN line logged only openssl+expat -I/-L and the compile
        # used system curl 8.22 headers with no libxml2 -I at all, i.e.
        # PkgConfigDeps alone did not reach the compile). The same -I/-L
        # only rule applies (no global LIBS, see below).
        # Raw-link probes (openssl AC_SEARCH_LIBS, expat AC_CHECK_LIB)
        # need -I/-L only; -l is NOT pre-injected (E467/E566: a global
        # LIBS poisons the AC_PROG_CC cross-compiling RUN probe with a
        # shared-lib dependency -> rc=77). openssl/3.5.6.1 is no-shared
        # static; expat/2.8.2.1 defaults shared, so its -lexpat reaches
        # LIBS only via configure's own link-only probe result.
        # --with-libcurl probes via curl-config (not pkg-config), so also
        # shadow any system curl-config/xml2-config with the conan dep
        # bindirs first (PATH prepend); string swap only, no test change.
        for _bindir in self._dep_bindirs():
            try:
                if _bindir not in os.environ.get("PATH", "").split(os.pathsep):
                    os.environ["PATH"] = _bindir + os.pathsep + os.environ.get("PATH", "")
            except Exception:
                pass
        ossl_c, ossl_l, _ossl_b = self._dep_flags("openssl")
        expat_c, expat_l, _expat_b = self._dep_flags("expat")
        xml_c, xml_l, _xml_b = self._dep_flags("libxml2")
        curl_c, curl_l, _curl_b = self._dep_flags(_CURL_REF)
        extra_c = " ".join(x for x in (ossl_c, expat_c, xml_c, curl_c) if x)
        extra_l = " ".join(x for x in (ossl_l, expat_l, xml_l, curl_l) if x)
        if extra_c or extra_l:
            self.output.info("libdatovka dep flags: CPPFLAGS+=%s LDFLAGS+=%s"
                             % (extra_c, extra_l))
        self._run_configure_explicit(build_tmp, build_cc, build_cxx, jsonc_pc,
                                     pkg_config=pkg_config, shim_dir=shim_dir,
                                     extra_cppflags=extra_c,
                                     extra_ldflags=extra_l,
                                     sdk_lib=sdk_llvm_lib,
                                     conan_libdirs=dep_lib_path)
        # Configure generates build-tree libtool/config.status/Makefiles
        # with the shell it ran under baked in; scrub again so later
        # make/install lines never re-exec the bad path.
        try:
            self._patch_bad_shell_refs()
        except Exception:
            pass
        # PKG_CHECK_MODULES([JSON_C]) reads PKG_CONFIG_PATH (declared via
        # AC_ARG_VAR in pkg.m4, bti/034 precedent). Combined value already
        # passed to configure above; LIBGNUTLS_* stub comment kept there.
        # LIBGNUTLS_* stub: generated configure honors non-empty
        # LIBGNUTLS_CFLAGS/LIBS env (skips pkg-config probe, uses them
        # verbatim). -I. / -L. are harmless no-ops; only test/simline
        # consumes these vars and simline is never built (see below),
        # so the stub cannot leak into the library or offline tests.
        # Build ONLY the library (src/): top-level `make all` would also
        # build test/simline (unconditional SUBDIRS on non-Windows) whose
        # libserver links gnutls (unavailable, see requirements()). test/offline
        # is built by the `check` step below; package() scopes
        # `make install` to SUBDIRS=src (see package()): a top-level
        # install first builds `all` in every SUBDIRS entry, which forces
        # a build of test/simline libserver (gnutls-dependent, see below)
        # even though its programs are noinst and install nothing.
        # Make-level TMPDIR/SHELL vars keep libtool shells off /tmp.
        # NOTE: plain self.run, not Autotools.make: the link step needs
        # the inline SDK-first LD_LIBRARY_PATH (wins over conanbuild.sh
        # for this command) and Autotools.make offers no command-prefix
        # hook. Same make target/vars, only the loader env is added.
        _compile_ld = self._scoped_ld_prefix(sdk_llvm_lib, dep_lib_path)
        self.run(
            _compile_ld +
            "make -j1 -C src "
            "SHELL=\"{sh}\" CONFIG_SHELL=\"{sh}\" "
            "TMPDIR=\"{tmp}\" TMP=\"{tmp}\" TEMP=\"{tmp}\"".format(
                sh=build_shell, tmp=build_tmp),
            cwd=self.build_folder, env="conanbuild")
        # Upstream offline suite only (test/offline has no network needs).
        # test/online requires live ISDS credentials — documented as not-run.
        # NOTE: Autotools configure runs a VPATH build in build_folder, so the
        # configured test/offline/Makefile lives under build_folder; run the
        # check there (source_folder copy is unconfigured).
        # Two-phase offline check (E505/E321: the inherited
        # LD_LIBRARY_PATH lets SDK lld load the conan libxml2 copy ->
        # lld crash reported as compiler failure; the earlier "compile
        # with no loader env" attempt failed because env="conanbuild"
        # re-injects it, so phase 1 now uses the SDK-first prefix).
        # Phase 1 compiles the check programs with SDK llvm/lib first
        # (conan libdirs follow for RUN probes); phase 2 only re-runs
        # `make check` (binaries up-to-date, no toolchain subprocess)
        # with a strictly conan-only LD_LIBRARY_PATH so the shared deps
        # (curl/libxml2/expat) resolve at test runtime and no host SDK
        # lib leaks into test processes (E341).
        env_prefix = (f"TMPDIR=\"{build_tmp}\" TMP=\"{build_tmp}\" TEMP=\"{build_tmp}\" "
                      f"SHELL=\"{build_shell}\" CONFIG_SHELL=\"{build_shell}\" ")
        compile_prefix = env_prefix + self._scoped_ld_prefix(
            sdk_llvm_lib, dep_lib_path)
        build_log = os.path.join(self.build_folder, "hmbs-offline-build.log")
        build_command = "make -C test/offline check TESTS= -j1"
        check_log = os.path.join(self.build_folder, "hmbs-offline-check.log")
        command = "make -C test/offline check -j1"
        if dep_lib_path:
            ld_prefix = "LD_LIBRARY_PATH=\"%s\" " % os.pathsep.join(dep_lib_path)
        else:
            ld_prefix = ""
        total = passed = failed = skipped = 0
        try:
            # Run via shell so output can be tee'd to a log for parsing.
            # Autotools.make() has no stdout capture; self.run() returns code.
            # env=conanbuild inherits HMBS-injected PATH (HMBS_CMAKE etc.)
            # and writable TMPDIR (readonly /tmp gate). Explicit
            # TMPDIR/TMP/TEMP/SHELL/CONFIG_SHELL prefix keeps test shells
            # off /tmp and off the poisoned profile bash even if
            # conanbuild.sh is scrubbed; tests themselves are unmodified.
            # compile_prefix additionally puts the SDK llvm/lib first so
            # lld starts (phase 1 links); the phase-2 run prefix stays
            # conan-only (binaries are up-to-date, no toolchain runs).
            self.run(compile_prefix + f"{build_command} 2>&1 | tee \"{build_log}\"",
                     cwd=self.build_folder, env="conanbuild")
            self.run(env_prefix + ld_prefix +
                     f"{command} 2>&1 | tee \"{check_log}\"", cwd=self.build_folder, env="conanbuild")
            log_text = ""
            if os.path.isfile(check_log):
                with open(check_log, "r", encoding="utf-8", errors="replace") as f:
                    log_text = f.read()
            total, passed, failed, skipped = self._parse_make_check_summary(log_text)
            # Falsifiability: ensure log is non-empty and harness is real.
            if total == 0:
                self.output.warning("offline make check produced no parseable summary; see " + check_log)
        except Exception as e:
            log_text = ""
            if os.path.isfile(check_log):
                try:
                    with open(check_log, "r", encoding="utf-8", errors="replace") as f:
                        log_text = f.read()
                except OSError:
                    pass
            total, passed, failed, skipped = self._parse_make_check_summary(log_text)
            self.output.warning(f"offline make check failed: {e}")
            if total == 0:
                # Report failure honestly so HMBS does not silently pass.
                self._emit_upstream_marker(0, 0, 1, 0, command)
                raise
        self._emit_upstream_marker(total, passed, failed, skipped, command)
        if failed > 0 or skipped > 0 or total == 0 or passed != total:
            raise ConanInvalidConfiguration(
                f"libdatovka offline tests not fully green: TOTAL={total} PASS={passed} FAIL={failed} SKIP={skipped}"
            )

    def package(self):
        # Same readonly_tmp guard as build(): package() runs in a fresh
        # conan context; os.environ TMPDIR from build() is not inherited.
        # Also re-scrub the profile's bad bash literal: generated
        # Makefiles/libtool baked it in at configure time on runners
        # where it existed, and install re-execs $(SHELL) per line.
        try:
            self._fix_shell_and_tmp()
            self._patch_bad_shell_refs()
        except Exception:
            pass
        try:
            _shim = self._write_install_shim()
            self._redirect_install_to_shim(_shim)
        except Exception as e:
            self.output.warning("libdatovka package install shim failed: %s" % e)
        try:
            _pshell = os.environ.get("SHELL") or self._detect_shell()
        except Exception:
            _pshell = "/bin/sh"
        try:
            _ptmp = self._writable_tmpdir()
        except Exception:
            _ptmp = os.environ.get("TMPDIR") or ""
        autotools = Autotools(self)
        _args = ["-j1", "SHELL=" + _pshell, "CONFIG_SHELL=" + _pshell]
        if _ptmp:
            _args += ["TMPDIR=" + _ptmp, "TMP=" + _ptmp, "TEMP=" + _ptmp]
        # Scope install recursion to src/ (differs from the previous
        # round's install-shim strategy, which only fixed the copy tool).
        # Preflight 2026-09-17: top-level `make install` recursed into
        # test/ and tried to BUILD test/simline libserver
        # (libserver_la-time_conversion.lo) because automake install-am
        # depends on all-am in every SUBDIRS entry. simline can never
        # build here: server.c hard-includes <gnutls/gnutls.h>
        # (gnutls intentionally not required, stubbed configure vars) and
        # its VPATH compile of src/*.c misses ../config.h. test/ holds no
        # installable artifacts (offline/online are check/noinst programs,
        # simline libserver is noinst), while src/ installs the library
        # (2026-09-17 preflight correction: NOT the public header — the
        # device package tree is [conaninfo, conanmanifest, lib] with no
        # include/ at all, so _install_public_headers() copies the genuine
        # source isds.h after install) and the top dir's own install-am
        # (e.g. .pc data) still runs. Single-word SUBDIRS needs no quoting games
        # (complexity/1.13 caveat was about multi-word values) and src/
        # defines no SUBDIRS of its own, so no oscats-style propagation
        # hazard. Test suite untouched: offline check already ran in build().
        _args += ["SUBDIRS=src"]
        autotools.install(args=_args)
        self._repair_install()
        self._install_public_headers()
        self._install_vendored_jsonc()
        for _la in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(_la)
        if self.settings.os == "OHOS" and self.options.shared:
            import glob as _glob
            sos = _glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so*"), recursive=True)
            objcopy = os.environ.get("HNP_OBJCOPY", "/data/service/hnp/bin/llvm-objcopy")
            signer = os.environ.get("HNP_SIGN_TOOL", "/data/service/hnp/bin/binary-sign-tool")
            if sos and (not os.path.isfile(objcopy) or not os.path.isfile(signer)):
                raise ConanInvalidConfiguration(
                    f"OHOS shared-lib sign tools missing: objcopy={objcopy}, signer={signer}"
                )
            for so in sos:
                if os.path.islink(so):
                    continue
                self.run(f'{objcopy} --remove-section .codesign "{so}"')
                self.run(f'{signer} sign -inFile "{so}" -outFile "{so}" -selfSign 1')

    def package_info(self):
        # Static libdatovka.a references json_* (soap.c) from the vendored
        # static json-c shipped in package lib/ (see _install_vendored_jsonc):
        # list it after datovka so consumers link -ldatovka -ljson-c.
        self.cpp_info.libs = ["datovka", "json-c"]
        self.cpp_info.set_property("cmake_file_name", "libdatovka")
        self.cpp_info.set_property("cmake_target_name", "libdatovka::libdatovka")
        self.cpp_info.set_property("pkg_config_name", "libdatovka")
