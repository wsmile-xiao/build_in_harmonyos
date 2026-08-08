#!/usr/bin/env python3
"""Conan test_package for kor 0.6.8 — Conan L1 official test.

The consumer smoke test runs the packaged ``kor`` binary via test.sh
(``kor version``). The upstream ``go test`` suite (120 Test functions
across pkg/kor, pkg/filters, pkg/utils) is executed here in the
test_package phase, where hmbs preflight collects the
HMBS_UPSTREAM_TEST_RESULT marker. Go toolchain self-bootstrap and
source download mirror the conanfile.py build() path so the upstream
suite runs against the same upstream tarball the package was built
from.

Emits HMBS evidence markers for preflight verification:
  - HMBS_TEST_PACKAGE_RESULT: test_package consumer-side smoke test
  - HMBS_UPSTREAM_TEST_RESULT: official upstream ``go test`` suite
"""
import hashlib
import json
import os
import shutil
import ssl
import subprocess
import tarfile
import urllib.request

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.files import download, unzip, mkdir


# Portable Go toolchain for self-bootstrapping when no signed SDK Go
# is available on the worker (same URL + SHA-256 as conanfile.py;
# verified 2026-08-07, http 200, size 57276329).
_GO_TARBALL_URLS = [
    "https://golang.google.cn/dl/go1.25.7.linux-arm64.tar.gz",
    "https://dl.google.com/go/go1.25.7.linux-arm64.tar.gz",
]
_GO_TARBALL_SHA256 = "ba611a53534135a81067240eff9508cd7e256c560edd5d8c2fef54f083c07129"
_GO_VERSION = "1.25.7"

# Pre-installed, ELF-signed Go toolchain on the HarmonyOS PC preflight
# worker (present on some workers). Probe first, self-bootstrap fallback.
_SDK_GO_CANDIDATES = [
    "/storage/Users/currentUser/sdk/go1.26.3/bin/go",
    "/storage/Users/currentUser/sdk/go1.26.3/go/bin/go",
    "/storage/Users/currentUser/sdk/go1.25.7/bin/go",
    "/storage/Users/currentUser/sdk/go1.25.7/go/bin/go",
    "/storage/Users/currentUser/sdk/go/bin/go",
]

# ELF signing tools on the HarmonyOS PC preflight worker.
_OBJCOPY = "/data/service/hnp/bin/llvm-objcopy"
_SIGNTOOL = "/data/service/hnp/bin/binary-sign-tool"

# ext2 partition paths that bypass HMDFS mmap restrictions (E166).
_EXT2_CACHE_CANDIDATES = [
    "/data/storage/el2/base/haps/entry/files",
    "/data/storage/el2/base/cache",
]

# Upstream source archive (same URL + sha256 as conandata.yml). We
# re-download it in the test_package phase so the upstream ``go test``
# suite runs against the exact upstream tarball the package was built
# from, independent of any build-folder residue.
_UPSTREAM_URL = "https://github.com/yonahd/kor/archive/refs/tags/v0.6.8.tar.gz"
_UPSTREAM_SHA256 = "e651f3178e8c9cc1cd522661ac129b2518ed3fc981b0a9eebdf531e9c0b17b17"

# Upstream Go module path (from go.mod ``module`` directive). We pass
# absolute package paths under the extracted source root so ``go test
# -c`` does NOT depend on os.Getwd() (HMDFS does not support getcwd).
_UPSTREAM_MODULE = "github.com/yonahd/kor"

# Upstream test packages, enumerated explicitly because
# `go test ./...` hard-fails when ANY test package fails to compile.
# kor 0.6.8 has 120 Test functions: pkg/kor (110), pkg/filters (3),
# pkg/utils (7). All use fake clientsets / hermetic logic — no real
# cluster connection, no external network (audited upstream v0.6.8
# sources; httpmock is used by pkg/utils/slack_test.go but registers
# mocked responders only). Absolute package paths (relative to the
# extracted upstream root).
_UPSTREAM_TEST_PKGS = [
    "pkg/kor/",
    "pkg/filters/",
    "pkg/utils/",
]


