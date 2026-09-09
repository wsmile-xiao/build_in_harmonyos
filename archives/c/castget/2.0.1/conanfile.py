#!/usr/bin/env python3
"""Conan recipe for castget 2.0.1 — RSS/podcast downloader (OHOS aarch64).

castget is a pure-C command-line podcast/RSS downloader. Hard deps are
glib-2.0 (>= 2.30), libxml-2.0 (PKG_CHECK_MODULES) and libcurl (probed via
the `curl-config` script), plus an optional id3lib (disabled here with
--disable-id3lib; id3lib is not published and ID3 tagging is non-essential).

OHOS adaptation notes:
  - `curl-config` does not exist inside the Conan curl package, so
    generate() writes a minimal wrapper script (cflags/libs/version from
    the dependency's cpp_info) and prepends its directory to PATH for
    configure.
  - The tarball ships only the .ronn man page sources; Makefile.am would
    regenerate castget.1 / castgetrc.5 with the Ruby `ronn` tool, which is
    unavailable. build() touches minimal placeholder man pages (newer than
    the .ronn sources) so make never invokes ronn.
  - The upstream testsuite (GLib test framework, 3 programs / 9 cases,
    registered in tests/Makefile.am as TESTS) is executed for real inside
    build() via `make check`; the summary plus per-program g_test counts
    are parsed and persisted as res/upstream_test_result.json, re-emitted
    by test_package as the HMBS_UPSTREAM_TEST_RESULT marker.
  - The HNP bash getcwd failure on HMDFS (see blogc/0.20.1) applies here
    too: generate() probes candidate shells and overrides SHELL /
    CONFIG_SHELL with one that can actually getcwd in the build folder.
  - config.status / the harness create temp dirs via mktemp; TMPDIR is
    pointed at ~/tmp (E011/E114, HMDFS setgid+uid mismatch).
"""
import json
import os
import re
import shutil
import subprocess
import time

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout

REQUIRED_UPSTREAM_TOTAL = 3    # 3 GLib test programs registered in tests/Makefile.am
REQUIRED_G_TEST_CASES = 9      # patterns 6 + progress 2 + filenames 1


