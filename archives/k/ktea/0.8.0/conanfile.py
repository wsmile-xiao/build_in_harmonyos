#!/usr/bin/env python3
"""Conan recipe - ktea 0.8.0 (Go)

ktea is a Kafka TUI (terminal user interface) client built on bubbletea.
Pure-Go CLI, no cgo. Upstream has NO vendor/ directory, so the module
closure (incl. the huge docker/containerd/k8s indirect tail pulled by
testcontainers) is fetched through GOPROXY (goproxy.cn) during build;
GOTOOLCHAIN=local pins the bootstrapped Go 1.26.5 SDK.

The binary has no --version flag (only -debug / -plain-fonts); version is
the package-level `var version string` in cmd/ktea, injected via
-ldflags -X main.version=v0.8.0 (upstream goreleaser does the same).

Upstream tests: 29 packages with *_test.go. kadmin (17 top-level + TestMain)
and sradmin (4 top-level + TestMain) start Docker-backed testcontainers
(Kafka / Schema-Registry compose) in TestMain - no Docker on OHOS, so they
are compile-only proven (go test -c) and their 23 Test funcs are recorded
as blocked in notes.md. The remaining 27 packages (49 top-level Test funcs)
are compiled to test-out, signed, copied back to the package source dir and
run with -test.v -test.count=1.
"""

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


