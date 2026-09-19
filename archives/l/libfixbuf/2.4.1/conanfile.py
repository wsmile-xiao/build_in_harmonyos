#!/usr/bin/env python3
"""Conan recipe — libfixbuf 2.4.1 (Autotools).

libfixbuf is the CERT NetSA IPFIX protocol library (C, autotools +
libtool). Upstream ships a configure script; only glib2 (>= 2.18) is
required. TLS/SCTP/Spread/tools are optional and stay disabled so the
package is a pure library with no extra runtime dependencies.

OHOS adaptations (see notes.md):
- autoconf config.guess/config.sub do not know OHOS: identify
  HarmonyOS/OHOS early (aarch64-unknown-linux-ohos) and accept the
  -linux-ohos triplet (E007 precedent: lzop 1.04, ldns 1.9.0).
- configure creates its tmp dir with umask 077 + mktemp -d, which fails
  on HMDFS/SELinux workers: fall back to TMPDIR with umask 000 +
  mkdir -p (E011/E114 precedent: ldns 1.9.0, lzop 1.04).
- single job make (-j1): parallel make hits the HMDFS jobserver
  fifo EPERM (E074 precedent).
- upstream has NO test suite (audited tarball, see
  test_package/MANIFEST.yml): build() does not run make check; the
  honest HMBS_UPSTREAM_TEST_RESULT status is no_tests/0.
- preflight hardening: /tmp can be read-only and the aggregated
  conanbuild env can point CONFIG_SHELL at an hnp bash that is
  inaccessible on some workers (configure re-exec dies with Error 127).
  generate() pins SHELL/CONFIG_SHELL to /bin/sh plus writable
  TMPDIR/TMP/TEMP (guile 2.2.7 / boolstuff 0.1.16 precedent).
- build() uses the standard Autotools.configure() helper (enscript
  1.6.6 / epsilon 0.9.2 precedent) so the OHOS toolchain composes
  configure args and CFLAGS/LDFLAGS/CC for the conftest link; no
  hand-rolled configure invocation or conanbuild-script rewriting.
"""
import os

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