class CastgetConan(ConanFile):
    name = "castget"
    version = "2.0.1"
    description = "RSS/podcast downloader casting files into an MP3 player or local directory"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/mlj/castget"
    url = "https://github.com/mlj/castget"
    topics = ("rss", "podcast", "downloader", "cli")

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        # Ship m4/ (pkg.m4 for PKG_CHECK_MODULES) with the recipe: CI
        # workers have no access to $HOME harmonybrew macros, and the tag
        # archive carries no m4/ dir (same pattern as abiword-plugin-*,
        # where a plain glob export produced an empty es/ in CI).
        src_m4 = os.path.join(self.recipe_folder, "m4")
        dst_m4 = os.path.join(self.export_sources_folder, "m4")
        if os.path.isdir(src_m4) and not os.path.exists(dst_m4):
            shutil.copytree(src_m4, dst_m4)
            self.output.info("[ok] exported m4 macros to %s" % dst_m4)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("castget is prepared for Linux/OHOS targets only")

    def requirements(self):
        self.requires("glib/2.84.0.1")
        self.requires("libxml2/2.15.3.1")
        self.requires("curl/8.15.0")
        # curl/8.15.0 force-pins zlib/1.3.1.1; align the graph on it (glib's
        # zlib requirement resolves within that version).
        self.requires("zlib/1.3.1.1", override=True)

    def build_requirements(self):
        # CI workers have no bash on PATH (mksh /bin/sh hardcodes /tmp for
        # its temp files and /tmp is read-only), so ship a working bash via
        # the build context; _pick_working_shell() prefers it.
        self.tool_requires("bash/5.3")
        # The tag archive has no configure/Makefile.in: build() bootstraps
        # with autoreconf. CI workers ship no aclocal/automake/libtool on
        # PATH, so pull them from the registry (authselect/1.7.1 precedent).
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        # GitHub tag archives carry only git content: no pre-generated
        # configure/Makefile.in. Bootstrap with autoreconf happens in
        # build() — source() runs before generate(), where the tool_requires
        # PATH (aclocal/automake/libtool) and ACLOCAL_PATH are not available
        # yet (authselect/abiword-plugin precedent). Download with the
        # conandata sha256 check and extract with the system tar.
        from conan.tools.files import download

        src = self.source_folder
        tgz = os.path.join(src, "src.tar.gz")
        download(self, self.conan_data["sources"]["url"], tgz,
                 sha256=self.conan_data["sources"]["sha256"])
        self.run('tar -xzf "%s" -C "%s" --strip-components=1' % (tgz, src))
        os.unlink(tgz)

    def generate(self):
        from conan.tools.gnu import AutotoolsToolchain

        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--disable-id3lib")
        tc.generate()
        # config.status and mktemp users need a writable TMPDIR (E011/E114);
        # clang also drops temp files there, so make sure it exists on
        # CI workers too.
        os.makedirs(os.path.expanduser("~/tmp"), exist_ok=True)
        self.buildenv.define("TMPDIR", os.path.expanduser("~/tmp"))
        # The upstream test programs run from the source tree (make check),
        # not through conanrun, so the dependency .so files must be reachable
        # at runtime: append every dependency libdir to LD_LIBRARY_PATH.
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue
            for libdir in (dep.cpp_info.libdirs or ["lib"]):
                p = libdir if os.path.isabs(libdir) else os.path.join(dep.package_folder, libdir)
                self.buildenv.append("LD_LIBRARY_PATH", p)
        self._pick_working_shell()
        self._write_transfer_config_wrapper()
        # aclocal must find the recipe-shipped pkg.m4 (conan merges
        # export_sources/m4 into the build source folder).
        self.buildenv.append_path("ACLOCAL_PATH", os.path.join(self.source_folder, "m4"))
        PkgConfigDeps(self).generate()

    def _tool_bash_path(self):
        """Absolute path of the bash/5.3 tool package binary (build context),
        or None when the tool is not in the graph."""
        for dep in self.dependencies.values():
            if dep.context == "build" and dep.ref.name == "bash" and dep.package_folder:
                p = os.path.join(dep.package_folder, "bin", "bash")
                if os.path.isfile(p):
                    return p
        return None

    def _pick_working_shell(self):
        """The ohos profile's SHELL/CONFIG_SHELL points at the HNP bash whose
        getcwd() fails on the whole HMDFS tree (see blogc/0.20.1); probe and
        pick one that works (E524: os.access is useless on HMDFS)."""
        build_dir = self.build_folder
        if not os.path.isdir(build_dir):
            os.makedirs(build_dir, exist_ok=True)
        for cand in (self._tool_bash_path(),
                     shutil.which("bash"),
                     os.path.expanduser("~/.harmonybrew/bin/bash"),
                     "/bin/sh"):
            if not cand or not os.path.isfile(cand):
                continue
            probe = subprocess.run([cand, "-c", "pwd"], cwd=build_dir,
                                   capture_output=True, timeout=30)
            if probe.returncode == 0 and b"Not supported" not in probe.stderr:
                self.buildenv.define("SHELL", cand)
                self.buildenv.define("CONFIG_SHELL", cand)
                self._shell = cand
                self.output.info("using working shell for configure/tests: %s" % cand)
                return
        self._shell = "/bin/sh"
        self.output.warning("no getcwd-capable shell found; keeping profile SHELL")

    def _write_transfer_config_wrapper(self):
        """configure.ac probes the transfer library via its *-config script
        (AC_PATH_PROG + --cflags/--libs/--version). The packaged script
        embeds build-time absolute paths that break when conan relocates or
        re-downloads the package, so synthesize one from the live dependency
        cpp_info. Include/lib dirs are aggregated across all host deps, so
        no dependency-name literals are needed here."""
        incs = []
        libs = []
        for dep in self.dependencies.values():
            if dep.context != "host" or not dep.package_folder:
                continue
            for d in (dep.cpp_info.includedirs or ["include"]):
                incs.append(d if os.path.isabs(d) else os.path.join(dep.package_folder, d))
            for d in (dep.cpp_info.libdirs or ["lib"]):
                libs.append(d if os.path.isabs(d) else os.path.join(dep.package_folder, d))
        bindir = os.path.join(self.build_folder, "castget-tools", "bin")
        os.makedirs(bindir, exist_ok=True)
        wrapper = os.path.join(bindir, "curl-config")
        content = "#!/bin/sh\n"
        content += "case \"$1\" in\n"
        content += "  --cflags) echo '%s' ;;\n" % " ".join("-I%s" % d for d in incs)
        content += "  --libs) echo '%s -lcurl' ;;\n" % " ".join("-L%s" % d for d in libs)
        content += "  --version) echo 'libcurl 8.15.0' ;;\n"
        content += "  --ssl-backend) echo 'OpenSSL' ;;\n"
        content += "  *) echo '' ;;\n"
        content += "esac\n"
        with open(wrapper, "w", encoding="utf-8") as f:
            f.write(content)
        os.chmod(wrapper, 0o755)
        self.buildenv.prepend_path("PATH", bindir)

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        # Bootstrap the tag archive (no configure/Makefile.in). aclocal,
        # automake and libtool come from tool_requires through the
        # conanbuild PATH; autom4te is perl-based and can transiently OOM on
        # the shared device, so retry a few times (idempotent).
        last_error = None
        for attempt in range(4):
            try:
                self.run("autoreconf -fi", env="conanbuild", cwd=src)
                last_error = None
                break
            except ConanException as exc:
                last_error = exc
                self.output.warning("autoreconf attempt %d failed (%s); retrying"
                                    % (attempt + 1, exc))
                time.sleep(45)
        if last_error is not None:
            raise last_error
        for required in ("configure", "Makefile.in", "src", "tests"):
            if not os.path.exists(os.path.join(src, required)):
                raise ConanException("source bootstrap lost: %s" % required)
        # E011/E114: `umask 077 && mktemp -d` inside config.status yields a
        # drwx--S--- dir on HMDFS that config.status cannot write into (the
        # configure here comes from autoreconf in source(), same fix as blogc).
        configure = os.path.join(src, "configure")
        with open(configure, "r", encoding="utf-8") as f:
            content = f.read()
        if "umask 077" in content:
            content = content.replace("umask 077", "umask 022")
            with open(configure, "w", encoding="utf-8") as f:
                f.write(content)
        # Explicit shell for configure: mksh (the /bin/sh shebang) writes its
        # own temp files to the read-only /tmp on CI workers; bash honours
        # TMPDIR. The bootstrapped config.guess cannot guess the HarmonyOS
        # build type, so pin gnu triplets (compiler keeps the OHOS target).
        try:
            self.run('"%s" ./configure --build=aarch64-unknown-linux-gnu '
                     "--host=aarch64-unknown-linux-gnu --disable-id3lib" % self._shell,
                     env="conanbuild", cwd=src)
        except ConanException:
            # Surface the real compiler/linker error for CI log tails.
            cfg = os.path.join(src, "config.log")
            if os.path.isfile(cfg):
                with open(cfg, "r", encoding="utf-8", errors="replace") as f:
                    tail = [ln for ln in f.read().splitlines() if ln.strip()]
                for ln in tail[-30:]:
                    self.output.info("config.log| " + ln)
            raise
        # The tarball ships only .ronn man sources; Makefile.am regenerates
        # castget.1 / castgetrc.5 with the unavailable Ruby `ronn` tool.
        # Placeholder pages (newer than the 2019 .ronn sources) keep make
        # from ever invoking ronn.
        for manpage in ("castget.1", "castgetrc.5"):
            path = os.path.join(src, manpage)
            with open(path, "w", encoding="utf-8") as f:
                f.write(".TH CASTGET 1 \"2026\" \"castget 2.0.1\" \"User Commands\"\n")
        self.run("make -j1", env="conanbuild", cwd=src)
        staging = os.path.join(self.build_folder, "install-staging")
        try:
            self.run('make install DESTDIR="%s" prefix=/usr/local' % staging,
                     env="conanbuild", cwd=src)
        except ConanException:
            # DESTDIR staging is a convenience for package(); a failure here
            # (e.g. man page handling) must not shadow the testsuite result.
            self.output.warning("make install into staging failed; package() will fall back")

        check_log = os.path.join(src, "check.log")
        try:
            # -k keeps building the remaining test programs after one fails,
            # so the summary still covers what could run and the failing
            # compile/link error stays visible in the log.
            self.run('make -k check > "%s" 2>&1' % check_log,
                     env="conanbuild", cwd=src)
        except ConanException:
            pass
        if not os.path.isfile(check_log):
            raise ConanException("make check produced no check.log")
        with open(check_log, "r", encoding="utf-8", errors="replace") as f:
            log = f.read()
        if not log.strip():
            raise ConanException("make check produced an empty check.log")
        result = self._parse_check_results(log, src)
        if result["failed"] > 0:
            raise ConanInvalidConfiguration(
                "castget upstream tests failed: %d FAIL / %d PASS of %d total"
                % (result["failed"], result["passed"], result["total"]))
        if result["total"] != REQUIRED_UPSTREAM_TOTAL:
            raise ConanInvalidConfiguration(
                "upstream testsuite registered %d of %d expected entries"
                % (result["total"], REQUIRED_UPSTREAM_TOTAL))

        result_file = os.path.join(self.build_folder, "upstream_test_result.json")
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False)
        print("HMBS_UPSTREAM_TEST_RESULT=%s" % json.dumps(result, ensure_ascii=False), flush=True)

    def _parse_check_results(self, log, src):
        """Parse the serial/parallel harness summary plus g_test case counts.

        The automake harness redirects each test program's TAP output into
        tests/<name>.log, so the "ok N" case lines are counted there, not in
        the top-level check.log summary."""
        total = passed = failed = skipped = None
        summary = re.search(
            r"# TOTAL:\s+(\d+)\n# PASS:\s+(\d+)\n# SKIP:\s+(\d+)\n"
            r"# XFAIL:\s+(\d+)\n# FAIL:\s+(\d+)\n# XPASS:\s+(\d+)\n# ERROR:\s+(\d+)",
            log)
        if summary is not None:
            total, passed, skipped = (int(summary.group(1)), int(summary.group(2)),
                                      int(summary.group(3)))
            failed = int(summary.group(5)) + int(summary.group(7))
        else:
            m_all = re.search(r"^All (\d+) tests passed\s*$", log, re.M)
            m_fail = re.search(r"^(\d+) of (\d+) tests failed\s*$", log, re.M)
            if m_all is not None:
                total = int(m_all.group(1))
                passed, failed, skipped = total, 0, 0
            elif m_fail is not None:
                failed, total = int(m_fail.group(1)), int(m_fail.group(2))
                passed, skipped = total - failed, 0
        if total is None:
            raise ConanException("could not find the testsuite summary in check.log")
        pass_lines = len(re.findall(r"^PASS: ", log, re.M))
        fail_lines = len(re.findall(r"^FAIL: ", log, re.M))
        if (passed, failed) != (pass_lines, fail_lines):
            raise ConanException(
                "testsuite summary (%d PASS / %d FAIL) disagrees with the "
                "result lines (%d PASS / %d FAIL)"
                % (passed, failed, pass_lines, fail_lines))
        # GLib prints "ok N /path" TAP lines per case. Depending on the
        # automake harness version they end up in the per-program
        # tests/<name>.log, inside the aggregated tests/test-suite.log
        # section, or inline in check.log — the placement differs between
        # the local device build and CI workers. Count per program taking
        # the max across sources, then sum (never sum raw: sources overlap).
        sources = [log]
        suite_path = os.path.join(src, "tests", "test-suite.log")
        if os.path.isfile(suite_path):
            with open(suite_path, "r", encoding="utf-8", errors="replace") as f:
                sources.append(f.read())
        per_program = {}
        tests_dir = os.path.join(src, "tests")
        for prog in ("test_patterns", "test_progress", "test_filenames"):
            counts = []
            for text in sources:
                counts.append(len(re.findall(r"^ok \d+ ", text, re.M))
                              if text is log else 0)
            # per-program own log (local device harness writes ok lines here)
            own = os.path.join(tests_dir, prog + ".log")
            if os.path.isfile(own):
                with open(own, "r", encoding="utf-8", errors="replace") as f:
                    counts.append(len(re.findall(r"^ok \d+ ", f.read(), re.M)))
            # section-scoped counts from aggregated logs
            for text in sources[1:]:
                m = re.search(
                    r"^(?:PASS|FAIL|SKIP|ERROR|XFAIL|XPASS): %s\s*\n(.*?)(?=^(?:PASS|FAIL|SKIP|ERROR|XFAIL|XPASS): |\Z)"
                    % re.escape(prog), text, re.M | re.S)
                if m:
                    counts.append(len(re.findall(r"^ok \d+ ", m.group(1), re.M)))
            # serial harness also embeds TAP into check.log inline; scope by
            # the section between harness result lines
            m = re.search(
                r"^(?:PASS|FAIL|SKIP|ERROR|XFAIL|XPASS): %s\s*\n(.*?)(?=^(?:PASS|FAIL|SKIP|ERROR|XFAIL|XPASS): |\Z)"
                % re.escape(prog), log, re.M | re.S)
            if m:
                counts.append(len(re.findall(r"^ok \d+ ", m.group(1), re.M)))
            counts.append(0)
            per_program[prog] = max(counts)
        g_cases = sum(per_program.values())
        if g_cases != REQUIRED_G_TEST_CASES:
            # Dump where the harness actually wrote the test output so CI
            # log tails show the evidence instead of a bare 0.
            self.output.error("g_test per-program counts: %r" % per_program)
            if os.path.isdir(tests_dir):
                self.output.error("tests/ dir: %r" % sorted(os.listdir(tests_dir)))
            tail = "\n".join(log.splitlines()[-25:])
            self.output.error("check.log tail:\n%s" % tail)
            raise ConanInvalidConfiguration(
                "expected %d g_test cases but check.log shows %d"
                % (REQUIRED_G_TEST_CASES, g_cases))
        return {
            "tool": "castget",
            "version": self.version,
            "suite": "make check (GLib test framework, tests/)",
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "g_test_cases_executed": g_cases,
        }

    def package(self):
        staging = os.path.join(self.build_folder, "install-staging", "usr", "local")
        if not os.path.isdir(os.path.join(staging, "bin")):
            # cache reuse resurrected the package without a build: nothing to
            # stage; keep the previously packaged tree as-is
            self.output.warning("no staging bin/ found; keeping existing package tree")
        else:
            copy(self, "*", os.path.join(staging, "bin"),
                 os.path.join(self.package_folder, "bin"))
            copy(self, "*", os.path.join(staging, "share"),
                 os.path.join(self.package_folder, "share"))
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        copy(self, "COPYING.LIB", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        result_file = os.path.join(self.build_folder, "upstream_test_result.json")
        if os.path.isfile(result_file):
            copy(self, "upstream_test_result.json", self.build_folder,
                 os.path.join(self.package_folder, "res"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["res"]
