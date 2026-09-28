#!/usr/bin/env python3
"""Conan recipe — lftp 4.9.3 (Autotools file-transfer client).

lftp is a sophisticated command-line file transfer client
(FTP/FTPS/HTTP/HTTPS/SFTP) by Alexander Lukyanov. C++ codebase with a
GNU Autotools build; the deliverable is a single `lftp` binary, so this
recipe is package_type="application" (R38: commands.json at package level).

OHOS adaptation (audited 2026-09-27 from the 4.9.3 tarball):
  * E007 platform triplet: the 2022-vintage build-aux/config.guess has no
    HarmonyOS branch and config.sub rejects linux-ohos (reproduced with
    sh: pristine config.sub fails "OS `ohos' not recognized").
    patches/0001 + 0002 add the HarmonyOS guess branch
    (*-unknown-linux-ohos) and the config.sub triplet/OS/kernel entries.
    Provenance: scripts/patch-autotools-ohos.pl transformations, plus one
    documented deviation -- the script's kernel-list hunk (2.3) is always
    skipped whenever 2.1 fires, but without it config.sub fails with
    "Kernel `linux' not known to work with OS `ohos'" (also reproduced).
    No --build/--host override (R1 native build; E007 forbids the bypass).
  * HMDFS mktemp permissions: mktemp-exit-1 wrapper forces the autoconf
    mkdir fallback (bash/5.3 precedent).
  * make -j1 (E074: HMDFS jobserver fifo EPERM under parallel make).
  * Dependencies, all W0-published: readline/8.3 (configure hard-requires
    readline), zlib/1.3.1 (configure hard-requires zlib), openssl/3.5.6
    (TLS; upstream default is no-SSL). gnutls/libidn2/expat/socks stay at
    their graceful auto-detect defaults (configure warns and continues).
  * Upstream tests: automake TESTS = 4 programs + 3 scripts = 7 entries
    (tests/Makefile.am). build() runs `make check`, parses
    tests/test-suite.log deterministically and emits
    HMBS_UPSTREAM_TEST_RESULT. Parsed failures are recorded honestly with
    gaps (leatherman/1.12.1 precedent, TEST_QUALITY_SPEC 3.3) instead of
    vetoing the package, because 4 of the 7 tests need live internet
    servers unreachable from the preflight sandbox.
"""
import json
import os
import re
import shlex
import shutil
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy
from conan.tools.files import export_conandata_patches, get, rm
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


# Audited from tests/Makefile.am (4.9.3 tarball):
#   check_PROGRAMS = ftp-mlsd ftp-list http-get ftp-cls-l
#   check_SCRIPTS  = module1 lftp-https-get lftp-queue-kill
#   TESTS = $(check_PROGRAMS) $(check_SCRIPTS)
_UPSTREAM_TEST_TOTAL = 7

# Tests that require live internet servers (audited from tests/ sources):
#   ftp-list.cc   -> FileAccess::New("ftp","mirror.yandex.ru")
#   ftp-cls-l.cc  -> open -d ftp://mirror.yandex.ru/
#   http-get.cc   -> FileAccess::New("http","lftp.yar.ru")
#   lftp-https-get -> cat https://lftp.yar.ru/features.html
# (ftp-mlsd.cc is offline: it parses a hardcoded MLSD listing.)
_NETWORK_TESTS = (
    "ftp-list",
    "http-get",
    "ftp-cls-l",
    "lftp-https-get",
)


