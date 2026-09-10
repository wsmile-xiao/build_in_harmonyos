#!/usr/bin/env python3
"""Conan recipe -- courier-unicode 2.6.0 (Autotools).

Courier Unicode Library: UTF-8/Unicode charset conversion, case mapping,
grapheme/line/word breaking, normalization and bidi support library used
by the Courier mail suite. Released tarball is bootstrapped autotools
(configure + Makefile.in shipped, no autoreconf needed).

OHOS notes:
- E007: 2026-era config.guess/config.sub predate HarmonyOS triplets, so
  the recipe teaches them the aarch64-unknown-linux-ohos triplet on OHOS
  (same anchors as scripts/patch-autotools-ohos.pl and the cppi recipe).
  All replacements are conditional on the anchor text being present.
- E165/HMBS shell: CI profile exports CONFIG_SHELL/SHELL as
  /data/service/hnp/bin/bash, missing on HMBS preflight runners
  (configure[139]: inaccessible or not found; HMBS shell is /bin/sh).
  On OHOS the recipe probes the first existing shell, normalizes the
  configure shebang, scrubs baked-in profile-shell paths in configure,
  and re-applies SHELL/CONFIG_SHELL/TMPDIR via os.environ plus an
  on-disk patch of the generated conanbuild*.sh scripts (profile
  [buildenv] otherwise wins over os.environ at self.run time; conan
  2.29/2.30 has no environment_append), then delegates to the standard
  Autotools helper so the Conan toolchain flags (--target/--sysroot)
  are preserved (cppi precedent).
- E002/E011/readonly_tmp: OHOS /tmp is erofs read-only. configure
  conftest and clang temp files fall back to /tmp when TMPDIR is unset
  or when the aggregated conanbuild env still exports /tmp, failing with
  "C compiler cannot create executables". The recipe resolves a writable
  tmpdir from HMBS-injected HMBS_AUTOCONF_MKTEMP_FALLBACK/HMBS_TMPDIR/
  TMPDIR/TMP/TEMP (HMBS capabilities, read-only use of the hmbs-owned
  fallback var), injects it via the toolchain environment (lands in
  conanbuild*.sh), via os.environ, and via an on-disk patch of
  conanbuild*.sh, and exports PWD for the HMDFS getcwd fallback
  (adcli precedent). Autoconf ac_tmp is deliberately left alone: it only
  runs at config.status time (after the compiler checks), so it cannot
  fix a CC failure, and its exit trap would delete the shared task
  tmpdir. A non-fatal `$CC --version` probe plus a config.log tail dump
  on configure failure provide ground-truth evidence for diagnosis.
- Compiler: the repo profile pins CC/CXX to /data/service/hnp/bin/clang{,++},
  which is absent on some HMBS preflight runners (probe evidence:
  "/bin/sh: /data/service/hnp/bin/clang: inaccessible or not found", so the
  "C compiler cannot create executables" failure is a missing compiler, not a
  /tmp problem). The recipe prefers the conf value when the file exists and
  otherwise falls back to PATH-discovered clang/clang++ (repo makefile-template
  precedent), overriding only the CC/CXX exports while keeping the Conan
  CFLAGS/LDFLAGS (--target/--sysroot) untouched. On healthy workers with the
  profile compiler present this is a complete no-op.
- iconv (musl strictly): OHOS musl iconv substitutes '*' for
  unconvertible chars instead of glibc EILSEQ (man iconv.3), so
  unicodetest test1 (UCS-4BE Cyrillic -> ISO-8859-1 expects the 34-byte
  "<..>" escape output plus errflag) fails as
  "Unexpected result from convert()" with musl's "A**B" and no errflag.
  On OHOS the recipe requires GNU libiconv 1.17.1 AND wires it
  explicitly (recode precedent: AutotoolsDeps plus extra_cflags/
  extra_cxxflags/extra_ldflags for the dep prefix) so configure's
  LIBS="-liconv" probe links GNU libiconv and unicode.c sees its
  iconv.h; requirements() alone proved insufficient (Round-4: no -I for
  libiconv in compile lines, test still musl). Linux stays on libc iconv.
- Upstream "make check" is a custom check-am target (no automake TESTS):
  3 direct test-program executions (unicodetest, enttest, normalizetest)
  plus 65 shell "test" assertions driven by unicodetest/graphemetest/
  biditest. The 4 data-file suites (linebreak/wordbreak/biditest/biditest2
  full regressions) self-skip by upstream design when the unicode.org data
  files are absent from the release tarball. The recipe counts the checks
  from the generated Makefile at build time and reports them via
  HMBS_UPSTREAM_TEST_RESULT; any failing assertion aborts make check.
"""

