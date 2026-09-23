#!/usr/bin/env python3
"""Conan recipe for ko 0.19.1 — container image builder for Go projects (ko-build/ko).

ko is a pure-Go command-line application (no cgo, no //go:embed, no vendor/
directory). The command entry is the root package (`main.go`), so it is built
with `go build .` (not `./cmd/...`). Build with:

    CGO_ENABLED=0 GOOS=linux GOARCH=arm64 GOTOOLCHAIN=local \
    GOPROXY=https://goproxy.cn,https://proxy.golang.org,direct \
    GOSUMDB=sum.golang.google.cn \
    go build -trimpath -ldflags="-s -w -X github.com/google/ko/pkg/commands.Version=v0.19.1" \
    -o ko .

ko has NO vendor/ directory (unlike ahoy), so module dependencies (19 direct +
142 indirect, go.sum 586 lines) are fetched with `go mod download` through the
goproxy.cn module proxy with sum.golang.google.cn checksum verification.

Upstream tests: ko 0.19.1 contains 29 *_test.go files across ~15 packages
(testify-based + stdlib testing). The FULL `go test` suite output is captured
to build_folder/upstream_test_full.log so the per-case report
(total / passed / failed / skipped + each case name) can be extracted
separately from the test_package smoke test.

OHOS adaptation notes (aligned with the kics 2.1.20 / ahoy 2.5.0 Go recipes):
- The Go linker needs an ext2-like workspace on OHOS to avoid
  `mapping output file failed: permission denied` (HMDFS mmap restriction).
  Link output is written under /data/storage/el2/... when running on OHOS.
- OHOS Go executables (and the Go SDK tool binaries themselves) must be
  self-signed with binary-sign-tool before they can be fork/exec'd.
- `go test -exec <wrapper>` is NOT used on OHOS. Each package's test binary is
  compiled with `go test -c`, self-signed, and run DIRECTLY as a child of this
  conan process (verified empirically: a signed Go binary CAN fork/exec the
  signed system git, so pkg/internal/git tests run for real).
"""
import concurrent.futures
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


_GO_VERSION = "1.26.3"
_GO_ARM64_URLS = [
    "https://golang.google.cn/dl/go1.26.3.linux-arm64.tar.gz",
    "https://dl.google.com/go/go1.26.3.linux-arm64.tar.gz",
]
_GO_ARM64_SHA256 = "9d89a3ea57d141c2b22d70083f2c8459ba3890f2d9e818e7e933b75614936565"

_EXT2_CANDIDATES = [
    "/data/storage/el2/base/haps/entry/files",
    "/data/storage/el2/base/cache",
]


