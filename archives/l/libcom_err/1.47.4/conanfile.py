#!/usr/bin/env python3
"""Conan recipe — libcom_err 1.47.4 (from e2fsprogs).

libcom_err is the "common error description library" (error-table / com_err)
shipped inside e2fsprogs.  Its self-contained autotools subproject lives in
``lib/et`` and produces ``libcom_err.a``, the ``com_err.h`` header, the
``com_err.pc`` pkg-config file and the ``compile_et`` error-table compiler.

We reuse the official e2fsprogs 1.47.4 release tarball, run the top-level
``./configure`` only to generate the build tree (MCONFIG + lib/et/Makefile +
lib/config.h), then build / test / install **only** ``lib/et``:

    make -C lib/et            # libcom_err.a (+ compile_et, com_err.pc)
    make -C lib/et check      # upstream regression suite:
                              #   6 compile_et test cases (lib/et/test_cases/*.et)
    make -C lib/et install    # headers, static lib, pkg-config, compile_et

Upstream test count (``upstream_test_total``):
  lib/et/test_cases/*.et  = 6 error-table files; each is diffed against the
  checked-in expected .c/.h, and ``make check`` prints one
  "Test case <name> succeeded" line per passing case.
"""
import json
import os
import re

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibcomerrConan(ConanFile):
    name = "libcom_err"
    version = "1.47.4"
    description = "Common error description library (com_err) from e2fsprogs"
    license = "MIT"
    homepage = "http://e2fsprogs.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libcom_err supports only Linux/OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require aarch64 (armv8)")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------
    # OHOS / HMFS robustness helpers (see archive notes.md)
    # ------------------------------------------------------------------
    def _writable_tmpdir(self):
        """OHOS /tmp is a read-only erofs mount; use the hmbs task temp dir."""
        for var in ("HMBS_TMPDIR", "TMPDIR", "TMP", "TEMP"):
            value = os.environ.get(var)
            if value:
                tmpdir = value
                break
        else:
            tmpdir = os.path.join(os.path.expanduser("~"), "tmp", "libcom_err-1.47.4")
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            tmpdir = self.build_folder or os.getcwd()
        return tmpdir

    def _patch_configure_workdir(self):
        """[shell_getcwd] + E011/E114: HMFS configure/mktemp workarounds.

        Autoconf-generated configure does ``ac_pwd=`pwd` && test -n "$ac_pwd"``
        which aborts with 'working directory cannot be determined' on HMFS;
        fall back to $PWD.  Also relax umask 077 -> 022 because HMFS cannot
        write an 0700 mktemp directory.  Best-effort: only rewrite when the
        exact upstream snippet is present, else log a warning and continue.
        """
        patched = False
        for name in ("configure",):
            path = os.path.join(self.source_folder, name)
            if not os.path.isfile(path):
                self.output.warning("[shell_getcwd] %s not found; skipping" % name)
                continue
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
            except OSError:
                continue
            orig = content
            if "umask 077" in content:
                content = content.replace("umask 077", "umask 022")
            old_pattern = 'ac_pwd=`pwd` && test -n "$ac_pwd" &&'
            new_pattern = 'ac_pwd=`pwd` 2>/dev/null || ac_pwd="$PWD"\ntest -n "$ac_pwd" &&'
            if old_pattern in content:
                content = content.replace(old_pattern, new_pattern, 1)
            if content != orig:
                try:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(content)
                    patched = True
                    self.output.info("[shell_getcwd] patched %s: umask+pwd fallback" % name)
                except OSError:
                    pass
        if not patched:
            self.output.warning("[shell_getcwd] no recognized pattern patched; relying on env")

    def _fix_config_status_mktemp(self):
        """E114: redirect config.status mktemp into a writable TMPDIR."""
        cs_file = None
        for base in (self.build_folder, self.source_folder):
            if not base:
                continue
            cand = os.path.join(base, "config.status")
            if os.path.isfile(cand):
                cs_file = cand
                break
        if not cs_file:
            return
        try:
            with open(cs_file, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except OSError:
            return
        tmpdir = self._writable_tmpdir()
        fixed_dir = os.path.join(tmpdir, "comerr-config-status-tmp")
        try:
            os.makedirs(fixed_dir, exist_ok=True)
        except OSError:
            return
        replaced = 0
        new_content, n = re.subn(
            r'tmp=`\(umask 077 && mktemp -d "\./confXXXXXX"\) 2>/dev/null`',
            'tmp=%s' % fixed_dir, content)
        content = new_content
        replaced += n
        new_content, n = re.subn(r'tmp=\./conf\$\$-\$RANDOM', 'tmp=%s' % fixed_dir, content)
        content = new_content
        replaced += n
        new_content, n = re.subn(r'\(umask 077 && mkdir "\$tmp"\)', 'true', content)
        content = new_content
        replaced += n
        if "umask 077" in content:
            content = content.replace("umask 077", "umask 022")
            replaced += 1
        if replaced:
            try:
                with open(cs_file, "w", encoding="utf-8") as f:
                    f.write(content)
                self.output.info("E114: redirected %d mktemp pattern(s) in config.status"
                                 % replaced)
            except OSError:
                pass

    # ------------------------------------------------------------------
    def generate(self):
        tc = AutotoolsToolchain(self)
        # NOTE: only options that e2fsprogs configure actually recognizes are
        # passed below; an unrecognized --disable-* aborts autoconf configure.
        # We build only lib/et via `make -C lib/et`, so the auxiliary-program
        # disables only avoid optional dependency probes.
        tc.configure_args.extend([
            "--prefix=/",
            "--disable-nls",
            "--disable-rpath",
            "--disable-backtrace",
            "--disable-tls",
            "--disable-testio-debug",
            "--disable-debugfs",
            "--disable-imager",
            "--disable-resizer",
            "--disable-defrag",
            "--disable-mmp",
            "--disable-tdb",
            "--disable-bmap-stats",
            "--disable-uuidd",
            "--disable-fuse2fs",
        ])
        if self.settings.os == "OHOS":
            tc.configure_args.extend([
                "--build=aarch64-linux-ohos",
                "--host=aarch64-linux-ohos",
                # HMFS (HarmonyOS filesystem) does not support hard links
                # (HMBS_CAP_HARDLINK=0); e2fsprogs' lib/Makefile.library
                # creates the convenience lib/libcom_err.a with $(LN), and the
                # install target creates include/com_err.h with $(LN), both as
                # hard links by default.  Switch both to symbolic links
                # (LINK_BUILD_FLAGS=-s / LINK_INSTALL_FLAGS=-sf), which HMFS
                # does support (HMBS_CAP_SYMLINK=1).
                "--enable-symlink-build",
                "--enable-symlink-install",
            ])
        tmpdir = self._writable_tmpdir()
        env = tc.environment()
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        tc.generate(env=env)

    def _make(self):
        """Resolve make executable (hmbs prepends tool dirs to PATH)."""
        make = self.conf.get("user.hmbs:make_path", default=None)
        return make or "make"

    def build(self):
        tmpdir = self._writable_tmpdir()
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass

        apply_conandata_patches(self)
        self._patch_configure_workdir()
        if self.settings.os == "OHOS":
            os.environ["PWD"] = self.build_folder
            self.output.info("[shell_getcwd] PWD=%s exported" % self.build_folder)
        try:
            os.chdir(self.build_folder)
        except OSError:
            pass

        autotools = Autotools(self)
        autotools.configure()
        self._fix_config_status_mktemp()

        make = self._make()
        # Build only the com_err library (lib/et) — not the whole e2fsprogs tree.
        self.run("%s -C lib/et -j1" % make, env="conanbuild")
        # ------------------------------------------------------------------
        # Upstream regression suite: make -C lib/et check
        #   counts come from the make check log (deterministic framework output)
        # ------------------------------------------------------------------
        check_log = os.path.join(self.build_folder, "check.log")
        check_cmd = "%s -C lib/et check -j1 > %s 2>&1" % (make, check_log)
        _rc = self.run(check_cmd, env="conanbuild", ignore_errors=True)
        # Deterministic discovered count: number of *.et fixtures the upstream
        # `check` loop iterates over (that is the registered test cases).
        test_cases_dir = os.path.join(self.source_folder, "lib", "et", "test_cases")
        try:
            et_names = sorted(
                n[:-3] for n in os.listdir(test_cases_dir) if n.endswith(".et"))
        except OSError:
            et_names = []
        discovered = len(et_names)
        # Parse the make check log.  The upstream `check` target prints exactly
        # one "Test case <name> succeeded/failed" line per run of a case, so the
        # case NAME is the stable unit (matching the discovered registration).
        # If a run got repeated and the log carries several lines for one name,
        # keep the *last* verdict seen per name: counts stay a single per-test
        # truth and `executed <= discovered` always holds (no line-duplication
        # inflation into executed > discovered).
        results = {}  # test name -> True(succeeded) / False(failed)
        verdict_re = re.compile(r"Test case ([A-Za-z0-9_.-]+) (succeeded|failed)")
        try:
            with open(check_log, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    m = verdict_re.search(line)
                    if m:
                        results[m.group(1)] = (m.group(2) == "succeeded")
        except OSError:
            pass
        failed = sum(1 for ok in results.values() if not ok)
        passed = len(results) - failed
        executed = len(results)
        if discovered == 0 and passed == 0 and failed == 0 and _rc == 0:
            status = "no_tests"
        else:
            status = "passed" if failed == 0 and executed == discovered else "failed"
        upstream = {
            "status": status,
            "framework": "autotools",
            "command": "make -C lib/et check",
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
        }
        # Gap accounting: every registered case that did not pass must appear in
        # `gaps`, with total count == discovered - passed.  Two cases are
        # distinguished by category: cases the check reported as failed
        # (test_failure) and registered cases it never reported (environment —
        # the fail-fast loop stopped early or no verdict line was produced).
        if upstream.get("status") != "no_tests":
            gaps = []
            if failed > 0:
                gaps.append({
                    "count": failed,
                    "category": "test_failure",
                    "detail": ("lib/et `make check` reported failed test case(s), "
                               "see check log for the diff (`Test case X failed`)."),
                    "evidence": check_log,
                })
            if discovered > executed:
                gaps.append({
                    "count": discovered - executed,
                    "category": "environment",
                    "detail": ("lib/et registered cases not executed by make check "
                               "(loop stopped early or produced no verdict line)"),
                    "evidence": check_log,
                })
            if gaps:
                upstream["gaps"] = gaps
        msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream)
        print(msg, flush=True)
        self.output.info(msg)
        # Do not abort packaging on a failing `make check`: report the honest
        # marker (including any gaps) and let packaging + the consumer test
        # finish so genuine failures are surfaced through the marker instead of
        # a hard abort.  test_package still runs independently.

    def package(self):
        make = self._make()
        self.run("%s -C lib/et install DESTDIR=%s" % (make, self.package_folder),
                 env="conanbuild")
        # Optional shared-lib path (upstream only builds .so with
        # --enable-elf-shlibs, which we intentionally leave off for static-only
        # robustness on OHOS/HMFS).  Keep headers for consumer use either way.
        if os.path.exists(os.path.join(self.package_folder, "lib")):
            for la in ("libcom_err.la",):
                p = os.path.join(self.package_folder, "lib", la)
                if os.path.exists(p):
                    os.remove(p)
        # License
        for lic in ("NOTICE", "COPYING"):
            p = os.path.join(self.source_folder, lic)
            if os.path.exists(p):
                copy(self, lic, self.source_folder,
                     os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["com_err"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("pkg_config_name", "com_err")
        self.cpp_info.set_property("cmake_file_name", "com_err")
        self.cpp_info.set_property("cmake_target_name", "com_err::com_err")
        # compile_et is installed to bin/ but this is a library package; treat
        # as pure library (no commands.json) and do not advertise bindirs.