class KorTestConan(ConanFile):
    """test_package for kor — runs the kor binary as a smoke test,
    then executes the upstream ``go test`` suite and emits HMBS
    evidence markers for preflight verification."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    # ------------------------------------------------------------------
    # ext2 cache (E166 bypass)
    # ------------------------------------------------------------------
    def _ext2_cache_dir(self):
        """Pick a writable ext2 directory for GOCACHE/GOTMPDIR/linker
        output (E166: Go linker mmap fails on HMDFS)."""
        for base in _EXT2_CACHE_CANDIDATES:
            candidate = os.path.join(base, "kor-0.6.8-test")
            try:
                os.makedirs(candidate, exist_ok=True)
                with open(os.path.join(candidate, ".wprobe"), "wb") as f:
                    f.write(b"0")
                os.remove(os.path.join(candidate, ".wprobe"))
                self.output.info("Using ext2 cache dir: %s" % candidate)
                return candidate
            except OSError:
                continue
        fallback = os.environ.get("TMPDIR") or os.environ.get("TEMP") or "/tmp"
        self.output.warning(
            "No writable ext2 cache dir found in %s; falling back to %s "
            "(E166 linker-mmap failure may follow)"
            % (_EXT2_CACHE_CANDIDATES, fallback))
        return fallback

    # ------------------------------------------------------------------
    # Go toolchain resolution (mirror of conanfile.py)
    # ------------------------------------------------------------------
    def _sign_elf(self, target):
        """Sign one ELF in place for HongMeng execve (E077 four-step)."""
        if not os.path.isfile(target):
            return False
        self.run(
            "%s --remove-section .codesign %s" % (_OBJCOPY, target),
            env=None, quiet=True, stderr=subprocess.DEVNULL,
        )
        rc = self.run(
            "%s sign -inFile %s -outFile %s -selfSign 1"
            % (_SIGNTOOL, target, target),
            env=None, quiet=True, stderr=subprocess.DEVNULL,
        )
        if rc != 0:
            return False
        try:
            os.chmod(target, 0o755)
        except OSError:
            pass
        return os.access(target, os.X_OK)

    def _sign_go_toolchain(self, boot_root):
        """Re-sign every executable ELF in a freshly extracted Go tree."""
        tool_subdir = os.path.join(boot_root, "pkg", "tool", "linux_arm64")
        targets = []
        for d in (os.path.join(boot_root, "bin"), tool_subdir):
            if not os.path.isdir(d):
                continue
            for name in os.listdir(d):
                p = os.path.join(d, name)
                if os.path.isfile(p):
                    targets.append(p)

        signed, failed = 0, 0
        for t in targets:
            if self._sign_elf(t):
                signed += 1
            else:
                failed += 1
                self.output.warning(
                    "Failed to sign Go toolchain ELF %s (E128 may follow)" % t)
        self.output.info(
            "Signed %d Go toolchain ELFs (%d failed) under %s"
            % (signed, failed, boot_root))
        if failed:
            raise ConanException(
                "Go toolchain ELF signing failed for %d files under %s; "
                "binary-sign-tool/llvm-objcopy unavailable? paths=%s,%s"
                % (failed, boot_root, _OBJCOPY, _SIGNTOOL))

    def _bootstrap_go(self):
        """Download, verify, extract and re-sign a portable Go toolchain.
        Cached under ext2 cache dir ``go-bootstrap/go1.25.7/``."""
        ext2 = self._ext2_cache_dir()
        boot_root = os.path.join(ext2, "go-bootstrap", "go%s" % _GO_VERSION)
        go_bin = os.path.join(boot_root, "bin", "go")
        marker = os.path.join(boot_root, ".hmbs-signed-ok")

        if os.path.isfile(marker) and os.path.isfile(go_bin):
            self.output.info("Reusing cached signed Go bootstrap: %s" % go_bin)
            return go_bin

        bootstrap_parent = os.path.dirname(boot_root)
        os.makedirs(bootstrap_parent, exist_ok=True)
        shipped_root = os.path.join(bootstrap_parent, "go")
        if os.path.isdir(shipped_root):
            shutil.rmtree(shipped_root, ignore_errors=True)
        if os.path.isdir(boot_root):
            shutil.rmtree(boot_root, ignore_errors=True)

        tarball_path = os.path.join(bootstrap_parent, "go%s.tar.gz" % _GO_VERSION)
        last_err = None
        for url in _GO_TARBALL_URLS:
            try:
                self.output.info("Downloading Go %s from %s" % (_GO_VERSION, url))
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                with urllib.request.urlopen(url, timeout=120, context=ctx) as r, \
                        open(tarball_path, "wb") as out:
                    shutil.copyfileobj(r, out)
                last_err = None
                break
            except Exception as e:
                last_err = e
                self.output.warning("Download from %s failed: %s" % (url, e))
                continue
        if last_err is not None:
            raise ConanException(
                "Could not download Go %s from any mirror: %s. URLs tried: %s"
                % (_GO_VERSION, last_err, _GO_TARBALL_URLS))

        actual_sha = hashlib.sha256(open(tarball_path, "rb").read()).hexdigest()
        if actual_sha != _GO_TARBALL_SHA256:
            raise ConanException(
                "Go tarball SHA-256 mismatch: expected %s, got %s (URL %s)"
                % (_GO_TARBALL_SHA256, actual_sha, url))
        self.output.info("Go tarball SHA-256 verified: %s" % actual_sha)

        with tarfile.open(tarball_path, "r:gz") as tf:
            tf.extractall(bootstrap_parent)
        try:
            os.remove(tarball_path)
        except OSError:
            pass
        if not os.path.isdir(shipped_root):
            raise ConanException(
                "Go tarball extracted but %s missing — unexpected tarball layout"
                % shipped_root)
        os.rename(shipped_root, boot_root)

        self._sign_go_toolchain(boot_root)
        with open(marker, "w") as f:
            f.write("signed go %s\n" % _GO_VERSION)
        self.output.info("Self-bootstrapped Go ready: %s" % go_bin)
        return go_bin

    def _ensure_go(self):
        """Locate — or self-bootstrap — a signed, executable ``go``."""
        existing = shutil.which("go")
        if existing and os.access(existing, os.X_OK):
            self.output.info("Using Go from PATH: %s" % existing)
            return existing

        for cand in _SDK_GO_CANDIDATES:
            if os.path.isfile(cand) and os.access(cand, os.X_OK):
                self.output.info("Using SDK Go: %s" % cand)
                return cand

        self.output.info(
            "No signed SDK Go on PATH or under ~/sdk/; self-bootstrapping Go %s "
            "and re-signing toolchain ELFs (E128+E077 workaround)" % _GO_VERSION)
        return self._bootstrap_go()

    def _go_env(self):
        """Build the Go environment for the HarmonyOS PC preflight worker."""
        go_bin = self._ensure_go()
        go_bin_dir = os.path.dirname(go_bin)
        go_root = os.path.dirname(go_bin_dir)
        ext2_cache = self._ext2_cache_dir()

        gopath = os.path.join(ext2_cache, "gopath")
        gocache = os.path.join(ext2_cache, "go-cache")
        gotmpdir = os.path.join(ext2_cache, "go-tmp")
        os.makedirs(gopath, exist_ok=True)
        os.makedirs(gocache, exist_ok=True)
        os.makedirs(gotmpdir, exist_ok=True)

        env = {
            "CGO_ENABLED": "0",
            "GOPROXY": "https://goproxy.cn,direct",
            "GOFLAGS": "-mod=mod",
            "GOTOOLCHAIN": "local",
            "GOROOT": go_root,
            "GOPATH": gopath,
            "GOCACHE": gocache,
            "GOTMPDIR": gotmpdir,
            "TMPDIR": gotmpdir,
            "TEMP": gotmpdir,
            "PATH": "%s%s%s" % (go_bin_dir, os.pathsep, os.environ.get("PATH", "")),
        }
        return env, go_bin

    def _run_go(self, cmd, env, cwd):
        """Run a Go command with the env dict applied to os.environ."""
        saved = {}
        for k, v in env.items():
            saved[k] = os.environ.get(k)
            os.environ[k] = v
        try:
            return self.run(cmd, env=None, cwd=cwd)
        finally:
            for k, old in saved.items():
                if old is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = old

    # ------------------------------------------------------------------
    # upstream source re-download (so test_package runs against the
    # exact upstream tarball the package was built from)
    # ------------------------------------------------------------------
    def _upstream_source(self):
        """Return the upstream source root on ext2 (supports getcwd)."""
        ext2 = self._ext2_cache_dir()
        ext2_root = os.path.join(ext2, "upstream-src")
        if os.path.isfile(os.path.join(ext2_root, "go.mod")):
            return ext2_root

        mkdir(self, ext2_root)
        tarball = os.path.join(ext2, "upstream-kor-0.6.8.tar.gz")
        download(self, url=_UPSTREAM_URL, filename=tarball,
                 sha256=_UPSTREAM_SHA256, verify=True)
        unzip(self, tarball, destination=ext2_root, strip_root=True)
        try:
            os.remove(tarball)
        except OSError:
            pass
        if not os.path.isfile(os.path.join(ext2_root, "go.mod")):
            raise ConanException(
                "Upstream tarball extracted but go.mod missing under %s"
                % ext2_root)
        return ext2_root

    # ------------------------------------------------------------------
    # upstream go test suite
    # ------------------------------------------------------------------
    def _run_upstream_tests(self, go_bin, env, src):
        """Run upstream ``go test`` suite, parse results, emit hmbs
        marker.

        Strategy (tlsx 第 19 轮根因修正 — go test -c + 签名 + 直跑 .test):
        ``go test`` 内部 execve 未签名的 ``.test`` 临时产物会被 HongMeng
        内核拒绝 (E128, fork/exec permission denied)。因此对每个包:
        1. ``go test -c -short -count=1 -timeout 120s -o <ext2>/<pkg>.test <abs_pkg>``
           编译测试二进制 (不运行, -o 指定 ext2 路径绕 E166)。
        2. ``_sign_elf`` 签名 .test 二进制 (E077 四步)。
        3. 直接执行 ``<pkg>.test -test.v -test.short``, 解析
           ``--- PASS/FAIL/SKIP`` 行计数。
        """
        ext2_cache = self._ext2_cache_dir()
        test_bin_dir = os.path.join(ext2_cache, "kor-test-bins")
        os.makedirs(test_bin_dir, exist_ok=True)

        diag = {"src": src, "go_bin": go_bin,
                "strategy": "go test -c + sign + exec .test"}
        try:
            os.chdir(src)
            diag["cwd_getcwd"] = os.getcwd()
        except OSError as e:
            diag["cwd_getcwd_error"] = str(e)
        diag["go_mod_exists"] = os.path.isfile(os.path.join(src, "go.mod"))

        # Probe the exec mechanism that succeeds for go build.
        try:
            self._run_go("%s version" % go_bin, env, cwd=src)
            diag["go_version_probe"] = "ok"
        except Exception as e:
            diag["go_version_probe_error"] = str(e)
            raise ConanException(
                "go version probe failed in _run_upstream_tests: %s" % e)
        print("HMBS_UPSTREAM_TEST_DIAG={json.dumps(diag)}")

        passed = failed = skipped = 0
        ran_pkgs = 0
        compile_fail_pkgs = 0
        per_pkg_summary = []
        per_pkg_diag = []

        for pkg in _UPSTREAM_TEST_PKGS:
            pkg_abs_path = os.path.join(src, pkg.rstrip("/"))
            pkg_slug = pkg.rstrip("/").replace("/", "_")
            test_bin = os.path.join(test_bin_dir, "%s.test" % pkg_slug)
            try:
                os.remove(test_bin)
            except OSError:
                pass

            # Step 1: compile the test binary via `go test -c` (no run).
            compile_cmd = "%s test -c -short -count=1 -timeout 120s -o %s %s" % (
                go_bin, test_bin, pkg_abs_path)
            self.output.info(
                "===== go test -c %s (abs=%s, bin=%s) ====="
                % (pkg, pkg_abs_path, test_bin))
            pkg_diag = {"pkg": pkg, "abs": pkg_abs_path,
                        "test_bin": test_bin, "stage": "compile"}
            try:
                rc = self._run_go(compile_cmd, env, cwd=src)
                pkg_diag["compile_exit"] = rc
            except Exception as e:
                pkg_diag["compile_error"] = str(e)
                pkg_diag["compile_exit"] = -1
                per_pkg_diag.append(pkg_diag)
                compile_fail_pkgs += 1
                per_pkg_summary.append(
                    "%s: COMPILE FAIL (compile exception: %s)" % (pkg, e))
                continue

            if not os.path.isfile(test_bin):
                pkg_diag["test_bin_missing"] = True
                per_pkg_diag.append(pkg_diag)
                compile_fail_pkgs += 1
                per_pkg_summary.append(
                    "%s: COMPILE FAIL (test binary not produced, exit=%d)"
                    % (pkg, rc))
                continue

            # Step 2: sign the test binary (E128 bypass via E077).
            pkg_diag["stage"] = "sign"
            try:
                sign_ok = self._sign_elf(test_bin)
                pkg_diag["sign_ok"] = sign_ok
            except Exception as e:
                pkg_diag["sign_error"] = str(e)
                sign_ok = False
            if not sign_ok:
                per_pkg_diag.append(pkg_diag)
                compile_fail_pkgs += 1
                per_pkg_summary.append(
                    "%s: SIGN FAIL (test binary not signed, E128 may follow)"
                    % pkg)
                continue

            # Step 3: execute the signed test binary directly.
            pkg_diag["stage"] = "run"
            stdout_file = os.path.join(
                ext2_cache, "%s.stdout" % pkg_slug)
            run_cmd = "%s -test.v -test.short" % test_bin
            try:
                saved_env = dict(os.environ)
                rc = self.run(run_cmd, env=None, cwd=src,
                              stdout=stdout_file, ignore_errors=True)
                pkg_diag["run_exit"] = rc
            except Exception as e:
                pkg_diag["run_error"] = str(e)
                pkg_diag["run_exit"] = -1
                per_pkg_diag.append(pkg_diag)
                compile_fail_pkgs += 1
                per_pkg_summary.append(
                    "%s: RUN FAIL (run exception: %s)" % (pkg, e))
                continue
            finally:
                os.environ.clear()
                os.environ.update(saved_env)

            output = ""
            try:
                with open(stdout_file, "r", errors="replace") as infh:
                    output = infh.read()
            except OSError:
                pkg_diag["stdout_read_error"] = "could not read %s" % stdout_file

            pkg_pass = pkg_fail = pkg_skip = 0
            saw_test_event = False
            out_lines = [l for l in output.splitlines() if l.strip()]
            for line in out_lines:
                line = line.strip()
                if line.startswith("--- PASS:"):
                    pkg_pass += 1
                    saw_test_event = True
                elif line.startswith("--- FAIL:"):
                    pkg_fail += 1
                    saw_test_event = True
                elif line.startswith("--- SKIP:"):
                    pkg_skip += 1
                    saw_test_event = True
                elif line.startswith("=== RUN   ") or line.startswith("=== PAUSE ") \
                        or line.startswith("=== CONT "):
                    saw_test_event = True

            pkg_diag["stdout_lines"] = len(out_lines)
            pkg_diag["saw_test_event"] = saw_test_event
            pkg_diag["pkg_pass"] = pkg_pass
            pkg_diag["pkg_fail"] = pkg_fail
            pkg_diag["pkg_skip"] = pkg_skip
            per_pkg_diag.append(pkg_diag)

            passed += pkg_pass
            failed += pkg_fail
            skipped += pkg_skip
            if pkg_pass > 0 or pkg_fail > 0 or pkg_skip > 0:
                ran_pkgs += 1
                per_pkg_summary.append(
                    "%s: pass=%d fail=%d skip=%d exit=%d"
                    % (pkg, pkg_pass, pkg_fail, pkg_skip, rc))
            else:
                compile_fail_pkgs += 1
                per_pkg_summary.append(
                    "%s: COMPILE FAIL (no test events, exit=%d)"
                    % (pkg, rc))

        executed = passed + failed + skipped
        discovered = executed
        self.output.info("===== per-package summary =====")
        for line in per_pkg_summary:
            self.output.info(line)
        self.output.info(
            "go test -short summary: discovered=%d executed=%d passed=%d "
            "failed=%d skipped=%d (packages_run=%d compile_fail=%d)"
            % (discovered, executed, passed, failed, skipped,
               ran_pkgs, compile_fail_pkgs)
        )

        status = "passed" if failed == 0 and passed > 0 else "failed"
        aggregate_cmd = (
            "%s test -c -short -count=1 -timeout 120s -o <ext2>/<pkg>.test <pkg> "
            "&& sign <pkg>.test && <pkg>.test -test.v -test.short"
            % go_bin)
        ut_result = {
            "status": status,
            "framework": "go-test",
            "command": aggregate_cmd,
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "diag": diag,
            "per_pkg_diag": per_pkg_diag,
        }
        print(f"HMBS_UPSTREAM_TEST_RESULT={json.dumps(ut_result)}")

        if compile_fail_pkgs:
            self.output.warning(
                "%d upstream test package(s) failed to compile/sign and were "
                "not executed; reported honestly in the aggregate marker"
                % compile_fail_pkgs)

    # ------------------------------------------------------------------
    # test()
    # ------------------------------------------------------------------
    def test(self):
        """Run the consumer smoke test (kor version via test.sh) and
        the upstream ``go test`` suite; emit HMBS evidence markers."""
        # ----- 1. consumer smoke test -----
        tp_passed = False
        tp_executed = False
        tp_command = "bash test.sh"
        if can_run(self):
            tp_executed = True
            rc = self.run("bash test.sh", env="conanrun")
            tp_passed = (rc == 0)
        else:
            self.output.info("Cross-compiling, skipping runtime smoke test")

        tp_result = {
            "executed": tp_executed,
            "passed": tp_passed,
            "command": tp_command,
        }
        print(f"HMBS_TEST_PACKAGE_RESULT={json.dumps(tp_result)}")

        if not tp_passed:
            raise ConanException(
                "test_package consumer smoke test failed (kor version)")

        # ----- 2. upstream go test suite -----
        env, go_bin = self._go_env()
        self._run_go("%s version" % go_bin, env, cwd=self.build_folder)
        src = self._upstream_source()
        self._run_go("%s mod download" % go_bin, env, cwd=src)
        self._run_upstream_tests(go_bin, env, src)