class KteaConan(ConanFile):
    name = "ktea"
    version = "0.8.0"
    description = "A Kafka TUI (terminal user interface) client built with bubbletea"
    license = "Apache-2.0"
    homepage = "https://github.com/jonas-grgt/ktea"
    url = "https://github.com/jonas-grgt/ktea"
    topics = ("kafka", "tui", "bubbletea", "cli", "go")
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # go.mod declares `go 1.25.4`; the bootstrapped SDK 1.26.5 satisfies it.
    _go_version = "1.26.5"
    _go_archives = {
        "arm64": (
            [
                "https://golang.google.cn/dl/go1.26.5.linux-arm64.tar.gz",
                "https://dl.google.com/go/go1.26.5.linux-arm64.tar.gz",
            ],
            "fe4789e92b1f33358680864bbe8704289e7bb5fc207d80623c308935bd696d49",
        ),
        "amd64": (
            [
                "https://dl.google.com/go/go1.26.5.linux-amd64.tar.gz",
                "https://golang.google.cn/dl/go1.26.5.linux-amd64.tar.gz",
            ],
            "5c2c3b16caefa1d968a94c1daca04a7ca301a496d9b086e17ad77bb81393f053",
        ),
    }
    # 27 packages with *_test.go that run headless (pure model/Update/View
    # unit tests with in-memory mocks, no TTY, no Docker, no network).
    _upstream_test_packages = (
        "./cmd/ktea",
        "./config",
        "./kcadmin",
        "./serdes",
        "./ui/components/border",
        "./ui/components/chips",
        "./ui/components/cmdbar",
        "./ui/components/notifier",
        "./ui/components/statusbar",
        "./ui/components/tab",
        "./ui/pages/cgroups_page",
        "./ui/pages/cgroups_topics_page",
        "./ui/pages/configs_page",
        "./ui/pages/consume_form_page",
        "./ui/pages/consume_page",
        "./ui/pages/create_cluster_page",
        "./ui/pages/create_schema_page",
        "./ui/pages/create_topic_page",
        "./ui/pages/kcon_clusters_page",
        "./ui/pages/kcon_page",
        "./ui/pages/publish_page",
        "./ui/pages/record_details_page",
        "./ui/pages/schema_details_page",
        "./ui/pages/subjects_page",
        "./ui/pages/topics_page",
        "./ui/tabs/cgroups_tab",
        "./ui/tabs/clusters_tab",
    )
    # kadmin (17 Test + TestMain) and sradmin (4 Test + TestMain): their
    # TestMain boots Docker-backed testcontainers (Kafka / Schema-Registry
    # compose) which cannot run on OHOS (no Docker). Proven by go test -c
    # compile only; the 23 Test funcs are reported as blocked (see notes.md).
    _upstream_blocked_packages = ("./kadmin", "./sradmin")
    _upstream_blocked_total = 23

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("ktea is prepared for Linux/OHOS targets only")

    def generate(self):
        env = Environment()
        env.define("CGO_ENABLED", "0")
        env.define("GOOS", self._goos())
        env.define("GOARCH", self._goarch())
        env.define("GOTOOLCHAIN", "local")
        env.define("GOFLAGS", "-mod=mod")
        env.define("GOPROXY", "https://goproxy.cn,direct")
        env.define("GOSUMDB", "sum.golang.google.cn")

        workspace = self._go_workspace()
        env.define("TMPDIR", os.path.join(workspace, "tmp"))
        env.define("GOTMPDIR", os.path.join(workspace, "tmp"))
        env.define("GOCACHE", os.path.join(workspace, "go-build-cache"))
        env.define("GOMODCACHE", os.path.join(workspace, "go-mod-cache"))

        go = self._go_executable()
        goroot = self._goroot_for_go(go)
        if goroot:
            env.define("GOROOT", goroot)
        env.prepend_path("PATH", os.path.dirname(go))
        env.vars(self).save_script("ktea_go_env")

    def build(self):
        apply_conandata_patches(self)
        go = self._go_executable()
        self._check_go_version(go)

        env = self._go_env_dict(go)

        # No vendor/ upstream: fetch the module closure once through GOPROXY.
        self._subprocess_run(
            [go, "mod", "download"],
            env, self.source_folder,
            os.path.join(self.build_folder, "go-mod-download.log"),
        )

        out_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(out_dir, exist_ok=True)
        if str(self.settings.os) == "OHOS":
            link_out_dir = os.path.join(self._go_workspace(), "link-out")
        else:
            link_out_dir = out_dir
        os.makedirs(link_out_dir, exist_ok=True)
        linked_exe = os.path.join(link_out_dir, "ktea")
        final_exe = os.path.join(out_dir, "ktea")

        # Single-pass build: link into the writable go-workspace (HMDFS mmap
        # restriction, E124/E134/E166), sign, then copy into the package dir.
        # go build skips writing when the output is up-to-date, so remove any
        # stale target first: a pre-existing signed ELF (from a previous run)
        # would otherwise be left untouched and its mode is pinned by hmfs
        # (chmod on a signed ELF raises EPERM, E077).
        if os.path.exists(linked_exe):
            os.remove(linked_exe)
        self._subprocess_run(
            [
                go, "build", "-trimpath", "-mod=mod",
                "-ldflags", self._go_ldflags(),
                "-o", linked_exe, "./cmd/ktea",
            ],
            env, self.source_folder,
        )
        self._sign_elf_if_ohos(linked_exe)
        if os.path.abspath(linked_exe) != os.path.abspath(final_exe):
            shutil.copy2(linked_exe, final_exe)

        self._run_upstream_tests(go)

    def package(self):
        copy(self, "ktea", os.path.join(self.build_folder, "bin"),
             os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "README.md", self.source_folder, os.path.join(self.package_folder, "res"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]

    # --- version injection (upstream goreleaser parity) ------------------
    @staticmethod
    def _go_ldflags():
        # cmd/ktea declares `var version string` (package main); upstream
        # goreleaser injects it via -X main.version. No --version flag exists.
        return "-s -w" " -X main.version=v0.8.0"

    # --- upstream tests ---------------------------------------------------
    def _run_upstream_tests(self, go):
        env = self._go_env_dict(go)
        log_path = os.path.join(self.build_folder, "upstream-go-test.log")
        if os.path.exists(log_path):
            os.remove(log_path)

        command = "go test -mod=mod -c <each pkg> + run signed test binaries -test.v"

        if str(self.settings.os) == "OHOS":
            test_out_dir = os.path.join(self._go_workspace(), "test-out")
            os.makedirs(test_out_dir, exist_ok=True)
            total = {"discovered": 0, "executed": 0, "passed": 0, "failed": 0, "skipped": 0}

            # Compile-only proof for the blocked Docker-backed packages
            # (kadmin/sradmin TestMain start testcontainers -> never run here).
            for package in self._upstream_blocked_packages:
                safe = self._pkg_safe(package)
                test_bin = os.path.join(test_out_dir, safe + ".test")
                if os.path.exists(test_bin):
                    os.remove(test_bin)  # stale signed binary would be skipped by go test -c
                self._subprocess_run(
                    [go, "test", "-mod=mod", "-c", "-o", test_bin, package],
                    env, self.source_folder, log_path,
                )
                self._sign_elf_if_ohos(test_bin)
                print(
                    "HMBS_GO_TEST_PKG=%s compile-only (blocked: TestMain needs Docker testcontainers, 23 tests total)" % package,
                    flush=True,
                )

            for package in self._upstream_test_packages:
                safe = self._pkg_safe(package)
                test_bin = os.path.join(test_out_dir, safe + ".test")
                if os.path.exists(test_bin):
                    os.remove(test_bin)  # stale signed binary would be skipped by go test -c
                self._subprocess_run(
                    [go, "test", "-mod=mod", "-c", "-o", test_bin, package],
                    env, self.source_folder, log_path,
                )
                self._sign_elf_if_ohos(test_bin)
                pkg_dir = self.source_folder if package == "." else os.path.join(self.source_folder, package[2:])
                pkg_log = os.path.join(test_out_dir, safe + ".log")
                # -test.count=1 disables result caching; run from the package
                # source dir so relative YAML fixture paths resolve (E318).
                self._subprocess_run([test_bin, "-test.v", "-test.count=1"], env, pkg_dir, log_path, pkg_log)
                counts = self._parse_go_test_log(pkg_log)
                for key in total:
                    total[key] += counts[key]
                print(
                    "HMBS_GO_TEST_PKG=%s discovered=%d passed=%d failed=%d skipped=%d"
                    % (package, counts["discovered"], counts["passed"], counts["failed"], counts["skipped"]),
                    flush=True,
                )
            discovered = total["discovered"]
            executed = discovered
            passed = total["passed"]
            failed = total["failed"]
            skipped = total["skipped"]
        else:
            command = "go test -mod=mod -v ./..."
            self._subprocess_run(
                [go, "test", "-mod=mod", "-v", "./..."],
                env, self.source_folder, log_path,
            )
            counts = self._parse_go_test_log(log_path)
            discovered = counts["discovered"]
            executed = counts["executed"]
            passed = counts["passed"]
            failed = counts["failed"]
            skipped = counts["skipped"]

        status = "passed"
        if executed == 0 or failed > 0:
            status = "failed"
        marker = {
            "status": status,
            "framework": "go test",
            "command": command,
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "blocked": self._upstream_blocked_total,
            "blocked_reason": "kadmin(17 Test+TestMain)+sradmin(4 Test+TestMain): TestMain starts Docker testcontainers (Kafka/Schema-Registry); no Docker on OHOS - compile-only proven",
        }
        line = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker)
        print(line, flush=True)
        self.output.info(line)
        if status != "passed":
            raise ConanException("ktea upstream go tests failed: %s" % line)

    @staticmethod
    def _pkg_safe(package):
        if package == ".":
            return "root"
        return package.lstrip("./").replace("/", "_")

    @staticmethod
    def _parse_go_test_log(log_path):
        passed = failed = skipped = 0
        with open(log_path, "r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                stripped = line.strip()
                if stripped.startswith("--- PASS:"):
                    passed += 1
                elif stripped.startswith("--- FAIL:"):
                    failed += 1
                elif stripped.startswith("--- SKIP:"):
                    skipped += 1
        discovered = passed + failed + skipped
        return {"discovered": discovered, "executed": discovered, "passed": passed, "failed": failed, "skipped": skipped}

    def _subprocess_run(self, args, env, cwd, log_path=None, tee_path=None):
        proc = subprocess.run(args, env=env, cwd=cwd, capture_output=True, text=True)
        output = (proc.stdout or "") + (proc.stderr or "")
        for path in (log_path, tee_path):
            if path:
                with open(path, "a", encoding="utf-8") as handle:
                    handle.write("$ %s\n" % " ".join(args))
                    handle.write(output)
                    if not output.endswith("\n"):
                        handle.write("\n")
        if output:
            print(output, flush=True)
        if proc.returncode != 0:
            raise ConanException(
                "command failed (%s): %s" % (proc.returncode, " ".join(args))
            )

    # --- go toolchain -----------------------------------------------------
    def _go_env_dict(self, go):
        workspace = self._go_workspace()
        env = dict(os.environ)
        env["CGO_ENABLED"] = "0"
        env["GOOS"] = self._goos()
        env["GOARCH"] = self._goarch()
        env["GOTOOLCHAIN"] = "local"
        env["GOFLAGS"] = "-mod=mod"
        env["GOPROXY"] = os.environ.get("GOPROXY", "https://goproxy.cn,direct")
        env["GOSUMDB"] = os.environ.get("GOSUMDB", "sum.golang.google.cn")
        env["TMPDIR"] = os.path.join(workspace, "tmp")
        env["GOTMPDIR"] = os.path.join(workspace, "tmp")
        env["GOCACHE"] = os.path.join(workspace, "go-build-cache")
        env["GOMODCACHE"] = os.path.join(workspace, "go-mod-cache")
        goroot = self._goroot_for_go(go)
        if goroot:
            env["GOROOT"] = goroot
        env["PATH"] = os.path.dirname(go) + os.pathsep + env.get("PATH", "")
        return env

    def _go_workspace(self):
        if str(self.settings.os) == "OHOS":
            root = os.environ.get(
                "OHOS_GO_WORKDIR",
                "/data/storage/el2/base/haps/entry/files/ktea-conan-go",
            )
        else:
            root = os.path.join(self.build_folder, ".go-work")
        workspace = os.path.join(root, self.version)
        for child in ("tmp", "go-build-cache", "go-mod-cache", "link-out", "test-out", "go-sdk"):
            Path(workspace, child).mkdir(parents=True, exist_ok=True)
        return workspace

    def _ensure_go_toolchain(self):
        host_arch = self._go_host_arch()
        if host_arch not in self._go_archives:
            raise ConanInvalidConfiguration(
                "Go SDK bootstrap is not prepared for host arch: %s" % host_arch
            )
        sdk_root = os.path.join(self._go_workspace(), "go-sdk", "go%s-%s" % (self._go_version, host_arch))
        goroot = os.path.join(sdk_root, "go")
        gobin = os.path.join(goroot, "bin", "go")
        if not os.path.isfile(gobin):
            urls, sha256 = self._go_archives[host_arch]
            self.output.info("Go %s not found; downloading %s" % (self._go_version, urls[0]))
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
            candidates.extend(os.path.join(tool_dir, name) for name in os.listdir(tool_dir))
        for candidate in candidates:
            if os.path.isfile(candidate) and self._is_elf(candidate):
                self._sign_elf_if_ohos(candidate)
        Path(marker).write_text("signed\n", encoding="utf-8")

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    @staticmethod
    def _has_ohos_signature(path):
        try:
            with open(path, "rb") as handle:
                data = handle.read()
        except OSError:
            return False
        return b".codesign" in data or b".note.ohos" in data

    def _sign_elf_if_ohos(self, path):
        if str(self.settings.os) != "OHOS":
            return
        if not self._has_ohos_signature(path):
            signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
            if not os.path.isfile(signer):
                raise ConanInvalidConfiguration("binary-sign-tool is required to sign OHOS Go executables")
            signed = "%s.signed" % path
            subprocess.check_call(
                [signer, "sign", "-selfSign", "1", "-inFile", path,
                 "-outFile", signed, "-signAlg", "SHA256withECDSA"]
            )
            shutil.move(signed, path)
        # hmfs pins a signed ELF's mode (chmod -> EPERM after signing, E077);
        # the fresh go output is already 775/755, so this is best-effort only.
        try:
            os.chmod(path, 0o755)
        except OSError:
            pass

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
            os.path.expanduser("~/sdk/go%s/bin/go" % self._go_version),
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
            output = subprocess.run([go, "version"], capture_output=True, timeout=30).stdout.decode()
        except OSError:
            return False
        match = re.search(r"go(\d+)\.(\d+)", output)
        if not match:
            return False
        required = [int(x) for x in self._go_version.split(".")[:2]]
        current = [int(match.group(1)), int(match.group(2))]
        return current >= required

    def _check_go_version(self, go):
        output = subprocess.check_output([go, "version"], text=True).strip()
        self.output.info(output)
        match = re.search(r"go(\d+)\.(\d+)", output)
        if not match:
            raise ConanInvalidConfiguration("Unable to parse Go version from: %s" % output)
        required = [int(x) for x in self._go_version.split(".")[:2]]
        if [int(match.group(1)), int(match.group(2))] < required:
            raise ConanInvalidConfiguration(
                "ktea 0.8.0 requires Go >= %s (go.mod declares 1.25.4), got: %s" % (self._go_version, output)
            )

    @staticmethod
    def _goroot_for_go(go):
        resolved = Path(go).resolve()
        goroot = resolved.parent.parent
        if resolved.parent.name == "bin" and (goroot / "pkg").is_dir():
            return str(goroot)
        return None

    @staticmethod
    def _go_host_arch():
        machine = platform.machine().lower()
        return {
            "x86_64": "amd64",
            "amd64": "amd64",
            "aarch64": "arm64",
            "arm64": "arm64",
            "armv8l": "arm64",
        }.get(machine, machine)
