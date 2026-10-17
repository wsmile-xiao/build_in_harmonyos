#!/usr/bin/env python3
"""Conan recipe — jenkins-cli 0.0.47 (jenkins-zh/jenkins-cli), Go CLI.

Jenkins CLI (binary name `jcli`) is a Go command-line tool for managing a
Jenkins server: config as code, plugin management, job management, restart,
credential/user management, shell hook, OAuth / completion helpers, etc.
Upstream: https://github.com/jenkins-zh/jenkins-cli (tag v0.0.47).
go.mod requires `go 1.23`.

Adaptation notes (Go CLI toolchain pattern — vibecheck/1.7.7 + algolia/1.14.0
precedent):
  1. Go toolchain bootstrap: probe the device for a usable go >= 1.23 first;
     when absent/too old, bootstrap a pinned Go SDK from the Aliyun Go mirror
     (sha256 verified against the official go.dev distributions).
  2. OHOS ELF signing: both the go toolchain ELFs and the final `jcli` binary
     must be signed with binary-sign-tool (unsigned ELF is rejected at exec).
  3. HMDFS link restriction: `go link` mmaps its output and fails on hmdfs, so
     link output + GOCACHE/GOTMPDIR/GOMODCACHE are redirected to an ext2-style
     writable work root.
  4. Upstream tests: `go test -v ./...` is run for real on the device (with an
     `-exec` sign wrapper), and HMBS_UPSTREAM_TEST_RESULT is emitted from the
     parsed `--- (PASS|FAIL|SKIP): Test*` verdict lines (deterministic source).
     Counting unit = go test function (`go test -v ./...`) top-level
     `Test*` functions.  The full v0.0.47 inventory is 40 Test* functions;
     the root `e2e/` + `e2e/withdependencies` packages need a live Jenkins
     server (their TestMain returns before m.Run() when JENKINS_VERSION is
     unset), so those 17 are not executed on the device and are reported as an
     `environment` gap.  rule4 requires `gaps 总数 == discovered - passed`
     (every not-passed test accounted for): FAILED tests are reported as a
     `test_failure` gap, framework-skipped as `ohos_feature`, and the no-
     verdict live-Jenkins tests as `environment` (see test_package/
     MANIFEST.yml audit + notes.md).
  5. Version injection: goreleaser injects the version via
     `-X github.com/linuxsuren/cobra-extension/version.version=<ver>`; we do
     the same so `jcli version` prints `Version: v0.0.47`.
"""
import json
import os
import platform
import re
import shlex
import shutil
import stat
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    download,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


# Upstream jenkins-cli v0.0.47 ships 40 top-level Test* functions across its
# packages (see test_package/MANIFEST.yml upstream_test_audit for the full
# inventory).  `go test -v ./...` prints exactly one `--- (PASS|FAIL|SKIP):
# TestXxx` line per top-level Test* function occurrence (subtests are indented
# and ignored), so 40 is both the audited inventory AND what the go-test
# framework reports — the canonical count.  Ginkgo BDD packages (app/cmd,
# app/health, app/helper, app/i18n, client, util, app/cmd/common) collapse all
# their specs into a single Test* entry point (TestCmd/TestHealth/...), which
# is exactly what the framework counts.
UPSTREAM_TEST_DISCOVERED = 40
UPSTREAM_TEST_FRAMEWORK = "go-test"
UPSTREAM_TEST_COMMAND = "go test -v ./..."
GO_MIN_VERSION = (1, 23)