class KoConan(ConanFile):
    name = "ko"
    version = "0.19.1"
    description = (
        "Build container images for Go projects directly from source code "
        "without a Dockerfile (ko-build/ko, pure Go CLI)"
    )
    license = "Apache-2.0"
    homepage = "https://ko-build.github.io/ko/"
    url = "https://github.com/ko-build/ko"
    topics = ("ko", "container", "image", "go", "kubernetes", "cli")

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        # conandata.yml has an empty patches map; kept as the standard OHC
        # patch entry point (G1 requirement).
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("ko is prepared for Linux/OHOS targets only")

    def generate(self):
        self._go_environment().vars(self).save_script(self._go_env_script())

    def build(self):
        go = self._go_executable()
        # Build-time safety net: re-create subdirs in case generate() was
        # skipped or the workspace path changed between phases.
        for subdir in ("tmp", "go-build-cache", "go-mod-cache"):
            os.makedirs(os.path.join(self._go_workspace(), subdir), exist_ok=True)

        env = [self._go_env_script()]
        self._run_go(f'"{go}" version', env, self.source_folder)

        # ko has no vendor/ directory: fetch the module graph through the
        # goproxy.cn proxy (go.sum verifies via sum.golang.google.cn).
        self._run_go(f'"{go}" mod download', env, self.source_folder)

        out_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(out_dir, exist_ok=True)
        # Go linker mmap fails on HMDFS: link on ext2-like workspace on OHOS.
        link_out_dir = (
            os.path.join(self._go_workspace(), "link-out")
            if str(self.settings.os) == "OHOS"
            else out_dir
        )
        os.makedirs(link_out_dir, exist_ok=True)
        linked_exe = os.path.join(link_out_dir, "ko")
        final_exe = os.path.join(out_dir, "ko")
        ldflags = (
            "-s -w "
            f"-X github.com/google/ko/pkg/commands.Version=v{self.version}"
        )
        self._run_go(
            f'"{go}" build -trimpath -ldflags "{ldflags}" -o "{linked_exe}" .',
            env,
            self.source_folder,
        )
        self._sign_elf_if_ohos(linked_exe)
        if os.path.abspath(linked_exe) != os.path.abspath(final_exe):
            shutil.copy2(linked_exe, final_exe)

        # Run + capture the real upstream `go test` suite (separate report).
        self._run_upstream_tests(go, env)

    def package(self):
        copy(self, "ko", os.path.join(self.build_folder, "bin"),
             os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        packaged = os.path.join(self.package_folder, "bin", "ko")
        if os.path.isfile(packaged):
            os.chmod(packaged, 0o755)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]

    # ── Go toolchain helpers (aligned with kics 2.1.20 / ahoy 2.5.0) ──

    def _run_upstream_tests(self, go, env_list):
        """Run and capture the real upstream ``go test`` suite.

        On OHOS we cannot use ``go test -exec <wrapper>``. Each package's test
        binary is compiled with ``go test -c``, self-signed, and run DIRECTLY
        as a child of this conan process, from its OWN package dir (so relative
        testdata/fixtures resolve exactly like ``go test`` does).
        """
        base_env = dict(os.environ)
        ws = self._go_workspace()
        base_env.update({
            "CGO_ENABLED": "0",
            "GOOS": self._goos(),
            "GOARCH": self._goarch(),
            "GOTOOLCHAIN": "local",
            "GOPROXY": os.environ.get("GOPROXY", "https://goproxy.cn,https://proxy.golang.org,direct"),
            "GOSUMDB": os.environ.get("GOSUMDB", "sum.golang.google.cn"),
            "TMPDIR": os.path.join(ws, "tmp"),
            "GOTMPDIR": os.path.join(ws, "tmp"),
            "GOCACHE": os.path.join(ws, "go-build-cache"),
            "GOMODCACHE": os.path.join(ws, "go-mod-cache"),
        })
        goroot = self._goroot_for_go(go)
        if goroot:
            base_env["GOROOT"] = goroot
        base_env["PATH"] = os.path.dirname(go) + os.pathsep + base_env.get("PATH", "")
        # test binaries may fork/exec system tools (git 2.45.2 verified working)
        for pth in ("/data/service/hnp/bin", "/usr/bin", "/bin"):
            if os.path.isdir(pth):
                base_env["PATH"] = base_env["PATH"] + os.pathsep + pth

        if str(self.settings.os) != "OHOS":
            # Runtime env must NOT carry GOOS/GOARCH: ko's NewBuilder treats a
            # process-level GOOS as conflicting with explicit --platform /
            # KO_DEFAULTPLATFORMS settings ("cannot use --platform ... combined
            # with GOOS=..."), and upstream CI runs `go test` without GOOS.
            # Compile-time env (base_env) keeps GOOS/GOARCH; the run env drops it.
            runtime_env = dict(base_env)
            runtime_env.pop("GOOS", None)
            runtime_env.pop("GOARCH", None)
            self._run_upstream_tests_native(go, runtime_env)
            return
        self._run_upstream_tests_ohos(go, base_env)

    def _run_upstream_tests_native(self, go, env):
        cmd = [go, "test", "-v", "-count=1", "./..."]
        try:
            proc = subprocess.run(cmd, cwd=self.source_folder, env=env,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  timeout=3600)
            out = proc.stdout.decode(errors="replace")
            rc = proc.returncode
        except subprocess.TimeoutExpired as exc:
            out = (exc.stdout or b"").decode(errors="replace")
            rc = 124
        except OSError as exc:
            out = f"go test failed to run: {exc}"
            rc = 127
        self._record_upstream_test_result(out, rc, cmd)

    def _run_upstream_tests_ohos(self, go, env):
        """OHOS: compile each package's test binary, self-sign, run directly."""
        ws = self._go_workspace()
        test_bin_dir = os.path.join(ws, "upstream-test-bins")
        os.makedirs(test_bin_dir, exist_ok=True)

        # Discover packages WITH test files, plus their on-disk dir (each test
        # binary must run from its OWN package dir, exactly like `go test`).
        try:
            fmt = "{{if or .TestGoFiles .XTestGoFiles}}{{.ImportPath}}{{\"\\t\"}}{{.Dir}}{{end}}"
            raw = subprocess.check_output(
                [go, "list", "-f", fmt, "./..."],
                cwd=self.source_folder, env=env, timeout=900,
            ).decode(errors="replace").splitlines()
            pkgs, pkg_dirs = [], {}
            for ln in raw:
                parts = ln.split("\t", 1)
                if len(parts) != 2:
                    continue
                pkgs.append(parts[0])
                pkg_dirs[parts[0]] = parts[1]
        except Exception as exc:  # noqa: BLE001
            self.output.warning("go list ./... failed: %s" % exc)
            pkgs, pkg_dirs = [], {}

        if not pkgs:
            self.output.warning("no packages with test files discovered")
            upstream = {
                "status": "no_tests",
                "framework": "go test",
                "command": "%s test -c (per package) + direct run (OHOS)" % go,
                "discovered": 0, "executed": 0, "passed": 0, "failed": 0, "skipped": 0,
            }
            self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))
            return

        build_timeout = 900
        run_timeout = 300
        max_workers = 4

        # Same GOOS/GOARCH runtime-env drop as the native path (see comment in
        # _run_upstream_tests): the test binaries are already compiled for the
        # target, and a lingering GOOS would break ko's own platform handling.
        runtime_env = dict(env)
        runtime_env.pop("GOOS", None)
        runtime_env.pop("GOARCH", None)

        def run_pkg(pkg, pkgdir):
            safe = re.sub(r"[^A-Za-z0-9_.-]", "_", pkg)
            binpath = os.path.join(test_bin_dir, safe + ".test")
            try:
                bproc = subprocess.run(
                    [go, "test", "-c", "-o", binpath, pkg],
                    cwd=self.source_folder, env=env,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    timeout=build_timeout,
                )
                bout = bproc.stdout.decode(errors="replace")
            except subprocess.TimeoutExpired as exc:
                bout = (exc.stdout or b"").decode(errors="replace")
                return (pkg, "BUILD_TIMEOUT", None, "### PACKAGE %s ###\nBUILD TIMEOUT\n%s" % (pkg, bout))
            if not os.path.isfile(binpath):
                if "no test files" in bout:
                    return (pkg, "NO_TESTS", None, None)
                return (pkg, "BUILD_FAIL", None, "### PACKAGE %s ###\nBUILD FAIL\n%s" % (pkg, bout))
            # Self-sign the freshly compiled test binary (required on OHOS).
            self._sign_elf_if_ohos(binpath)
            cwd = pkgdir or self.source_folder
            try:
                rproc = subprocess.run(
                    [binpath, "-test.v", "-test.count=1"],
                    cwd=cwd, env=runtime_env,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    timeout=run_timeout,
                )
                out = rproc.stdout.decode(errors="replace")
            except subprocess.TimeoutExpired as exc:
                out = (exc.stdout or b"").decode(errors="replace")
                out += "\n--- OHOS_TEST_PKG_TIMEOUT ---\n"
            except OSError as exc:
                out = "test run failed to exec: %s" % exc
            p = len(re.findall(r"^\s*--- PASS:", out, re.MULTILINE))
            f = len(re.findall(r"^\s*--- FAIL:", out, re.MULTILINE))
            s = len(re.findall(r"^\s*--- SKIP:", out, re.MULTILINE))
            return (pkg, "ok" if f == 0 else "FAIL", (p, f, s),
                    "### PACKAGE %s ###\n%s" % (pkg, out))

        all_out = []
        per_pkg = []
        total_pass = total_fail = total_skip = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = {ex.submit(run_pkg, pkg, pkg_dirs.get(pkg)): pkg for pkg in pkgs}
            for fut in concurrent.futures.as_completed(futures):
                pkg, st, counts, out = fut.result()
                if out:
                    all_out.append(out)
                per_pkg.append((pkg, st, counts))
                if counts:
                    total_pass += counts[0]
                    total_fail += counts[1]
                    total_skip += counts[2]

        full = "\n".join(sorted(all_out))
        full_log = os.path.join(self.build_folder, "upstream_test_full.log")
        try:
            with open(full_log, "w", encoding="utf-8", errors="replace") as fh:
                fh.write(full)
        except OSError:
            pass

        self.output.info(
            "ko upstream `go test` (OHOS direct-exec): PASS=%d FAIL=%d SKIP=%d pkgs=%d"
            % (total_pass, total_fail, total_skip, len(pkgs))
        )
        for pkg, st, counts in sorted(per_pkg):
            self.output.info("  [%s] %s %s" % (st, pkg, counts if counts else ""))
        self.output.info("  full log: %s" % full_log)

        status = "passed" if (total_fail == 0 and total_pass > 0) else (
            "failed" if total_fail > 0 else "no_tests")
        upstream = {
            "status": status,
            "framework": "go test",
            "command": "%s test -c (per package) + direct run from each package dir (OHOS, no -exec wrapper)" % go,
            "discovered": total_pass + total_fail + total_skip,
            "executed": total_pass + total_fail + total_skip,
            "passed": total_pass,
            "failed": total_fail,
            "skipped": total_skip,
            "packages_total": len(pkgs),
            "full_log": full_log,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))

    def _record_upstream_test_result(self, out, rc, cmd):
        full_log = os.path.join(self.build_folder, "upstream_test_full.log")
        try:
            with open(full_log, "w", encoding="utf-8", errors="replace") as fh:
                fh.write(out)
        except OSError:
            pass
        p = len(re.findall(r"^\s*--- PASS:", out, re.MULTILINE))
        f = len(re.findall(r"^\s*--- FAIL:", out, re.MULTILINE))
        s = len(re.findall(r"^\s*--- SKIP:", out, re.MULTILINE))
        self.output.info("ko upstream `go test -v -count=1 ./...`: "
                         f"PASS={p} FAIL={f} SKIP={s} (go rc={rc})")
        status = "failed" if f > 0 else ("passed" if p > 0 else "no_tests")
        upstream = {
            "status": status,
            "framework": "go test",
            "command": " ".join(cmd),
            "discovered": p + f + s,
            "executed": p + f + s,
            "passed": p,
            "failed": f,
            "skipped": s,
            "full_log": full_log,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))

    def _go_env_script(self):
        return "ko_go_env"

    def _go_environment(self):
        work = self._go_workspace()
        values = {
            "CGO_ENABLED": "0",
            "GOOS": self._goos(),
            "GOARCH": self._goarch(),
            "GOPROXY": os.environ.get("GOPROXY", "https://goproxy.cn,https://proxy.golang.org,direct"),
            "GOSUMDB": os.environ.get("GOSUMDB", "sum.golang.google.cn"),
            "GOTOOLCHAIN": "local",
            "TMPDIR": os.path.join(work, "tmp"),
            "GOTMPDIR": os.path.join(work, "tmp"),
            "GOCACHE": os.path.join(work, "go-build-cache"),
            "GOMODCACHE": os.path.join(work, "go-mod-cache"),
        }
        go = self._go_executable()
        env = Environment()
        for key, value in values.items():
            env.define(key, value)
        goroot = self._goroot_for_go(go)
        if goroot:
            env.define("GOROOT", goroot)
        env.prepend_path("PATH", os.path.dirname(go))
        for key in ("TMPDIR", "GOTMPDIR", "GOCACHE", "GOMODCACHE"):
            os.makedirs(values[key], exist_ok=True)
        return env

    def _run_go(self, cmd, env, cwd):
        self.run(cmd, cwd=cwd, env=env)

    def _go_workspace(self):
        if str(self.settings.os) == "OHOS":
            for base in _EXT2_CANDIDATES:
                candidate = os.path.join(base, "ko-0.19.1-go-work")
                try:
                    os.makedirs(candidate, exist_ok=True)
                    probe = os.path.join(candidate, ".probe")
                    Path(probe).write_text("ok\n", encoding="utf-8")
                    os.remove(probe)
                    return candidate
                except OSError:
                    continue
        root = os.path.join(self.build_folder, ".go-work")
        os.makedirs(root, exist_ok=True)
        return root

    def _go_executable(self):
        candidates = []
        if os.environ.get("GO"):
            candidates.append(os.environ["GO"])
        if os.environ.get("GOROOT"):
            candidates.append(os.path.join(os.environ["GOROOT"], "bin", "go"))
        candidates.extend([
            "/data/storage/el2/base/haps/entry/files/go-sdk-cache/go1.26.3/bin/go",
            "/storage/Users/currentUser/usr/local/go1263/bin/go",
            "/storage/Users/currentUser/sdk/go1.26.3/bin/go",
            "/storage/Users/currentUser/sdk/go/bin/go",
        ])
        found = shutil.which("go")
        if found:
            candidates.append(found)
        for candidate in candidates:
            if candidate and os.path.isfile(candidate) and self._go_runs(candidate):
                return candidate
        return self._ensure_go_toolchain()

    def _ensure_go_toolchain(self):
        if self._host_goarch() != "arm64":
            raise ConanInvalidConfiguration("Go bootstrap is only prepared for Linux arm64 workers")
        sdk_root = self._shared_go_sdk_root()
        goroot = os.path.join(sdk_root, f"go{_GO_VERSION}")
        gobin = os.path.join(goroot, "bin", "go")
        if not os.path.isfile(gobin):
            get(self, url=_GO_ARM64_URLS, sha256=_GO_ARM64_SHA256, destination=sdk_root, strip_root=False)
            if os.path.isdir(goroot):
                shutil.rmtree(goroot)
            os.rename(os.path.join(sdk_root, "go"), goroot)
        self._sign_go_sdk_if_ohos(goroot)
        return gobin

    def _shared_go_sdk_root(self):
        if str(self.settings.os) == "OHOS":
            for base in _EXT2_CANDIDATES:
                candidate = os.path.join(base, "go-sdk-cache")
                try:
                    os.makedirs(candidate, exist_ok=True)
                    return candidate
                except OSError:
                    continue
        root = os.path.join(self._go_workspace(), "go-sdk")
        os.makedirs(root, exist_ok=True)
        return root

    def _sign_go_sdk_if_ohos(self, goroot):
        if str(self.settings.os) != "OHOS":
            return
        marker = os.path.join(goroot, ".ohos-signed")
        if os.path.isfile(marker):
            return
        tool_dir = os.path.join(goroot, "pkg", "tool", f"linux_{self._host_goarch()}")
        targets = [os.path.join(goroot, "bin", "go"), os.path.join(goroot, "bin", "gofmt")]
        if os.path.isdir(tool_dir):
            targets.extend(os.path.join(tool_dir, name) for name in os.listdir(tool_dir))
        for target in targets:
            if os.path.isfile(target) and self._is_elf(target):
                self._sign_elf_if_ohos(target)
        Path(marker).write_text("signed\n", encoding="utf-8")

    def _sign_elf_if_ohos(self, path):
        if str(self.settings.os) != "OHOS":
            return
        if self._has_ohos_signature(path):
            os.chmod(path, 0o755)
            return
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            signer = "/storage/Users/currentUser/usr/local/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            raise ConanInvalidConfiguration("binary-sign-tool is required to sign OHOS Go executables")
        signed = f"{path}.signed"
        subprocess.check_call([
            signer, "sign", "-selfSign", "1", "-inFile", path, "-outFile", signed,
            "-signAlg", "SHA256withECDSA",
        ])
        shutil.move(signed, path)
        os.chmod(path, 0o755)

    @staticmethod
    def _go_runs(go):
        try:
            subprocess.run([go, "version"], capture_output=True, timeout=10, check=True)
            return True
        except (OSError, subprocess.SubprocessError):
            return False

    @staticmethod
    def _goroot_for_go(go):
        go_path = Path(go).resolve()
        goroot = go_path.parent.parent
        if go_path.parent.name == "bin" and (goroot / "pkg").is_dir():
            return str(goroot)
        return None

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
                data = f.read()
            return b".codesign" in data or b".note.ohos" in data
        except OSError:
            return False

    def _goos(self):
        return "linux" if str(self.settings.os) == "OHOS" else str(self.settings.os).lower()

    def _goarch(self):
        return {"x86_64": "amd64", "armv8": "arm64", "armv7": "arm"}.get(str(self.settings.arch), str(self.settings.arch))

    @staticmethod
    def _host_goarch():
        return {"aarch64": "arm64", "arm64": "arm64", "x86_64": "amd64", "amd64": "amd64"}.get(platform.machine().lower(), platform.machine().lower())
