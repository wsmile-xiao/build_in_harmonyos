#!/usr/bin/env python3
"""Conan recipe - kubeconform 0.7.0 (Go)

Kubeconform is a FAST Kubernetes manifests validator with support for
Custom Resources. Pure-Go CLI, built with the vendored module cache
(-mod=vendor), no CGO, no network access required at build time.
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


class KubeconformConan(ConanFile):
    name = "kubeconform"
    version = "0.7.0"
    description = "A FAST Kubernetes manifests validator, with support for Custom Resources"
    license = "Apache-2.0"
    homepage = "https://github.com/yannh/kubeconform"
    url = "https://github.com/yannh/kubeconform"
    topics = ("kubernetes", "validation", "manifest", "cli", "go")
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    _go_version = "1.24.0"
    _go_archives = {
        "amd64": (
            [
                "https://golang.google.cn/dl/go1.24.0.linux-amd64.tar.gz",
                "https://dl.google.com/go/go1.24.0.linux-amd64.tar.gz",
            ],
            "dea9ca38a0b852a74e81c26134671af7c0fbe65d81b0dc1c5bfe22cf7d4c8858",
        ),
        "arm64": (
            [
                "https://golang.google.cn/dl/go1.24.0.linux-arm64.tar.gz",
                "https://dl.google.com/go/go1.24.0.linux-arm64.tar.gz",
            ],
            "c3fa6d16ffa261091a5617145553c71d21435ce547e44cc6dfb7470865527cc7",
        ),
    }
    # Go test packages at v0.7.0 (12 _test.go files, 20 top-level Test funcs).
    # acceptance.bats / acceptance-nonetwork.bats need docker + bats + network
    # schemas, so they are documented in notes.md and not executed here.
    _upstream_test_packages = (
        "./pkg/config",
        "./pkg/loader",
        "./pkg/output",
        "./pkg/registry",
        "./pkg/resource",
        "./pkg/validator",
    )

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("kubeconform is prepared for Linux/OHOS targets only")

    def generate(self):
        env = Environment()
        env.define("CGO_ENABLED", "0")
        env.define("GOOS", self._goos())
        env.define("GOARCH", self._goarch())
        env.define("GOTOOLCHAIN", "local")
        env.define("GOFLAGS", "-mod=vendor")
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
        env.vars(self).save_script("kubeconform_go_env")

    def build(self):
        apply_conandata_patches(self)
        go = self._go_executable()
        self._check_go_version(go)

        self._run_upstream_tests(go)

        out_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(out_dir, exist_ok=True)
        if str(self.settings.os) == "OHOS":
            link_out_dir = os.path.join(self._go_workspace(), "link-out")
        else:
            link_out_dir = out_dir
        os.makedirs(link_out_dir, exist_ok=True)
        linked_exe = os.path.join(link_out_dir, "kubeconform")
        final_exe = os.path.join(out_dir, "kubeconform")

        env = self._go_env_dict(go)
        self._subprocess_run(
            [
                go, "build", "-trimpath", "-mod=vendor",
                "-ldflags", "-s -w -X main.version=v0.7.0",
                "-o", linked_exe, "./cmd/kubeconform",
            ],
            env, self.source_folder,
        )
        self._sign_elf_if_ohos(linked_exe)
        if os.path.abspath(linked_exe) != os.path.abspath(final_exe):
            shutil.copy2(linked_exe, final_exe)

    def package(self):
        copy(self, "kubeconform", os.path.join(self.build_folder, "bin"),
             os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "Readme.md", self.source_folder, os.path.join(self.package_folder, "res"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]

    # --- upstream tests -------------------------------------------------
    def _run_upstream_tests(self, go):
        env = self._go_env_dict(go)
        log_path = os.path.join(self.build_folder, "upstream-go-test.log")
        if os.path.exists(log_path):
            os.remove(log_path)

        if str(self.settings.os) == "OHOS":
            test_out_dir = os.path.join(self._go_workspace(), "test-out")
            os.makedirs(test_out_dir, exist_ok=True)
            for package in self._upstream_test_packages:
                safe = package.lstrip("./").replace("/", "_")
                test_bin = os.path.join(test_out_dir, safe + ".test")
                self._subprocess_run(
                    [go, "test", "-mod=vendor", "-c", "-o", test_bin, package],
                    env, self.source_folder, log_path,
                )
                self._sign_elf_if_ohos(test_bin)
                pkg_dir = os.path.join(self.source_folder, package.lstrip("./"))
                self._subprocess_run([test_bin, "-test.v"], env, pkg_dir, log_path)
            command = "go test -mod=vendor -c <each pkg> + run signed test binaries -test.v"
        else:
            self._subprocess_run(
                [go, "test", "-mod=vendor", "-v", "./..."],
                env, self.source_folder, log_path,
            )
            command = "go test -mod=vendor -v ./..."

        discovered, executed, passed, failed, skipped = self._parse_go_test_log(log_path)
        status = "passed"
        if executed == 0 or failed > 0 or skipped > 0 or executed != discovered:
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
        }
        line = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker)
        print(line, flush=True)
        self.output.info(line)
        if status != "passed":
            raise ConanException("kubeconform upstream go tests failed: %s" % line)

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
        return discovered, discovered, passed, failed, skipped

    def _subprocess_run(self, args, env, cwd, log_path=None):
        proc = subprocess.run(args, env=env, cwd=cwd, capture_output=True, text=True)
        output = (proc.stdout or "") + (proc.stderr or "")
        if log_path:
            with open(log_path, "a", encoding="utf-8") as handle:
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

    # --- go toolchain ----------------------------------------------------
    def _go_env_dict(self, go):
        workspace = self._go_workspace()
        env = dict(os.environ)
        env["CGO_ENABLED"] = "0"
        env["GOOS"] = self._goos()
        env["GOARCH"] = self._goarch()
        env["GOTOOLCHAIN"] = "local"
        env["GOFLAGS"] = "-mod=vendor"
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
                "/data/storage/el2/base/haps/entry/files/kubeconform-conan-go",
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
        if self._has_ohos_signature(path):
            os.chmod(path, 0o755)
            return
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            raise ConanInvalidConfiguration("binary-sign-tool is required to sign OHOS Go executables")
        signed = "%s.signed" % path
        subprocess.check_call(
            [signer, "sign", "-selfSign", "1", "-inFile", path,
             "-outFile", signed, "-signAlg", "SHA256withECDSA"]
        )
        shutil.move(signed, path)
        os.chmod(path, 0o755)

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
                "kubeconform 0.7.0 requires Go >= %s, got: %s" % (self._go_version, output)
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