class LftpConan(ConanFile):
    name = "lftp"
    version = "4.9.3"
    description = "Sophisticated command-line file transfer client (FTP/HTTP/SFTP)"
    license = "GPL-3.0-or-later"
    homepage = "https://lftp.yar.ru/"
    url = "https://github.com/lavv17/lftp"
    topics = ("ftp", "sftp", "http", "file-transfer", "client")
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # W0-verified published: configure hard-requires readline + zlib;
        # openssl enables FTPS/HTTPS (upstream default is no-SSL).
        self.requires("readline/8.3")
        self.requires("zlib/1.3.1")
        self.requires("openssl/3.5.6")

    def validate(self):
        # R32: platform check must accept both Linux and OHOS.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "lftp is only supported on Linux/OHOS, not %s"
                % self.settings.os
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = AutotoolsDeps(self)
        deps.generate()
        tc = AutotoolsToolchain(self)
        # Deterministic dep prefixes (macros honour these over PATH search):
        # lftp_LIB_READLINE --with-readline=DIR, AX_CHECK_ZLIB
        # --with-zlib=DIR, LFTP_OPENSSL_CHECK --with-openssl=DIR.
        tc.configure_args.append(
            "--with-readline=%s"
            % self.dependencies["readline"].package_folder.replace("\\", "/")
        )
        tc.configure_args.append(
            "--with-zlib=%s"
            % self.dependencies["zlib"].package_folder.replace("\\", "/")
        )
        tc.configure_args.append(
            "--with-openssl=%s"
            % self.dependencies["openssl"].package_folder.replace("\\", "/")
        )
        # Single TLS backend (openssl); gnutls stays off for determinism.
        tc.configure_args.append("--without-gnutls")
        # Relocatable conan package: never embed -R conan-cache paths
        # (gnulib lib-link would add -R<pkg>/lib when rpath is enabled).
        tc.configure_args.append("--disable-rpath")
        tc.generate()

        env = Environment()
        for dep in self.dependencies.values():
            # configure conftest programs link shared dep libs; the OHOS
            # loader needs their libdirs on LD_LIBRARY_PATH at build time
            # (lbreakouthd/1.2.3 precedent).
            for libdir in dep.cpp_info.libdirs:
                env.prepend_path("LD_LIBRARY_PATH", libdir)
        env.vars(self, scope="build").save_script("conanbuild_lftp_deps_env")

    def _good_shell(self):
        """Healthy shell for native OHOS builds, else None.

        Branch key is settings_build.os (E232 forbid_1: settings.os is the
        target and would misroute cross-build executors). Returns None off
        OHOS so every other executor keeps the default Autotools path.
        """
        if self.settings_build.os != "OHOS":
            return None
        if os.path.exists("/system/bin/sh"):
            return "/system/bin/sh"
        return "/bin/sh"

    def _patch_autoconf_umask(self, path):
        # E011/HMDFS: autoconf template `umask 077 && mktemp -d
        # "./confXXXXXX"` yields an owner-unwritable dir on HMDFS, so
        # config.status fails with "can't create ./conf*/subs1.awk:
        # Permission denied" (complexity/1.13, liblzf/3.6 precedent).
        # Rewrite to umask 022; only the temp-dir mask changes.
        try:
            with open(path, "r", encoding="utf-8", errors="surrogateescape") as h:
                content = h.read()
        except OSError:
            return
        if "umask 077" not in content:
            return
        content = content.replace("umask 077", "umask 022")
        try:
            with open(path, "w", encoding="utf-8", errors="surrogateescape", newline="\n") as h:
                h.write(content)
        except OSError:
            return
        self.output.info("lftp: relaxed umask 077->022 in %s" % os.path.basename(path))

    def _writable_tmpdir(self):
        # Reuse the HMBS-injected writable TMPDIR/TMP/TEMP; never /tmp
        # (read-only on OHOS); else a build-local tmp dir.
        for var in ("TMPDIR", "TMP", "TEMP"):
            cand = os.environ.get(var, "")
            if cand and cand != "/tmp" and os.path.isdir(cand):
                return cand
        tmpd = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpd, exist_ok=True)
        return tmpd

    def _mktemp_fallback_shim(self, tmpdir):
        # HMBS [unsafe_local_mktemp]: an mktemp -d dir on the true-machine
        # FS cannot be written by later config.status steps. When
        # HMBS_AUTOCONF_MKTEMP_FALLBACK=1, shadow mktemp during the
        # configure step only so "./conf*" calls fail and Autoconf takes
        # its mkdir fallback (cyrus-sasl-login/liblzf/cdck precedent).
        # All other mktemp calls delegate to the real binary.
        if os.environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK") != "1":
            return ""
        shim_dir = os.path.join(tmpdir, "hmbs-mktemp-shim")
        try:
            os.makedirs(shim_dir, exist_ok=True)
        except OSError:
            return ""
        real = (shutil.which("mktemp") or "/bin/mktemp").replace('"', "")
        shim = os.path.join(shim_dir, "mktemp")
        script = (
            "#!/bin/sh\n"
            'for arg in "$@"; do\n'
            '  case "$arg" in\n'
            "    *conf*) exit 1 ;;\n"
            "  esac\n"
            "done\n"
            'for candidate in /bin/mktemp /usr/bin/mktemp; do\n'
            '  if [ -x "$candidate" ]; then\n'
            '    exec "$candidate" "$@"\n'
            "  fi\n"
            "done\n"
            'exec "%s" "$@"\n' % real
        )
        try:
            with open(shim, "w", encoding="utf-8", newline="\n") as h:
                h.write(script)
            try:
                os.chmod(shim, 0o755)
            except OSError:
                pass  # HMBS_CAP_CHMOD=0: HMDFS ignores chmod
        except OSError:
            return ""
        self.output.info("lftp: mktemp fallback shim active for configure: %s" % shim_dir)
        return shim_dir

    def build(self):
        apply_conandata_patches(self)
        # E011 deterministic fix: patch umask before configure runs, so
        # both configure and the generated config.status create writable
        # temp dirs on HMDFS even if the PATH shim is bypassed.
        self._patch_autoconf_umask(os.path.join(self.source_folder, "configure"))
        autotools = Autotools(self)
        sh = self._good_shell()
        if sh is None:
            autotools.configure()
            # R9: single job -- parallel make hits HMDFS jobserver fifo EPERM.
            autotools.make(args=["-j1"])
        else:
            # OHOS native build (E232 + cvsgraph/classads getcwd drafts):
            # /data/service/hnp/bin/bash fails getcwd() on the HMDFS conan
            # build cache (shell-init/job-working-directory storm, then
            # "working directory cannot be determined"), and the deep
            # build-release subdir triggers the same storm one layer down.
            # So launch configure explicitly with the healthy system shell
            # and build in-source; CONFIG_SHELL is pinned so autoconf bakes
            # the good shell into Makefiles/config.status instead of the
            # profile-injected hnp bash. Configure args still come from the
            # Conan toolchain object (E232 forbid_2: never hand-rebuild).
            # NOTE (2026-09-27 preflight): _configure_args is a shell-ready
            # string in Conan 2.30, not a list -- iterating it splits every
            # character (`- - p r e f i x ...`) and configure dies with
            # "unrecognized option: `-'". Pass through verbatim; only join
            # with quoting on the old list form for compatibility.
            configure = os.path.join(self.source_folder, "configure").replace(
                "\\", "/"
            )
            args = autotools._configure_args
            if isinstance(args, (list, tuple)):
                args = " ".join(shlex.quote(a) for a in args)
            # HMBS unsafe_local_mktemp: configure-phase-only shim + umask.
            # The old always-fail wrapper is gone: it shadowed every mktemp
            # call in every phase and depended on chmod (HMBS_CAP_CHMOD=0).
            # Now only "./conf*" fails (mkdir fallback), other mktemp uses
            # delegate to the real binary, and the shim is active for the
            # configure command only -- make/check run without it.
            tmpdir = self._writable_tmpdir()
            os.environ["TMPDIR"] = tmpdir
            os.environ["TMP"] = tmpdir
            os.environ["TEMP"] = tmpdir
            shim_dir = self._mktemp_fallback_shim(tmpdir)
            shim_export = 'export PATH="%s:$PATH"; ' % shim_dir if shim_dir else ""
            tmp_export = (
                'export TMPDIR="%s"; export TMP="%s"; export TEMP="%s"; '
                % (tmpdir, tmpdir, tmpdir)
            )
            # 2026-09-28 preflight install-man1 Error 64:
            # runtime `install -c` fails. Pin INSTALL to the tarball's
            # portable install-sh (searched, not assumed top-level).
            install_sh = self._find_install_sh()
            install_export = ""
            if install_sh:
                install_export = 'export INSTALL="%s -c"; ' % install_sh
                self.output.info("lftp: pinning INSTALL to %s" % install_sh)
            else:
                self.output.warning("lftp: install-sh not found, keeping system install")
            self.run(
                '%sumask 022; CONFIG_SHELL="%s" "%s" "%s" %s'
                % (shim_export + tmp_export + install_export, sh, sh, configure, args),
                cwd=self.source_folder,
                env="conanbuild",
            )
            # Generated config.status carries its own hardcoded umask 077
            # copy; relax it as well so its temp dir stays writable.
            self._patch_autoconf_umask(os.path.join(self.source_folder, "config.status"))
            if not os.path.isfile(os.path.join(self.source_folder, "Makefile")) and os.path.isfile(
                os.path.join(self.source_folder, "config.status")
            ):
                self.output.warning("lftp: Makefile missing after configure; retrying ./config.status once")
                self.run(
                    '%sumask 022; CONFIG_SHELL="%s" "%s" ./config.status'
                    % (shim_export + tmp_export, sh, sh),
                    cwd=self.source_folder,
                    env="conanbuild",
                )
            # R9: single job (E074: HMDFS jobserver fifo EPERM).
            self.run(
                '%sumask 022; CONFIG_SHELL="%s" make -j1'
                % (tmp_export, sh),
                cwd=self.source_folder,
                env="conanbuild",
            )
        if can_run(self):
            self._run_upstream_tests(autotools, sh=sh)

    def _find_suite_log(self):
        """Locate tests/test-suite.log (VPATH build or in-source build)."""
        hits = []
        for root in (self.build_folder, self.source_folder):
            if not root:
                continue
            for dirpath, _dirnames, filenames in os.walk(root):
                if "test-suite.log" in filenames and os.path.basename(
                    dirpath
                ) == "tests":
                    hits.append(os.path.join(dirpath, "test-suite.log"))
        if not hits:
            return None
        return str(max(hits, key=lambda p: os.path.getmtime(p)))

    def _find_install_sh(self):
        """Locate the tarball's portable install-sh (top level or aux dirs)."""
        candidates = ("install-sh", "build-aux/install-sh", "config/install-sh")
        for rel in candidates:
            try:
                if os.path.isfile(os.path.join(self.source_folder, rel)):
                    return os.path.join(self.source_folder, rel).replace("\\", "/")
            except OSError:
                continue
        # Last resort: shallow recursive search (top 3 levels).
        try:
            for dirpath, _dirnames, filenames in os.walk(self.source_folder):
                rel = os.path.relpath(dirpath, self.source_folder)
                depth = 0 if rel == "." else len(rel.split(os.sep))
                if depth > 3:
                    continue
                if "install-sh" in filenames:
                    return os.path.join(dirpath, "install-sh").replace("\\", "/")
        except OSError:
            pass
        return ""

    def _timeout_runner(self, tmpdir):
        """Write a sh-invoked wrapper converting timeout 124 -> exit 1.

        automake's parallel harness failed to write .trs for tests killed
        with exit 124 (ftp-list/ftp-cls-l left no .trs, counted as unrun),
        while normal FAIL (exit 1, e.g. lftp-https-get) is recorded. The
        wrapper runs `timeout <secs> cmd`, maps 124 to 1 with a stderr
        note, and is invoked via `sh <wrapper> <secs>` so no chmod/exec
        bit is needed (HMBS_CAP_CHMOD=0). Returns TESTS_ENVIRONMENT value
        or "" when `timeout` is unavailable.
        """
        if not shutil.which("timeout"):
            return ""
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            return ""
        wrapper = os.path.join(tmpdir, "hmbs-test-timeout.sh")
        script = (
            "#!/bin/sh\n"
            "# usage: hmbs-test-timeout.sh <secs> <cmd> [args...]\n"
            'secs="$1"; shift\n'
            'timeout "$secs" "$@"\n'
            "rc=$?\n"
            'if [ "$rc" -eq 124 ]; then\n'
            '  echo "HMBS: test timed out after ${secs}s: $*" >&2\n'
            "  exit 1\n"
            "fi\n"
            'exit "$rc"\n'
        )
        try:
            with open(wrapper, "w", encoding="utf-8", newline="\n") as h:
                h.write(script)
        except OSError:
            return ""
        # Forward slashes for the shell; invoked via `sh`, no +x needed.
        return "sh %s 60" % wrapper.replace("\\", "/")

    def _collect_trs_counts(self):
        """Fallback: parse tests/*.trs `:test-result:` lines (parallel harness).

        When `make check` aborts before assembling test-suite.log, the
        per-test .trs files of completed TESTS still exist and are a
        deterministic single source (no stdout counting). Returns
        (dir_found, counts_dict, names_dict) where counts keys are
        PASS/FAIL/SKIP/XFAIL/XPASS/ERROR and names maps result -> [names].
        """
        counts = {"PASS": 0, "FAIL": 0, "SKIP": 0, "XFAIL": 0, "XPASS": 0, "ERROR": 0}
        names = {"PASS": [], "FAIL": [], "SKIP": [], "XFAIL": [], "XPASS": [], "ERROR": []}
        tests_dirs = []
        for root in (self.build_folder, self.source_folder):
            if not root:
                continue
            for dirpath, _dirnames, filenames in os.walk(root):
                if os.path.basename(dirpath) == "tests" and any(
                    f.endswith(".trs") for f in filenames
                ):
                    tests_dirs.append(dirpath)
        trs_files = []
        for d in tests_dirs:
            try:
                for f in os.listdir(d):
                    if f.endswith(".trs"):
                        trs_files.append(os.path.join(d, f))
            except OSError:
                continue
        if not trs_files:
            return False, counts, names
        for path in trs_files:
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as h:
                    content = h.read()
            except OSError:
                continue
            m = re.search(r"^:test-result:\s*(\S+)\s*$", content, re.MULTILINE)
            if not m:
                continue
            result = m.group(1).strip().upper()
            if result not in counts:
                continue
            tname = os.path.splitext(os.path.basename(path))[0]
            counts[result] += 1
            names[result].append(tname)
        return True, counts, names

    def _run_upstream_tests(self, autotools, sh=None):
        """Run `make check` and emit HMBS_UPSTREAM_TEST_RESULT.

        Deterministic source: tests/test-suite.log written by automake
        (TOTAL/PASS/FAIL/SKIP/XFAIL/XPASS/ERROR summary block plus
        per-test "PASS: name" lines). No stdout word counting, no guessing
        branches: every figure comes from that single file.

        Parsed failures do NOT veto the package build (leatherman/1.12.1
        precedent, TEST_QUALITY_SPEC 3.3): 4 of 7 lftp tests need live
        internet servers, so an offline sandbox can never be green. Every
        non-passing test gets a gaps[] entry with source-grounded evidence;
        the marker keeps status=failed honestly and build() continues so
        test_package still runs.
        """
        # 2026-09-28 preflight #3: `-k` runs all 7 TESTS but timeout-killed
        # programs (ftp-list/ftp-cls-l, exit 124) leave no .trs, so the
        # fallback counted 5/7 with 2 "unrun". Wrap timeout to map 124 -> 1
        # (normal FAIL, harness writes .trs) via a sh-invoked wrapper.
        tmpdir = os.environ.get("TMPDIR") or self._writable_tmpdir()
        tests_env = self._timeout_runner(tmpdir)
        if tests_env:
            self.output.info("lftp: bounding each upstream test with `%s` + make -k" % tests_env)
        else:
            self.output.warning("lftp: `timeout` not found; running make check -k unbounded")
        check_cmd_label = (
            "make check -k TESTS_ENVIRONMENT=\"%s\"" % tests_env if tests_env else "make check -k"
        )
        try:
            if sh is None:
                if tests_env:
                    autotools.make(
                        target="check",
                        args=["-j1", "-k", "TESTS_ENVIRONMENT=\"%s\"" % tests_env],
                    )
                else:
                    autotools.make(target="check", args=["-j1", "-k"])
            else:
                # Same healthy-shell + in-source context as build().
                # No mktemp shim here: the fallback is configure-phase only
                # per HMBS diagnosis; make check keeps the real mktemp.
                tmpdir = os.environ.get("TMPDIR") or self._writable_tmpdir()
                if tests_env:
                    check_shell = (
                        'export TMPDIR="%s"; export TMP="%s"; export TEMP="%s"; '
                        'CONFIG_SHELL="%s" make check -j1 -k TESTS_ENVIRONMENT="%s"'
                        % (tmpdir, tmpdir, tmpdir, sh, tests_env)
                    )
                else:
                    check_shell = (
                        'export TMPDIR="%s"; export TMP="%s"; export TEMP="%s"; '
                        'CONFIG_SHELL="%s" make check -j1 -k'
                        % (tmpdir, tmpdir, tmpdir, sh)
                    )
                self.run(
                    check_shell,
                    cwd=self.source_folder,
                    env="conanbuild",
                )
            check_ok = True
        except Exception as e:
            self.output.warning("lftp: make check interrupted: %s" % e)
            check_ok = False
        log = self._find_suite_log()
        if log is None:
            # test-suite.log not assembled (e.g. make stopped before the
            # summary). Try the parallel-harness per-test .trs files first:
            # they are the same deterministic source, one file per TEST.
            trs_found, trs_counts, trs_names = self._collect_trs_counts()
            if trs_found and sum(trs_counts.values()) > 0:
                n_pass = trs_counts["PASS"]
                n_fail = trs_counts["FAIL"] + trs_counts["XPASS"] + trs_counts["ERROR"]
                n_skip = trs_counts["SKIP"] + trs_counts["XFAIL"]
                n_done = n_pass + n_fail + n_skip
                n_unrun = max(0, _UPSTREAM_TEST_TOTAL - n_done)
                marker = {
                    "status": "failed",
                    "framework": "automake",
                    "command": check_cmd_label,
                    "discovered": _UPSTREAM_TEST_TOTAL,
                    "executed": n_pass + n_fail,
                    "passed": n_pass,
                    "failed": n_fail,
                    "skipped": n_skip,
                    "reason": "test-suite.log not assembled; partial counts "
                    "from tests/*.trs :test-result: lines in the same tree",
                }
                gaps = []
                for tname in trs_names["FAIL"] + trs_names["XPASS"] + trs_names["ERROR"]:
                    if tname in _NETWORK_TESTS:
                        gaps.append(
                            {
                                "count": 1,
                                "category": "environment",
                                "detail": "test %s needs a live internet server "
                                "(audited: tests/%s connects to a public host)"
                                % (tname, tname),
                                "evidence": "tests/%s.trs" % tname,
                            }
                        )
                    else:
                        gaps.append(
                            {
                                "count": 1,
                                "category": "test_failure",
                                "detail": "test %s failed; not in the audited "
                                "network-dependent set, see tests/%s.trs" % (tname, tname),
                                "evidence": "tests/%s.trs" % tname,
                            }
                        )
                for tname in trs_names["SKIP"] + trs_names["XFAIL"]:
                    gaps.append(
                        {
                            "count": 1,
                            "category": "environment",
                            "detail": "test %s skipped, see tests/%s.trs" % (tname, tname),
                            "evidence": "tests/%s.trs" % tname,
                        }
                    )
                if n_unrun:
                    gaps.append(
                        {
                            "count": n_unrun,
                            "category": "environment",
                            "detail": "%d test(s) never ran: make check stopped "
                            "before the summary (use make -k + per-test "
                            "timeout); see tests/*.trs" % n_unrun,
                            "evidence": "tests/*.trs",
                        }
                    )
                if gaps:
                    marker["gaps"] = gaps
                self.output.info(
                    "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker)
                )
                self.output.warning(
                    "upstream tests partial from .trs (%d/%d done); "
                    "recorded honestly, continuing to package" % (n_done, _UPSTREAM_TEST_TOTAL)
                )
                return
            # Killed before any log (e.g. Signal 9 on the whole make):
            # record honestly and keep building (leatherman precedent) --
            # a missing test log must not masquerade as a compile error.
            searched = [str(r) for r in (self.build_folder, self.source_folder) if r]
            marker = {
                "status": "failed",
                "framework": "automake",
                "command": check_cmd_label,
                "discovered": _UPSTREAM_TEST_TOTAL,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": "tests/test-suite.log not found under "
                + ", ".join(searched),
                "gaps": [
                    {
                        "count": _UPSTREAM_TEST_TOTAL,
                        "category": "environment",
                        "detail": "make check left no test-suite.log "
                        "(interrupted, e.g. Signal 9 on a hanging "
                        "network test); no test outcome observed",
                        "evidence": ", ".join(searched),
                    }
                ],
            }
            self.output.info(
                "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker)
            )
            self.output.warning(
                "upstream tests interrupted with no log; recorded honestly, "
                "continuing to package (see HMBS_UPSTREAM_TEST_RESULT)"
            )
            return
        text = Path(log).read_text(encoding="utf-8", errors="replace")
        counts = {}
        for key in ("TOTAL", "PASS", "FAIL", "SKIP", "XFAIL", "XPASS", "ERROR"):
            m = re.search(r"^# %s:\s*(\d+)\s*$" % key, text, re.MULTILINE)
            counts[key] = int(m.group(1)) if m else 0
        if counts["TOTAL"] <= 0:
            # Killed mid-run (2026-09-27: Signal 9 after PASS http-get):
            # the summary block never lands, but per-test PASS:/FAIL:/
            # SKIP: lines already in the same file are still a
            # deterministic single source -- parse those, mark the rest
            # as unrun environment gaps, and keep building.
            part_pass = re.findall(r"^PASS:\s*(\S+)\s*$", text, re.MULTILINE)
            part_fail = re.findall(r"^FAIL:\s*(\S+)\s*$", text, re.MULTILINE)
            part_skip = re.findall(r"^SKIP:\s*(\S+)\s*$", text, re.MULTILINE)
            part_skip += re.findall(r"^XFAIL:\s*(\S+)\s*$", text, re.MULTILINE)
            n_pass = len(part_pass)
            n_fail = len(part_fail)
            n_skip = len(part_skip)
            n_done = n_pass + n_fail + n_skip
            n_unrun = max(0, _UPSTREAM_TEST_TOTAL - n_done)
            marker = {
                "status": "failed",
                "framework": "automake",
                "command": check_cmd_label,
                "discovered": _UPSTREAM_TEST_TOTAL,
                "executed": n_pass + n_fail,
                "passed": n_pass,
                "failed": n_fail,
                "skipped": n_skip,
                "reason": "no '# TOTAL:' summary in %s "
                "(interrupted before automake summary; partial counts "
                "from PASS:/FAIL:/SKIP: lines in the same file)" % log,
            }
            gaps = []
            for tname in part_fail:
                if tname in _NETWORK_TESTS:
                    gaps.append(
                        {
                            "count": 1,
                            "category": "environment",
                            "detail": "test %s needs a live internet server "
                            "(audited: tests/%s connects to a public host)"
                            % (tname, tname),
                            "evidence": log,
                        }
                    )
                else:
                    gaps.append(
                        {
                            "count": 1,
                            "category": "test_failure",
                            "detail": "test %s failed; not in the audited "
                            "network-dependent set, see log" % tname,
                            "evidence": log,
                        }
                    )
            for tname in part_skip:
                gaps.append(
                    {
                        "count": 1,
                        "category": "environment",
                        "detail": "test %s skipped before harness was "
                        "interrupted, see log" % tname,
                        "evidence": log,
                    }
                )
            if n_unrun:
                gaps.append(
                    {
                        "count": n_unrun,
                        "category": "environment",
                        "detail": "%d test(s) never ran: make check was "
                        "killed (Signal 9) while a network test "
                        "(ftp-cls-l opens mirror.yandex.ru) hung; "
                        "per-test timeout `%s` now bounds this" % (n_unrun, tests_env or "n/a"),
                        "evidence": log,
                    }
                )
            if gaps:
                marker["gaps"] = gaps
            self.output.info(
                "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker)
            )
            self.output.warning(
                "upstream tests interrupted mid-run (partial %d/%d done); "
                "recorded honestly, continuing to package" % (n_done, _UPSTREAM_TEST_TOTAL)
            )
            return
        # Single-source identities (automake semantics: XPASS counts as a
        # failure, XFAIL as skipped; TOTAL = PASS+FAIL+SKIP+XFAIL+XPASS+ERR).
        total = counts["TOTAL"]
        skipped = counts["SKIP"] + counts["XFAIL"]
        passed = counts["PASS"]
        executed = total - skipped
        failed = executed - passed
        # Per-test outcomes, same file.
        failed_names = re.findall(r"^FAIL:\s*(\S+)\s*$", text, re.MULTILINE)
        skipped_names = re.findall(r"^SKIP:\s*(\S+)\s*$", text, re.MULTILINE)
        skipped_names += re.findall(r"^XFAIL:\s*(\S+)\s*$", text, re.MULTILINE)
        status = "passed" if (check_ok and failed == 0) else "failed"
        marker = {
            "status": status,
            "framework": "automake",
            "command": check_cmd_label,
            "discovered": _UPSTREAM_TEST_TOTAL,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        if status != "passed":
            gaps = []
            for tname in failed_names:
                if tname in _NETWORK_TESTS:
                    gaps.append(
                        {
                            "count": 1,
                            "category": "environment",
                            "detail": "test %s needs a live internet server "
                            "(audited: tests/%s connects to a public host; "
                            "preflight sandbox is offline)" % (tname, tname),
                            "evidence": log,
                        }
                    )
                else:
                    gaps.append(
                        {
                            "count": 1,
                            "category": "test_failure",
                            "detail": "test %s failed; not in the audited "
                            "network-dependent set, see log" % tname,
                            "evidence": log,
                        }
                    )
            for tname in skipped_names:
                if tname == "module1":
                    gaps.append(
                        {
                            "count": 1,
                            "category": "environment",
                            "detail": "module1 skips without --with-modules "
                            "(default no; module1.la never built, "
                            "tests/module1 exits 77 by design)",
                            "evidence": log,
                        }
                    )
                elif tname in _NETWORK_TESTS:
                    gaps.append(
                        {
                            "count": 1,
                            "category": "environment",
                            "detail": "test %s skipped: needs live internet "
                            "or TLS probing unavailable offline" % tname,
                            "evidence": log,
                        }
                    )
                else:
                    gaps.append(
                        {
                            "count": 1,
                            "category": "test_failure",
                            "detail": "test %s skipped unexpectedly, "
                            "see log" % tname,
                            "evidence": log,
                        }
                    )
            # Fail closed on accounting bugs, but never veto the package:
            # a test-accounting bug must not masquerade as a compile error.
            if sum(g["count"] for g in gaps) != total - passed:
                marker["reason"] = (
                    "gap accounting mismatch: gaps=%d vs non-passing=%d "
                    "(fail=%s skip=%s)"
                    % (
                        sum(g["count"] for g in gaps),
                        total - passed,
                        failed_names,
                        skipped_names,
                    )
                )
                if gaps:
                    marker["gaps"] = gaps
                self.output.info(
                    "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker)
                )
                self.output.warning(
                    "upstream gap accounting mismatch; recorded honestly, "
                    "continuing to package (see HMBS_UPSTREAM_TEST_RESULT)"
                )
                return
            if gaps:
                marker["gaps"] = gaps
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker))
        if status != "passed":
            self.output.warning(
                "upstream tests failed but recorded honestly: "
                "total=%d passed=%d failed=%d skipped=%d "
                "(see HMBS_UPSTREAM_TEST_RESULT)" % (total, passed, failed, skipped)
            )

    def package(self):
        sh = self._good_shell()
        if sh is None:
            autotools = Autotools(self)
            autotools.install()
        else:
            # In-source install with the healthy shell (DESTDIR honours the
            # toolchain's --prefix=/, same contract as Autotools.install()).
            # INSTALL pinned to install-sh when found: runtime `install -c`
            # fails at install-man1 with Error 64 (2026-09-28 preflight).
            install_sh = self._find_install_sh()
            if install_sh:
                self.output.info("lftp: make install with INSTALL=%s -c" % install_sh)
                self.run(
                    'CONFIG_SHELL="%s" make install DESTDIR=%s INSTALL="%s -c"'
                    % (sh, self.package_folder.replace("\\", "/"), install_sh),
                    cwd=self.source_folder,
                    env="conanbuild",
                )
            else:
                self.output.warning("lftp: install-sh not found, keeping system install")
                self.run(
                    'CONFIG_SHELL="%s" make install DESTDIR=%s'
                    % (sh, self.package_folder.replace("\\", "/")),
                    cwd=self.source_folder,
                    env="conanbuild",
                )
        # Drop libtool leftovers; lftp ships no shared libs of its own.
        libdir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(libdir):
            rm(self, "*.la", libdir)
            rm(self, "*.dylib", libdir)
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        # Standalone executable, not a library (lbreakouthd/1.2.3 pattern).
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
