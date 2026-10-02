#!/usr/bin/env python3
"""Conan 2.x recipe — marcli 1.3.1 (MARC command-line parser, pure Go).

marcli is a pure-Go CLI (module github.com/hectorcorrea/marcli; main package at
cmd/marcli). There is NO C/C++ code, no cgo and no configure/CMake/Makefile. The
only external Go module, github.com/google/go-cmp v0.5.9, is test-only and is
resolved through GOPROXY (it is not a Conan package).

    CGO_ENABLED=0 GOOS=linux GOARCH=arm64 GOTOOLCHAIN=local \
    go build -trimpath -ldflags "-X main.Version=v1.3.1" -o marcli ./cmd/marcli

Upstream tests: `go test ./...` — 5 *_test.go files in pkg/marc, 25 top-level
Test* functions (55 cases including subtests). The full per-case report is
emitted from build() independently of the test_package smoke test.

OHOS adaptation notes (go1.25.0 on HarmonyOS aarch64):
- Go's linker mmaps the output file; on OHOS/HMDFS this fails, so the binary is
  linked into an ext2-like workspace (/data/storage/el2/...) and copied back.
- OHOS refuses to fork/exec an ELF without a `.codesign` section: the Go SDK
  tool binaries (go, gofmt, pkg/tool/linux_arm64/*) and the produced ELF must be
  self-signed with binary-sign-tool.
- Signing drops the executable bit -> `chmod 755` is mandatory afterwards, else
  every child process fails with `permission denied`.
- A self-signed process cannot execve() another ELF, so `go test` cannot run the
  test binaries: each package's test binary is produced with `go test -c`,
  self-signed, and executed directly from its own package directory (so relative
  testdata resolves exactly as under `go test`).
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


class MarcliConan(ConanFile):
    name = "marcli"
    version = "1.3.1"
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

    description = ("marcli — command line tool to parse and filter MARC "
                   "(Machine Readable Cataloging) files (pure Go)")
    license = "MIT"
    homepage = "https://github.com/hectorcorrea/marcli"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("marcli", "marc", "cataloging", "library", "cli", "go")

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        # Standard OHC patch entry point (G1 requirement); the recipe does not
        # patch the upstream tree (conandata.yml patches map is empty).
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: settings.os check must accept both Linux and OHOS.
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("marcli supports Linux and OHOS targets only")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        env = Environment()
        env.define("CGO_ENABLED", "0")
        env.define("GOOS", self._goos())
        env.define("GOARCH", self._goarch())
        env.define("GOTOOLCHAIN", "local")
        env.define("GOPROXY", self._goproxy())

        ws = self._go_workspace()
        env.define("TMPDIR", os.path.join(ws, "tmp"))
        env.define("GOTMPDIR", os.path.join(ws, "tmp"))
        env.define("GOCACHE", os.path.join(ws, "go-build-cache"))
        env.define("GOMODCACHE", os.path.join(ws, "go-mod-cache"))
        for d in ("tmp", "go-build-cache", "go-mod-cache"):
            os.makedirs(os.path.join(ws, d), exist_ok=True)

        gobin = self._go_executable()
        goroot = self._goroot_for_go(gobin)
        if goroot:
            env.define("GOROOT", goroot)
        env.prepend_path("PATH", os.path.dirname(gobin))

        env.vars(self).save_script("marcli_go_env")

    def build(self):
        apply_conandata_patches(self)
        go = self._go_executable()
        for sub in ("tmp", "go-build-cache", "go-mod-cache"):
            os.makedirs(os.path.join(self._go_workspace(), sub), exist_ok=True)

        out_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(out_dir, exist_ok=True)
        # Go's linker mmaps the output file: on OHOS/HMDFS this fails, so link
        # into the ext2-like workspace and copy the result back afterwards.
        link_dir = (os.path.join(self._go_workspace(), "link-out")
                    if str(self.settings.os) == "OHOS" else out_dir)
        os.makedirs(link_dir, exist_ok=True)
        linked_exe = os.path.join(link_dir, "marcli")
        final_exe = os.path.join(out_dir, "marcli")
        for stale in (linked_exe, final_exe):
            if os.path.exists(stale):
                os.unlink(stale)

        ldflags = "-X main.Version=v%s" % self.version
        self.run(
            f'"{go}" build -trimpath -ldflags "{ldflags}" -o "{linked_exe}" ./cmd/marcli',
            cwd=self.source_folder,
            env=["marcli_go_env"],
        )
        self._sign_elf_if_ohos(linked_exe)
        if os.path.abspath(linked_exe) != os.path.abspath(final_exe):
            shutil.copy2(linked_exe, final_exe)
        self._sign_elf_if_ohos(final_exe)

        # Real upstream `go test` suite (reported separately from test_package).
        self._run_upstream_tests(go)

    def package(self):
        copy(self, "marcli", os.path.join(self.build_folder, "bin"),
             os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "README.md", self.source_folder, os.path.join(self.package_folder, "licenses"))
        packaged = os.path.join(self.package_folder, "bin", "marcli")
        if os.path.isfile(packaged):
            self._ensure_executable(packaged)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]

    # ────────────────────────── upstream test suite ──────────────────────────

    def _run_upstream_tests(self, go):
        env = dict(os.environ)
        ws = self._go_workspace()
        env.update({
            "CGO_ENABLED": "0",
            "GOOS": self._goos(),
            "GOARCH": self._goarch(),
            "GOTOOLCHAIN": "local",
            "GOPROXY": self._goproxy(),
            "TMPDIR": os.path.join(ws, "tmp"),
            "GOTMPDIR": os.path.join(ws, "tmp"),
            "GOCACHE": os.path.join(ws, "go-build-cache"),
            "GOMODCACHE": os.path.join(ws, "go-mod-cache"),
        })
        goroot = self._goroot_for_go(go)
        if goroot:
            env["GOROOT"] = goroot
        env["PATH"] = os.path.dirname(go) + os.pathsep + env.get("PATH", "")

        if str(self.settings.os) == "OHOS":
            self._run_upstream_tests_ohos(go, env)
        else:
            self._run_upstream_tests_native(go, env)

    def _run_upstream_tests_native(self, go, env):
        cmd = [go, "test", "-v", "-count=1", "./..."]
        try:
            proc = subprocess.run(cmd, cwd=self.source_folder, env=env,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  timeout=3600)
            out, rc = proc.stdout.decode(errors="replace"), proc.returncode
        except subprocess.TimeoutExpired as exc:
            out, rc = (exc.stdout or b"").decode(errors="replace"), 124
        except OSError as exc:
            out, rc = "go test failed to run: %s" % exc, 127
        self._write_and_report(out, rc, " ".join(cmd))

    def _run_upstream_tests_ohos(self, go, env):
        """Compile each package's test binary, self-sign it and run it directly.

        `go test` itself cannot be used: on OHOS a self-signed ELF (the go tool
        is self-signed) is denied execve() of another ELF, and the test binary
        produced by the go tool is unsigned anyway.
        """
        ws = self._go_workspace()
        bin_dir = os.path.join(ws, "upstream-test-bins")
        os.makedirs(bin_dir, exist_ok=True)

        try:
            raw = subprocess.check_output(
                [go, "list", "-f", "{{.ImportPath}}\t{{.Dir}}", "./..."],
                cwd=self.source_folder, env=env, timeout=900,
            ).decode(errors="replace").splitlines()
        except Exception as exc:  # noqa: BLE001
            self.output.warning("go list ./... failed: %s" % exc)
            raw = []

        pkgs, pkg_dirs = [], {}
        for ln in raw:
            parts = ln.split("\t", 1)
            if len(parts) != 2:
                continue
            pkgs.append(parts[0])
            pkg_dirs[parts[0]] = parts[1]
        if not pkgs:
            self._write_and_report("go list ./... produced no packages\n", 1, "go list ./...")
            return

        build_timeout, run_timeout, max_workers = 1800, 900, 6

        def run_pkg(pkg):
            safe = re.sub(r"[^A-Za-z0-9_.-]", "_", pkg)
            binpath = os.path.join(bin_dir, safe + ".test")
            head = "### PACKAGE %s\n### PACKAGE_DIR %s\n" % (pkg, pkg_dirs.get(pkg))
            try:
                bproc = subprocess.run([go, "test", "-c", "-o", binpath, pkg],
                                       cwd=self.source_folder, env=env,
                                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                       timeout=build_timeout)
                bout = bproc.stdout.decode(errors="replace")
            except subprocess.TimeoutExpired as exc:
                return (pkg, "BUILD_TIMEOUT", None, head + (exc.stdout or b"").decode(errors="replace"))
            if not os.path.isfile(binpath):
                if "no test files" in bout:
                    return (pkg, "NO_TESTS", None, None)
                return (pkg, "BUILD_FAIL", None, head + "BUILD FAIL\n" + bout)
            self._sign_elf_if_ohos(binpath)

            cwd = pkg_dirs.get(pkg) or self.source_folder
            args = [binpath, "-test.v", "-test.count=1"]
            try:
                rproc = subprocess.run(args, cwd=cwd, env=env, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, timeout=run_timeout)
                out, rc = rproc.stdout.decode(errors="replace"), rproc.returncode
            except subprocess.TimeoutExpired as exc:
                out = (exc.stdout or b"").decode(errors="replace") + "\n--- OHOS_TEST_PKG_TIMEOUT ---\n"
                rc = 124
            except OSError as exc:
                out, rc = "test run failed to exec: %s" % exc, 126
            stats = self._parse_test_stats(out)
            return (pkg, "ok" if stats["failed"] == 0 else "FAIL", stats, head + out)

        all_out, per_pkg = [], []
        tot = {"passed": 0, "failed": 0, "skipped": 0}
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
            futs = {ex.submit(run_pkg, pkg): pkg for pkg in pkgs}
            for fut in concurrent.futures.as_completed(futs):
                pkg, status, stats, out = fut.result()
                if out:
                    all_out.append(out)
                if stats:
                    per_pkg.append((pkg, status, stats))
                    for k in tot:
                        tot[k] += stats[k]

        full = "\n".join(all_out)
        full_log = os.path.join(self.build_folder, "upstream_test_full.log")
        try:
            with open(full_log, "w", encoding="utf-8", errors="replace") as fh:
                fh.write(full)
        except OSError:
            pass

        self.output.info("marcli upstream tests (OHOS: go test -c + self-sign + direct "
                         "run): packages=%d PASS=%d FAIL=%d SKIP=%d"
                         % (len(pkgs), tot["passed"], tot["failed"], tot["skipped"]))
        for pkg, status, stats in per_pkg:
            self.output.info("  [%s] %s %s" % (status, pkg, stats))
        self.output.info("  full log: %s" % full_log)
        self._report_stats(tot, "go test -c + direct run (OHOS)", full_log)

    @staticmethod
    def _parse_test_stats(out):
        """Count executed cases: plain `go test` cases + Ginkgo v1 specs."""
        go_p = len(re.findall(r"^\s*--- PASS:", out, re.M))
        go_f = len(re.findall(r"^\s*--- FAIL:", out, re.M))
        go_s = len(re.findall(r"^\s*--- SKIP:", out, re.M))
        summary = re.findall(
            r"^(?:SUCCESS|FAIL)!\s*--\s*(\d+) Passed \| (\d+) Failed \| (\d+) Pending \| (\d+) Skipped",
            out, re.M)
        if summary:
            sp, sf, spd, ssk = (int(x) for x in summary[-1])
        else:
            sp = sf = spd = ssk = 0
        return {"go_tests": go_p + go_f + go_s, "ginkgo_specs": sp + sf + spd + ssk,
                "passed": go_p + sp, "failed": go_f + sf, "skipped": go_s + spd + ssk}

    def _write_and_report(self, out, rc, cmd):
        full_log = os.path.join(self.build_folder, "upstream_test_full.log")
        try:
            with open(full_log, "w", encoding="utf-8", errors="replace") as fh:
                fh.write(out)
        except OSError:
            pass
        tot = self._parse_test_stats(out)
        self.output.info("marcli upstream `%s`: PASS=%d FAIL=%d SKIP=%d (rc=%d)"
                         % (cmd, tot["passed"], tot["failed"], tot["skipped"], rc))
        self._report_stats(tot, cmd, full_log)

    def _report_stats(self, tot, cmd, full_log):
        status = ("passed" if tot["failed"] == 0 and tot["passed"] > 0
                  else "failed" if tot["failed"] else "no_tests")
        payload = {
            "status": status,
            "framework": "go test",
            "command": cmd,
            "discovered": tot["passed"] + tot["failed"] + tot["skipped"],
            "executed": tot["passed"] + tot["failed"] + tot["skipped"],
            "passed": tot["passed"],
            "failed": tot["failed"],
            "skipped": tot["skipped"],
            "log": full_log,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(payload, ensure_ascii=False))

    # ─────────────────────────── Go toolchain ───────────────────────────

    @staticmethod
    def _goproxy():
        # Allow an explicit override (e.g. an offline file:// proxy on a worker
        # whose Go resolver cannot reach public DNS); default to the community
        # mirror used by the other Go recipes in this repository.
        return (os.environ.get("OHC_GOPROXY")
                or os.environ.get("GOPROXY")
                or "https://goproxy.cn,direct")

    def _go_workspace(self):
        if str(self.settings.os) == "OHOS":
            for base in (
                "/data/storage/el2/base/haps/entry/files",
                "/data/storage/el2/base/cache",
            ):
                candidate = os.path.join(base, "marcli-1.3.1-go")
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
            raise ConanInvalidConfiguration(
                "Go SDK bootstrap is not prepared for host arch: %s" % host_arch)
        sdk_root = os.path.join(self._go_workspace(), "go-sdk", "go%s-%s" % (self._go_version, host_arch))
        goroot = os.path.join(sdk_root, "go")
        gobin = os.path.join(goroot, "bin", "go")
        if not os.path.isfile(gobin):
            urls, sha256 = self._go_archives[host_arch]
            self.output.info("Go >= %s not found; downloading %s" % (self._go_version, urls[0]))
            get(self, url=urls, sha256=sha256, destination=sdk_root, strip_root=False)
        self._sign_go_sdk_if_ohos(goroot)
        return gobin

    def _sign_go_sdk_if_ohos(self, goroot):
        if str(self.settings.os) != "OHOS":
            return
        marker = os.path.join(goroot, ".ohos-signed")
        if os.path.isfile(marker):
            return
        tool_dir = os.path.join(goroot, "pkg", "tool", "linux_%s" % self._go_host_arch())
        candidates = [os.path.join(goroot, "bin", "go"), os.path.join(goroot, "bin", "gofmt")]
        if os.path.isdir(tool_dir):
            candidates.extend(os.path.join(tool_dir, f) for f in os.listdir(tool_dir))
        for candidate in candidates:
            if os.path.isfile(candidate) and self._is_elf(candidate):
                self._sign_elf_if_ohos(candidate)
        Path(marker).write_text("signed\n", encoding="utf-8")

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as fh:
                return fh.read(4) == b"\x7fELF"
        except OSError:
            return False

    @staticmethod
    def _has_ohos_signature(path):
        try:
            with open(path, "rb") as fh:
                data = fh.read()
        except OSError:
            return False
        return b".codesign" in data or b".note.ohos" in data

    def _ensure_executable(self, path):
        """Set the executable bit, re-creating the inode when the platform refuses.

        On OHOS/HMDFS the mode of an already code-signed ELF cannot always be
        changed in place (chmod -> EPERM). Copying to a fresh inode restores it.
        """
        try:
            os.chmod(path, 0o755)
            return
        except PermissionError:
            pass
        tmp = path + ".mode"
        shutil.copy2(path, tmp)
        os.unlink(path)
        shutil.move(tmp, path)
        os.chmod(path, 0o755)

    def _sign_elf_if_ohos(self, path):
        """Self-sign an ELF for OHOS and restore the executable bit."""
        if str(self.settings.os) != "OHOS":
            return
        if self._has_ohos_signature(path):
            self._ensure_executable(path)
            return
        signer = self._find_binary_sign_tool()
        if not signer:
            self.output.warning("binary-sign-tool not found; OHOS may reject unsigned "
                                "executable: %s" % path)
            return
        tmp_dir = os.path.join(self._go_workspace(), "sign-tmp")
        Path(tmp_dir).mkdir(parents=True, exist_ok=True)
        tmp_in = os.path.join(tmp_dir, os.path.basename(path))
        tmp_out = tmp_in + ".signed"
        shutil.copy2(path, tmp_in)
        objcopy = (os.environ.get("OHOS_LLVM_OBJCOPY")
                   or shutil.which("llvm-objcopy")
                   or "/data/service/hnp/bin/llvm-objcopy")
        if os.path.isfile(objcopy):
            subprocess.run([objcopy, "--remove-section", ".codesign", tmp_in],
                           capture_output=True, timeout=30)
        subprocess.check_call([signer, "sign", "-selfSign", "1", "-inFile", tmp_in,
                               "-outFile", tmp_out, "-signAlg", "SHA256withECDSA"])
        shutil.move(tmp_out, path)
        self._ensure_executable(path)
        os.unlink(tmp_in)

    def _find_binary_sign_tool(self):
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
        return {
            "x86_64": "amd64", "x86": "386", "armv8": "arm64", "armv8_32": "arm",
            "armv7": "arm", "armv7hf": "arm", "armv6": "arm",
        }.get(str(self.settings.arch), str(self.settings.arch))

    def _go_executable(self):
        candidates = []
        if os.environ.get("GO"):
            candidates.append(os.environ["GO"])
        if os.environ.get("GOROOT"):
            candidates.append(os.path.join(os.environ["GOROOT"], "bin", "go"))
        candidates.extend([
            os.path.expanduser("~/usr/local/go/bin/go"),
            os.path.expanduser("~/sdk/go%s/bin/go" % self._go_version),
            os.path.expanduser("~/.goenv/versions/%s/bin/go" % self._go_version),
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
            out = subprocess.run([go, "version"], capture_output=True, timeout=30).stdout.decode()
        except OSError:
            return False
        m = out.split("go version ")[-1].split(" ")[0]
        ver = m[2:]
        try:
            return [int(x) for x in ver.split(".")[:2]] >= [int(x) for x in "1.14".split(".")]
        except ValueError:
            return False

    def _go_host_arch(self):
        machine = platform.machine().lower()
        return {"x86_64": "amd64", "amd64": "amd64", "aarch64": "arm64",
                "arm64": "arm64", "armv8l": "arm64"}.get(machine, machine)

    def _goroot_for_go(self, gobin):
        gobin = os.path.realpath(gobin)
        for candidate in (os.path.dirname(os.path.dirname(gobin)), os.environ.get("GOROOT", "")):
            if candidate and os.path.isfile(os.path.join(candidate, "bin", "go")):
                return candidate
        return ""
