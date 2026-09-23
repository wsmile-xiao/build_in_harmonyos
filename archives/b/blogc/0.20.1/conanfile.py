#!/usr/bin/env python3
"""Conan recipe for blogc 0.20.1 — blog compiler toolchain (OHOS aarch64).

blogc is a pure-C blog/static-site compiler shipped as CLI tools (blogc,
blogc-make, blogc-runserver). The 0.20.1 release tarball is autotools-only
(the CMake build exists only in the git tree) and its build-aux/config.sub
predates the *-linux-ohos triplet, so configure runs with gnu-style
build/host triplets while the compiler keeps the OHOS target (same approach
as authselect/1.7.1).

The upstream testsuite is executed for real inside build() via `make check`:
  - cmocka unit-test programs (test_requires cmocka/2.0.2 + PkgConfigDeps so
    configure's PKG_CHECK_MODULES([CMOCKA]) succeeds),
  - end-to-end shell suites (tests/blogc/check_blogc.sh and, with
    --enable-make, tests/blogc-make/check_blogc_make.sh).

OHOS specifics:
  - ELF execution on the HMFS conan cache tree works on the current device
    but has been reported blocked ("Operation not permitted") on other
    adaptation paths (boxes/2.3.1); make check therefore probes `./blogc
    -v` in place first and only on failure relocates the built tree to a
    writable workspace (~/tmp/blogc-ws) and self-signs every ELF
    (binary-sign-tool) before running the suites.
  - config.status creates temp dirs with `umask 077 && mktemp`, which HMDFS
    turns into an unwritable setgid dir (E011/E114): the generated
    configure is patched to umask 022 before it runs.

Known cross-compile limits (documented in notes.md):
  - configure probes linker -wrap support with AC_RUN_IFELSE, which cannot
    run target binaries, so have_ld_wrap=no and the wrap-dependent test
    programs (blogc 5, blogc-make check_exec, blogc-runserver 2) are not
    registered.
  - tests/blogc/check_rusage.c exists in the tarball but is only registered
    when sys/resource.h and sys/time.h are both present (they are, on OHOS
    musl).
"""
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout

REQUIRED_UPSTREAM_TOTAL = 27  # 25 cmocka programs + 2 end-to-end shell suites