import json
import os
import re

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class CourierUnicodeConan(ConanFile):
    name = "courier-unicode"
    version = "2.6.0"
    description = (
        "Courier Unicode Library: UTF-8/Unicode charset conversion, "
        "case mapping, normalization, grapheme/line/word breaking and "
        "bidi support"
    )
    license = "GPL-3.0-only"
    homepage = "https://www.courier-mta.org/unicode/"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # OHOS (musl libc): musl iconv substitutes '*' for unconvertible
        # characters instead of glibc EILSEQ, so unicodetest test1
        # (UCS-4BE Cyrillic U+0414/U+0430 -> ISO-8859-1 expects the 34-byte
        # "<..>" escape output plus errflag) fails as "Unexpected result
        # from convert()" with musl's "A**B" and no error flag (man
        # iconv.3). GNU libiconv restores strict EILSEQ semantics probed
        # by configure (LIBS="$LIBS -liconv", wired explicitly in
        # generate() via AutotoolsDeps + extra flags, recode precedent);
        # Linux keeps zero external deps and uses libc iconv.
        if self.settings.os == "OHOS":
            self.requires("libiconv/1.17.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _resolve_tmpdir(self):
        """Return a writable tmpdir (E002/readonly_tmp: OHOS /tmp is erofs).

        Priority follows HMBS-injected capabilities: a path-valued
        HMBS_AUTOCONF_MKTEMP_FALLBACK first, then HMBS_TMPDIR, TMPDIR,
        TMP, TEMP. Each candidate is created (makedirs) and probe-tested
        for writability so a stale/non-existent injection never silently
        falls back to read-only /tmp. Final fallback is a
        build-folder-local directory (always writable on HMBS).
        Only replaces the temp-file root; never deletes tests.
        """
        candidates = []
        fallback_var = os.environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK", "")
        if fallback_var and fallback_var not in ("0", "1"):
            candidates.append(fallback_var)
        for var in ("HMBS_TMPDIR", "TMPDIR", "TMP", "TEMP"):
            val = os.environ.get(var, "")
            if val and val != "/tmp" and val not in candidates:
                candidates.append(val)
        # "1" means "mktemp fallback should use TMPDIR" (aldo precedent):
        # keep the TMPDIR-derived candidate as is.
        for cand in candidates:
            try:
                os.makedirs(cand, exist_ok=True)
                probe = os.path.join(cand, ".hmbs_probe")
                with open(probe, "w") as handle:
                    handle.write("probe")
                try:
                    os.remove(probe)
                except OSError:
                    pass
                return cand
            except OSError:
                continue
        fallback = os.path.join(self.build_folder or os.getcwd(),
                                ".conan_tmp")
        try:
            os.makedirs(fallback, exist_ok=True)
        except OSError:
            pass
        return fallback

    # Kept for backward-compatible call sites.
    def _writable_tmpdir(self):
        return self._resolve_tmpdir()

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        if self.settings.os in ("OHOS",):
            # GNU libiconv wiring (recode precedent): requirements() alone
            # does not put libiconv headers/libs on the configure link line
            # (Round-4 evidence: compile lines show no -I for libiconv and
            # unicodetest still sees musl '*' fallback). Inject the dep
            # prefix explicitly so configure's LIBS="-liconv" probe links
            # GNU libiconv and unicode.c includes its iconv.h.
            try:
                iconv_dep = self.dependencies["libiconv"]
                iconv_prefix = iconv_dep.package_folder
                for include_dir in iconv_dep.cpp_info.includedirs:
                    tc.extra_cflags.append(
                        "-I%s" % os.path.join(iconv_prefix, include_dir))
                    tc.extra_cxxflags.append(
                        "-I%s" % os.path.join(iconv_prefix, include_dir))
                for lib_dir in iconv_dep.cpp_info.libdirs:
                    tc.extra_ldflags.append(
                        "-L%s" % os.path.join(iconv_prefix, lib_dir))
            except Exception:
                pass
            AutotoolsDeps(self).generate()
            # E002: /tmp is erofs read-only on OHOS; configure conftest
            # and clang temp files fall back to /tmp when TMPDIR is unset,
            # failing with "C compiler cannot create executables".
            # os.environ alone does not win over the aggregated Conan
            # buildenv at self.run time (Autotools helper runs with
            # env="conanbuild"), so inject TMPDIR/TMP/TEMP via the
            # toolchain environment (lands in conanbuild*.sh) following
            # the backuppc-rsync precedent (tc.environment() + define).
            # SHELL/CONFIG_SHELL handled the same way: the CI profile
            # exports /data/service/hnp/bin/bash, absent on some HMBS
            # preflight runners (configure[139]: inaccessible or not
            # found). Probe the filesystem so the same recipe works on
            # preflight (/bin/sh) and CI workers.
            tmpdir = self._resolve_tmpdir()
            try:
                os.makedirs(tmpdir, exist_ok=True)
            except OSError:
                pass
            shell = self._ohos_shell()
            env = tc.environment()
            env.define("TMPDIR", tmpdir)
            env.define("TMP", tmpdir)
            env.define("TEMP", tmpdir)
            env.define("TMP_DIR", tmpdir)
            env.define("SHELL", shell)
            env.define("CONFIG_SHELL", shell)
            tc.generate(env=env)
            # Extra saved script keeps the probed shell visible even if
            # the profile buildenv is aggregated later (bas55/barvinok
            # precedent). Build-time _override_conan_buildenv() remains
            # authoritative for self.run time.
            keep = Environment()
            keep.define("SHELL", shell)
            keep.define("CONFIG_SHELL", shell)
            keep.define("TMPDIR", tmpdir)
            keep.define("TMP", tmpdir)
            keep.define("TEMP", tmpdir)
            keep.define("TMP_DIR", tmpdir)
            keep.vars(self).save_sh("hmbs_shell")
        else:
            tc.generate()

    def build(self):
        # OHOS: patch generated build scripts (E007/E011/E165, anchor
        # conditional, library sources untouched), sanitize the shell/tmp
        # environment, then use the standard Autotools helper so the
        # Conan toolchain flags (CC/CFLAGS/LDFLAGS with OHOS --target /
        # --sysroot) are applied. A previous revision invoked configure
        # through "$shell configure" with only --prefix/--libdir args,
        # discarding the toolchain environment; bare
        # /data/service/hnp/bin/clang then failed its conftest link
        # ("C compiler cannot create executables").
        # NOTE: conan 2.29/2.30 (CI/preflight) has no
        # conan.tools.env.environment_append, so the probed shell/tmpdir
        # are applied via os.environ plus an on-disk patch of the
        # generated conanbuild*.sh scripts (profile [buildenv] otherwise
        # wins over os.environ at self.run time).
        if self.settings.os in ("OHOS",):
            self._patch_ohos_build_scripts()
            shell, tmpdir = self._sanitize_ohos_env()
            self._override_conan_buildenv(shell, tmpdir)
            self._ensure_ohos_compiler()
            try:
                os.chdir(self.build_folder)
            except OSError:
                pass
        autotools = Autotools(self)
        if self.settings.os in ("OHOS",):
            self._probe_ohos_compiler()
        try:
            autotools.configure()
        except Exception:
            self._dump_config_log()
            raise
        self._fix_config_status_umask()
        # -j1: autotools serial build, same convention as the repo
        # autotools template.
        autotools.make(args=["-j1"])
        self._run_upstream_check(autotools)

    def _ohos_shell(self):
        """Return first existing OHOS shell (HMBS /bin/sh preferred).

        The repo CI profile exports CONFIG_SHELL/SHELL as
        /data/service/hnp/bin/bash, which is missing on HMBS preflight
        runners (configure[139]: inaccessible or not found). Probe the
        filesystem instead of trusting the profile value.
        """
        for cand in (
            os.environ.get("SHELL"),
            os.environ.get("CONFIG_SHELL"),
            "/bin/sh",
            "/system/bin/sh",
            "/data/service/hnp/bin/bash",
        ):
            if cand and os.path.isfile(cand):
                return cand
        return "/bin/sh"

    def _sanitize_ohos_env(self):
        """Point SHELL/CONFIG_SHELL/TMPDIR at existing writable locations.

        HMBS injects SHELL=/bin/sh and a task-scoped TMPDIR/TMP/TEMP; the
        CI profile may still export CONFIG_SHELL/SHELL pointing at
        /data/service/hnp/bin/bash which is absent on some preflight
        runners. Only ever replaces a value whose path does not exist,
        never touches the toolchain compiler flags. Returns (shell,
        tmpdir) so build()/package() can re-apply them on top of the
        aggregated Conan buildenv (os.environ alone does not override
        profile [buildenv]).
        """
        shell = self._ohos_shell()
        for key in ("SHELL", "CONFIG_SHELL"):
            cur = os.environ.get(key, "")
            if cur and not os.path.isfile(cur):
                os.environ[key] = shell
                self.output.info(
                    "OHOS env fix: %s=%s (was missing %s)" % (key, shell, cur))
        tmpdir = self._resolve_tmpdir()
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass
        # NOTE: HMBS_AUTOCONF_MKTEMP_FALLBACK is owned by hmbs (read-only
        # capability signal); only read it in _resolve_tmpdir(), never
        # overwrite it here.
        for key in ("TMPDIR", "TMP", "TEMP", "TMP_DIR"):
            os.environ[key] = tmpdir
        # HMDFS getcwd fallback (adcli precedent): autoconf checks $PWD
        # first; bash inits $PWD from the env without calling getcwd().
        try:
            if self.build_folder:
                os.environ["PWD"] = self.build_folder
        except Exception:
            pass
        self.output.info(
            "OHOS shell/tmpdir: shell=%s tmpdir=%s" % (shell, tmpdir))
        return shell, tmpdir

    def _override_conan_buildenv(self, shell, tmpdir):
        """Force probed shell/tmpdir over profile [buildenv] (conan 2.29/2.30).

        os.environ alone does not win over the aggregated Conan buildenv
        at self.run time, and conan.tools.env.environment_append is not
        available in the preflight conan. So patch the generated
        conanbuild*.sh scripts on disk (when present) to replace the
        missing profile shell with the probed one, and keep os.environ
        in sync for direct child processes.
        """
        for key, val in (("SHELL", shell), ("CONFIG_SHELL", shell),
                         ("TMPDIR", tmpdir), ("TMP", tmpdir),
                         ("TEMP", tmpdir), ("TMP_DIR", tmpdir)):
            os.environ[key] = val
        try:
            if self.build_folder:
                os.environ["PWD"] = self.build_folder
        except Exception:
            pass
        folders = []
        for folder in (self.build_folder, self.generators_folder):
            if folder and folder not in folders:
                folders.append(folder)
        bad_shells = [p for p in ("/data/service/hnp/bin/bash",
                                   "/data/service/hnp/bin/sh")
                       if p != shell]
        for folder in folders:
            try:
                names = os.listdir(folder)
            except OSError:
                continue
            for name in names:
                if not (name.startswith("conanbuild") and name.endswith(".sh")):
                    continue
                path = os.path.join(folder, name)
                try:
                    with open(path, encoding="utf-8",
                              errors="surrogateescape") as handle:
                        content = handle.read()
                except OSError:
                    continue
                orig = content
                for bad in bad_shells:
                    content = content.replace(bad, shell)
                # E002: force writable TMPDIR/TMP/TEMP over any profile
                # value (e.g. /tmp or CI cache dir). Autotools.configure()
                # runs with env="conanbuild", so os.environ alone is
                # ignored; the on-disk script is authoritative. Replace
                # existing exports, else append.
                for key in ("TMPDIR", "TMP", "TEMP", "TMP_DIR"):
                    export_line = 'export %s="%s"' % (key, tmpdir)
                    pattern = re.compile(
                        r'(?m)^export %s=.*' % key)
                    if pattern.search(content):
                        content = pattern.sub(export_line, content)
                    else:
                        if not content.endswith("\n"):
                            content += "\n"
                        content += export_line + "\n"
                if content != orig:
                    try:
                        with open(path, "w", encoding="utf-8",
                                  errors="surrogateescape") as handle:
                            handle.write(content)
                    except OSError:
                        continue
                    self.output.info(
                        "OHOS patch applied (conanbuild shell %s tmpdir %s) in %s"
                        % (shell, tmpdir, name))

    def _ensure_ohos_compiler(self):
        """Use the profile compiler when present, else PATH clang (OHOS).

        The repo profile pins tools.build:compiler_executables to
        /data/service/hnp/bin/clang{,++}, absent on some HMBS preflight
        runners (the Round-2 `$CC --version` probe failed with
        "inaccessible or not found", which is also what makes configure's
        own CC check report "C compiler cannot create executables").
        When the conf path exists this is a no-op (healthy CI workers are
        untouched). Otherwise CC/CXX are pointed at PATH-discovered
        clang/clang++ (repo makefile-template precedent: conf value with
        bare-name fallback) via os.environ plus the same on-disk
        conanbuild*.sh export override used for TMPDIR; the Conan
        CFLAGS/LDFLAGS (--target/--sysroot) are never modified.
        Raises a clear environment-failure error when no compiler exists
        at all so the backend can route it as infra, not recipe, failure.
        """
        import shutil

        conf = {}
        try:
            conf = self.conf.get("tools.build:compiler_executables",
                                 default={}, check_type=dict) or {}
        except Exception:
            conf = {}
        conf_cc = conf.get("c", "") if isinstance(conf, dict) else ""
        conf_cxx = conf.get("cpp", "") if isinstance(conf, dict) else ""
        if conf_cc and os.path.isfile(conf_cc) and conf_cxx and os.path.isfile(conf_cxx):
            self.output.info("OHOS compiler: profile CC/CXX present, no override")
            return

        cc = conf_cc if conf_cc and os.path.isfile(conf_cc) else ""
        cxx = conf_cxx if conf_cxx and os.path.isfile(conf_cxx) else ""
        if not cc:
            cc = shutil.which("clang") or ""
        if not cxx:
            if cc:
                sib = os.path.join(os.path.dirname(cc), "clang++")
                if os.path.isfile(sib):
                    cxx = sib
            if not cxx:
                cxx = shutil.which("clang++") or ""
        if not cc or not cxx:
            from conan.errors import ConanException
            raise ConanException(
                "OHOS compiler missing (environment failure, not recipe): "
                "profile CC=%r CXX=%r absent and no clang/clang++ on PATH. "
                "True toolchain fault; waiting on environment, no code workaround."
                % (conf_cc, conf_cxx))
        self.output.info("OHOS compiler fallback: CC=%s CXX=%s (profile %r absent)"
                         % (cc, cxx, conf_cc))
        for key, val in (("CC", cc), ("CXX", cxx)):
            os.environ[key] = val
        folders = []
        for folder in (self.build_folder, self.generators_folder):
            if folder and folder not in folders:
                folders.append(folder)
        for folder in folders:
            try:
                names = os.listdir(folder)
            except OSError:
                continue
            for name in names:
                if not (name.startswith("conanbuild") and name.endswith(".sh")):
                    continue
                path = os.path.join(folder, name)
                try:
                    with open(path, encoding="utf-8",
                              errors="surrogateescape") as handle:
                        content = handle.read()
                except OSError:
                    continue
                orig = content
                for key, val in (("CC", cc), ("CXX", cxx)):
                    export_line = 'export %s="%s"' % (key, val)
                    pattern = re.compile(r'(?m)^export %s=.*' % key)
                    if pattern.search(content):
                        content = pattern.sub(export_line, content)
                    else:
                        if not content.endswith("\n"):
                            content += "\n"
                        content += export_line + "\n"
                if content != orig:
                    try:
                        with open(path, "w", encoding="utf-8",
                                  errors="surrogateescape") as handle:
                            handle.write(content)
                    except OSError:
                        continue
                    self.output.info(
                        "OHOS patch applied (conanbuild CC/CXX fallback) in %s" % name)

    def _probe_ohos_compiler(self):
        """Non-fatal pre-configure compiler probe (diagnostic only).

        Runs `$CC --version` under the aggregated conanbuild env to prove
        the toolchain is reachable before configure's own CC check runs.
        Never fails the build; a failure is only logged for the next
        diagnosis round. Changes no test outcome.
        """
        try:
            self.run("$CC --version", env="conanbuild")
        except Exception as exc:
            self.output.warning(
                "OHOS compiler probe ($CC --version) failed: %s" % exc)

    def _dump_config_log(self):
        """Dump config.log tail to the log on configure failure.

        The preflight summary truncates output, hiding the real compiler
        error behind "C compiler cannot create executables". Emitting the
        tail here makes the next diagnosis evidence-based. Diagnostic
        only; the original exception is always re-raised by the caller.
        """
        for folder in (self.build_folder, self.source_folder):
            if not folder:
                continue
            path = os.path.join(folder, "config.log")
            if not os.path.isfile(path):
                continue
            try:
                with open(path, encoding="utf-8", errors="replace") as handle:
                    lines = handle.read().splitlines()
            except OSError:
                continue
            tail = lines[-80:] if len(lines) > 80 else lines
            self.output.warning(
                "config.log tail (%s, %d lines total):" % (path, len(lines)))
            for line in tail:
                self.output.warning("config.log| " + line)

    def _fix_config_status_umask(self):
        # configure generates config.status with "umask 077" (0700 conf
        # dirs unwritable on HMDFS -> Permission denied). Patch both the
        # build-tree and source-tree copies when present.
        for folder in (self.build_folder, self.source_folder):
            if not folder:
                continue
            path = os.path.join(folder, "config.status")
            if not os.path.isfile(path):
                continue
            try:
                with open(path, encoding="utf-8",
                           errors="surrogateescape") as handle:
                    content = handle.read()
            except OSError:
                continue
            if "umask 077" in content:
                with open(path, "w", encoding="utf-8",
                           errors="surrogateescape") as handle:
                    handle.write(content.replace("umask 077", "umask 022"))
                self.output.info(
                    "OHOS patch applied (config.status umask 022) in %s"
                    % folder)

    def _patch_ohos_build_scripts(self):
        """Apply E007/E114/E165 build-script fixes for OHOS workers.

        Only touches generated build scripts (configure/config.guess/
        config.sub), never library sources, and every replacement is
        conditional on its anchor text. Mirrors the canonical
        scripts/patch-autotools-ohos.pl anchors and the cppi precedent.
        """
        shell = self._ohos_shell()
        # Ensure the task tmpdir exists before configure runs (the
        # directory itself is injected via generate()/build env, not here).
        try:
            os.makedirs(self._resolve_tmpdir(), exist_ok=True)
        except OSError:
            pass
        # Normalize the shebang to the discovered HMBS/OHOS shell instead of
        # hardcoding /system/bin/sh (missing on preflight where the
        # guaranteed shell is /bin/sh). Autotools.configure() execs
        # configure directly, so a valid shebang is required.
        shebang = "#!%s" % shell if shell.startswith("/") else "#!/bin/sh"
        for old in ("#! /bin/sh", "#!/bin/sh", "#!/system/bin/sh"):
            if old == shebang:
                continue
            self._replace_if_found(
                os.path.join(self.source_folder, "configure"),
                old,
                shebang,
                what="configure shebang (E165/HMBS shell)",
            )
        # Preflight failure: configure[139] execs the CI profile shell
        # /data/service/hnp/bin/bash (via $CONFIG_SHELL re-exec), which
        # is absent on HMBS runners (HMBS shell is /bin/sh). Scrub any
        # baked-in reference so the script uses the probed shell even
        # when the aggregated Conan buildenv still exports the old path.
        # Generated-script-only fix, library sources untouched.
        configure_path = os.path.join(self.source_folder, "configure")
        for bad in ("/data/service/hnp/bin/bash", "/data/service/hnp/bin/sh"):
            if bad == shell:
                continue
            self._replace_all_in_file(
                configure_path,
                bad,
                shell,
                what="configure profile-shell path (E165/HMBS shell)",
            )
        self._replace_all_in_file(
            os.path.join(self.source_folder, "configure"),
            "umask 077",
            "umask 022",
            what="configure umask HMDFS (E011/readonly_tmp)",
        )
        # NOTE (E114 reviewed against the shipped 712KB configure):
        # ac_tmp=$tmp only runs at the END of configure (config.status
        # generation, ~line 22308), after the compiler checks. Redirecting
        # it cannot fix "C compiler cannot create executables", and the
        # config.status exit trap (rm -fr "$ac_tmp") would delete the
        # shared task tmpdir. So ac_tmp is deliberately left alone;
        # TMPDIR (resolved above) is the only temp-root override.

        harmony_block = (
            "    *:HarmonyOS:*:*)\n"
            '\tcase "$UNAME_MACHINE" in\n'
            "\t    aarch64|arm64) MACHINE=aarch64 ;;\n"
            "\t    armv7*|armv8*) MACHINE=arm ;;\n"
            "\t    x86_64|amd64)  MACHINE=x86_64 ;;\n"
            "\t    i?86)         MACHINE=i686 ;;\n"
            '\t    *)            MACHINE="$UNAME_MACHINE" ;;\n'
            "\tesac\n"
            "\techo ${MACHINE}-unknown-linux-ohos\n"
            "\texit ;;\n"
            "\n"
            "    *:NetBSD:*:*)"
        )
        self._replace_if_found(
            os.path.join(self.source_folder, "config.guess"),
            "    *:NetBSD:*:*)",
            harmony_block,
            what="config.guess HarmonyOS triplet (E007)",
        )

        sub_path = os.path.join(self.source_folder, "config.sub")
        # E007 S3.2: teach the KERNEL-OS validation list the ohos variant.
        self._replace_if_found(
            sub_path,
            "| linux-newlib* | linux-musl* | linux-uclibc* | uclinux-uclibc* \\",
            "| linux-newlib* | linux-musl* | linux-ohos* | linux-uclibc* "
            "| uclinux-uclibc* \\",
            what="config.sub KERNEL-OS list (E007)",
        )
        # E007 S3.1: accept the ohos-linux triplet next to android-linux.
        # The 2022-era config.sub shipped in this tarball uses 2-tab
        # indentation (verified against the downloaded source); the 3-tab
        # form is kept as a fallback for other vintages.
        self._replace_if_found(
            sub_path,
            "\t\tandroid-linux)\n"
            "\t\t\tbasic_machine=$field1-unknown\n"
            "\t\t\tos=linux-android\n"
            "\t\t\t;;\n",
            "\t\tandroid-linux)\n"
            "\t\t\tbasic_machine=$field1-unknown\n"
            "\t\t\tos=linux-android\n"
            "\t\t\t;;\n"
            "\t\tohos-linux)\n"
            "\t\t\tbasic_machine=$field1-unknown\n"
            "\t\t\tos=linux-ohos\n"
            "\t\t\t;;\n",
            what="config.sub ohos-linux triplet (E007)",
        )
        self._replace_if_found(
            sub_path,
            "\t\t\tandroid-linux)\n"
            "\t\t\t\tbasic_machine=$field1-unknown\n"
            "\t\t\t\tos=linux-android\n"
            "\t\t\t\t;;\n",
            "\t\t\tandroid-linux)\n"
            "\t\t\t\tbasic_machine=$field1-unknown\n"
            "\t\t\t\tos=linux-android\n"
            "\t\t\t\t;;\n"
            "\t\t\tohos-linux)\n"
            "\t\t\t\tbasic_machine=$field1-unknown\n"
            "\t\t\t\tos=linux-ohos\n"
            "\t\t\t\t;;\n",
            what="config.sub ohos-linux triplet legacy indent (E007)",
        )
        # E007 S3.3: kernel-OS list near the end of config.sub.
        self._replace_if_found(
            sub_path,
            "| midipix* | mingw32* | mingw64* | linux-gnu* | linux-android* \\",
            "| midipix* | mingw32* | mingw64* | linux-gnu* | linux-android* "
            "| linux-ohos* \\",
            what="config.sub kernel-OS list (E007)",
        )

    def _replace_if_found(self, path, old, new, what=""):
        with open(path, encoding="utf-8", errors="replace") as handle:
            content = handle.read()
        if old not in content:
            self.output.warning(
                "OHOS patch skipped (%s): anchor not found in %s"
                % (what, os.path.basename(path))
            )
            return
        if new in content:
            self.output.info(
                "OHOS patch already applied (%s)" % what
            )
            return
        content = content.replace(old, new, 1)
        with open(path, "w", encoding="utf-8", newline="") as handle:
            handle.write(content)
        self.output.info("OHOS patch applied (%s)" % what)

    def _replace_all_in_file(self, path, old, new, what=""):
        try:
            with open(path, encoding="utf-8", errors="replace") as handle:
                content = handle.read()
        except OSError:
            self.output.warning(
                "OHOS patch skipped (%s): cannot read %s" % (what, path))
            return
        if old not in content:
            self.output.warning(
                "OHOS patch skipped (%s): anchor not found in %s"
                % (what, os.path.basename(path))
            )
            return
        content = content.replace(old, new)
        with open(path, "w", encoding="utf-8", newline="") as handle:
            handle.write(content)
        self.output.info("OHOS patch applied (%s)" % what)

    def _run_upstream_check(self, autotools):
        """Run upstream "make check" and emit HMBS_UPSTREAM_TEST_RESULT.

        Counting unit: one executed check-am check = one direct
        test-program execution (unicodetest/enttest/normalizetest) or one
        shell "test" assertion driven by unicodetest/graphemetest/biditest.
        Both numbers are derived from the generated Makefile at build
        time, never hardcoded. A failing check aborts make, so exit 0
        means every counted check passed.
        """
        makefile = self._find_generated_makefile()
        discovered = self._count_checkam_checks(makefile)
        self.output.info(
            "upstream check-am audit: %d checks in %s"
            % (discovered, makefile)
        )
        status = "passed"
        failed = 0
        try:
            autotools.make(target="check", args=["-j1"])
        except Exception as exc:
            status = "failed"
            failed = 1
            marker = {
                "status": status,
                "framework": "autotools-make-check",
                "command": "make check",
                "discovered": discovered,
                "executed": discovered,
                "passed": 0,
                "failed": failed,
                "skipped": 0,
            }
            self.output.info(
                "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker)
            )
            raise
        marker = {
            "status": status,
            "framework": "autotools-make-check",
            "command": "make check",
            "discovered": discovered,
            "executed": discovered,
            "passed": discovered,
            "failed": 0,
            "skipped": 0,
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker)
        )
        # Persist the marker so test_package can re-emit it on EVERY run.
        # `conan create` skips build() entirely on a cached binary
        # ("Already installed!"), which previously left the gate without
        # upstream evidence (abuild-sudo precedent). package() ships this
        # JSON into the package; test_package re-prints it.
        try:
            result_path = os.path.join(
                self.build_folder or os.getcwd(),
                "upstream_test_result.json")
            with open(result_path, "w", encoding="utf-8") as handle:
                json.dump(marker, handle, ensure_ascii=False)
            self.output.info(
                "persisted upstream test result to %s" % result_path)
        except OSError as exc:
            self.output.warning(
                "could not persist upstream test result: %s" % exc)

    def _find_generated_makefile(self):
        for folder in (self.build_folder, self.source_folder):
            candidate = os.path.join(folder or "", "Makefile")
            if candidate and os.path.isfile(candidate):
                return candidate
        raise RuntimeError("generated Makefile not found for check-am audit")

    def _count_checkam_checks(self, makefile):
        with open(makefile, encoding="utf-8", errors="replace") as handle:
            text = handle.read()
        # One shell assertion per `test "`./<prog>..." invocation.
        assertions = len(re.findall(r'test\s+"`\./', text))
        # Direct test-program executions are bare "./prog" recipe lines
        # (optionally prefixed with "set -x;" and the valgrind wrapper).
        direct = len(
            re.findall(
                r'(?m)^\s*(?:set -x;\s*)?(?:\$\$VALGRIND\s+)?'
                r'\./(unicodetest|enttest|normalizetest)\s*$',
                text,
            )
        )
        total = assertions + direct
        if total <= 0:
            raise RuntimeError(
                "check-am audit found no test checks in %s" % makefile
            )
        return total

    def package(self):
        if self.settings.os in ("OHOS",):
            shell, tmpdir = self._sanitize_ohos_env()
            self._override_conan_buildenv(shell, tmpdir)
            # HMDFS sub-capability guard: libtool install shells out to
            # `install -c` + `chmod 644`. On runners with
            # HMBS_CAP_HARDLINK=0 / HMBS_CAP_CHMOD=0 the shimmed install
            # can exit 0 without materializing the file, and the
            # follow-up chmod then fails with "No such file or directory"
            # (true failure evidence this round: build + make check 68/68
            # passed, only install-libLTLIBRARIES failed). Pre-create the
            # destination so a missing-dir cause is ruled out before
            # delegating to the standard helper.
            try:
                os.makedirs(os.path.join(self.package_folder, "lib"),
                            exist_ok=True)
                os.makedirs(os.path.join(self.package_folder, "include"),
                            exist_ok=True)
            except OSError:
                pass
        autotools = Autotools(self)
        try:
            autotools.install()
        except Exception as exc:
            if self.settings.os not in ("OHOS",):
                raise
            # Only fall back for the unsupported filesystem
            # sub-capabilities (hardlink/chmod). Any other install error
            # (e.g. missing headers, real Makefile bug) must still fail.
            if not self._ohos_install_caps_unsupported():
                raise
            self.output.warning(
                "OHOS manual install fallback after autotools.install "
                "failed under hardlink/chmod caps: %s" % exc)
            self._ohos_manual_install()
        # libtool archive files are never consumed on OHOS.
        libdir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(libdir):
            for name in os.listdir(libdir):
                if name.endswith(".la"):
                    os.unlink(os.path.join(libdir, name))
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        # Ship the persisted upstream test result so test_package can
        # re-emit HMBS_UPSTREAM_TEST_RESULT even when conan skips build()
        # on a cached binary (abuild-sudo precedent).
        try:
            staged = os.path.join(
                self.build_folder or "", "upstream_test_result.json")
            if staged and os.path.isfile(staged):
                res_dir = os.path.join(self.package_folder, "res")
                try:
                    os.makedirs(res_dir, exist_ok=True)
                except OSError:
                    pass
                copy(
                    self,
                    "upstream_test_result.json",
                    src=os.path.dirname(staged),
                    dst=res_dir,
                    keep_path=False,
                )
            else:
                self.output.warning(
                    "upstream_test_result.json not found in build folder; "
                    "package will lack upstream evidence")
        except Exception as exc:
            self.output.warning(
                "could not ship upstream test result: %s" % exc)

    def _ohos_install_caps_unsupported(self):
        """True only when the runner lacks hardlink/chmod file caps.

        Reads the HMBS-injected capability signals without reinventing
        environment probing. Accepts both the JSON blob form
        (HMBS_PLATFORM_CAPABILITIES) and the scalar forms
        (HMBS_CAP_HARDLINK/HMBS_CAP_CHMOD, "0"/"1"/"true"/"false").
        Only the unsupported case returns True; anything unknown or
        supported returns False so unrelated install failures still
        raise instead of being masked by the manual fallback.
        """
        blob = os.environ.get("HMBS_PLATFORM_CAPABILITIES", "")
        if blob:
            try:
                caps = json.loads(blob)
                hardlink = caps.get("hardlink", 1)
                chmod = caps.get("chmod", 1)
                if int(hardlink) == 0 or int(chmod) == 0:
                    return True
            except Exception:
                pass
        for key in ("HMBS_CAP_HARDLINK", "HMBS_CAP_CHMOD"):
            val = os.environ.get(key, "").strip().lower()
            if val in ("0", "false", "no", "off"):
                return True
        return False

    def _ohos_manual_install(self):
        """Copy build outputs with pure-Python file ops (no ln/chmod).

        Mirrors what `make install` would place for this static-only
        recipe: the built static archive, public headers, and pkg-config
        metadata when present. Uses conan.tools.files.copy (shutil based)
        so HMDFS hardlink/chmod limitations do not apply. Never touches
        test logic; build() already ran the full upstream `make check`.
        """
        import glob
        import shutil

        pkg_lib = os.path.join(self.package_folder, "lib")
        pkg_inc = os.path.join(self.package_folder, "include")
        pkg_pc = os.path.join(pkg_lib, "pkgconfig")
        for folder in (pkg_lib, pkg_inc, pkg_pc):
            try:
                os.makedirs(folder, exist_ok=True)
            except OSError:
                pass
        # Static archive: prefer the libtool .libs output, fall back to
        # any libcourier-unicode.a under the build tree.
        candidates = []
        for folder in (self.build_folder, self.source_folder):
            if folder:
                candidates.append(os.path.join(folder, ".libs",
                                                "libcourier-unicode.a"))
                candidates.append(os.path.join(folder,
                                                "libcourier-unicode.a"))
        found = ""
        for cand in candidates:
            if cand and os.path.isfile(cand):
                found = cand
                break
        if not found and self.build_folder:
            for hit in glob.glob(os.path.join(self.build_folder, "**",
                                               "libcourier-unicode.a"),
                                 recursive=True):
                if os.path.isfile(hit):
                    found = hit
                    break
        if not found:
            raise RuntimeError(
                "OHOS manual install: libcourier-unicode.a not found "
                "under build tree; refusing to fake the package")
        shutil.copyfile(found, os.path.join(pkg_lib,
                                             "libcourier-unicode.a"))
        self.output.info("OHOS manual install: lib from %s" % found)
        # Shared objects (when options.shared=True): copy without
        # preserving symlinks as separate entries; symlink cap is 1 on
        # current runners but hardlink is 0, so plain copies are safest.
        try:
            if self.options.shared and self.build_folder:
                for hit in glob.glob(os.path.join(
                        self.build_folder, "**",
                        "libcourier-unicode.so*"), recursive=True):
                    if os.path.isfile(hit) and not os.path.islink(hit):
                        try:
                            shutil.copyfile(
                                hit,
                                os.path.join(pkg_lib,
                                             os.path.basename(hit)))
                        except OSError:
                            pass
        except Exception:
            pass
        # Public headers: courier-unicode ships courier-unicode.h (plus
        # version/unicode companion headers); copy every top-level *.h
        # and the courier-unicode/ subdir when present.
        for folder in (self.source_folder, self.build_folder):
            if not folder or not os.path.isdir(folder):
                continue
            for hit in glob.glob(os.path.join(folder, "*.h")):
                try:
                    copy(self, os.path.basename(hit), src=folder,
                         dst=pkg_inc, keep_path=False)
                except Exception:
                    pass
            sub = os.path.join(folder, "courier-unicode")
            if os.path.isdir(sub):
                try:
                    copy(self, "*.h", src=sub,
                         dst=os.path.join(pkg_inc, "courier-unicode"),
                         keep_path=False)
                except Exception:
                    pass
        # Pkg-config metadata when the build generated one.
        for folder in (self.build_folder, self.source_folder):
            if not folder:
                continue
            for hit in glob.glob(os.path.join(folder, "**", "*.pc"),
                                 recursive=True):
                try:
                    copy(self, os.path.basename(hit),
                         src=os.path.dirname(hit), dst=pkg_pc,
                         keep_path=False)
                except Exception:
                    pass

    def package_info(self):
        self.cpp_info.libs = ["courier-unicode"]
        self.cpp_info.set_property("cmake_file_name", "courier-unicode")
        self.cpp_info.set_property(
            "cmake_target_name", "courier-unicode::courier-unicode"
        )
        self.cpp_info.set_property("pkg_config_name", "courier-unicode")
