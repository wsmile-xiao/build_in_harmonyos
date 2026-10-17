#!/usr/bin/env python3
"""Conan recipe for yash 2.60 — yet another POSIX-compliant shell.

yash (magicant/yash) is a self-contained C99 shell with a hand-written
(non-autoconf) configure script and a real upstream test suite:
tests/ holds 243 .tst files (126 POSIX + 117 yash-specific, driven by
tests/Makefile via .trs result files).

Platform notes:
- Line editing needs a terminfo library; ncurses/6.6 is pulled from
  the ohpcd artifact repo and pointed at via CPPFLAGS/LDFLAGS
  (--with-term-lib=ncurses).  NLS is disabled (no gettext on platform).
- LD_LIBRARY_PATH is explicitly emptied during build: some CI workers
  carry an ambient LD pointing at /usr/local/lib whose incompatible
  libxml2.so.16 breaks the SDK's lld on every link (CI-021 build
  #48068 — mechanism documented in libodfgen/libabw).
- The hand-written configure compiles and runs feature probes, which
  works natively on the device (build == host == OHOS/aarch64).
- Upstream tests run during build() and the pass/fail tally is parsed
  from tests/*.trs and recorded in the log (failures are surfaced, not
  hidden — the recipe fails if the summary cannot be produced).
"""

import os
import shlex
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

OHOS_SHELL_CANDIDATES = ("/data/service/hnp/bin/bash", "/usr/bin/zsh", "bash")


