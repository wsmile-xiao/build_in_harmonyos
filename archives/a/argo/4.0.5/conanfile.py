#!/usr/bin/env python3
"""Conan 2.x recipe — Argo Workflows CLI 4.0.5

Argo Workflows is a Kubernetes-native workflow engine.
This recipe builds the `argo` CLI binary using the Go toolchain.
The Go SDK is auto-downloaded if not found on the build machine.

Build system: Go (custom)
Output: single static binary (argo)
"""
import hashlib
import os
import platform
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


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


class ArgoConan(ConanFile):
    name = "argo"
    version = "4.0.5"
    description = "Argo Workflows CLI — Kubernetes-native workflow engine command-line tool"
    license = "Apache-2.0"
    homepage = "https://github.com/argoproj/argo-workflows"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: settings.os check must use in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"argo supports Linux and OHOS only, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Use Conan Environment to set Go build variables (R33 compliant)
        work = self._go_workspace()
        env = Environment()
        env.define("CGO_ENABLED", "0")
        env.define("GOOS", "linux")
        env.define("GOARCH", "arm64")
        env.define("GOPROXY", "https://goproxy.cn,direct")
        env.define("GOTOOLCHAIN", "local")
        env.define("TMPDIR", os.path.join(work, "tmp"))
        env.define("GOTMPDIR", os.path.join(work, "tmp"))
        env.define("GOCACHE", os.path.join(work, "go-build-cache"))
        env.define("GOMODCACHE", os.path.join(work, "go-mod-cache"))

        go = self._go_executable()
        goroot = self._goroot_for_go(go)
        if goroot:
            env.define("GOROOT", goroot)
        env.prepend_path("PATH", os.path.dirname(go))

        for d in ("tmp", "go-build-cache", "go-mod-cache"):
            os.makedirs(os.path.join(work, d), exist_ok=True)

        env.vars(self).save_script("argo_go_env")

    def build(self):
        apply_conandata_patches(self)

        # Create UI placeholder for go:embed dist/app
        ui_dist = os.path.join(self.source_folder, "ui", "dist", "app")
        os.makedirs(ui_dist, exist_ok=True)
        if not os.path.exists(os.path.join(ui_dist, "index.html")):
            with open(os.path.join(ui_dist, "index.html"), "w") as f:
                f.write("<!DOCTYPE html><html><head><title>Argo</title></head><body>Argo UI placeholder</body></html>")

        go = self._go_executable()

        # Determine output path — use ext2 partition for OHOS (Go linker mmap)
        work = self._go_workspace()
        output_path = os.path.join(work, "link-out", "argo")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Download Go modules
        self.run(f'"{go}" mod download', env=["conanbuild", "argo_go_env"], cwd=self.source_folder)

        # Build argo CLI binary
        ldflags = (
            "-s -w "
            "-X github.com/argoproj/argo-workflows/v4.version=v4.0.5 "
            "-X github.com/argoproj/argo-workflows/v4.buildDate=2026-08-19T00:00:00Z "
            "-X github.com/argoproj/argo-workflows/v4.gitCommit=0ab1452144d8f4d57c50b37ce50dad218868e950 "
            "-X github.com/argoproj/argo-workflows/v4.gitTreeState=clean "
            "-extldflags -static"
        )
        self.run(
            f'"{go}" build -ldflags "{ldflags}" -o "{output_path}" ./cmd/argo',
            env=["conanbuild", "argo_go_env"],
            cwd=self.source_folder,
        )

        # Sign ELF on OHOS
        self._sign_elf_if_ohos(output_path)

        # Copy built binary to build folder for packaging
        final = os.path.join(self.build_folder, "argo")
        if os.path.exists(output_path):
            shutil.copy2(output_path, final)

    def package(self):
        copy(self, "argo", self.build_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        packaged = os.path.join(self.package_folder, "bin", "argo")
        if os.path.isfile(packaged):
            os.chmod(packaged, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []

    # ── Go toolchain management ──

    def _go_workspace(self):
        if str(self.settings.os) == "OHOS":
            for base in _EXT2_CANDIDATES:
                candidate = os.path.join(base, "argo-4.0.5-go")
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
            os.path.expanduser("~/.harmonybrew/bin/go"),
            os.path.expanduser("~/usr/local/go/bin/go"),
            os.path.expanduser("~/sdk/go1.26.3/bin/go"),
            os.path.expanduser("~/sdk/go/bin/go"),
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
            raise ConanInvalidConfiguration(
                "Go bootstrap is only prepared for Linux arm64 workers"
            )
        sdk_root = self._shared_go_sdk_root()
        goroot = os.path.join(sdk_root, f"go{_GO_VERSION}")
        gobin = os.path.join(goroot, "bin", "go")
        if not os.path.isfile(gobin):
            get(self, url=_GO_ARM64_URLS, sha256=_GO_ARM64_SHA256,
                destination=sdk_root, strip_root=False)
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
            signer = os.path.expanduser("~/usr/local/bin/binary-sign-tool")
        if not os.path.isfile(signer):
            raise ConanInvalidConfiguration(
                "binary-sign-tool is required to sign OHOS Go executables"
            )
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

    @staticmethod
    def _host_goarch():
        return {"aarch64": "arm64", "arm64": "arm64", "x86_64": "amd64", "amd64": "amd64"}.get(
            platform.machine().lower(), platform.machine().lower())
