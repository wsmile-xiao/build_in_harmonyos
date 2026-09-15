#!/usr/bin/env python3
"""Conan recipe — ctpl 0.3.5 (Autotools)

CTPL (C Template Parser Library) — C template engine library (libctpl +
optional `ctpl` CLI tool). Autotools release tarball with pre-generated
configure + Makefile.in.

Upstream: https://ctpl.tuxfamily.org/ (mirror https://github.com/b4n/ctpl)
License: GPL-3.0-or-later
"""

import glob as _glob
import json
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class CtplConan(ConanFile):
    name = "ctpl"
    version = "0.3.5"
    description = "C Template Parser Library — fast template engine in C"
    license = "GPL-3.0-or-later"
    homepage = "https://ctpl.tuxfamily.org/"
    url = "https://github.com/b4n/ctpl"
    topics = ("template", "parser", "ctemplate")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # glib provides glib-2.0 + gio-2.0 (+ gio-unix-2.0 for the CLI tool).
        # 2.88.0 is the registry-uploaded autotools-era version (cassbeam /
        # cdemud precedent); transitive propagation so test_package linking
        # ctpl::ctpl also sees glib headers/libs.
        self.requires("zlib/1.3.1.1", override=True)
        self.requires("glib/2.88.0", transitive_headers=True, transitive_libs=True)

    def build_requirements(self):
        # configure.ac uses PKG_CHECK_MODULES(GLIB/GIO/CTPL_CLI): needs a
        # pkg-config binary on PATH. pkgconf recipe only ships `pkgconf`,
        # PkgConfigDeps + conanbuild PATH expose it; AutotoolsToolchain
        # forwards PKG_CONFIG. Precedent: cassbeam/castget.
        self.tool_requires("pkgconf/3.0.5")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "ctpl %s only supports Linux and OHOS, got os=%s" % (self.version, self.settings.os)
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        self._patch_pcre2_pc_static()
        tc = AutotoolsToolchain(self)
        # HarmonyOS: config.guess cannot recognise OHOS; pin GNU triplets so
        # configure skips the guess probe (compiler still targets OHOS via
        # toolchain CFLAGS/LDFLAGS/sysroot). Precedent: cdecl/castget.
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # E015: upstream AM_GNU_GETTEXT([external]) probes
        # "GNU gettext in libc/libintl" and both say no on OHOS
        # (CI #44690: NLS=no, INTLLIBS empty), yet ctpl-i18n.c calls
        # bindtextdomain/g_dgettext unconditionally and static
        # libglib-2.0.a/libgio-2.0.a need g_libintl_* from glib's
        # vendored proxy-libintl. Put the absolute libintl archive on
        # LDFLAGS so configure link probes and every libtool link see
        # it (absolute path = plain file for libtool, never a stale
        # .la lookup; addrwatch precedent uses -lintl in extra_ldflags).
        for _intl in self._intl_abs_archives():
            tc.extra_ldflags.append(_intl)
            self.output.info("[ok] extra LDFLAGS intl %s" % _intl)
            break
        else:
            tc.extra_ldflags.append("-lintl")
        tc.generate()

    def _pcre2_abs_archives(self):
        """Locate pcre2 static archives for absolute-path linking.

        E236: pcre2 recipe ships .la files with libdir='//lib'
        (--prefix=/ artefact). When libtool sees `-lpcre2-8` it prefers
        the stale .la over the sibling .a and aborts with
        "//lib/libpcre2-8.la is not a valid libtool archive".
        An absolute `/path/libpcre2-8.a` on the link line is treated
        as a plain file, so libtool never opens the .la.
        Precedent: babeltrace/libgsf (patch pcre2.pc Libs to .a).
        """
        for dep_name in ("pcre2",):
            try:
                dep = self.dependencies[dep_name]
            except Exception:
                continue
            try:
                pkg = dep.package_folder
            except Exception:
                pkg = None
            if pkg:
                for sub in ("lib", "lib64"):
                    for base in ("libpcre2-8.a", "libpcre2-posix.a"):
                        cand = os.path.join(pkg, sub, base)
                        if os.path.isfile(cand):
                            yield cand
        # Transitive fallback: scan any host dep libdir for the archives.
        try:
            hosts = list(self.dependencies.host.values())
        except Exception:
            hosts = []
        for dep in hosts:
            try:
                libdirs = list(getattr(dep.cpp_info, "libdirs", []))
            except Exception:
                continue
            for libdir in libdirs:
                if not libdir or not os.path.isdir(libdir):
                    continue
                for base in ("libpcre2-8.a", "libpcre2-posix.a"):
                    cand = os.path.join(libdir, base)
                    if os.path.isfile(cand):
                        yield cand

    def _intl_abs_archives(self):
        """Locate the vendored proxy-libintl archive inside glib.

        glib/2.88.0 vendors proxy-libintl and exposes it as `intl` in
        the glib-2.0/gio-2.0 component libs, but ctpl's own
        AM_GNU_GETTEXT probe resolves to NLS=no/INTLLIBS empty on OHOS
        (CI #44690) so no -lintl ever reaches the link line. Yield the
        absolute archive (plain file for libtool) so callers can append
        it without a -L search. Prefer the static .a (default_options
        shared=False); fall back to the shared object when static is
        absent. Precedent: zeitgeist test_package GLIB_LIBINTL.
        """
        for dep_name in ("glib",):
            try:
                dep = self.dependencies[dep_name]
            except Exception:
                continue
            try:
                pkg = dep.package_folder
            except Exception:
                pkg = None
            if pkg:
                for sub in ("lib", "lib64"):
                    for base in ("libintl.a", "libintl.so"):
                        cand = os.path.join(pkg, sub, base)
                        if os.path.isfile(cand):
                            yield cand
                            return
        try:
            hosts = list(self.dependencies.host.values())
        except Exception:
            hosts = []
        for dep in hosts:
            try:
                libdirs = list(getattr(dep.cpp_info, "libdirs", []))
            except Exception:
                continue
            for libdir in libdirs:
                if not libdir or not os.path.isdir(libdir):
                    continue
                for base in ("libintl.a", "libintl.so"):
                    cand = os.path.join(libdir, base)
                    if os.path.isfile(cand):
                        yield cand
                        return

    def _patch_pcre2_pc_static(self):
        """Rewrite generated pcre2 .pc Libs to absolute .a paths."""
        archives = []
        seen = set()
        for cand in self._pcre2_abs_archives():
            if cand not in seen:
                seen.add(cand)
                archives.append(cand)
        if not archives:
            self.output.warning("pcre2 static archives not found; skipping .pc static patch")
            return
        have_8 = any(a.endswith("libpcre2-8.a") for a in archives)
        have_posix = any(a.endswith("libpcre2-posix.a") for a in archives)
        repl = " ".join(sorted(archives))
        patched = 0
        try:
            pc_dir = self.generators_folder
        except Exception:
            pc_dir = None
        if not pc_dir or not os.path.isdir(pc_dir):
            return
        for name in os.listdir(pc_dir):
            if not name.endswith(".pc"):
                continue
            pc = os.path.join(pc_dir, name)
            try:
                with open(pc, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except OSError:
                continue
            orig = content
            if "-lpcre2-8" in content and have_8:
                for a in sorted(archives):
                    if a.endswith("libpcre2-8.a"):
                        content = content.replace("-lpcre2-8", a)
                        break
            if "-lpcre2-posix" in content and have_posix:
                for a in sorted(archives):
                    if a.endswith("libpcre2-posix.a"):
                        content = content.replace("-lpcre2-posix", a)
                        break
            # Bare `-lpcre2` (some .pc use the short name).
            if re.search(r"(?<!\w)-lpcre2(?![\w-])", content):
                for a in sorted(archives):
                    if a.endswith("libpcre2-8.a"):
                        content = re.sub(r"(?<!\w)-lpcre2(?![\w-])", a, content)
                        break
            if content != orig:
                with open(pc, "w", encoding="utf-8", newline="\n") as f:
                    f.write(content)
                patched += 1
                self.output.info("[ok] pcre2 static patched %s -> %s" % (pc, repl))
        if patched == 0:
            self.output.info("pcre2 .pc static patch: no -lpcre2 tokens found (already static?)")

    def _patch_configure_umask(self):
        # E011: configure/config.status use `umask 077 && mktemp -d` which
        # yields an unwritable dir on HMDFS; relax to 022 (variable form only,
        # no baked absolute paths).
        for root, _, files in os.walk(self.source_folder):
            if "configure" not in files:
                continue
            cfg = os.path.join(root, "configure")
            try:
                with open(cfg, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
            except OSError:
                continue
            if "umask 077" in content:
                content = content.replace("umask 077", "umask 022")
                with open(cfg, "w", encoding="utf-8", newline="\n") as f:
                    f.write(content)
                self.output.info("[ok] relaxed umask 077 -> 022 in %s" % cfg)

    def _write_install_shim(self):
        # HMDFS: toybox install rejects chmod and the HMBS-provided
        # runtime/.../bin/install shim only accepts single-file two-arg
        # calls (E182/E188: adms/libgsf/lzop/libxcb/xeyes precedent).
        # libtool install plus automake install-* rules need mkdir/cp
        # semantics with multi-source support; chmod is best-effort
        # (HMBS_CAP_CHMOD=0). Created with os.open 0o755 so no chmod
        # dependency for executability.
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
            "  mkdir -p \"$(dirname \"$dest\")\"\n"
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
        return install

    def _redirect_install_to_shim(self, shim_install):
        # configure bakes the probed install path into every generated
        # Makefile's INSTALL variable. Point it at our cp/mkdir shim so
        # `make install` (libtool + automake rules) never invokes the
        # HMDFS-incompatible install. INSTALL_DATA/INSTALL_PROGRAM
        # reference ${INSTALL} and are recomputed automatically.
        for root, _, files in os.walk(self.build_folder):
            if "Makefile" not in files:
                continue
            mf = os.path.join(root, "Makefile")
            try:
                with open(mf, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except OSError:
                continue
            if "INSTALL =" not in content:
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
                with open(mf, "w", encoding="utf-8", newline="\n") as f:
                    f.writelines(lines)
                self.output.info("[ok] install shim redirected %s" % mf)

    def build(self):
        apply_conandata_patches(self)
        self._patch_configure_umask()
        # HMDFS: parent dirs may be unresolvable via getcwd(); preset PWD so
        # the shell pwd builtin takes the logical path (cdecl precedent).
        try:
            os.chdir(self.build_folder)
        except OSError:
            self.output.warning("chdir(build_folder) failed; relying on PWD fallback")
        os.environ["PWD"] = self.build_folder
        # E002: device /tmp is read-only erofs; point TMPDIR at a writable
        # dir (hmbs-injected TMPDIR first, else build-folder .tmp).
        tmpdir = os.environ.get("TMPDIR") or os.path.join(self.build_folder, ".tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir
        autotools = Autotools(self)
        autotools.configure()
        # E236: libtool gives visible .la files precedence over sibling .a.
        # A relocated Conan dep (pcre2 via glib) keeps a stale
        # `libdir='//lib'` / `//lib/libpcre2-8.la` reference, so the
        # libctpl.la link aborts with "was moved / is not a valid libtool
        # archive". Two layers (babeltrace/libgsf precedent): generate-time
        # .pc static patch plus here copy only the required .a files into a
        # build-private la-free directory, redirect the upstream-scoped LIBS
        # variables (-L<shadow>, pcre2 tokens as absolute .a) in the
        # generated Makefiles. The Conan cache is left untouched; only the
        # two known-stale pcre2 archives use absolute paths (plain files for
        # libtool, never nested members).
        shadow = self._stage_dependency_archives()
        self._patch_makefiles_la_free(shadow)
        # E182/E188: redirect install to cp/mkdir shim before any make
        # install so libtool/automake never hit the single-file-only HMBS
        # shim or toybox chmod rejection (xeyes/wv precedent).
        shim = self._write_install_shim()
        self._redirect_install_to_shim(shim)
        autotools.make(args=["-j1"])
        self._run_upstream_tests(autotools)

    def _stage_dependency_archives(self):
        """Copy every host dependency static archive into a la-free dir."""
        dest = os.path.join(self.build_folder, ".dependency-archives")
        if os.path.isdir(dest):
            shutil.rmtree(dest, ignore_errors=True)
        os.makedirs(dest, exist_ok=True)
        copied = 0
        for dep in self.dependencies.host.values():
            for libdir in getattr(dep.cpp_info, "libdirs", []):
                if not libdir or not os.path.isdir(libdir):
                    continue
                for entry in os.listdir(libdir):
                    if not entry.endswith(".a"):
                        continue
                    dst = os.path.join(dest, entry)
                    if os.path.isfile(dst):
                        continue
                    shutil.copy2(os.path.join(libdir, entry), dst)
                    copied += 1
        self.output.info(
            "[ok] staged %d static archives into %s (la-free)" % (copied, dest)
        )
        if copied == 0:
            raise RuntimeError(
                "no dependency static archives staged; cannot isolate libtool metadata"
            )
        return dest

    def _patch_makefiles_la_free(self, shadow):
        """Redirect GLIB/GIO/CTPL_CLI LIBS to the la-free shadow dir.

        PKG_CHECK_MODULES bakes pkg-config `-L<cache-lib> -lfoo` strings into
        every generated Makefile (src, testsuite, ...). The stale `-L` dirs
        point at Conan-cache .la files with invalid `libdir='//lib'`, so
        libtool would follow a dead path. Rewrite the link variables
        in-place in all generated Makefiles: all `-L` tokens become the
        single shadow dir (which holds copies of the .a files and no .la
        files); pcre2 `-l` tokens become absolute .a paths so libtool never
        opens the stale `//lib/libpcre2-8.la`; the vendored proxy-libintl
        archive is appended where missing (E015: upstream NLS=no leaves
        INTLLIBS empty yet ctpl-i18n.c + static libglib need g_libintl_*,
        CI #44690); other `-l`/flags are kept verbatim so the exact
        configure-detected flag set is preserved.

        File rewrite (not `make VAR="..."` command-line overrides): a
        space-containing `VAR=value` passed via Autotools.make args is
        re-joined into one shell string without quoting, so make splits it
        into separate argv entries (`-lfoo` becomes a goal/option) and aborts
        with `empty variable name`. Editing the file avoids shell quoting
        entirely (bitlbee-facebook precedent passes la-free via env/file,
        never via make argv; E566 appends missing -lintl via xxx_LDADD
        file patch for the same reason).
        """
        # Absolute pcre2 archives: libtool treats them as plain files and
        # skips the stale .la lookup (babeltrace/libgsf precedent). Resolve
        # once here as a safety net in case the generate-time .pc patch was
        # incomplete (e.g. configure cached flags before the patch).
        pcre2_map = {}
        for cand in self._pcre2_abs_archives():
            if cand.endswith("libpcre2-8.a"):
                pcre2_map["-lpcre2-8"] = cand
            elif cand.endswith("libpcre2-posix.a"):
                pcre2_map["-lpcre2-posix"] = cand
        # Absolute proxy-libintl archive (plain file for libtool).
        intl_abs = None
        for cand in self._intl_abs_archives():
            intl_abs = cand
            break
        if intl_abs is None:
            # Shadow copy fallback: _stage_dependency_archives copies every
            # host .a (including glib's libintl.a) into the la-free dir.
            cand = os.path.join(shadow, "libintl.a")
            if os.path.isfile(cand):
                intl_abs = cand
        if intl_abs:
            self.output.info("[ok] la-free intl %s" % intl_abs)
        else:
            self.output.warning("libintl archive not found; -lintl links may fail")
        # NOTE: configure substitutes @GLIB_LIBS@/@GIO_LIBS@ into
        # libctpl_la_LIBADD / LDADD literals at configure time, so patching
        # only the GLIB_LIBS/GIO_LIBS variables leaves the actual
        # `test` link (test_LDADD = $(libctpl_la_LIBADD)) on the stale -L
        # without -lintl (CI #44690 CCLD test: undefined g_libintl_*).
        # Hence patch every link variable, not just the PKG_* ones.
        link_var = re.compile(
            r"^((?:[A-Za-z0-9_]+_(?:LIBS|LIBADD|LDADD)|LDADD|LIBS|INTLLIBS|LIBINTL)\s*=\s*)(.*)$"
        )
        patched_files = 0
        patched_vars = set()
        for root, _, files in os.walk(self.build_folder):
            if "Makefile" not in files:
                continue
            mf = os.path.join(root, "Makefile")
            try:
                with open(mf, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
            except OSError:
                continue
            changed = False
            out = []
            for line in lines:
                m = link_var.match(line.rstrip("\n"))
                if m:
                    varname = m.group(1).split("=")[0].strip()
                    # Skip compile-flag variables that merely contain
                    # LIBS as a substring guard (CFLAGS/CPPFLAGS never
                    # match the regex above, kept for clarity).
                    if "CFLAGS" in varname or "CPPFLAGS" in varname:
                        out.append(line)
                        continue
                    prefix, val = m.group(1), m.group(2).strip()
                    if val:
                        kept = []
                        for t in val.split():
                            if t.startswith("-L"):
                                continue
                            if t in pcre2_map:
                                kept.append(pcre2_map[t])
                            elif t == "-lpcre2" and "-lpcre2-8" in pcre2_map:
                                kept.append(pcre2_map["-lpcre2-8"])
                            elif t in ("-lintl", "libintl.la") and intl_abs:
                                kept.append(intl_abs)
                            else:
                                kept.append(t)
                        # E015: append the vendored intl archive where the
                        # upstream link line has no intl token at all.
                        if intl_abs and not any(
                            ("intl" in k) for k in kept
                        ):
                            kept.append(intl_abs)
                        new_val = "-L%s" % shadow
                        if kept:
                            new_val += " " + " ".join(kept)
                        out.append(prefix + new_val + "\n")
                        changed = True
                        patched_vars.add(varname)
                        continue
                out.append(line)
            if changed:
                with open(mf, "w", encoding="utf-8", newline="\n") as f:
                    f.writelines(out)
                patched_files += 1
                self.output.info("[ok] la-free patched %s" % mf)
        if patched_files == 0 or not patched_vars:
            raise RuntimeError(
                "cannot derive la-free GLIB/GIO lib overrides from generated Makefiles"
            )
        self.output.info(
            "[ok] la-free: %d Makefiles, vars=%s, shadow=%s"
            % (patched_files, sorted(patched_vars), shadow)
        )

    def _run_upstream_tests(self, autotools):
        """Run `make check` (automake TESTS) and emit the HMBS marker.

        Upstream testsuite/Makefile.am registers TESTS = parsing-tests,
        float-test, read-number-test (+ tests.sh when the CLI tool is built).
        parsing-tests itself walks testsuite/success/ (14 templates) and
        testsuite/fail/ (6 templates) against testsuite/environ. Counts below
        come from the automake test-suite.log summary, cross-checked against
        PASS:/FAIL: result lines (cdecl precedent).
        """
        rc = 0
        try:
            autotools.make(target="check", args=["-j1"])
        except Exception as exc:  # noqa: BLE001 - collect real counts before raising
            rc = 1
            self.output.warning("make check returned failure (will verify counts): %s" % exc)
        total = passed = failed = skipped = 0
        logs = _glob.glob(os.path.join(self.build_folder, "**", "test-suite.log"), recursive=True)
        for log in logs:
            try:
                with open(log, "r", encoding="utf-8", errors="ignore") as _f:
                    text = _f.read()
            except OSError:
                continue
            for key in ("TOTAL", "PASS", "FAIL", "SKIP"):
                m = re.search(r"^# %s:\s+(\d+)" % key, text, re.M)
                if m:
                    n = int(m.group(1))
                    if key == "TOTAL":
                        total += n
                    elif key == "PASS":
                        passed += n
                    elif key == "FAIL":
                        failed += n
                    else:
                        skipped += n
        # XFAIL/XPASS/ERROR contribute to failures when present.
        for log in logs:
            try:
                with open(log, "r", encoding="utf-8", errors="ignore") as _f:
                    text = _f.read()
            except OSError:
                continue
            for key in ("XFAIL", "XPASS", "ERROR"):
                m = re.search(r"^# %s:\s+(\d+)" % key, text, re.M)
                if m:
                    n = int(m.group(1))
                    if key in ("XPASS", "ERROR"):
                        failed += n
        executed = total - skipped
        self.output.info(
            "upstream make check: total=%d executed=%d passed=%d failed=%d skipped=%d"
            % (total, executed, passed, failed, skipped)
        )
        # Falsifiability: a zero-execution PASS (empty suite / harness that
        # silently skipped everything) must not be reported as passed.
        if total == 0 or executed == 0:
            raise RuntimeError("make check produced no executed test cases")
        # Reference fixtures must be non-empty: an empty testsuite dir would
        # let every comparison trivially pass (toybox-tar precedent).
        suite_dir = os.path.join(self.source_folder, "testsuite", "success")
        try:
            names = [n for n in os.listdir(suite_dir) if not n.endswith("-output")]
            sizes = [os.path.getsize(os.path.join(suite_dir, n)) for n in names]
            if not names or any(s == 0 for s in sizes):
                raise RuntimeError("testsuite fixtures missing or empty: %r" % names)
        except OSError as exc:
            raise RuntimeError("cannot verify testsuite fixtures: %s" % exc)
        status = "passed" if rc == 0 and failed == 0 and executed == passed else "failed"
        upstream = {
            "status": status,
            "framework": "automake",
            "command": "make check -j1",
            "discovered": total,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))
        result_file = os.path.join(self.build_folder, "upstream_test_result.json")
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(upstream, f, ensure_ascii=False)
        if status != "passed":
            for log in logs:
                self.output.error("=== %s ===" % log)
            raise RuntimeError(
                "upstream tests failed: total=%d passed=%d failed=%d skipped=%d"
                % (total, passed, failed, skipped)
            )

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # E236 verification: the final package must not ship libtool
        # metadata; downstream libtool links would otherwise re-read stale
        # dependency_libs paths.
        lib_dir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(lib_dir):
            for entry in os.listdir(lib_dir):
                if entry.endswith(".la"):
                    os.remove(os.path.join(lib_dir, entry))
                    self.output.info("[ok] removed libtool archive %s" % entry)
        result_file = os.path.join(self.build_folder, "upstream_test_result.json")
        if os.path.isfile(result_file):
            from conan.tools.files import copy

            copy(self, "upstream_test_result.json", self.build_folder,
                 os.path.join(self.package_folder, "res"))

    def package_info(self):
        self.cpp_info.libs = ["ctpl"]
        self.cpp_info.set_property("cmake_file_name", "ctpl")
        self.cpp_info.set_property("cmake_target_name", "ctpl::ctpl")
        self.cpp_info.set_property("pkg_config_name", "ctpl")
        self.cpp_info.requires = ["glib::glib-2.0", "glib::gio-2.0"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
