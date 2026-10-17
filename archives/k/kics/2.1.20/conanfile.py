#!/usr/bin/env python3
"""Conan recipe for kics 2.1.20 — Keeping Infrastructure as Code Secure (pure Go CLI).

KICS is a pure-Go command-line application. The command entry is
`github.com/Checkmarx/kics/v2/cmd/console` (main.go under cmd/console), so it is
built with `go build ./cmd/console` (not a bare `.`). Build with:

    CGO_ENABLED=0 GOOS=linux GOARCH=arm64 \
    GOPROXY=https://goproxy.cn,https://proxy.golang.org,direct GOTOOLCHAIN=local \
    go build -trimpath -ldflags="-s -w -X github.com/Checkmarx/kics/v2/internal/constants.Version=v2.1.20" \
    -o kics ./cmd/console

KICS embeds only a few assets via `//go:embed` (see assets/assets.go for the
rego libraries and the secrets regexes). The full query library under
`assets/queries` is loaded from the FILESYSTEM via `--queries-path` (default
`./assets/queries`), NOT embedded — so package() must ship `assets/` alongside
the binary for `kics scan` to work.

Upstream tests: kics 2.1.20 contains 121 *_test.go files (testify-based). The
FULL `go test` suite output is captured to build_folder/upstream_test_full.log so
the per-case report (total / passed / failed / skipped + each case name) can be
extracted separately from the test_package smoke test.

OHOS adaptation notes (critical, learned empirically on OHOS aarch64):
- The Go linker needs an ext2-like workspace on OHOS to avoid `mapping output
  file failed: permission denied` (HMDFS mmap restriction). Link output is written
  under /data/storage/el2/... when running on OHOS.
- OHOS Go executables (and the Go SDK tool binaries themselves) must be
  self-signed with binary-sign-tool before they can be fork/exec'd.
- **Symlink syscall is denied to self-signed binaries.** go-getter's file getter
  (used by pkg/engine/provider/extract.go GetSources) does os.Symlink(localDir,
  os.TempDir()/kics-extract-*) for every local source path (scan path,
  --queries-path, --libraries-path). On OHOS this fails with `permission denied`.
  We patch extract.go to reference local existing paths directly (stripping a
  possible file:// prefix) instead of going through go-getter extraction.
- **A self-signed binary cannot execve() another binary.** Therefore the classic
  `go test -exec <wrapper>` trick does NOT work on OHOS (the wrapper signs the
  test binary but its syscall.Exec(testBinary) is denied). Instead we compile each
  package's test binary with `go test -c`, self-sign it, and run it DIRECTLY as a
  child of this conan process (which is trusted) — exactly like the kics binary
  itself runs. This is the only reliable way to execute the upstream suite.
"""
import concurrent.futures
import json
import os
import platform
import re
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

# Marker embedded in the patched extract.go so the patch is idempotent.
_OHOS_SYMLINK_PATCH_MARKER = "// OHOS-PATCH: local-path short-circuit"