# install(1) shim for HMBS HMDFS workers (chmod=0/hardlink=0/install_shim).
# Adapted from wv/1.2.9 _write_install_shim + cataract/1.0.0 _INSTALL_SHIM
# precedent: the HMBS-provided install cannot reliably create the package
# lib dir for libtool's `install -c .libs/libfixbuf.a <pkg>/lib/libfixbuf.a`
# (2026-09-19 preflight: install echoes success but the file is missing, so
# the follow-up `chmod 644 <pkg>/lib/libfixbuf.a` dies with ENOENT), and the
# follow-up chmod itself is best-effort on HMDFS (chmod capability = 0).
# The shim only provides mkdir/cp semantics: mkdir -p the dest dir, cp -f
# each SRC to DEST, chmod best-effort (`|| true`). No test logic touched.
_INSTALL_SHIM = (
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


class LibfixbufConan(ConanFile):
    name = "libfixbuf"
    version = "2.4.1"
    description = "CERT NetSA implementation of the IPFIX protocol (flow export/collect library)"
    license = "LGPL-3.0-only"
    homepage = "https://tools.netsa.cert.org/fixbuf2/index.html"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("ipfix", "netflow", "network", "cert-netsa")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # configure.ac: AM_PATH_GLIB_2_0([2.18.0], ..., [gthread]).
        # Headers are included transitively (public.h includes glib.h).
        self.requires("glib2/2.88.0", transitive_headers=True, transitive_libs=True)

    def build_requirements(self):
        # AM_PATH_GLIB_2_0 probes via pkg-config.
        self.tool_requires("pkgconf/3.0.5")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = AutotoolsDeps(self)
        deps.generate()
        pc = PkgConfigDeps(self)
        pc.generate()
        # E348 (graphene 1.10.8 precedent): PkgConfigDeps emits only the
        # one .pc declared by glib2/2.88.0 (glib-2.0.pc), but libfixbuf's
        # configure probes the GLib multi-.pc family (AM_PATH_GLIB_2_0
        # with the gthread module + a gio-2.0 probe: preflight
        # HMBS_CONFIG_FAIL shows --exists failing for glib-2.0 args and
        # gio-2.0). Write forwarding alias .pc files into the generators
        # folder: Version dynamically inherited from glib-2.0.pc (never
        # hardcoded), Requires: glib-2.0 so paths/Cflags/Libs come from
        # the real generated .pc. Never point PKG_CONFIG_PATH at the
        # package-embedded .pc (prefix=/, E348 forbid_2).
        self._forward_glib_family_pc()
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        else:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        # Pure library: skip ipfixDump + cert_ipfix.xml + man pages.
        # The tools need pod2man/pod2html at build time and add a CLI
        # surface the library package does not need (R38 stays library).
        tc.configure_args.append("--disable-tools")
        # AM_PATH_GLIB_2_0 compiles AND runs a glib test program by
        # default; the run phase fails under OHOS (cataract 1.0.0 /
        # babeltrace 1.5.11 precedent). pkg-config cflags/libs are
        # sufficient, so skip only the run check. Unknown
        # --disable-glibtest is warned and ignored if unsupported.
        tc.configure_args.append("--disable-glibtest")
        # Tenth round: explicit GNU triplets REMOVED (revert of ninth
        # round). E007 + knowledge/operations/build-systems.md S3.0
        # forbid faking --build/--host=*-gnu: configure then misdetects
        # cross-compilation and AC_RUN_IFELSE results go wrong. The
        # tenth-round preflight proved it: with gnu triplets active the
        # fingerprint was byte-identical (Error 77 + /tmp/sh*.tmp, CC
        # still hnp clang), so the bypass fixed nothing. Keep the E007
        # source patch (config.guess/config.sub -> linux-ohos) as the
        # only triplet path; no explicit triplets are passed here.
        # HMBS preflight hardening: pin POSIX shell + writable tmp dir.
        # The aggregated conanbuild env may export CONFIG_SHELL pointing
        # at an inaccessible hnp bash (configure[162] re-exec -> Error
        # 127) and /tmp may be read-only. Resolve via the shared probed
        # helper so generate()/build()/package() see the same writable
        # dir (HMBS-injected TMPDIR preferred, build-folder fallback).
        # This Environment entry is the persistent channel for
        # configure/make/install/config.status children.
        tmpdir = self._hmbs_tmpdir()
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass
        # Same-process channel: generate-phase children (pkg-config
        # probes, toolchain probes) inherit os.environ, not the
        # not-yet-written tc.environment() file. Sync now so no probe
        # falls back to read-only /tmp (Error 77 + readonly_tmp).
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir
        os.environ["HMBS_TMPDIR"] = tmpdir
        env = tc.environment()
        env.define("SHELL", "/bin/sh")
        env.define("CONFIG_SHELL", "/bin/sh")
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        # 2026-09-19 preflight: `checking for pkg-config... no` then
        # `configure: error: Cannot find a suitable glib2 (>= 2.18)` with
        # `configure[19239]: no: inaccessible or not found` (PKG_CONFIG
        # fell back to the literal `no`). VirtualBuildEnv alone did not
        # put a `pkg-config`-named binary on PATH (pkgconf ships
        # `pkgconf`), and Conan 2.29 does not export the PkgConfigDeps
        # folder via PKG_CONFIG_PATH (ccfits 2.7 / astrometry 0.97
        # precedent), so AM_PATH_GLIB_2_0 finds neither the tool nor
        # glib-2.0.pc. Pin both explicitly: absolute PKG_CONFIG plus
        # PATH (tool dir) plus PKG_CONFIG_PATH (generators folder).
        # Only the discovery variables are set; no check is skipped.
        try:
            _pkg_bin, _pkg_bindir = self._hmbs_pkg_config_bin()
        except Exception:
            _pkg_bin, _pkg_bindir = None, None
        if _pkg_bin:
            env.define("PKG_CONFIG", _pkg_bin)
        if _pkg_bindir:
            env.prepend_path("PATH", _pkg_bindir)
        try:
            _gen = self.generators_folder
        except Exception:
            _gen = None
        if _gen and os.path.isdir(_gen):
            env.prepend_path("PKG_CONFIG_PATH", _gen)
        # Same-process channel (see TMPDIR comment above): generate-phase
        # children inherit os.environ, so mirror the pins now.
        if _pkg_bin:
            os.environ["PKG_CONFIG"] = _pkg_bin
        if _pkg_bindir:
            _sep = os.pathsep
            _old_path = os.environ.get("PATH", "")
            if _pkg_bindir not in _old_path.split(_sep):
                os.environ["PATH"] = _pkg_bindir + _sep + _old_path if _old_path else _pkg_bindir
        if _gen and os.path.isdir(_gen):
            _sep = os.pathsep
            _old_pc = os.environ.get("PKG_CONFIG_PATH", "")
            if _gen not in _old_pc.split(_sep):
                os.environ["PKG_CONFIG_PATH"] = _gen + _sep + _old_pc if _old_pc else _gen
        # E501: OHOS SDK lld needs its llvm/lib dir in LD_LIBRARY_PATH
        # (libxml2.so.16 has no RUNPATH). Version-agnostic glob so a
        # future SDK bump does not hard-code 26.0.0.18.
        try:
            import glob as _gg
            for _lib in _gg.glob(
                    "/data/service/hnp/ohos-sdk*/ohos/native/llvm/lib"):
                if os.path.isdir(_lib):
                    env.prepend_path("LD_LIBRARY_PATH", _lib)
                    break
        except Exception:
            pass
        tc.generate(env=env)
        # Expose pkgconf tool binary (pkg-config) to configure via PATH.
        # Without this, AM_PATH_GLIB_2_0 sees "checking for pkg-config...
        # no" and dies with "Cannot find a suitable glib2" even though
        # glib2/2.88.0 + PkgConfigDeps are present (cataract 1.0.0 same
        # shape: AutotoolsToolchain + PkgConfigDeps + VirtualBuildEnv).
        VirtualBuildEnv(self).generate()

    def _forward_glib_family_pc(self):
        """Write E348 forwarding alias .pc files for the GLib family.

        Adapted from graphene 1.10.8 (E348 rec) + fallback alias loop:
        alias list covers every non-main .pc libfixbuf's configure can
        probe (gthread-2.0 via AM_PATH_GLIB_2_0's module arg, gio-2.0 via
        its own probe, plus gobject-2.0/gmodule-2.0 for completeness).
        Files already present are left untouched; Version is inherited
        from the generated glib-2.0.pc, never hardcoded (E348 forbid_1).
        """
        try:
            folder = self.generators_folder
        except Exception:
            return
        if not folder or not os.path.isdir(folder):
            return
        src = os.path.join(folder, "glib-2.0.pc")
        if not os.path.isfile(src):
            try:
                self.output.warning(
                    "glib family forward: glib-2.0.pc not generated, skip")
            except Exception:
                pass
            return
        ver = "0"
        try:
            with open(src, encoding="utf-8") as f:
                for line in f:
                    if line.startswith("Version:"):
                        ver = line.split(":", 1)[1].strip() or "0"
                        break
        except OSError:
            pass
        for alias in ("gobject-2.0", "gio-2.0", "gthread-2.0", "gmodule-2.0"):
            dst = os.path.join(folder, alias + ".pc")
            if os.path.isfile(dst):
                continue
            try:
                with open(dst, "w", encoding="utf-8", newline="\n") as f:
                    f.write("Name: %s\n" % alias)
                    f.write("Description: forwarding .pc generated by "
                            "libfixbuf recipe (Requires glib-2.0)\n")
                    f.write("Version: %s\n" % ver)
                    f.write("Requires: glib-2.0\n")
            except OSError:
                pass

    def _fix_la_libdirs(self):
        """Repair stale '//lib' paths inside dependency .la files.

        Adapted from ekg2 0.3.1 _fix_la_libdirs (E236): build a
        //lib/<name>.la -> real-path map across host deps, then fix
        libdir='//lib', dependency_libs references and -L//lib in every
        dep .la. Only cache .la text is corrected; no source, check or
        test logic is touched.
        """
        import glob as _glob
        try:
            _host = self.dependencies.host.values()
        except Exception:
            try:
                _host = self.dependencies.values()
            except Exception:
                return
        la_map = {}
        _dep_libdirs = []
        for dep in _host:
            try:
                folder = dep.package_folder
            except Exception:
                continue
            if not folder or not os.path.isdir(folder):
                continue
            try:
                libdirs = list(dep.cpp_info.libdirs) or ["lib"]
            except Exception:
                libdirs = ["lib"]
            for libdir in libdirs:
                pkg_lib = os.path.join(folder, libdir)
                if not os.path.isdir(pkg_lib):
                    continue
                _dep_libdirs.append(pkg_lib)
                try:
                    found = _glob.glob(os.path.join(pkg_lib, "*.la"))
                except OSError:
                    continue
                for la in found:
                    la_map[os.path.join("//lib", os.path.basename(la))] = la
        for pkg_lib in _dep_libdirs:
            try:
                found = _glob.glob(os.path.join(pkg_lib, "*.la"))
            except OSError:
                continue
            for la in found:
                try:
                    with open(la, "r", encoding="utf-8",
                              errors="replace") as f:
                        data = f.read()
                except OSError:
                    continue
                orig = data
                data = data.replace("libdir='//lib'",
                                    "libdir='%s'" % pkg_lib)
                for bad, good in la_map.items():
                    if bad in data:
                        data = data.replace(bad, good)
                data = data.replace(" -L//lib ", " ")
                if data != orig:
                    try:
                        with open(la, "w", encoding="utf-8",
                                  newline="\n") as f:
                            f.write(data)
                    except OSError:
                        pass

    def _patch_config_guess_sub(self):
        """Teach the shipped autoconf helpers about OHOS (E007).

        Robust variant: libfixbuf 2.4.1 ships config.guess 2020-11-07
        whose marker whitespace/quoting differs from newer trees, so a
        single-marker replace silently no-ops and configure dies with
        "unable to guess system type / cannot guess build type". This
        version walks the whole source tree, accepts quoted and unquoted
        main-case markers, and inserts an enscript-style HarmonyOS/OHOS
        branch (E007 precedent: enscript 1.6.6 0001). config.sub is
        patched via generic linux-android anchors so old and new layouts
        accept the linux-ohos triplet. Also relaxes umask 077 to 000 in
        config.guess tmp creation (E011/HMDFS).
        """
        candidates = set()
        for root, _, files in os.walk(self.source_folder):
            for name in files:
                if name in ("config.guess", "config.sub"):
                    candidates.add(os.path.join(root, name))
        for extra in (
            os.path.join(self.source_folder, "autoconf", "config.guess"),
            os.path.join(self.source_folder, "autoconf", "config.sub"),
            os.path.join(self.source_folder, "config.guess"),
            os.path.join(self.source_folder, "config.sub"),
        ):
            if os.path.isfile(extra):
                candidates.add(extra)
        ohos_block = (
            "    *:HarmonyOS:*:* | *:OHOS:*:* | *:OpenHarmony:*:*)\n"
            "\t# HarmonyOS/OHOS uname; native triplet so configure\n"
            "\t# does not fall through to the compiler probe (E007).\n"
            "\techo ${UNAME_MACHINE}-unknown-linux-ohos\n"
            "\texit ;;\n"
        )
        for path in sorted(candidates):
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
            except OSError:
                continue
            orig = content
            base = os.path.basename(path)
            if base == "config.guess":
                if "HarmonyOS" not in content or "linux-ohos" not in content:
                    inserted = False
                    for anchor in ("*:NetBSD:*:*)", "*:NetBSD:*:*"):
                        if anchor in content:
                            content = content.replace(anchor, ohos_block + anchor, 1)
                            inserted = True
                            break
                    if not inserted:
                        for marker in (
                            'case "${UNAME_MACHINE}:${UNAME_SYSTEM}:${UNAME_RELEASE}:${UNAME_VERSION}" in',
                            "case $UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:$UNAME_VERSION in",
                        ):
                            if marker in content:
                                content = content.replace(marker, marker + "\n" + ohos_block, 1)
                                inserted = True
                                break
                    if not inserted:
                        import re as _re
                        m = _re.search(r"^.*case.*UNAME_MACHINE.*UNAME_SYSTEM.*in.*$", content, _re.MULTILINE)
                        if m:
                            pos = m.end()
                            content = content[:pos] + "\n" + ohos_block + content[pos:]
                            inserted = True
                if "umask 077" in content:
                    content = content.replace("umask 077", "umask 000")
                # readonly_tmp: config.guess 2020-11-07 creates its probe
                # dir via mktemp with an explicit /tmp template on some
                # branches (or via $TMPDIR that is still /tmp when the
                # parent env was stale). Only the temp root is replaced
                # so dash/toybox-ash mktemp honors the writable HMBS dir;
                # no probe logic is skipped.
                if "/tmp/cg" in content:
                    content = content.replace("/tmp/cg", "${TMPDIR:-/tmp}/cg")
                if "/tmp/sh" in content:
                    content = content.replace("/tmp/sh", "${TMPDIR:-/tmp}/sh")
            else:  # config.sub: canonical 3-point OHOS patch (E007).
                # Traced against libfixbuf 2.4.1 autoconf/config.sub
                # (timestamp 2020-11-07, new field-split layout): input
                # aarch64-unknown-linux-ohos splits to basic_os=linux-ohos,
                # then the "*-*)" branch yields kernel=linux os=ohos, which
                # dies at OS validation without ohos* (error in preflight:
                # "OS `ohos\u0027 not recognized"). All three points below
                # mirror scripts/patch-autotools-ohos.pl sections 2.1-2.3.
                # 2.1 triplet-split section: handle ohos-linux like
                # android-linux (3-component ambiguous inputs).
                if "ohos-linux)" not in content and "android-linux)" in content:
                    old_android = (
                        "\t\t\tandroid-linux)\n"
                        "\t\t\t\tbasic_machine=$field1-unknown\n"
                        "\t\t\t\tbasic_os=linux-android\n"
                        "\t\t\t\t;;\n"
                    )
                    new_android = (
                        old_android
                        + "\t\t\tohos-linux)\n"
                        + "\t\t\t\tbasic_machine=$field1-unknown\n"
                        + "\t\t\t\tbasic_os=linux-ohos\n"
                        + "\t\t\t\t;;\n"
                    )
                    if old_android in content:
                        content = content.replace(old_android, new_android, 1)
                # 2.2 OS validation list: accept ohos as an OS name.
                if "ohos*" not in content:
                    if "gnu* | android*" in content:
                        content = content.replace(
                            "gnu* | android*", "gnu* | android* | ohos*", 1
                        )
                # 2.3 kernel-OS validation list: accept linux-ohos.
                # NOTE: guard on the starred form; 2.1 above already
                # inserts bare "linux-ohos" (basic_os value).
                if "linux-ohos*" not in content:
                    if "linux-android*" in content:
                        content = content.replace(
                            "linux-android*", "linux-android* | linux-ohos*", 1
                        )
                    elif "linux-gnu*" in content:
                        content = content.replace(
                            "linux-gnu*", "linux-gnu* | linux-ohos*", 1
                        )
                # Legacy layout fallback (pre-2020 config.sub): -linux-android*.
                if "-linux-android*" in content and "-linux-ohos*" not in content:
                    content = content.replace(
                        "-linux-android*", "-linux-android* | -linux-ohos*", 1
                    )
            if content != orig:
                try:
                    with open(path, "w", encoding="utf-8", newline="\n") as f:
                        f.write(content)
                except OSError:
                    pass

    def _patch_configure_mktemp(self):
        """HMDFS-safe tmp dir creation inside configure (E011/E114)."""
        configure_path = os.path.join(self.source_folder, "configure")
        try:
            with open(configure_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except OSError:
            return
        orig = content
        # readonly_tmp (2026-09-18 compile Error 77 + /tmp/sh*.tmp):
        # the shipped primary tmp uses mktemp -d in the current build
        # dir ("./confXXXXXX"), which is writable even when /tmp is
        # read-only -- keep that ./ primary (only relax umask for
        # HMDFS) instead of moving it to $TMPDIR (dangling-TMPDIR risk).
        # Only the fallback branch (used when mktemp is missing) is
        # redirected to the probed writable TMPDIR with mkdir -p.
        old_primary_mktemp = '(umask 077 && mktemp -d "./confXXXXXX")'
        new_primary_mktemp = '(umask 000 && mktemp -d "./confXXXXXX")'
        if old_primary_mktemp in content:
            content = content.replace(old_primary_mktemp, new_primary_mktemp, 1)
        old_primary = 'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&'
        new_primary = 'tmp=`(umask 000 && mktemp -d "./confXXXXXX") 2>/dev/null` &&'
        if old_primary in content:
            content = content.replace(old_primary, new_primary, 1)
        old_fallback = "  tmp=./conf$-$RANDOM\n  (umask 077 && mkdir \"$tmp\")"
        new_fallback = "  tmp=${TMPDIR:-.}/conf$-$RANDOM\n  (umask 000 && mkdir -p \"$tmp\")"
        if old_fallback in content:
            content = content.replace(old_fallback, new_fallback, 1)
        # Generic: remaining bare mktemp must honor TMPDIR first.
        if "umask 077" in content:
            content = content.replace("umask 077", "umask 000")
        # readonly_tmp: any mktemp template with an explicit /tmp root
        # bypasses $TMPDIR (toybox/dash mktemp honors TMPDIR only when
        # the template has no dir). Only the root is swapped; the
        # template suffix and test logic are untouched.
        if 'mktemp -d "/tmp/' in content:
            content = content.replace('mktemp -d "/tmp/', 'mktemp -d "${TMPDIR:-/tmp}/')
        if "mktemp -d '/tmp/" in content:
            content = content.replace("mktemp -d '/tmp/", "mktemp -d '${TMPDIR:-/tmp}/")
        if "mktemp -d /tmp/" in content:
            content = content.replace("mktemp -d /tmp/", 'mktemp -d "${TMPDIR:-/tmp}/')
        if 'mktemp "/tmp/' in content:
            content = content.replace('mktemp "/tmp/', 'mktemp "${TMPDIR:-/tmp}/')
        if content != orig:
            try:
                with open(configure_path, "w", encoding="utf-8", newline="\n") as f:
                    f.write(content)
            except OSError:
                pass

    def _hmbs_pkg_config_bin(self):
        """Return (pkg_config_bin, pkg_config_bindir) or (None, None).

        2026-09-19: configure needs the literal `pkg-config` name, but the
        pkgconf tool package exposes `pkgconf` (and only sometimes a
        `pkg-config` alias). Resolving the absolute binary here lets
        generate()/build() export PKG_CONFIG directly (AC_PATH_TOOL
        honors a preset $PKG_CONFIG) plus prepend its bindir to PATH.
        Never fails; returns Nones when the tool package is absent.
        """
        try:
            dep = self.dependencies.build.get("pkgconf")
        except Exception:
            try:
                dep = self.dependencies.build["pkgconf"]
            except Exception:
                return None, None
        try:
            folder = dep.package_folder
        except Exception:
            return None, None
        if not folder or not os.path.isdir(folder):
            return None, None
        for _name in ("pkg-config", "pkgconf"):
            for _d in ("bin", ""):
                _p = os.path.join(folder, _d, _name) if _d else os.path.join(folder, _name)
                try:
                    if os.path.isfile(_p):
                        _bindir = os.path.dirname(_p)
                        return _p, _bindir
                except OSError:
                    continue
        return None, None

    def _hmbs_tmpdir(self):
        """Return a probed-writable tmp dir, shared by all stages.

        Strategy change (2026-09-18 eighth round): after two consecutive
        identical compile Error 77 + /tmp/sh*.tmp failures DESPITE the
        fully hardened propagation mechanism (os.environ sync in
        generate(), in-place stale /tmp replacement + last-wins pin in
        sanitized scripts, explicit ${TMPDIR:-/tmp} mktemp roots), the
        remaining variable is the LOCATION, not the mechanism. The
        Python probe reports the HMBS-injected runtime tmp
        (/storage/.../runtime/libfixbuf-2.4.1/tmp) as writable, yet every
        configure child (toybox-ash heredoc /tmp/shXXXXXX + clang
        conftest link) still falls back to read-only /tmp. That split
        matches a per-process SELinux domain restriction (the harness
        itself fails preflight.sh[306] with /proc/cmdline + /tmp errors),
        so a Python-visible writable dir is not shell-visible there.
        This round prefers the build-folder-local dir FIRST (same
        SELinux/filesystem context as the .o outputs that must succeed
        anyway; balboa/cyrus-sasl source-local tmp precedent), keeping
        the HMBS-injected candidates only as fallback. Toolchain,
        triplet patches and test posture are untouched.
        """
        def _probed(cand):
            if not cand or cand in ("0", "1") or cand == "/tmp":
                return None
            try:
                os.makedirs(cand, exist_ok=True)
            except OSError:
                return None
            if not os.path.isdir(cand):
                return None
            try:
                probe = os.path.join(cand, ".hmbs_probe")
                with open(probe, "w", encoding="utf-8") as _pf:
                    _pf.write("probe")
                try:
                    os.remove(probe)
                except OSError:
                    pass
            except OSError:
                return None
            return cand

        # Build-local FIRST (different strategy this round, see docstring):
        # same context as the .o outputs; HMBS runtime tmp only fallback.
        try:
            _local = os.path.join(self.build_folder, ".hmbs-tmp")
        except (TypeError, AttributeError):
            _local = None
        if _local:
            _hit = _probed(_local)
            if _hit:
                return _hit
        for cand in (
            os.environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK"),
            os.environ.get("HMBS_TMPDIR"),
            os.environ.get("TMPDIR"),
            os.environ.get("TMP"),
            os.environ.get("TEMP"),
        ):
            # HMBS_AUTOCONF_MKTEMP_FALLBACK is "0"/"1" flag mode on some
            # workers (avahi precedent) -- only path-like values qualify.
            if cand in ("0", "1"):
                continue
            hit = _probed(cand)
            if hit:
                return hit
        fallback = os.path.join(self.build_folder, ".hmbs-tmp")
        try:
            os.makedirs(fallback, exist_ok=True)
        except OSError:
            pass
        return fallback

    def _sanitize_hmbs_shell_scripts(self, tmpdir, cc=None, cxx=None,
                                     extra_ld=None, pkg_config=None,
                                     pkg_config_path=None):
        """Drop-in HMBS shell/tmp hardening for aggregated Conan scripts.

        The aggregated conanbuild env can export CONFIG_SHELL pointing at
        an hnp bash that is inaccessible on some workers (configure[162]
        re-exec -> Error 127) and stale TMPDIR pointing at read-only
        /tmp. The toolchain Environment pinning in generate() loses when
        conanbuild.sh is sourced after the toolchain file, so rewrite the
        generated scripts on disk before configure/make/install run:
        replace the dead hnp bash path with /bin/sh and append forced
        exports (last export wins when sourced). Only touches generated
        conanbuild/conanautotools/conanrun scripts, never upstream
        sources, and only replaces the tmp root (no test skipping).
        When cc/cxx/extra_ld are given (eleventh round: hnp clang
        itself reports "inaccessible or not found", Error 127), their
        exports are appended in the same last-wins block so configure's
        conftest uses the accessible compiler.
        """
        folders = set()
        for folder in (getattr(self, "build_folder", None),
                       getattr(self, "generators_folder", None)):
            if folder and os.path.isdir(folder):
                folders.add(folder)
        if not folders:
            return
        # Quote once for shell double-quoted export lines.
        safe_tmp = tmpdir.replace("\\", "/").replace('"', "")
        marker = "# HMBS_TMPDIR_SHELL_PIN"
        for folder in folders:
            for root, _, files in os.walk(folder):
                for name in files:
                    if not name.endswith(".sh"):
                        continue
                    if not (name.startswith("conanbuild")
                            or name.startswith("conanautotools")
                            or name.startswith("conanrun")):
                        continue
                    path = os.path.join(root, name)
                    try:
                        with open(path, "r", encoding="utf-8",
                                  errors="replace") as f:
                            content = f.read()
                    except OSError:
                        continue
                    orig = content
                    if "/data/service/hnp/bin/bash" in content:
                        content = content.replace(
                            "/data/service/hnp/bin/bash", "/bin/sh")
                    # readonly_tmp: replace stale read-only /tmp roots in
                    # place (in addition to the appended pin below). The
                    # aggregated profile env may set TMPDIR/TMP/TEMP to
                    # /tmp without `export`; a later `export TMPDIR`
                    # would then re-export the stale value even though
                    # our appended line ran first across files. In-place
                    # replacement guarantees every assignment in every
                    # sourced file already points at the writable dir;
                    # the appended block remains as last-wins insurance.
                    import re as _re
                    for _var in ("TMPDIR", "TMP", "TEMP"):
                        content = _re.sub(
                            _var + r'="/tmp"',
                            _var + f'="{safe_tmp}"',
                            content)
                        content = _re.sub(
                            _var + r"='/tmp'",
                            _var + f'="{safe_tmp}"',
                            content)
                        content = _re.sub(
                            _var + r"=/tmp(\s|$|;|#)",
                            _var + f'="{safe_tmp}"\\1',
                            content)
                    if marker not in content:
                        content += (
                            "\n" + marker + "\n"
                            + 'export SHELL="/bin/sh"\n'
                            + 'export CONFIG_SHELL="/bin/sh"\n'
                            + f'export TMPDIR="{safe_tmp}"\n'
                            + f'export TMP="{safe_tmp}"\n'
                            + f'export TEMP="{safe_tmp}"\n'
                        )
                    # Eleventh round: accessible-compiler pin (last-wins).
                    # Only appended when build() selected a working CC;
                    # never rewrites upstream sources.
                    if cc:
                        _cc = cc.replace("\\", "/").replace('"', "")
                        _pin = f'export CC="{_cc}"\n'
                        if _pin not in content:
                            content += _pin
                    if cxx:
                        _cxx = cxx.replace("\\", "/").replace('"', "")
                        _pin = f'export CXX="{_cxx}"\n'
                        if _pin not in content:
                            content += _pin
                    if extra_ld and os.path.isdir(extra_ld):
                        _ld = extra_ld.replace("\\", "/").replace('"', "")
                        _pin = f'export LD_LIBRARY_PATH="{_ld}:$LD_LIBRARY_PATH"\n'
                        if _pin not in content:
                            content += _pin
                    # 2026-09-19: last-wins pin for pkg-config discovery
                    # (see generate()). The aggregated conanbuild.sh is
                    # sourced around configure, so re-export here to
                    # survive any ordering that drops generate()'s pin.
                    if pkg_config:
                        _pc = pkg_config.replace("\\", "/").replace('"', "")
                        _pin = f'export PKG_CONFIG="{_pc}"\n'
                        if _pin not in content:
                            content += _pin
                        _pcd = os.path.dirname(_pc)
                        if _pcd:
                            _pin = f'export PATH="{_pcd}:$PATH"\n'
                            if _pin not in content:
                                content += _pin
                    if pkg_config_path and os.path.isdir(pkg_config_path):
                        _pp = pkg_config_path.replace("\\", "/").replace('"', "")
                        _pin = f'export PKG_CONFIG_PATH="{_pp}:$PKG_CONFIG_PATH"\n'
                        if _pin not in content:
                            content += _pin
                    if content != orig:
                        try:
                            with open(path, "w", encoding="utf-8",
                                      newline="\n") as f:
                                f.write(content)
                        except OSError:
                            pass

    def _hmbs_cc_probe(self, tmpdir):
        """Accessible-compiler selection (eleventh round).

        Eleventh-round preflight gave the decisive line the tenth-round
        HMBS_CONFIG_FAIL diagnostic was built to capture:
        `configure: /data/service/hnp/bin/clang: inaccessible or not
        found` (exit 127). The fault is the conf-provided compiler path
        itself, not /tmp and not triplets. This method probes ordered
        candidates with `<cand> --version` (no shell) and returns the
        first that executes (cc, cxx, sdk llvm lib or None). It also
        direct-compiles a trivial TU with the selected CC and exports
        CC/CXX/LD_LIBRARY_PATH to os.environ. The caller appends the
        same exports last-wins into the sourced scripts. Never fails
        the build; only emits HMBS_CC_PROBE/HMBS_CC_SELECT lines.
        """
        import glob as _gg
        import shutil as _sh
        import subprocess as _sp
        try:
            _conf = self.conf.get("tools.build:compiler_executables",
                                  default={}) or {}
        except Exception:
            _conf = {}
        _sdk_lib = None
        try:
            for _lib in _gg.glob("/data/service/hnp/ohos-sdk*/ohos/native/llvm/lib"):
                if os.path.isdir(_lib):
                    _sdk_lib = _lib
                    break
        except Exception:
            pass
        _sdk_clang = None
        _sdk_clangxx = None
        try:
            _bins = _gg.glob("/data/service/hnp/ohos-sdk*/ohos/native/llvm/bin/clang")
            if _bins and os.path.isfile(_bins[0]):
                _sdk_clang = _bins[0]
            _binsxx = _gg.glob("/data/service/hnp/ohos-sdk*/ohos/native/llvm/bin/clang++")
            if _binsxx and os.path.isfile(_binsxx[0]):
                _sdk_clangxx = _binsxx[0]
        except Exception:
            pass
        # Fork-light (2026-09-18 readonly_tmp+can't-fork round): cap
        # candidates so the probe adds at most ~5 forks on a stressed
        # worker; full ordered list is kept only as comment. which()
        # itself does not fork, but each _works() --version does.
        _c_cands = []
        for _c in (_conf.get("c"), os.environ.get("CC"),
                   _sdk_clang, "clang"):
            if _c and _c not in _c_cands:
                _c_cands.append(_c)
        _cxx_cands = []
        for _c in (_conf.get("cpp"), _conf.get("cxx"), os.environ.get("CXX"),
                   _sdk_clangxx, "clang++"):
            if _c and _c not in _cxx_cands:
                _cxx_cands.append(_c)

        def _works(cmd):
            try:
                import copy as _copy
                _env = _copy.copy(os.environ)
                _env["TMPDIR"] = tmpdir
                _env["TMP"] = tmpdir
                _env["TEMP"] = tmpdir
                _p = _sp.run(cmd.split() + ["--version"], capture_output=True,
                             text=True, timeout=30, env=_env)
                return _p.returncode == 0
            except Exception:
                return False

        cc = None
        for _c in _c_cands:
            if _works(_c):
                cc = _c
                break
        cxx = None
        for _c in _cxx_cands:
            if _works(_c):
                cxx = _c
                break
        try:
            self.output.info("HMBS_CC_SELECT | cc=%s cxx=%s sdk_lib=%s" % (
                cc, cxx, _sdk_lib))
        except Exception:
            pass
        if cc:
            os.environ["CC"] = cc
        if cxx:
            os.environ["CXX"] = cxx
        if _sdk_lib:
            _prev = os.environ.get("LD_LIBRARY_PATH", "")
            if _sdk_lib not in _prev:
                os.environ["LD_LIBRARY_PATH"] = _sdk_lib + (
                    ":" + _prev if _prev else "")
        # Direct trivial-compile proof with the selected CC (or the
        # conf default when nothing executed, to keep evidence flowing).
        _proof_cc = cc or _c_cands[0] if _c_cands else "cc"
        try:
            self.output.info("HMBS_CC_PROBE | cc=%s tmpdir=%s" % (_proof_cc, tmpdir))
        except Exception:
            pass
        # Fork-light: single tmpdir-only trivial-compile proof (builddir
        # proof removed; one fork instead of two on stressed workers).
        for _label, _dir in (("tmpdir", tmpdir),):
            try:
                if not _dir:
                    continue
                os.makedirs(_dir, exist_ok=True)
                _src = os.path.join(_dir, ".hmbs_cc_probe.c")
                _out = os.path.join(_dir, ".hmbs_cc_probe")
                with open(_src, "w", encoding="utf-8", newline="\n") as _f:
                    _f.write("int main(void){return 0;}\n")
                _cmd = _proof_cc.split() + [_src, "-o", _out]
                import copy as _copy2
                _penv = _copy2.copy(os.environ)
                _penv["TMPDIR"] = tmpdir
                _penv["TMP"] = tmpdir
                _penv["TEMP"] = tmpdir
                _p = _sp.run(_cmd, capture_output=True, text=True, timeout=60,
                             env=_penv)
                _tail = ((_p.stdout or "") + (_p.stderr or "")).strip().splitlines()
                _tail = _tail[-5:] if _tail else ["<no output>"]
                try:
                    self.output.info(
                        "HMBS_CC_PROBE | %s rc=%d out=%s" % (_label, _p.returncode, _out))
                    for _ln in _tail:
                        self.output.info("HMBS_CC_PROBE | %s log: %s" % (_label, _ln[:400]))
                except Exception:
                    pass
                for _tmp in (_src, _out):
                    try:
                        if os.path.isfile(_tmp):
                            os.remove(_tmp)
                    except OSError:
                        pass
            except Exception as _e:
                try:
                    self.output.info("HMBS_CC_PROBE | %s exception: %r" % (_label, _e))
                except Exception:
                    pass
        return cc, cxx, _sdk_lib

    def build(self):
        apply_conandata_patches(self)
        self._patch_config_guess_sub()
        self._patch_configure_mktemp()
        # E236 (gts 0.7.6 / ekg2 0.3.1 precedent): OHOS conan autotools
        # packages install with --prefix=/, so their .la files bake
        # libdir='//lib' and dependency_libs referencing //lib/*.la.
        # When libtool links libfixbuf.la it reads those .la files and
        # dies with "'//lib/libpcre2-8.la' is not a valid libtool
        # archive". Rewrite the stale //lib roots to each dep's real lib
        # dir (ekg2 _fix_la_libdirs pattern); .la files are kept so
        # transitive static deps still resolve via dependency_libs.
        self._fix_la_libdirs()
        # Writable tmp + POSIX shell for configure children that bypass
        # conanbuild sourcing (diagnostic probes, mkdir fallbacks). The
        # persistent channel remains generate()'s tc.environment() pinning.
        tmpdir = self._hmbs_tmpdir()
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir
        os.environ["HMBS_TMPDIR"] = tmpdir
        os.environ["SHELL"] = "/bin/sh"
        os.environ["CONFIG_SHELL"] = "/bin/sh"
        # Disk channel (libfreexl/2.0.0 precedent): the aggregated
        # conanbuild.sh is sourced around Autotools.configure() and can
        # re-export the dead hnp bash + stale /tmp AFTER the toolchain
        # env above. Scrub those scripts on disk first so configure's
        # CONFIG_SHELL re-exec (line 162) sees /bin/sh and mktemp
        # fallbacks see the writable HMBS tmpdir. Standard helper is
        # kept so CFLAGS/LDFLAGS/CC stay intact (hand-rolled sh
        # configure previously surfaced as "C compiler cannot create
        # executables").
        # Eleventh round: select an accessible compiler first (conf
        # compiler itself is "inaccessible or not found", exit 127),
        # then pin scripts once last-wins with the selection. Falls back
        # to the conf default when nothing executes, so a true env
        # fault still surfaces naturally in configure.
        try:
            _cc, _cxx, _sdk_lib = self._hmbs_cc_probe(tmpdir)
        except Exception:
            _cc, _cxx, _sdk_lib = None, None, None
        # 2026-09-19: re-export pkg-config discovery for configure
        # children (same reason as generate()'s pin; see helper above).
        try:
            _pkg_bin, _ = self._hmbs_pkg_config_bin()
        except Exception:
            _pkg_bin = None
        try:
            _pkg_path = self.generators_folder
        except Exception:
            _pkg_path = None
        if _pkg_bin:
            os.environ["PKG_CONFIG"] = _pkg_bin
            _pcd = os.path.dirname(_pkg_bin)
            _old_path = os.environ.get("PATH", "")
            if _pcd and _pcd not in _old_path.split(os.pathsep):
                os.environ["PATH"] = _pcd + os.pathsep + _old_path if _old_path else _pcd
        if _pkg_path and os.path.isdir(_pkg_path):
            _old_pc = os.environ.get("PKG_CONFIG_PATH", "")
            if _pkg_path not in _old_pc.split(os.pathsep):
                os.environ["PKG_CONFIG_PATH"] = _pkg_path + os.pathsep + _old_pc if _old_pc else _pkg_path
        try:
            self._sanitize_hmbs_shell_scripts(tmpdir, _cc, _cxx, _sdk_lib,
                                              _pkg_bin, _pkg_path)
        except Exception:
            pass
        # Standard helper (enscript 1.6.6 / epsilon 0.9.2 precedent): the
        # toolchain composes configure args plus CFLAGS/LDFLAGS/CC, so the
        # early conftest link sees the intact OHOS toolchain env. A
        # hand-rolled `sh configure` invocation risked dropping those and
        # surfacing as "C compiler cannot create executables".
        autotools = Autotools(self)
        try:
            autotools.configure()
        except Exception:
            # Tenth round: targeted failure-block extraction (replaces
            # ninth-round tail-60 dump, which the summarizer truncated
            # to an empty "configure: exit 77"). Emit the compiler-check
            # block plus linker error lines; re-raised unchanged, no
            # check skipped.
            import glob as _glob
            _logs = _glob.glob(
                os.path.join(self.build_folder, "**", "config.log"),
                recursive=True)
            for _log in _logs[:2]:
                try:
                    with open(_log, "r", encoding="utf-8",
                              errors="replace") as _f:
                        _lines = _f.read().splitlines()
                    _anchor = -1
                    for _i, _ln in enumerate(_lines):
                        if "checking whether the C compiler works" in _ln:
                            _anchor = _i
                    if _anchor >= 0:
                        _block = _lines[_anchor:_anchor + 40]
                    else:
                        _block = _lines[-40:]
                    self.output.info(
                        "HMBS_CONFIG_FAIL file=%s anchor=%d total=%d" % (
                            _log, _anchor, len(_lines)))
                    for _ln in _block:
                        self.output.info("HMBS_CONFIG_FAIL | " + _ln[:500])
                    # Extra: any linker/compiler error lines anywhere.
                    _errs = [_ln for _ln in _lines
                             if ("error" in _ln.lower() or "cannot create" in _ln.lower()
                                 or "failed program" in _ln.lower())]
                    for _ln in _errs[-10:]:
                        self.output.info("HMBS_CONFIG_FAIL | err: " + _ln[:500])
                except OSError:
                    pass
            raise
        # R9/HMDFS: single job only (jobserver fifo EPERM under -jN).
        autotools.make(args=["-j1"])

    def _write_install_shim(self):
        """Write the mkdir/cp install shim (wv/1.2.9 pattern).

        Uses os.open with mode 0o755 so no separate chmod syscall is
        needed to make the shim executable (chmod capability = 0 on the
        preflight worker). Returns the shim absolute path.
        """
        shim_dir = os.path.join(self.build_folder, "_ohos_install_shim")
        try:
            os.makedirs(shim_dir, exist_ok=True)
        except OSError:
            pass
        install = os.path.join(shim_dir, "install")
        try:
            fd = os.open(install,
                         os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o755)
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                stream.write(_INSTALL_SHIM)
        except OSError:
            try:
                with open(install, "w", encoding="utf-8",
                          newline="\n") as stream:
                    stream.write(_INSTALL_SHIM)
            except OSError:
                pass
        return install

    def _redirect_install_to_shim(self, shim_install):
        """Point generated Makefiles at the shim (wv/1.2.9 pattern).

        Rewrites INSTALL/install_sh/mkdir_p/MKDIR_P assignments in every
        generated Makefile under build_folder so `make install` uses the
        mkdir/cp shim instead of the HMBS install that drops the libtool
        archive copy. Only assignment lines are touched; no build, check
        or test logic is changed.
        """
        replacements = {
            "INSTALL = ": "INSTALL = {}".format(shim_install),
            "install_sh = ": "install_sh = {}".format(shim_install),
            "mkdir_p = ": "mkdir_p = {} -d".format(shim_install),
            "MKDIR_P = ": "MKDIR_P = {} -d".format(shim_install),
        }
        for root, _, files in os.walk(self.build_folder):
            for name in files:
                if name != "Makefile":
                    continue
                makefile = os.path.join(root, name)
                try:
                    with open(makefile, "r", encoding="utf-8",
                              errors="ignore") as stream:
                        lines = stream.readlines()
                except OSError:
                    continue
                changed = False
                output = []
                for line in lines:
                    stripped = line.lstrip()
                    replacement = next((
                        value for prefix, value in replacements.items()
                        if stripped.startswith(prefix)), None)
                    if replacement is None:
                        output.append(line)
                        continue
                    ending = (
                        "\r\n" if line.endswith("\r\n")
                        else "\n" if line.endswith("\n")
                        else "")
                    indent = line[:len(line) - len(stripped)]
                    output.append(indent + replacement + ending)
                    changed = True
                if changed:
                    try:
                        with open(makefile, "w", encoding="utf-8",
                                  newline="\n") as stream:
                            stream.writelines(output)
                    except OSError:
                        pass

    def _tolerate_chmod_in_makefiles(self):
        """Make bare chmod calls best-effort (cataract/1.0.0 pattern).

        libtool's install mode runs a separate `chmod 644 <dest>` after
        the copy; on HMDFS (HMBS_CAP_CHMOD=0) chmod is unsupported. Only
        the chmod root is tolerated (`|| true`); the copy itself still
        must succeed, and no test target is touched.
        """
        import re as _re
        try:
            _base = self.build_folder
        except (TypeError, AttributeError):
            return
        if not _base or not os.path.isdir(_base):
            return
        for root, _, files in os.walk(_base):
            for name in files:
                if name != "Makefile":
                    continue
                path = os.path.join(root, name)
                try:
                    with open(path, "r", encoding="utf-8",
                              errors="replace") as f:
                        content = f.read()
                except OSError:
                    continue
                orig = content
                if "chmod 644" in content:
                    content = _re.sub(
                        r"chmod\s+644\s+([^\n;]+)",
                        r"chmod 644 \1 || true", content)
                if "chmod 755" in content:
                    content = _re.sub(
                        r"chmod\s+755\s+([^\n;]+)",
                        r"chmod 755 \1 || true", content)
                if content != orig:
                    try:
                        with open(path, "w", encoding="utf-8",
                                  newline="\n") as f:
                            f.write(content)
                    except OSError:
                        pass

    def package(self):
        tmpdir = self._hmbs_tmpdir()
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir
        os.environ["HMBS_TMPDIR"] = tmpdir
        os.environ["SHELL"] = "/bin/sh"
        os.environ["CONFIG_SHELL"] = "/bin/sh"
        self._sanitize_hmbs_shell_scripts(tmpdir)
        # 2026-09-19 package() install fix (readonly_tmp-adjacent FS caps):
        # libtool `install -c .libs/libfixbuf.a <pkg>/lib/libfixbuf.a` via
        # the HMBS install echoes success but leaves no file, so the
        # follow-up `chmod 644 <pkg>/lib/libfixbuf.a` dies with ENOENT
        # (build() line 1006, HMBS caps chmod=0/hardlink=0/install_shim).
        # Adapt the wv/1.2.9 + cataract/1.0.0 precedent: redirect the
        # generated Makefiles at a mkdir/cp shim (chmod best-effort) and
        # tolerate bare chmod in Makefiles. Only the install copy path is
        # touched; build, checks and test posture are unchanged.
        try:
            _shim = self._write_install_shim()
            self._redirect_install_to_shim(_shim)
            self._tolerate_chmod_in_makefiles()
        except Exception:
            pass
        autotools = Autotools(self)
        autotools.install(args=["-j1"])
        # Drop libtool archives; keep the real lib + headers + pkgconfig.
        import glob as _glob

        for la in _glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            try:
                os.remove(la)
            except OSError:
                pass
        copy(
            self,
            "LICENSE*",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["fixbuf"]
        self.cpp_info.requires = ["glib2::glib2"]
        self.cpp_info.system_libs = ["m", "pthread"]
        self.cpp_info.set_property("pkg_config_name", "libfixbuf")
