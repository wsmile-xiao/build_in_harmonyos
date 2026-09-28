#!/usr/bin/env python3
"""Conan recipe — GNU lightning 2.2.3 (run-time code generation / JIT library, Autotools)."""

import json
import os
import pathlib
import re
import tempfile

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LightningConan(ConanFile):
    name = "lightning"
    version = "2.2.3"
    description = (
        "GNU lightning: a library that generates assembly language code at "
        "run time, exposing a standardized RISC instruction set ideal for "
        "Just-In-Time compilers"
    )
    license = "LGPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/lightning/"
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

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # The optional binutils disassembler would require libbfd/libopcodes/
        # libiberty/zlib which are not present on HarmonyOS PC; the core JIT
        # library does not need it. Disable it explicitly instead of relying
        # on the fragile "auto" detection.
        tc.configure_args.append("--disable-disassembler")
        tc.configure_args.append("--disable-devel-disassembler")
        # E003 / OHOS has no Texinfo: `make all` recurses into doc/ and tries
        # to rebuild lightning.info with makeinfo (absent). Override MAKEINFO
        # with a no-op `true` so the info node is considered up-to-date
        # instead of letting automake's `missing` wrapper abort (Error 127).
        # The core JIT library and the check/ test suite never need a real
        # .info file.
        tc.configure_args.append("MAKEINFO=true")
        tc.generate()
        # E002 readonly /tmp + HMDFS getcwd: persist a writable TMPDIR and a
        # usable shell into buildenv so `make`/`make check` children see them.
        try:
            tmp = self._writable_tmpdir()
            pathlib.Path(tmp).mkdir(parents=True, exist_ok=True)
            env = Environment()
            env.define("TMPDIR", tmp)
            env.define("TMP", tmp)
            env.define("TEMP", tmp)
            env.define("SHELL", self._bash())
            env.define("CONFIG_SHELL", self._bash())
            for _k in ("HMBS_AUTOCONF_MKTEMP_FALLBACK", "HMBS_CAP_LOCAL_MKTEMP",
                       "HMBS_TMPDIR", "HMBS_CAP_CHMOD", "HMBS_CAP_HARDLINK"):
                _v = os.environ.get(_k)
                if _v:
                    env.define(_k, _v)
            env.vars(self, scope="build").save_script("hmbs_env")
        except Exception as exc:
            self.output.warning("hmbs env generate skipped: %s" % exc)

    # ------------------------------------------------------------------
    # HMFS / HMDFS Autotools hardening.
    #
    # On HarmonyOS PC the temp filesystem (HMDFS) restricts getcwd/readdir
    # on parent directories, so `pwd` inside configure can fail with
    # "configure: error: working directory cannot be determined". Autoconf
    # resolves the working dir via `ac_pwd=\`pwd\``; we fall that back to the
    # inherited PWD and point TMPDIR at a writable location (read-only /tmp).
    # ------------------------------------------------------------------
    def _bash(self):
        for cand in (os.environ.get("HMBS_SHELL"), os.environ.get("CONFIG_SHELL"),
                     "/bin/sh", "/bin/bash"):
            if cand and os.path.isfile(cand):
                return cand
        return "/bin/sh"

    def _writable_tmpdir(self):
        for var in ("HMBS_TMPDIR", "TMPDIR", "TMP", "TEMP"):
            d = os.environ.get(var)
            if d and os.path.isdir(d):
                try:
                    fd, p = tempfile.mkstemp(dir=d)
                    os.close(fd)
                    os.unlink(p)
                    return d
                except Exception:
                    continue
        d = os.path.join(self.build_folder or ".", "tmp")
        try:
            os.makedirs(d, exist_ok=True)
        except Exception:
            pass
        return d

    def _fs_env(self):
        """Prepare HMFS-friendly filesystem env: writable PWD/TMPDIR and a usable shell."""
        try:
            os.makedirs(self.build_folder, exist_ok=True)
            os.chdir(self.build_folder)
        except Exception:
            pass
        os.environ["PWD"] = self.build_folder
        hmbs_tmp = self._writable_tmpdir()
        try:
            os.makedirs(hmbs_tmp, exist_ok=True)
        except Exception:
            pass
        for k in ("TMPDIR", "TMP", "TEMP"):
            os.environ[k] = hmbs_tmp
        sh = self._bash()
        os.environ["SHELL"] = sh
        os.environ["CONFIG_SHELL"] = sh
        self.output.info("HMBS env: PWD=%s TMPDIR=%s SHELL=%s" % (self.build_folder, hmbs_tmp, sh))

    def _patch_configure_for_ohos(self, base_dir):
        """Patch configure/config.status for HMFS: getcwd fallback, umask, TMPDIR."""
        for cfg_name in ("configure", "config.status"):
            p = pathlib.Path(base_dir) / cfg_name
            if not p.is_file():
                continue
            try:
                t = p.read_text(encoding="utf-8", errors="replace")
                orig = t
                # --- HMFS getcwd fallback (root fix for "working directory cannot be determined") ---
                # lightning's configure uses literal backticks (no backslash):
                #   ac_pwd=`pwd` && test -n "$ac_pwd" && ...
                t = t.replace(
                    'ac_pwd=`pwd` && test -n "$ac_pwd" &&',
                    'ac_pwd=`pwd 2>/dev/null || echo $PWD` && test -n "$ac_pwd" &&')
                t = re.sub(r'ac_pwd=`pwd`', r'ac_pwd=`pwd 2>/dev/null || echo $PWD`', t)
                t = t.replace('if (pwd) >/dev/null 2>&1 && test -n "`pwd`"',
                              'if (pwd) >/dev/null 2>&1 || test -n "$PWD"')
                # --- autoconf secure tmp dir: writable TMPDIR + permissive umask ---
                t = t.replace(
                    'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&',
                    'tmp=`(umask 022 && mktemp -d "${TMPDIR:-.}/confXXXXXX") 2>/dev/null` &&')
                t = t.replace('tmp=./conf$-$RANDOM', 'tmp="${TMPDIR:-.}/conf$-$RANDOM"')
                t = t.replace('(umask 077 && mkdir "$tmp")', '(umask 022 && mkdir "$tmp")')
                t = t.replace('"./confXXXXXX"', '"${TMPDIR:-.}/confXXXXXX"')
                if os.environ.get("HMBS_CAP_CHMOD", "1") == "0":
                    t = t.replace("umask 077", "umask 022")
                if t != orig:
                    p.write_text(t, encoding="utf-8")
                    self.output.info("patched %s for HMFS getcwd/tmp in %s" % (cfg_name, p))
            except Exception as exc:
                self.output.warning("ohos patch skipped for %s: %s" % (p, exc))

    def build(self):
        apply_conandata_patches(self)
        self._fs_env()
        self._patch_configure_for_ohos(self.source_folder)
        self._patch_configure_for_ohos(self.build_folder)
        autotools = Autotools(self)
        autotools.configure()
        # configure generates config.status containing the same tmp/pwd snippets
        self._patch_configure_for_ohos(self.build_folder)
        autotools.make(args=["-j1"])
        self._run_upstream_tests()

    # ------------------------------------------------------------------
    # Upstream test suite (make check)
    #
    # GNU lightning's `check/Makefile.am` registers an automake `TESTS`
    # list (base `.tst` transcription tests driven by check.sh plus the
    # standalone C test programs).  On aarch64 none of the x87/arm/nodata
    # conditionals apply, so `make check` runs exactly the audited
    # TESTS entries and writes `check/test-suite.log` with the standard
    # automake summary block:
    #   # TOTAL: N  /  # PASS: N  /  # FAIL: N  /  # SKIP: N
    #   # XFAIL: N  /  # XPASS: N  /  # ERROR: N
    # ------------------------------------------------------------------
    def _run_upstream_tests(self):
        command = "make -j1 check"
        try:
            # Non-zero exit is expected when any upstream test regresses;
            # the summary inside test-suite.log is the authoritative count
            # source, so capture it instead of letting self.run raise.
            self.run(command, cwd=self.build_folder, ignore_errors=True)
        except Exception as exc:  # pragma: no cover - defensive
            self.output.warning("make check raised: %s" % exc)

        log_path = os.path.join(self.build_folder, "check", "test-suite.log")
        if not os.path.isfile(log_path):
            raise ConanException(
                "upstream `make check` produced no test-suite.log at %s "
                "(search path: %s); refusing to continue without a test "
                "summary." % (log_path, self.build_folder)
            )
        with open(log_path, "r", encoding="utf-8", errors="replace") as handle:
            summary = handle.read()

        total = self._summary_field(summary, "TOTAL")
        passed = self._summary_field(summary, "PASS")
        failed = self._summary_field(summary, "FAIL")
        skipped = self._summary_field(summary, "SKIP")
        xfail = self._summary_field(summary, "XFAIL")
        xpass = self._summary_field(summary, "XPASS")
        error = self._summary_field(summary, "ERROR")

        # Automake summary semantics: TOTAL is the number of registered
        # TESTS; PASS/FAIL/ERROR (and XPASS) are actually executed while
        # SKIP/XFAIL are reported as non-executed/expected outcomes.
        executed = passed + failed + error + xpass
        skipped_tot = skipped + xfail

        self.output.info(
            "upstream automake summary: TOTAL=%d PASS=%d FAIL=%d ERROR=%d "
            "SKIP=%d XFAIL=%d XPASS=%d"
            % (total, passed, failed, error, skipped, xfail, xpass)
        )

        # Falsifiability guard: exit-0 alone proves nothing, so require the
        # automake summary to be internally consistent (the six categories
        # must sum exactly to the registered TOTAL) before emitting a marker.
        if executed + skipped_tot != total:
            raise ConanException(
                "automake summary inconsistent: PASS(%d)+FAIL(%d)+ERROR(%d)+"
                "XPASS(%d)+SKIP(%d)+XFAIL(%d) = %d != TOTAL(%d)"
                % (passed, failed, error, xpass, skipped, xfail,
                   executed + skipped_tot, total)
            )

        upstream = {
            "status": "passed" if (failed + error == 0) else "failed",
            "framework": "autotools_tests",
            "command": command,
            "discovered": total,
            "executed": executed,
            "passed": passed,
            "failed": failed + error,
            "skipped": skipped_tot,
        }
        if failed + error > 0:
            upstream["gaps"] = self._build_gaps(summary, failed + error)
        self._upstream_result = upstream

        marker = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False)
        print(marker, flush=True)
        self.output.info(marker)
        try:
            with open(
                os.path.join(self.build_folder, "hmbs_upstream.json"),
                "w",
                encoding="utf-8",
                newline="\n",
            ) as handle:
                json.dump(upstream, handle, ensure_ascii=False, indent=2)
        except OSError as exc:  # pragma: no cover
            self.output.warning("write hmbs_upstream.json failed: %s" % exc)

    @staticmethod
    def _summary_field(summary, field):
        match = re.search(
            r"^#\s*%s:\s*(\d+)" % field, summary, re.MULTILINE
        )
        if not match:
            raise ConanException(
                "cannot parse '# %s:' from test-suite.log; got summary:\n%s"
                % (field, summary[-2000:])
            )
        return int(match.group(1))

    @staticmethod
    def _build_gaps(summary, failed_count):
        names = re.findall(r"^FAIL:\s*(\S+)", summary, re.MULTILINE)
        # non-zero ERROR lines also count as failures; include any orphan
        # executables reported in the summary tail if none matched above.
        names = names or re.findall(r"^ERROR:\s*(\S+)", summary, re.MULTILINE)
        detail = (
            "upstream automake suite reported %d failed/errored tests; "
            "failing entries: %s"
            % (failed_count, ", ".join(names[:20]) if names else "(see test-suite.log)")
        )
        return [
            {
                "count": failed_count,
                "category": "test_failure",
                "detail": detail,
                "evidence": "check/test-suite.log summary (# FAIL/# ERROR)",
            }
        ]

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(
            self,
            "COPYING*",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        # Persist the upstream automake summary so test_package can re-emit
        # the exact HMBS_UPSTREAM_TEST_RESULT evidence (one deterministic
        # source, no hardcoded numbers) instead of re-parsing test-suite.log.
        upstream = getattr(self, "_upstream_result", None)
        if upstream is not None:
            with open(
                os.path.join(self.build_folder, "hmbs_upstream.json"),
                "r",
                encoding="utf-8",
            ) as handle:
                upstream = json.load(handle)
            res_dir = os.path.join(self.package_folder, "res")
            os.makedirs(res_dir, exist_ok=True)
            with open(
                os.path.join(res_dir, "upstream_test_result.json"),
                "w",
                encoding="utf-8",
                newline="\n",
            ) as handle:
                json.dump(upstream, handle, ensure_ascii=False, indent=2)

    def package_info(self):
        self.cpp_info.libs = ["lightning"]