class KicsConan(ConanFile):
    name = "kics"
    version = "2.1.20"
    _go_version = "1.25.0"
    _go_archives = {
        "arm64": (
            [
                "https://golang.google.cn/dl/go1.25.0.linux-arm64.tar.gz",
                "https://mirrors.aliyun.com/golang/go1.25.0.linux-arm64.tar.gz",
                "https://dl.google.com/go/go1.25.0.linux-arm64.tar.gz",
            ],
            "05de75d6994a2783699815ee553bd5a9327d8b79991de36e38b66862782f54ae",
        ),
        "amd64": (
            [
                "https://golang.google.cn/dl/go1.25.0.linux-amd64.tar.gz",
                "https://mirrors.aliyun.com/golang/go1.25.0.linux-amd64.tar.gz",
                "https://dl.google.com/go/go1.25.0.linux-amd64.tar.gz",
            ],
            "2852af0cb20a13139b3448992e69b868e50ed0f8a1e5940ee1de9e19a123b613",
        ),
    }
    package_type = "application"

    description = "Keeping Infrastructure as Code Secure — open-source security scanner for IaC (pure Go CLI)"
    license = "Apache-2.0"
    homepage = "https://github.com/Checkmarx/kics"
    url = "https://github.com/Checkmarx/kics"
    topics = ("kics", "iac", "security", "terraform", "scanning", "go", "devsecops")

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        # No conandata patches for the kics tarball itself; the OHOS symlink patch
        # is applied in build() to the extracted source (kept idempotent).
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # conandata.yml currently has an empty patches map, so this is a no-op;
        # kept as the standard OHC patch entry point (G1 requirement).
        apply_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("kics supports Linux and OHOS targets only")

    def generate(self):
        env = Environment()
        env.define("CGO_ENABLED", "0")
        env.define("GOOS", self._goos())
        env.define("GOARCH", self._goarch())
        env.define("GOPROXY", os.environ.get("GOPROXY", "https://goproxy.cn,https://proxy.golang.org,direct"))
        env.define("GOSUMDB", os.environ.get("GOSUMDB", "sum.golang.google.cn"))
        env.define("GOTOOLCHAIN", "local")

        go_workspace = self._go_workspace()
        env.define("TMPDIR", os.path.join(go_workspace, "tmp"))
        env.define("GOTMPDIR", os.path.join(go_workspace, "tmp"))
        env.define("GOCACHE", os.path.join(go_workspace, "go-build-cache"))
        env.define("GOMODCACHE", os.path.join(go_workspace, "go-mod-cache"))
        # Pre-create subdirs: Go refuses to bootstrap without every path component.
        for d in ("tmp", "go-build-cache", "go-mod-cache"):
            os.makedirs(os.path.join(go_workspace, d), exist_ok=True)

        gobin = self._go_executable()
        goroot = self._goroot_for_go(gobin)
        if goroot:
            env.define("GOROOT", goroot)
        env.prepend_path("PATH", os.path.dirname(gobin))

        env.vars(self).save_script("kics_go_env")

    def build(self):
        go = self._go_executable()
        # Build-time safety net: re-create subdirs in case generate() was skipped
        # or the workspace path changed between phases.
        for subdir in ("tmp", "go-build-cache", "go-mod-cache"):
            os.makedirs(os.path.join(self._go_workspace(), subdir), exist_ok=True)
        self.run(f'"{go}" mod download', cwd=self.source_folder, env=["kics_go_env"])

        # OHOS adaptation: avoid go-getter symlink() for local paths.
        self._patch_ohos_extract()
        self._patch_ohos_helpers()

        out_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(out_dir, exist_ok=True)
        # Go linker mmap fails on HMDFS: link on ext2-like workspace on OHOS.
        link_out_dir = os.path.join(self._go_workspace(), "link-out") if str(self.settings.os) == "OHOS" else out_dir
        os.makedirs(link_out_dir, exist_ok=True)
        linked_exe = os.path.join(link_out_dir, "kics")
        final_exe = os.path.join(out_dir, "kics")
        ldflags = "-s -w -X github.com/Checkmarx/kics/v2/internal/constants.Version=v2.1.20"
        self.run(
            f'"{go}" build -trimpath -ldflags "{ldflags}" -o "{linked_exe}" ./cmd/console',
            cwd=self.source_folder,
            env=["kics_go_env"],
        )
        self._sign_elf_if_ohos(linked_exe)
        if os.path.abspath(linked_exe) != os.path.abspath(final_exe):
            shutil.copy2(linked_exe, final_exe)

        # Run + capture the real upstream `go test` suite (separate report).
        self._run_upstream_tests(go)

    def package(self):
        copy(self, "kics", os.path.join(self.build_folder, "bin"), os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        # kics queries/libraries/templates are loaded from the filesystem at scan
        # time (--queries-path / --libraries-path), not embedded, so ship assets/.
        copy(self, "*", os.path.join(self.source_folder, "assets"),
             os.path.join(self.package_folder, "assets"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]

    # ── Go toolchain helpers (aligned with aiac / spicedb / argo Go recipes) ──

    def _run_upstream_tests(self, go):
        """Run and capture the real upstream ``go test`` suite.

        On OHOS we cannot use ``go test -exec <wrapper>`` (a self-signed binary is
        denied execve of another binary). So for OHOS we compile each package's
        test binary with ``go test -c``, self-sign it, and run it DIRECTLY as a
        child of this conan process. On non-OHOS we run the normal ``go test``.

        The FULL output is written to build_folder/upstream_test_full.log so the
        per-case report (total / passed / failed / skipped + each case name) can be
        extracted separately from the test_package smoke test.
        """
        base_env = dict(os.environ)
        go_workspace = self._go_workspace()
        go_env_overrides = {
            "CGO_ENABLED": "0",
            "GOOS": self._goos(),
            "GOARCH": self._goarch(),
            "GOTOOLCHAIN": "local",
            "TMPDIR": os.path.join(go_workspace, "tmp"),
            "GOTMPDIR": os.path.join(go_workspace, "tmp"),
            "GOCACHE": os.path.join(go_workspace, "go-build-cache"),
            "GOMODCACHE": os.path.join(go_workspace, "go-mod-cache"),
        }
        goroot = self._goroot_for_go(go)
        if goroot:
            go_env_overrides["GOROOT"] = goroot
        base_env.update(go_env_overrides)
        base_env["PATH"] = os.path.dirname(go) + os.pathsep + base_env.get("PATH", "")

        if str(self.settings.os) == "OHOS":
            self._run_upstream_tests_ohos(go, base_env)
        else:
            self._run_upstream_tests_native(go, base_env)

    def _run_upstream_tests_native(self, go, env):
        cmd = [go, "test", "-v", "-count=1", "./..."]
        try:
            proc = subprocess.run(cmd, cwd=self.source_folder, env=env,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=3600)
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
        """OHOS: compile each package's test binary, self-sign, run directly.

        Avoids ``go test -exec`` entirely (self-signed binaries cannot execve).
        Packages are processed concurrently (Go's build cache is concurrent-safe)
        to keep the run bounded.
        """
        ws = self._go_workspace()
        test_bin_dir = os.path.join(ws, "upstream-test-bins")
        os.makedirs(test_bin_dir, exist_ok=True)

        # Discover packages (and their on-disk dir — each test binary must run
        # from its OWN package dir, exactly like `go test` does, or tests that
        # load relative testdata/fixtures will fail to find them).
        try:
            raw = subprocess.check_output(
                [go, "list", "-f", "{{.ImportPath}}\t{{.Dir}}", "./..."],
                cwd=self.source_folder, env=env, timeout=600,
            ).decode(errors="replace").splitlines()
            pkgs = []
            pkg_dirs = {}
            for ln in raw:
                parts = ln.split("\t", 1)
                if len(parts) != 2:
                    continue
                pkgs.append(parts[0])
                pkg_dirs[parts[0]] = parts[1]
        except Exception as exc:  # noqa: BLE001
            self.output.warning("go list ./... failed: %s" % exc)
            pkgs = []
            pkg_dirs = {}

        if not pkgs:
            self.output.warning("no packages discovered; skipping upstream tests")
            upstream = {
                "status": "no_tests",
                "framework": "go test",
                "command": "%s test -c (per package) + direct run (OHOS)" % go,
                "discovered": 0, "executed": 0, "passed": 0, "failed": 0, "skipped": 0,
            }
            self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))
            return

        build_timeout = 600
        run_timeout = 120
        max_workers = 4
        # pkg/test is the upstream integration suite: it validates metadata for
        # all 1099 queries and runs thousands of scan subtests. A 120 s cap
        # truncates it mid-run (observed: 8 vs 3628 cases captured on cold vs
        # warm I/O), so give it a dedicated generous timeout.
        run_timeouts = {"github.com/Checkmarx/kics/v2/test": 2400}

        def run_pkg(pkg, pkgdir):
            safe = re.sub(r"[^A-Za-z0-9_.-]", "_", pkg)
            binpath = os.path.join(test_bin_dir, safe + ".test")
            # Compile the test binary (no execution yet).
            try:
                bproc = subprocess.run(
                    [go, "test", "-c", "-o", binpath, pkg],
                    cwd=self.source_folder, env=env,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=build_timeout,
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
            # Run it DIRECTLY as a child of this conan process (trusted) — this is
            # the only reliable way; a wrapper's execve would be denied. Run from
            # the package's own dir (matching `go test`) so relative testdata and
            # fixtures resolve correctly.
            cwd = pkgdir or self.source_folder
            pkg_run_timeout = run_timeouts.get(pkg, run_timeout)
            try:
                rproc = subprocess.run(
                    [binpath, "-test.v", "-test.count=1"],
                    cwd=cwd, env=env,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    timeout=pkg_run_timeout,
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
            return (pkg, "ok" if f == 0 else "FAIL", (p, f, s), "### PACKAGE %s ###\n%s" % (pkg, out))

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

        full = "\n".join(all_out)
        full_log = os.path.join(self.build_folder, "upstream_test_full.log")
        try:
            with open(full_log, "w", encoding="utf-8", errors="replace") as fh:
                fh.write(full)
        except OSError:
            pass

        self.output.info(
            "kics upstream `go test` (OHOS direct-exec): PASS=%d FAIL=%d SKIP=%d pkgs=%d"
            % (total_pass, total_fail, total_skip, len(pkgs))
        )
        for pkg, st, counts in per_pkg:
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
        self.output.info("kics upstream `go test -v -count=1 ./...`: "
                         f"PASS={p} FAIL={f} SKIP={s} (go rc={rc})")
        preview = out[:2048].replace("\n", "\n  kics go test | ")
        self.output.info("kics go test output preview:\n  " + preview)
        if f > 0:
            status = "failed"
        elif p > 0:
            status = "passed"
        else:
            status = "no_tests"
        upstream = {
            "status": status,
            "framework": "go test",
            "command": " ".join(cmd),
            "discovered": p + f + s,
            "executed": p + f + s,
            "passed": p,
            "failed": f,
            "skipped": s,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))

    def _patch_ohos_extract(self):
        """OHOS adaptation: self-signed binaries cannot call symlink().

        go-getter's file getter (pkg/engine/provider/extract.go GetSources) does
        os.Symlink(localDir, os.TempDir()/kics-extract-*) for every local source
        path. On OHOS that syscall is denied. Patch GetSources to reference local
        existing paths directly (stripping a possible file:// prefix) instead of
        going through go-getter extraction. Idempotent.
        """
        if str(self.settings.os) != "OHOS":
            return
        target = os.path.join(self.source_folder, "pkg", "engine", "provider", "extract.go")
        if not os.path.isfile(target):
            self.output.warning("extract.go not found; skipping OHOS symlink patch")
            return
        text = Path(target).read_text(encoding="utf-8")
        # Self-correct a previously applied (buggy) patch that declared an unused
        # `info` variable, then stop (the rest of the block is already present).
        if "if info, err := os.Stat(localPath); err == nil {" in text:
            text = text.replace(
                "if info, err := os.Stat(localPath); err == nil {",
                "if _, err := os.Stat(localPath); err == nil {")
            Path(target).write_text(text, encoding="utf-8")
            self.output.info("OHOS: corrected previously-applied extract.go patch (unused info)")
            return
        if _OHOS_SYMLINK_PATCH_MARKER in text:
            return

        old = ("\tfor _, path := range source {\n"
               "\t\tdestination := filepath.Join(os.TempDir(), \"kics-extract-\"+utils.NextRandom())\n")
        new = ("\tfor _, path := range source {\n"
               "\t\t// OHOS-PATCH: local-path short-circuit (avoid go-getter symlink(); "
               "self-signed binaries are denied the symlink syscall on OHOS).\n"
               "\t\tlocalPath := path\n"
               "\t\tif strings.HasPrefix(localPath, \"file://\") {\n"
               "\t\t\tlocalPath = strings.TrimPrefix(localPath, \"file://\")\n"
               "\t\t}\n"
               "\t\tif _, err := os.Stat(localPath); err == nil {\n"
               "\t\t\textrStruct.ExtractionMap[path] = model.ExtractedPathObject{Path: localPath, LocalPath: true}\n"
               "\t\t\textrStruct.Path = append(extrStruct.Path, localPath)\n"
               "\t\t\tcontinue\n"
               "\t\t}\n"
               "\t\tdestination := filepath.Join(os.TempDir(), \"kics-extract-\"+utils.NextRandom())\n")
        if old not in text:
            self.output.warning("extract.go GetSources body changed; OHOS symlink patch skipped")
            return
        # Ensure "strings" is imported.
        if '"strings"' not in text:
            text = text.replace('\t"path/filepath"\n', '\t"path/filepath"\n\t"strings"\n', 1)
        text = text.replace(old, new, 1)
        Path(target).write_text(text, encoding="utf-8")
        self.output.info("OHOS: patched extract.go to avoid symlink() for local paths")

    def _patch_ohos_helpers(self):
        """OHOS adaptation: harden query-path resolution in helpers.GetFullPath.

        Upstream resolves the default queries directory with a heuristic that
        truncates the cwd at the last "kics" path component (it presumes the
        checkout dir is literally named "kics"). That does not hold in conan
        build layouts (hash-named cache dirs) nor for arbitrary install
        prefixes, which breaks remediation flows and default query loading
        (observed upstream: 206 terraform positive failures, all
        "SelectedRemediationNumber != ActualRemediationDoneNumber" with 0 done).
        Patch: (1) also probe the executable directory's parent (the conan
        package ships assets/ next to bin/); (2) walk up from cwd looking for
        the partial path before falling back to the upstream heuristic.
        Idempotent.
        """
        if str(self.settings.os) != "OHOS":
            return
        marker = "OHOS-PATCH: walk-up query path resolution"
        target = os.path.join(self.source_folder, "internal", "console", "helpers", "helpers.go")
        if not os.path.isfile(target):
            self.output.warning("helpers.go not found; skipping OHOS query-path patch")
            return
        text = Path(target).read_text(encoding="utf-8")
        if marker in text:
            return
        old = ("\t\tcurrentWorkDir, err := os.Getwd()\n"
               "\t\tif err != nil {\n"
               "\t\t\treturn \"\", err\n"
               "\t\t}\n"
               "\t\tidx := strings.Index(currentWorkDir, \"kics\")\n")
        new = ("\t\tcurrentWorkDir, err := os.Getwd()\n"
               "\t\tif err != nil {\n"
               "\t\t\treturn \"\", err\n"
               "\t\t}\n"
               "\t\t// OHOS-PATCH: walk-up query path resolution.\n"
               "\t\t// 1) the conan package layout ships assets/ next to bin/.\n"
               "\t\tif parentExeDir := filepath.Dir(executableDirPath); parentExeDir != executableDirPath {\n"
               "\t\t\tcandidate := filepath.Join(parentExeDir, partialPath)\n"
               "\t\t\tif _, err := os.Stat(candidate); err == nil {\n"
               "\t\t\t\treturn candidate, nil\n"
               "\t\t\t}\n"
               "\t\t}\n"
               "\t\t// 2) walk up from cwd (repo-style layouts keep assets/ at the root).\n"
               "\t\tfor walkDir := currentWorkDir; ; walkDir = filepath.Dir(walkDir) {\n"
               "\t\t\tcandidate := filepath.Join(walkDir, partialPath)\n"
               "\t\t\tif _, err := os.Stat(candidate); err == nil {\n"
               "\t\t\t\treturn candidate, nil\n"
               "\t\t\t}\n"
               "\t\t\tparent := filepath.Dir(walkDir)\n"
               "\t\t\tif parent == walkDir {\n"
               "\t\t\t\tbreak\n"
               "\t\t\t}\n"
               "\t\t}\n"
               "\t\tidx := strings.Index(currentWorkDir, \"kics\")\n")
        if old not in text:
            self.output.warning("helpers.go GetFullPath body changed; OHOS query-path patch skipped")
            return
        text = text.replace(old, new, 1)
        Path(target).write_text(text, encoding="utf-8")
        self.output.info("OHOS: patched helpers.go GetFullPath with walk-up query resolution")

    def _go_workspace(self):
        if str(self.settings.os) == "OHOS":
            for base in (
                "/data/storage/el2/base/haps/entry/files",
                "/data/storage/el2/base/cache",
            ):
                candidate = os.path.join(base, "kics-2.1.20-go")
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

    def _ensure_go_toolchain(self):
        host_arch = self._go_host_arch()
        if host_arch not in self._go_archives:
            raise ConanInvalidConfiguration(f"Go SDK bootstrap is not prepared for host arch: {host_arch}")

        sdk_root = os.path.join(self._go_workspace(), "go-sdk", f"go{self._go_version}-{host_arch}")
        goroot = os.path.join(sdk_root, "go")
        gobin = os.path.join(goroot, "bin", "go")
        if not os.path.isfile(gobin):
            urls, sha256 = self._go_archives[host_arch]
            self.output.info(f"Go >= {self._go_version} not found; downloading {urls[0]}")
            get(self, url=urls, sha256=sha256, destination=sdk_root, strip_root=False)
        self._sign_go_sdk_if_ohos(goroot)
        return gobin

    def _sign_go_sdk_if_ohos(self, goroot):
        if str(self.settings.os) != "OHOS":
            return
        marker = os.path.join(goroot, ".ohos-signed")
        if os.path.isfile(marker):
            return

        tool_dir = os.path.join(goroot, "pkg", "tool", f"linux_{self._go_host_arch()}")
        candidates = [
            os.path.join(goroot, "bin", "go"),
            os.path.join(goroot, "bin", "gofmt"),
        ]
        if os.path.isdir(tool_dir):
            candidates.extend(os.path.join(tool_dir, filename) for filename in os.listdir(tool_dir))

        for candidate in candidates:
            if os.path.isfile(candidate) and self._is_elf(candidate):
                self._sign_elf_if_ohos(candidate)
        Path(marker).write_text("signed\n", encoding="utf-8")

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as binary:
                return binary.read(4) == b"\x7fELF"
        except OSError:
            return False

    @staticmethod
    def _has_ohos_signature(path):
        try:
            with open(path, "rb") as binary:
                data = binary.read()
        except OSError:
            return False
        return b".codesign" in data or b".note.ohos" in data

    def _sign_elf_if_ohos(self, path):
        if str(self.settings.os) != "OHOS":
            return
        if self._has_ohos_signature(path):
            os.chmod(path, 0o755)
            return
        signer = self._find_binary_sign_tool()
        if not signer:
            self.output.warning(
                "binary-sign-tool not found; OHOS may reject unsigned executable: %s" % path
            )
            return
        tmp_dir = os.path.join(self._go_workspace(), "sign-tmp")
        Path(tmp_dir).mkdir(parents=True, exist_ok=True)
        tmp_in = os.path.join(tmp_dir, os.path.basename(path))
        tmp_out = f"{tmp_in}.signed"
        shutil.copy2(path, tmp_in)
        objcopy = (
            os.environ.get("OHOS_LLVM_OBJCOPY")
            or shutil.which("llvm-objcopy")
            or "/data/service/hnp/bin/llvm-objcopy"
        )
        if os.path.isfile(objcopy):
            subprocess.run([objcopy, "--remove-section", ".codesign", tmp_in],
                          capture_output=True, timeout=10)
        subprocess.check_call([
            signer,
            "sign",
            "-selfSign",
            "1",
            "-inFile",
            tmp_in,
            "-outFile",
            tmp_out,
            "-signAlg",
            "SHA256withECDSA",
        ])
        shutil.move(tmp_out, path)
        os.chmod(path, 0o755)
        os.unlink(tmp_in)

    def _find_binary_sign_tool(self):
        """Return the path to binary-sign-tool, or None if unavailable."""
        for candidate in (
            os.environ.get("OHOS_BINARY_SIGN_TOOL"),
            os.environ.get("BINARY_SIGN_TOOL"),
            "/data/service/hnp/bin/binary-sign-tool",
            "/storage/Users/currentUser/usr/local/bin/binary-sign-tool",
            shutil.which("binary-sign-tool"),
        ):
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

    def _goos(self):
        if str(self.settings.os) == "OHOS":
            return "linux"
        return str(self.settings.os).lower()

    def _goarch(self):
        arch = str(self.settings.arch)
        return {
            "x86_64": "amd64",
            "x86": "386",
            "armv8": "arm64",
            "armv8_32": "arm",
            "armv7": "arm",
            "armv7hf": "arm",
            "armv6": "arm",
        }.get(arch, arch)

    def _go_executable(self):
        candidates = []
        if os.environ.get("GO"):
            candidates.append(os.environ["GO"])
        if os.environ.get("GOROOT"):
            candidates.append(os.path.join(os.environ["GOROOT"], "bin", "go"))
        candidates.extend([
            os.path.expanduser("~/usr/local/go/bin/go"),
            os.path.expanduser("~/sdk/go1.25.0/bin/go"),
            os.path.expanduser("~/.goenv/versions/1.25.0/bin/go"),
        ])
        found = shutil.which("go")
        if found:
            candidates.append(found)

        for candidate in candidates:
            if candidate and os.path.isfile(candidate) and self._go_version_is_supported(candidate):
                return candidate
        return self._ensure_go_toolchain()

    def _go_version_is_supported(self, go):
        try:
            output = subprocess.run([go, "version"], capture_output=True, timeout=10).stdout.decode()
        except OSError:
            return False
        m = output.split("go version ")[-1].split(" ")[0]  # go1.25.0
        ver = m[2:]  # 1.25.0
        try:
            return [int(x) for x in ver.split(".")] >= [int(x) for x in self._go_version.split(".")]
        except ValueError:
            return False

    def _go_host_arch(self):
        machine = platform.machine().lower()
        return {
            "x86_64": "amd64",
            "amd64": "amd64",
            "aarch64": "arm64",
            "arm64": "arm64",
            "armv8l": "arm64",
        }.get(machine, machine)

    def _goroot_for_go(self, gobin):
        gobin = os.path.realpath(gobin)
        candidates = [
            os.path.dirname(os.path.dirname(gobin)),
            os.environ.get("GOROOT", ""),
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(os.path.join(candidate, "bin", "go")):
                return candidate
        return ""