class YashConan(ConanFile):
    name = "yash"
    version = "2.60"
    description = ("yash - yet another shell: a POSIX-compliant command "
                   "line shell with its own line editor")
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/magicant/yash"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires("ncurses/6.6")

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"yash is adapted for Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        # url may arrive as a candidate list (the CI pre-download step
        # rewrites conandata's url into [mirror, official]) — conan's
        # get() handles both shapes natively.
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        build = self.build_folder
        self._copy_tree(self.source_folder, build)

        dep = self.dependencies["ncurses"]
        inc = os.path.join(dep.package_folder, "include")
        lib = os.path.join(dep.package_folder, "lib")

        env = dict(os.environ)
        # lld/libxml2 shield — see class docstring.
        env["LD_LIBRARY_PATH"] = ""
        env["CC"] = self._cc()
        shell = self._resolve_shell()
        env["SHELL"] = shell
        env["CONFIG_SHELL"] = shell
        env["CPPFLAGS"] = f"-I{inc}"
        env["LDFLAGS"] = f"-L{lib} -Wl,-rpath,{lib}"
        # The published ncurses package ships wide-char archives only
        # (libncursesw.a), so select ncursesw explicitly.
        cmd = (f"{shlex.quote(shell)} ./configure --prefix=/ "
               "--with-term-lib=ncursesw --disable-nls < /dev/null")
        completed = subprocess.run(cmd, shell=True, cwd=build, env=env)
        if completed.returncode != 0:
            self._dump_failure_diagnostics(build, env)
            raise ConanException(
                f"configure failed (rc={completed.returncode})")
        completed = subprocess.run("make -j2 < /dev/null", shell=True,
                                   cwd=build, env=env)
        if completed.returncode != 0:
            self._dump_failure_diagnostics(build, env)
            raise ConanException("make failed")
        self._run_upstream_tests(build, env)

    def _run_upstream_tests(self, build, env):
        """Run upstream's .tst suite (tests/Makefile) and parse .trs.

        .trs files carry one line per assertion: "%%% OK[...]" /
        "%%% ERROR[...]" / "%%% SKIPPED: ...".  A test file counts as
        failed when it contains any ERROR line.  Failures are reported
        in the log, not hidden; the build only fails when the suite
        produced no results at all.
        """
        tests_dir = os.path.join(build, "tests")
        # Remove any stale enqueue.sh queue dir (a killed earlier run
        # leaves tmp.queue behind; nobody would consume it).
        import shutil as _shutil
        _shutil.rmtree(os.path.join(tests_dir, "tmp.queue"),
                       ignore_errors=True)
        # Exclude %REQUIRETTY% tests: this platform's session has a
        # controlling terminal (checkfg passes) but no foreground
        # process-group semantics — job-control tests hang indefinitely
        # under both ptwrap and direct execution (sigstop3-p.tst hung
        # 10+ min on device, observed twice).  They are reported as
        # excluded-with-reason, and the per-test timeout below backstops
        # anything unexpected.
        all_tst = sorted(f for f in os.listdir(tests_dir)
                         if f.endswith(".tst"))
        run_list, excluded = [], []
        for name in all_tst:
            with open(os.path.join(tests_dir, name),
                      errors="replace") as handle:
                if "%REQUIRETTY%" in handle.read():
                    excluded.append(name)
                else:
                    run_list.append(name)
        self.output.info(
            f"[upstream-tests] total={len(all_tst)} "
            f"run={len(run_list)} excluded(REQUIRETTY)={len(excluded)}")
        self.output.info("[upstream-tests] excluded: "
                         + ",".join(n[:-4] for n in excluded))
        # Redirect the suite output to a file, NOT the inherited stdout:
        # tests that orphan their testee (observed on platform) would
        # otherwise hold conan's pipe open and block this process
        # forever.  Orphaned test processes are swept afterwards.
        suite_log = os.path.join(tests_dir, "suite-run.log")
        with open(suite_log, "w") as sink:
            subprocess.run("make -j1 -k test "
                           f"TEST_SOURCES='{' '.join(run_list)}' "
                           "RUN_TEST='timeout -s KILL 120 ./resetsig ../yash ./run-test.sh' "
                           "< /dev/null; echo TESTS_RC=$?",
                           shell=True, cwd=tests_dir, env=env,
                           stdout=sink, stderr=subprocess.STDOUT)
        subprocess.run("pkill -9 -f 'run-test.sh' 2>/dev/null; "
                       "pkill -9 -f 'checkfg' 2>/dev/null; true",
                       shell=True, env=env)
        with open(suite_log, errors="replace") as handle:
            tail = handle.readlines()[-30:]
        for line in tail:
            self.output.info("[suite] " + line.rstrip())
        file_pass, file_fail, failed_names = 0, 0, []
        ok_assertions, err_assertions, skipped = 0, 0, 0
        for name in sorted(os.listdir(tests_dir)):
            if not name.endswith(".trs"):
                continue
            path = os.path.join(tests_dir, name)
            with open(path, errors="replace") as handle:
                lines = handle.readlines()
            errs = sum(1 for ln in lines if ln.startswith("%%% ERROR["))
            oks = sum(1 for ln in lines if ln.startswith("%%% OK["))
            skips = sum(1 for ln in lines if ln.startswith("%%% SKIPPED:"))
            ok_assertions += oks
            err_assertions += errs
            skipped += skips
            if errs:
                file_fail += 1
                failed_names.append(name)
            else:
                file_pass += 1
        self.output.info(
            f"[upstream-tests] files: PASS={file_pass} FAIL={file_fail}; "
            f"assertions: OK={ok_assertions} ERROR={err_assertions} "
            f"SKIPPED={skipped}")
        if failed_names:
            self.output.info("[upstream-tests] failed files: "
                             + ",".join(failed_names))
        if file_pass + file_fail == 0:
            raise ConanException(
                "upstream test suite produced no .trs results")

    def package(self):
        build = self.build_folder
        inst = os.path.join(build, "inst")
        env = dict(os.environ)
        env["LD_LIBRARY_PATH"] = ""
        env["SHELL"] = self._resolve_shell()
        completed = subprocess.run(
            f"make install DESTDIR={shlex.quote(inst + os.sep)} < /dev/null",
            shell=True, cwd=build, env=env)
        if completed.returncode != 0:
            raise ConanException(
                f"make install failed (rc={completed.returncode})")
        copy(self, "yash", src=os.path.join(inst, "bin"),
             dst=os.path.join(self.package_folder, "bin"),
             keep_path=False)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]

    # ── helpers ─────────────────────────────────────────────────────────

    def _cc(self):
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default=None)
        if compilers:
            if isinstance(compilers, str):
                import json
                try:
                    compilers = json.loads(compilers)
                except ValueError:
                    compilers = {}
            if compilers.get("c"):
                return compilers["c"]
        return "clang"

    def _resolve_shell(self):
        for candidate in OHOS_SHELL_CANDIDATES:
            if os.path.isfile(candidate):
                return candidate
        return "/bin/sh"

    def _copy_tree(self, src, dst):
        import shutil
        shutil.copytree(src, dst, dirs_exist_ok=True, symlinks=True)

    def _dump_failure_diagnostics(self, directory, environment):
        self.output.info("---- ohos diagnostics: environment ----")
        for name in ("CC", "CFLAGS", "CPPFLAGS", "LDFLAGS", "LDLIBS",
                     "TMPDIR", "LD_LIBRARY_PATH", "PATH", "SHELL"):
            if name in environment:
                self.output.info(f"{name}={environment[name]}")
        config_log = os.path.join(directory, "config.log")
        if os.path.isfile(config_log):
            with open(config_log, errors="replace") as handle:
                lines = handle.readlines()
            for line in lines[-25:]:
                self.output.info(line.rstrip())