class BlogcConan(ConanFile):
    name = "blogc"
    version = "0.20.1"
    description = "A blog compiler — pure-C static site generator toolchain"
    license = "BSD-3-Clause"
    homepage = "https://github.com/blogc/blogc"
    url = "https://github.com/blogc/blogc"
    topics = ("blog", "static-site", "template", "cli")

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("blogc is prepared for Linux/OHOS targets only")

    def build_requirements(self):
        # cmocka is linked into the host-context unit-test programs built by
        # `make`; PkgConfigDeps hands configure's PKG_CHECK_MODULES([CMOCKA])
        # a pkg-config file for it. Not propagated to consumers.
        self.test_requires("cmocka/2.0.2")
        # CI workers have no bash on PATH (mksh /bin/sh hardcodes /tmp for
        # its temp files and /tmp is read-only), so ship a working bash via
        # the build context; _pick_working_shell() prefers it and
        # AC_PATH_PROG([bash]) in configure finds it through PATH.
        self.tool_requires("bash/5.3")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _configure_args(self):
        return [
            "--build=aarch64-unknown-linux-gnu",
            # tarball config.sub has no *-linux-ohos entry; gnu triplet keeps
            # configure's cross-compile logic while clang targets OHOS.
            "--host=aarch64-unknown-linux-gnu",
            "--enable-static",
            "--disable-shared",
            # Build every tool so their suites can register and run.
            "--enable-make",
            "--enable-runserver",
            # Keep configure away from host-only extras.
            "--disable-rpmbuild",
            "--disable-ronn",
            "--disable-valgrind",
        ]

    def generate(self):
        from conan.tools.gnu import AutotoolsToolchain

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(self._configure_args())
        tc.generate()
        # config.status and the test suites create temp dirs via mktemp;
        # HMDFS setgid+bad-uid makes ./confXXXXXX unwritable otherwise.
        # clang also drops temp files there, so make sure it exists on CI
        # workers too.
        os.makedirs(os.path.expanduser("~/tmp"), exist_ok=True)
        self.buildenv.define("TMPDIR", os.path.expanduser("~/tmp"))
        self._pick_working_shell()
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
        """Override the profile's SHELL/CONFIG_SHELL when they cannot getcwd.

        The ohos-aarch64 profile sets SHELL/CONFIG_SHELL to the HNP bash
        (/data/service/hnp/bin/bash, 5.3.0), whose getcwd fails on the whole
        HMDFS tree ("getcwd: cannot access parent directories: Not
        supported", bash shell-init error). autoconf's configure hard-depends
        on getcwd and re-executes itself through $CONFIG_SHELL, so it dies
        with "working directory cannot be determined" before anything else.
        Probe candidate shells by actually running `pwd` in the build folder
        and export the first one that works (the system /bin/sh and the
        harmonybrew bash both pass; os.access/chmod are useless on HMDFS,
        E524).
        """
        build_dir = self.build_folder
        if not os.path.isdir(build_dir):
            os.makedirs(build_dir, exist_ok=True)
        candidates = [self._tool_bash_path(),
                      shutil.which("bash"),
                      os.path.expanduser("~/.harmonybrew/bin/bash"),
                      "/bin/sh"]
        for cand in candidates:
            if not cand or not os.path.isfile(cand):
                self.output.info("shell candidate missing: %s" % cand)
                continue
            probe = subprocess.run([cand, "-c", "pwd"], cwd=build_dir,
                                   capture_output=True, timeout=30)
            self.output.info("shell probe %s rc=%s out=%r err=%r"
                             % (cand, probe.returncode,
                                probe.stdout[:60], probe.stderr[:80]))
            if probe.returncode == 0 and b"Not supported" not in probe.stderr:
                self.buildenv.define("SHELL", cand)
                self.buildenv.define("CONFIG_SHELL", cand)
                self._shell = cand
                self.output.info("using working shell for configure/tests: %s" % cand)
                return
        self._shell = "/bin/sh"
        self.output.warning("no getcwd-capable shell found; keeping profile SHELL")

    def build(self):
        apply_conandata_patches(self)
        # E011/E114: `umask 077 && mktemp -d` inside config.status yields a
        # drwx--S--- dir on HMDFS that config.status cannot write into.
        configure = os.path.join(self.source_folder, "configure")
        with open(configure, "r", encoding="utf-8") as f:
            content = f.read()
        if "umask 077" in content:
            content = content.replace("umask 077", "umask 022")
            with open(configure, "w", encoding="utf-8") as f:
                f.write(content)

        src = self.source_folder
        # Run configure through the probed shell explicitly: the shebang
        # /bin/sh (mksh) writes its own temp files to the read-only /tmp on
        # CI workers, while bash honours TMPDIR.
        try:
            self.run(" ".join([self._shell, "./configure"] + self._configure_args()),
                     env="conanbuild", cwd=src)
        except ConanException:
            # Surface the real compiler/linker error: the CI log only keeps
            # the tail of the create output, so print the config.log tail
            # (it holds the failing $CC invocation verbatim) before raising.
            cfg = os.path.join(src, "config.log")
            if os.path.isfile(cfg):
                with open(cfg, "r", encoding="utf-8", errors="replace") as f:
                    tail = [ln for ln in f.read().splitlines() if ln.strip()]
                for ln in tail[-30:]:
                    self.output.info("config.log| " + ln)
            raise
        self.run("make -j1", env="conanbuild", cwd=src)
        # DESTDIR staging so package() never depends on the workspace being
        # alive (conan cache reuse can resurrect the package alone).
        staging = os.path.join(self.build_folder, "install-staging")
        shutil.rmtree(staging, ignore_errors=True)
        os.makedirs(staging, exist_ok=True)
        self.run('make install DESTDIR="%s" prefix=/usr/local' % staging,
                 env="conanbuild", cwd=src)

        # Sign everything executable before the harness starts the suites
        # when the suites must run from the relocated workspace.
        check_src = self._prepare_runnable_tree(src)
        check_log = os.path.join(check_src, "check.log")
        try:
            self.run('make check > "%s" 2>&1' % check_log,
                     env="conanbuild", cwd=src)
        except ConanException:
            # Harness exit code is parsed from the summary below; persist
            # the full log as evidence before raising.
            pass
        with open(check_log, "r", encoding="utf-8", errors="replace") as f:
            log = f.read()
        if not log.strip():
            raise ConanException("make check produced an empty check.log")
        result = self._parse_check_results(log, src)
        if result["failed"] > 0:
            raise ConanInvalidConfiguration(
                "blogc upstream tests failed: %d FAIL / %d PASS of %d total"
                % (result["failed"], result["passed"], result["total"]))
        if result["total"] != REQUIRED_UPSTREAM_TOTAL:
            raise ConanInvalidConfiguration(
                "upstream testsuite registered %d of %d expected entries — "
                "tests were partially disabled (cmocka/bash/diff/tee missing?)"
                % (result["total"], REQUIRED_UPSTREAM_TOTAL))

        result_file = os.path.join(self.build_folder, "upstream_test_result.json")
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False)
        print("HMBS_UPSTREAM_TEST_RESULT=%s" % json.dumps(result, ensure_ascii=False), flush=True)

    def _prepare_runnable_tree(self, src):
        """Return the tree where `make check` can actually execute ELFs.

        HMFS ELF execution works in-place on the current device, but other
        adaptation paths have hit "Operation not permitted" on the conan
        cache tree (boxes/2.3.1); probe first and only on failure relocate
        the built tree to a user-writable workspace and self-sign ELFs.
        os.access(X_OK) is useless here: HMDFS ignores chmod, permission
        bits are untrustworthy (E524), so the probe really runs the binary.
        """
        if str(self.settings.os) != "OHOS":
            return src
        try:
            self.run("./blogc -v", env="conanbuild", cwd=src)
            return src
        except ConanException:
            root = os.environ.get(
                "OHOS_UPSTREAM_WORKDIR",
                os.path.expanduser("~/tmp/blogc-ws"))
            ws = os.path.join(root, self.version)
            shutil.rmtree(ws, ignore_errors=True)
            os.makedirs(os.path.dirname(ws), exist_ok=True)
            dst = os.path.join(ws, "src")
            shutil.copytree(src, dst)
            self._sign_tree_elfs(dst)
            return dst

    def _parse_check_results(self, log, src):
        """Parse the testsuite summary plus per-program cmocka counts.

        blogc uses the serial test harness ("All N tests passed" /
        "M of N tests failed"); parallel harness summaries
        ("# TOTAL: ...") are supported too, in case of future changes.
        """
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
        # cross-check against the per-test result lines the harness prints
        pass_lines = len(re.findall(r"^PASS: ", log, re.M))
        fail_lines = len(re.findall(r"^FAIL: ", log, re.M))
        if (passed, failed) != (pass_lines, fail_lines):
            raise ConanException(
                "testsuite summary (%d PASS / %d FAIL) disagrees with the "
                "result lines (%d PASS / %d FAIL)"
                % (passed, failed, pass_lines, fail_lines))
        unit_tests = 0
        for count in re.findall(r"\[==========\] Running (\d+) test\(s\)\.", log):
            unit_tests += int(count)
        return {
            "tool": "blogc",
            "version": self.version,
            "suite": "make check (cmocka unit tests + end-to-end shell suites)",
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "cmocka_assertions_executed": unit_tests,
            "workspace": src,
        }

    @staticmethod
    def _signer_env():
        """Clean env for out-of-build tools: the conan buildenv points
        LD_LIBRARY_PATH at the NDK llvm/lib, whose libc++ lacks the
        libc++_h symbols binary-sign-tool needs (it runs fine with the
        default device environment)."""
        return {k: v for k, v in os.environ.items()
                if not k.startswith("LD_LIBRARY")}

    def _has_ohos_signature(self, path):
        try:
            out = subprocess.run(
                ["/data/service/hnp/bin/llvm-readelf", "-S", path],
                capture_output=True, timeout=30, env=self._signer_env())
            return b".codesign" in out.stdout
        except Exception:
            return False

    def _sign_elf_if_ohos(self, path, force=False):
        if str(self.settings.os) != "OHOS":
            return
        if not os.path.isfile(path):
            return
        if self._has_ohos_signature(path) and not force:
            return
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        tmp_in = path + ".unsigned"
        tmp_out = path + ".signed"
        shutil.copy2(path, tmp_in)
        subprocess.run([objcopy, "--remove-section", ".codesign", tmp_in],
                       capture_output=True, timeout=30, env=self._signer_env())
        subprocess.check_call([
            signer, "sign", "-selfSign", "1",
            "-inFile", tmp_in, "-outFile", tmp_out,
        ], env=self._signer_env())
        shutil.move(tmp_out, path)
        os.chmod(path, 0o755)
        os.unlink(tmp_in)

    def _sign_tree_elfs(self, root):
        """Self-sign every built ELF under the executable workspace.

        libtool drops the real binaries in */.libs/ behind wrapper scripts,
        and the tool binaries sit at the tree root; both need signatures.
        """
        for base, dirs, files in os.walk(root):
            if base.endswith(os.sep + ".git"):
                dirs[:] = []
                continue
            for name in files:
                path = os.path.join(base, name)
                if name.endswith((".a", ".la", ".o", ".log", ".trs", ".txt", ".sh")):
                    continue
                try:
                    with open(path, "rb") as f:
                        if f.read(4) != b"\x7fELF":
                            continue
                except OSError:
                    continue
                self._sign_elf_if_ohos(path)

    def package(self):
        staging = os.path.join(self.build_folder, "install-staging", "usr", "local")
        copy(self, "*", os.path.join(staging, "bin"),
             os.path.join(self.package_folder, "bin"))
        copy(self, "*", os.path.join(staging, "share"),
             os.path.join(self.package_folder, "share"))
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        # Ship the real-device upstream test result so test_package can
        # re-emit HMBS_UPSTREAM_TEST_RESULT even when build() is cached out.
        copy(self, "upstream_test_result.json", self.build_folder,
             os.path.join(self.package_folder, "res"))
        # Copies off the workspace carry a stale .codesign that breaks exec;
        # re-sign the packaged tools.
        if str(self.settings.os) == "OHOS":
            bindir = os.path.join(self.package_folder, "bin")
            for name in sorted(os.listdir(bindir)):
                self._sign_elf_if_ohos(os.path.join(bindir, name), force=True)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["res"]