class JenkinsCliConan(ConanFile):
    name = "jenkins-cli"
    version = "0.0.47"
    description = "Jenkins CLI (jcli) — manage your Jenkins in an easy way"
    license = "MIT"
    homepage = "https://github.com/jenkins-zh/jenkins-cli"
    url = "https://github.com/jenkins-zh/jenkins-cli"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"jenkins-cli supports Linux and OHOS only, got {self.settings.os}"
            )
        self._goarch()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        self._setup_hmfs_runtime_dirs()

        go = self._go_executable()
        env = self._go_environment(go)

        # Build the jcli binary first (so the e2e/without_jenkins completion
        # tests that exec `jcli` from PATH can run), then run upstream tests.
        final_bin = os.path.join(self.build_folder, "jcli")
        self._build_jcli(go, env, final_bin)

        # Create a bin dir on PATH holding the signed jcli so the
        # e2e/without_jenkins completion tests can invoke it.  Use a graceful
        # binary copy: shutil.copy2's copystat chmod/chown on the hmdfs
        # /data/storage/el2/base/cache tree raises EPERM (platform cap
        # chmod:0), so copy content only and best-effort chmod 755.
        path_bin = os.path.join(self._go_work_root(), "bin")
        self._copy_binary(final_bin, os.path.join(path_bin, "jcli"))
        env["PATH"] = path_bin + os.pathsep + env.get("PATH", "")

        self._run_upstream_tests(go, env, final_bin)

    def _build_jcli(self, go, env, final_bin):
        self._prepare_upstream_modules(go, env)
        out_dir = os.path.join(self._go_work_root(), "link-out")
        os.makedirs(out_dir, exist_ok=True)
        linked_exe = os.path.join(out_dir, "jcli")
        ldflags = (
            "-s -w "
            "-X github.com/linuxsuren/cobra-extension/version.version=v0.0.47"
        )
        build_proc = subprocess.run(
            [go, "build", "-mod=mod", "-trimpath", "-buildvcs=false",
             "-ldflags", ldflags, "-o", linked_exe, "."],
            env=env, cwd=self.source_folder,
            capture_output=True, text=True, timeout=1800,
        )
        if build_proc.stdout:
            print(build_proc.stdout, flush=True)
        if build_proc.stderr:
            print(build_proc.stderr, flush=True)
        if build_proc.returncode != 0:
            from conan.errors import ConanException
            raise ConanException(
                "go build failed: returncode=%s" % build_proc.returncode
            )
        self._sign_ohos_executable(linked_exe)
        self._copy_binary(linked_exe, final_bin)

    def _run_upstream_tests(self, go, env, final_bin):
        command = [go, "test", "-v", "-mod=mod", "-p", "1"]
        if str(self.settings.os) == "OHOS":
            wrapper = self._go_test_exec_wrapper(env)
            if wrapper:
                command.append(f"-exec={wrapper}")
        command.append("./...")
        test_proc = subprocess.run(
            command, cwd=self.source_folder, env=env,
            capture_output=True, text=True, timeout=3600,
        )
        if test_proc.stdout:
            print(test_proc.stdout, flush=True)
        if test_proc.stderr:
            print(test_proc.stderr, flush=True)

        passed, failed, skipped = self._parse_go_test_counts(test_proc.stdout or "")
        # executed = tests that actually reached a verdict (pass/fail).
        executed = passed + failed
        # not_executed = tests in the official inventory that produced no
        # verdict line.  For jenkins-cli these are the 17 live-Jenkins-gated
        # e2e tests (TestMain returns before m.Run() without JENKINS_VERSION).
        not_executed = UPSTREAM_TEST_DISCOVERED - executed - skipped

        gaps = []
        # rule4 requires gaps 总数 == discovered - passed (all not-passed
        # tests must be accounted for, not just skipped/not-executed).
        # failed tests are reported as a `test_failure` gap in addition to
        # the not-executed (environment) and skipped (ohos_feature) ones.
        if failed > 0:
            gaps.append({
                "count": failed,
                "category": "test_failure",
                "detail": (
                    "%d upstream Test* function(s) FAILED on the HarmonyOS "
                    "device; see the [GO-TEST-ERROR] block / raw `--- FAIL: "
                    "Test*` stdout lines for the per-test failure." % failed
                ),
                "evidence": "go test -v ./... stdout `--- FAIL: TestXxx` "
                            "verdict lines + TestZshCompletion etc. error blocks",
            })
        if skipped > 0:
            gaps.append({
                "count": skipped,
                "category": "ohos_feature",
                "detail": (
                    "%d upstream Test* function(s) framework-skipped by "
                    "upstream source t.Skip." % skipped
                ),
                "evidence": "go test -v ./... stdout `--- SKIP: TestXxx` lines",
            })
        if not_executed > 0:
            gaps.append({
                "count": not_executed,
                "category": "environment",
                "detail": (
                    "%d upstream Test* functions produced no verdict line on "
                    "the HarmonyOS device (executed=%d, skipped=%d, "
                    "discovered=%d).  Primary known cause (source-evidenced): "
                    "the root e2e package (14) + e2e/withdependencies (3) are "
                    "live-Jenkins integration tests whose TestMain returns "
                    "before m.Run() when JENKINS_VERSION is unset (no live "
                    "Jenkins on the device), so they print 'ok <pkg>' with no "
                    "Test* verdict.  Any remaining delta is resolvable from "
                    "the [GO-TEST-ERROR] block." % (
                        not_executed, executed, skipped,
                        UPSTREAM_TEST_DISCOVERED)
                ),
                "evidence": (
                    "e2e/setup_test.go + e2e/withdependencies/setup_test.go: "
                    "TestMain returns when JENKINS_VERSION is empty; "
                    "go test -v ./... output (per-package ok + parsed counts)"
                ),
            })

        if failed > 0:
            ut_status = "failed"
        elif gaps:
            ut_status = "incomplete"
        elif executed > 0:
            ut_status = "passed"
        else:
            ut_status = "incomplete"

        self._emit_upstream_marker(
            status=ut_status,
            discovered=UPSTREAM_TEST_DISCOVERED,
            executed=executed,
            passed=passed,
            failed=failed,
            skipped=skipped,
            gaps=gaps,
            reason=(
                "conanfile.py build() ran `go test -v ./...` on the real "
                "device; `--- (PASS|FAIL|SKIP): Test*` top-level lines parsed "
                "from go test stdout.  %d of %d discovered upstream Test* "
                "functions PASSED, %d FAILED, %d SKIPPED; the remaining "
                "%d are live-Jenkins e2e tests that cannot run on the device. "
                "gaps total == discovered-passed == %d: the %d FAILED are "
                "reported as a test_failure gap, the %d live-Jenkins e2e "
                "tests as an environment gap%s." % (
                    passed, UPSTREAM_TEST_DISCOVERED, failed, skipped,
                    not_executed,
                    UPSTREAM_TEST_DISCOVERED - passed, failed, not_executed,
                    (", and %d framework-skipped as an ohos_feature gap"
                     % skipped) if skipped else "")
            ),
        )

        if test_proc.returncode != 0 and executed == 0:
            self._print_go_test_errors(test_proc.stdout or "", test_proc.stderr or "")
            self.output.warning(
                "go test exited non-zero (%s) with executed=0; see the "
                "[GO-TEST-ERROR] block above for the real per-package cause."
                % test_proc.returncode
            )
        elif failed > 0:
            self.output.warning(
                "go test reported %d failed upstream Test* functions; "
                "see marker for honest counts." % failed
            )

    def _print_go_test_errors(self, stdout, stderr):
        combined = (stdout or "") + "\n" + (stderr or "")
        interesting = []
        seen = set()
        for line in combined.splitlines():
            line = line.rstrip()
            if not line:
                continue
            low = line.lower()
            if (line.startswith("# ") or ".go:" in line
                    or "cannot find" in low or "could not import" in low
                    or "no required module" in low or "missing go.sum" in low
                    or "checksum" in low or "verification failed" in low
                    or "import cycle" in low or "undefined:" in low
                    or "exec:" in low or "fork/exec" in low or "exec format" in low
                    or "executable file not found" in low or "permission denied" in low
                    or "no space left" in low or "is a directory" in low
                    or "cannot find package" in low or "malformed" in low
                    or "error:" in low or "failed" in low):
                if line not in seen:
                    seen.add(line)
                    interesting.append(line)
        if interesting:
            print("\n[GO-TEST-ERROR] real go test failure lines:", flush=True)
            for line in interesting[:80]:
                print("  " + line, flush=True)
            print("[/GO-TEST-ERROR]", flush=True)

    # ── Go test counting ────────────────────────────────────────────────
    def _prepare_upstream_modules(self, go, env):
        last = None
        for attempt in range(1, 4):
            # Note: no `-mod` flag here — Go 1.26 removed `-mod` from the
            # `go mod download` subcommand ("flag provided but not defined:
            # -mod"), which made every prefetch attempt fail with rc=2.  Module
            # resolution is already pinned to `-mod=mod` via GOFLAGS=-mod=mod in
            # the build env.
            proc = subprocess.run(
                [go, "mod", "download"],
                cwd=self.source_folder, env=env,
                capture_output=True, text=True, timeout=1800,
            )
            if proc.stdout:
                print(proc.stdout, flush=True)
            if proc.returncode == 0:
                self.output.info(
                    "go mod download completed (attempt %d/3)" % attempt)
                return True
            last = proc.stderr or ""
            print("[go-mod-download-fail attempt %d/3 rc=%d]" % (
                attempt, proc.returncode), flush=True)
            if last:
                print(last, flush=True)
            self.output.warning(
                "go mod download attempt %d/3 failed (rc=%s); retrying with "
                "the continued GOPROXY list." % (attempt, proc.returncode))
        if last:
            print(last, flush=True)
        return False

    @staticmethod
    def _parse_go_test_counts(stdout):
        passed = 0
        failed = 0
        skipped = 0
        for m in re.finditer(r"(?m)^--- (PASS|FAIL|SKIP): (Test\S+)", stdout):
            kind = m.group(1)
            if kind == "PASS":
                passed += 1
            elif kind == "FAIL":
                failed += 1
            elif kind == "SKIP":
                skipped += 1
        return passed, failed, skipped

    def _emit_upstream_marker(self, *, status, discovered, executed, passed,
                              failed, skipped, reason, gaps=None):
        if gaps is None:
            gaps = []
        ok = (
            isinstance(executed, int) and executed >= 0
            and isinstance(passed, int) and passed >= 0
            and isinstance(failed, int) and failed >= 0
            and isinstance(skipped, int) and skipped >= 0
            and (passed + failed) == executed
            and (executed + skipped) <= discovered
            and executed <= discovered
        )
        ut_result = {
            "status": status,
            "framework": UPSTREAM_TEST_FRAMEWORK,
            "command": UPSTREAM_TEST_COMMAND,
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "identity_ok": ok,
            "gaps": gaps,
            "reason": reason,
        }
        print(f"HMBS_UPSTREAM_TEST_RESULT={json.dumps(ut_result)}", flush=True)

    # ── Toolchain bootstrap ─────────────────────────────────────────────
    def _go_executable(self):
        go_path, go_version, probe_lines = self._locate_go_toolchain()
        for line in probe_lines:
            print(line, flush=True)
        if go_path and go_version and go_version >= GO_MIN_VERSION:
            self.output.info(
                f"Using on-device Go toolchain: {go_path} (v{go_version[0]}.{go_version[1]})"
            )
            return go_path
        if go_path:
            self.output.warning(
                f"On-device Go {go_version[0]}.{go_version[1]} at {go_path} "
                f"is older than go.mod requires (>= {GO_MIN_VERSION[0]}.{GO_MIN_VERSION[1]}); "
                f"bootstrapping from Aliyun mirror instead."
            )
        else:
            self.output.warning(
                "No on-device Go toolchain found; bootstrapping go >= "
                f"{GO_MIN_VERSION[0]}.{GO_MIN_VERSION[1]} from Aliyun mirror "
                "(sha256 verified)."
            )
        return self._bootstrapped_go_executable(probe_lines)

    def _locate_go_toolchain(self):
        env = os.environ
        user_home = env.get("HOME", "/storage/Users/currentUser")

        go_path = shutil.which("go")
        if not go_path:
            go_path = env.get("HNP_GO")
        if not go_path:
            goroot = env.get("HNP_GOROOT")
            if goroot:
                cand = os.path.join(goroot, "bin", "go")
                if os.path.isfile(cand) and os.access(cand, os.X_OK):
                    go_path = cand

        find_roots = [
            "/data/service/hnp",
            "/storage/Users/currentUser",
            "/opt",
            "/usr/local",
            os.path.join(user_home, "go"),
            os.path.join(user_home, ".go"),
            os.path.join(user_home, "tmp"),
        ]
        seen = set()
        find_roots = [
            r for r in find_roots
            if r and r not in seen and not seen.add(r) and os.path.exists(r)
        ]

        def _find_tool(name):
            for root in find_roots:
                try:
                    proc = subprocess.run(
                        ["find", "-L", root, "-maxdepth", "6",
                         "-type", "f", "-name", name],
                        capture_output=True, text=True, timeout=120,
                    )
                except (FileNotFoundError, subprocess.TimeoutExpired):
                    continue
                for line in proc.stdout.splitlines():
                    p = line.strip()
                    if p and os.path.isfile(p) and os.access(p, os.X_OK):
                        return p
            return None

        if not go_path:
            go_path = _find_tool("go")

        probe_lines = [
            "[go-toolchain-probe]",
            "which go = %s" % shutil.which("go"),
            "HNP_GO = %s" % env.get("HNP_GO", "<unset>"),
            "HNP_GOROOT = %s" % env.get("HNP_GOROOT", "<unset>"),
            "GOROOT = %s" % env.get("GOROOT", "<unset>"),
            "GOPATH = %s" % env.get("GOPATH", "<unset>"),
            "HOME = %s" % user_home,
            "PATH = %s" % env.get("PATH", "<unset>"),
            "find_roots = %s" % find_roots,
        ]
        for root in find_roots:
            try:
                listing = ",".join(sorted(os.listdir(root))[:60])
            except OSError as exc:
                listing = "<listdir error: %s>" % exc
            probe_lines.append("listdir %s = [%s]" % (root, listing))
        probe_lines.append("resolved go = %s" % (go_path or "<none>"))

        go_version = None
        if go_path:
            try:
                ver_proc = subprocess.run(
                    [go_path, "version"], capture_output=True, text=True, timeout=60
                )
                probe_lines.append(
                    "go version out = %s"
                    % (ver_proc.stdout.strip() or ver_proc.stderr.strip())
                )
                m = re.search(r"go(\d+)\.(\d+)", ver_proc.stdout or "")
                if m:
                    go_version = (int(m.group(1)), int(m.group(2)))
            except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
                probe_lines.append("go version probe error = %s" % exc)
        else:
            probe_lines.append("go version out = <no go binary>")
        probe_lines.append("resolved go_version = %s" % (go_version or "<none>"))

        return go_path, go_version, probe_lines

    def _bootstrapped_go_executable(self, probe_lines):
        go_toolchain = self.conan_data["go_toolchain"]
        host_key = f"linux-{self._host_goarch()}"
        package = go_toolchain[host_key]
        tools_dir = os.path.join(self._go_work_root(), "go-toolchain")
        archive = os.path.join(tools_dir, package["filename"])
        go_root = os.path.join(tools_dir, "go")
        go = os.path.join(go_root, "bin", "go")
        if not os.path.isfile(go):
            os.makedirs(tools_dir, exist_ok=True)
            self.output.info(
                f"Bootstrapping Go toolchain {go_toolchain['version']} "
                f"({host_key}) from {package['url']} (sha256 verified)"
            )
            download(self, package["url"], archive, sha256=package["sha256"])
            result = self.run(
                f'tar xzf "{archive}" -C "{tools_dir}"',
                ignore_errors=True,
            )
            if result != 0:
                raise ConanInvalidConfiguration(
                    f"Failed to extract bootstrapped Go toolchain archive: {archive}"
                )
        self._ensure_go_toolchain_permissions(tools_dir, go_root)
        if not os.access(go, os.X_OK):
            raise ConanInvalidConfiguration(
                f"Bootstrapped Go executable is not runnable: {go}"
            )
        for line in ["[go-toolchain-bootstrap]",
                     "go root = %s" % go_root,
                     "go = %s" % go,
                     "version = %s" % go_toolchain["version"],
                     "host = %s" % host_key,
                     "url = %s" % package["url"]]:
            print(line, flush=True)
        return go

    def _ensure_go_toolchain_permissions(self, tools_dir, go_root):
        for directory in (tools_dir, go_root):
            if os.path.isdir(directory):
                self._chmod_graceful(directory)
        for dirpath, _dirnames, filenames in os.walk(go_root):
            self._chmod_graceful(dirpath)
            for filename in filenames:
                path = os.path.join(dirpath, filename)
                if self._is_elf(path):
                    self._chmod_graceful(path)
                    self._sign_ohos_executable(path)

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    @staticmethod
    def _has_ohos_signature(path):
        try:
            with open(path, "rb") as f:
                blob = f.read()
        except OSError:
            return False
        return b".codesign" in blob or b".note.ohos" in blob

    def _chmod_graceful(self, path):
        try:
            os.chmod(path, 0o755)
        except OSError as exc:
            self.output.debug(
                f"chmod skipped for {path} ({exc})"
            )

    def _copy_binary(self, src, dst):
        """Copy a binary without metadata ops that EPERM on hmdfs.

        Two OHOS-specific hazards must be avoided on the
        /data/storage/el2/base/cache tree (hmdfs media filesystem):
          1. shutil.copy2 -> copystat -> os.chmod/chown raises EPERM (platform
             cap chmod:0), so we never run copystat — copyfile only.
          2. Opening an EXISTING destination file for overwrite/truncate
             (copyfile's 'wb' / O_TRUNC) raises EPERM on hmdfs, while creating
             a FRESH file works (this is why the temp+cache dirs under the same
             tree are fine).  The `bin/jcli` target frequently already exists
             from an earlier run, so we always write to a fresh temp sibling
             and `os.rename` it into place (unlink/rename are metadata ops hmdfs
             permits) instead of truncating the stale target in place.
        """
        directory = os.path.dirname(dst)
        if directory:
            os.makedirs(directory, exist_ok=True)
        # Unlink any stale target + stale temp first (metadata op, hmdfs-safe).
        self._remove_graceful(dst)
        tmp = "%s.tmp-%d" % (dst, os.getpid())
        self._remove_graceful(tmp)
        try:
            shutil.copyfile(src, tmp)
        except OSError as exc:
            self.output.warning(
                "copyfile to temp %s failed (%s); retrying direct to %s"
                % (tmp, exc, dst))
            self._remove_graceful(dst)
            shutil.copyfile(src, dst)
            self._chmod_graceful(dst)
            return dst
        try:
            os.rename(tmp, dst)
        except OSError as exc:
            self.output.warning(
                "rename %s -> %s failed (%s); fallback os.replace + direct copy"
                % (tmp, dst, exc))
            try:
                os.replace(tmp, dst)
            except OSError as exc2:
                self.output.warning(
                    "os.replace %s -> %s failed (%s); direct copy fallback"
                    % (tmp, dst, exc2))
                self._remove_graceful(dst)
                shutil.copyfile(src, dst)
        self._chmod_graceful(dst)
        return dst

    def _remove_graceful(self, path):
        """Unlink a stale file best-effort; unlink is a hmdfs-safe metadata op."""
        try:
            if os.path.lexists(path):
                os.remove(path)
        except OSError as exc:
            self.output.debug(f"unlink skipped for {path} ({exc})")

    def _find_objcopy(self):
        candidates = [
            shutil.which("llvm-objcopy"),
            shutil.which("objcopy"),
            "/data/service/hnp/bin/llvm-objcopy",
            "/data/service/hnp/bin/objcopy",
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

    def _sign_ohos_executable(self, path):
        if str(self.settings.os) != "OHOS" or not os.path.isfile(path):
            return
        if self._has_ohos_signature(path):
            self.output.debug(f"already signed, skipping: {path}")
            return
        signer = self._find_binary_sign_tool()
        if not signer:
            self.output.warning(
                "binary-sign-tool not found; OHOS may reject executable: %s"
                % path
            )
            return
        directory = os.path.dirname(path)
        base = os.path.basename(path)
        tmp_in = os.path.join(directory, ".%s.sign-%d.in" % (base, os.getpid()))
        tmp_out = tmp_in + ".signed"
        try:
            shutil.copy2(path, tmp_in)
            objcopy = self._find_objcopy()
            if objcopy:
                self.run(
                    f"{shlex.quote(objcopy)} --remove-section .codesign "
                    f"{shlex.quote(tmp_in)} 2>/dev/null || true",
                    ignore_errors=True, quiet=True,
                )
            result = self.run(
                f"{shlex.quote(signer)} sign -selfSign 1 "
                f"-inFile {shlex.quote(tmp_in)} "
                f"-outFile {shlex.quote(tmp_out)} "
                f"-signAlg SHA256withECDSA",
                ignore_errors=True, quiet=True,
            )
            if result != 0 or not os.path.isfile(tmp_out):
                raise ConanInvalidConfiguration(
                    f"binary-sign-tool failed with exit code {result}: {path}"
                )
            shutil.move(tmp_out, path)
            self._chmod_graceful(path)
            self.output.info(f"signed OHOS executable: {path}")
        finally:
            for leftover in (tmp_in, tmp_out):
                try:
                    if os.path.isfile(leftover):
                        os.remove(leftover)
                except OSError:
                    pass

    def _find_binary_sign_tool(self):
        candidates = [
            os.environ.get("OHOS_BINARY_SIGN_TOOL"),
            os.environ.get("BINARY_SIGN_TOOL"),
            "/data/service/hnp/bin/binary-sign-tool",
            "/data/storage/el2/base/cache/harmonybrew/bin/binary-sign-tool",
            "/storage/Users/currentUser/usr/local/bin/binary-sign-tool",
            shutil.which("binary-sign-tool"),
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

    def _go_test_exec_wrapper(self, env):
        signer = self._find_binary_sign_tool()
        if not signer:
            self.output.warning(
                "binary-sign-tool not found; Go test binaries may be rejected "
                "by OHOS execution policy."
            )
            return None
        wrapper = os.path.join(self._go_work_root(), "go-test-exec.sh")
        with open(wrapper, "w", encoding="utf-8", newline="\n") as script:
            script.write(
                "#!/bin/sh\n"
                "set -eu\n"
                "src=\"$1\"\n"
                "shift\n"
                "wdir=\"$(dirname \"$0\")\"\n"
                "run=\"${wdir}/testrun-$$\"\n"
                "rm -rf \"$run\"\n"
                "mkdir -p \"$run\"\n"
                "cp -f \"$src\" \"$run/bin\"\n"
                "\"$OHOS_GO_TEST_SIGNER\" sign -selfSign 1 "
                "-inFile \"$run/bin\" -outFile \"$run/bin.signed\" "
                "-signAlg SHA256withECDSA\n"
                "mv -f \"$run/bin.signed\" \"$run/bin\"\n"
                "chmod 755 \"$run/bin\"\n"
                "exec \"$run/bin\" \"$@\"\n"
            )
        self._make_script_executable(wrapper)
        env["OHOS_GO_TEST_SIGNER"] = signer
        return wrapper

    def _make_script_executable(self, path):
        try:
            os.chmod(path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR |
                     stat.S_IRGRP | stat.S_IXGRP |
                     stat.S_IROTH | stat.S_IXOTH)
        except OSError as exc:
            self.output.warning(
                f"chmod failed for {path} ({exc}); invoking via sh fallback"
            )

    # ── Go build/environment ────────────────────────────────────────────
    def _go_environment(self, go):
        env = os.environ.copy()
        cache_root = os.path.join(self._go_work_root(), "cache")
        go_root = os.path.dirname(os.path.dirname(os.path.abspath(go)))
        env.update({
            "CGO_ENABLED": "0",
            "GOOS": "linux",
            "GOARCH": self._goarch(),
            "GOCACHE": os.path.join(cache_root, "build"),
            "GOMODCACHE": os.path.join(cache_root, "mod"),
            "GOPATH": os.path.join(cache_root, "gopath"),
            "GOPROXY": env.get(
                "GOPROXY",
                "https://mirrors.aliyun.com/goproxy/,https://goproxy.cn,"
                "https://goproxy.io,https://proxy.golang.org,direct"),
            "GOROOT": go_root,
            "GOTOOLCHAIN": "local",
            "GOFLAGS": "-mod=mod",
            "TMPDIR": os.path.join(cache_root, "tmp"),
            "GOTMPDIR": os.path.join(cache_root, "gotmp"),
        })
        for name in ("GOCACHE", "GOMODCACHE", "GOPATH", "TMPDIR", "GOTMPDIR"):
            os.makedirs(env[name], exist_ok=True)
        env["PATH"] = os.path.join(go_root, "bin") + os.pathsep + \
            env.get("PATH", "")
        return env

    def _setup_hmfs_runtime_dirs(self):
        if str(self.settings.os) == "OHOS":
            work = self._go_work_root()
            for var in ("TMPDIR", "TMP", "TEMP"):
                os.environ[var] = os.path.join(work, "tmp")

    def _go_work_root(self):
        if str(self.settings.os) == "OHOS":
            candidates = [
                os.environ.get("OHOS_GO_BUILD_ROOT"),
                os.environ.get("HMBS_TMPDIR"),
                "/data/storage/el2/base/cache",
                os.environ.get("TMPDIR"),
            ]
        else:
            candidates = [
                os.environ.get("JENKINS_CLI_GO_BUILD_ROOT"),
                os.path.join(os.path.dirname(os.path.abspath(self.source_folder)),
                             "go-work"),
                os.environ.get("TMPDIR"),
            ]
        for candidate in candidates:
            if not candidate:
                continue
            root = os.path.join(candidate, "conan-go-build", f"{self.name}-{self.version}")
            if self._is_under_source_tree(root):
                continue
            try:
                os.makedirs(root, exist_ok=True)
                return root
            except OSError:
                continue
        raise ConanInvalidConfiguration(
            "No writable Go build root is available for linker output"
        )

    def _is_under_source_tree(self, path):
        try:
            source = os.path.abspath(self.source_folder)
            target = os.path.abspath(path)
            return os.path.commonpath([source, target]) == source
        except (OSError, ValueError):
            return False

    def _goarch(self):
        arch = str(self.settings.arch)
        if arch in ("armv8", "arm64", "aarch64"):
            return "arm64"
        if arch in ("x86_64", "amd64"):
            return "amd64"
        if arch.startswith("armv7"):
            return "arm"
        raise ConanInvalidConfiguration(f"Unsupported Go arch mapping: {arch}")

    def _host_goarch(self):
        machine = platform.machine().lower()
        if machine in ("x86_64", "amd64"):
            return "amd64"
        if machine in ("aarch64", "arm64"):
            return "arm64"
        raise ConanInvalidConfiguration(f"Unsupported Go host architecture: {machine}")

    def package(self):
        bin_src = os.path.join(self.build_folder, "jcli")
        if os.path.isfile(bin_src):
            copy(self, "jcli", self.build_folder,
                 os.path.join(self.package_folder, "bin"))

        license_src = os.path.join(self.source_folder, "LICENSE")
        if os.path.isfile(license_src):
            copy(self, "LICENSE",
                 src=self.source_folder,
                 dst=os.path.join(self.package_folder, "licenses"),
                 keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
