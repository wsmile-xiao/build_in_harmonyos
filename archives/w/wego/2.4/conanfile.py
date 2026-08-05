#!/usr/bin/env python3
"""Conan recipe for wego 2.4 — pure Go weather CLI.

wego is a Go module CLI (weather client for the terminal). The command entry
is the root package `github.com/schachmat/wego` (main.go at the repo root),
NOT a `./cmd/wego` subdirectory. Build with:

    CGO_ENABLED=0 GOOS=linux GOARCH=<arch> go build -ldflags="-s -w" -o wego .

Upstream 2.4 ships no *_test.go files; TestXxx/BenchmarkXxx/ExampleXxx all 0.
CI runs `go test -v ./...` but every package prints `[no test files]`.
Therefore upstream_tests is empty and we rely on test_package consumer checks
(`wego -h` exit 0 + stable keyword assertions).

HMDFS note: the Go linker needs a tmpfs workspace on HarmonyOS to avoid
`mapping output file failed: permission denied` (HMDFS mmap restriction).
OHOS Go executables (and the Go SDK tool binaries themselves) must be
self-signed with binary-sign-tool before execution.
"""
import os
import re
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class WegoConan(ConanFile):
    name = "wego"
    version = "2.4"
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
    package_type = "application"

    description = "wego is a weather client for the terminal (Go CLI, CGO_ENABLED=0 static)"
    license = "ISC"
    homepage = "https://github.com/schachmat/wego"
    url = "https://github.com/schachmat/wego"
    topics = ("weather", "cli", "terminal", "forecast", "go")

    settings = "os", "arch"

    def export_sources(self):
        # wego 2.4 ships no patches; export_conandata_patches is a no-op when
        # conandata.yml has empty patches: {}. Declared for G1 recipe completeness.
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("wego is prepared for Linux/OHOS targets only")

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

        gobin = self._go_executable()
        goroot = self._goroot_for_go(gobin)
        if goroot:
            env.define("GOROOT", goroot)
        env.prepend_path("PATH", os.path.dirname(gobin))

        env.vars(self).save_script("wego_go_env")

    def build(self):
        apply_conandata_patches(self)  # no-op when patches: {} (wego 2.4 needs none)
        go = self._go_executable()
        self._check_go_version(go)
        self.run(f'"{go}" mod download', cwd=self.source_folder, env=["wego_go_env"])

        # wego's command entry is the root package (main.go at repo root).
        out_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(out_dir, exist_ok=True)
        # OHOS: write link output to tmpfs workspace, then copy to bin/ after signing
        link_out_dir = os.path.join(self._go_workspace(), "link-out") if str(self.settings.os) == "OHOS" else out_dir
        os.makedirs(link_out_dir, exist_ok=True)
        linked_exe = os.path.join(link_out_dir, self._exe_name())
        final_exe = os.path.join(out_dir, self._exe_name())
        ldflags = "-s -w"
        self.run(
            f'"{go}" build -trimpath -ldflags "{ldflags}" -o "{linked_exe}" .',
            cwd=self.source_folder,
            env=["wego_go_env"],
        )
        self._sign_elf_if_ohos(linked_exe)
        if os.path.abspath(linked_exe) != os.path.abspath(final_exe):
            shutil.copy2(linked_exe, final_exe)

    def package(self):
        copy(self, self._exe_name(), os.path.join(self.build_folder, "bin"), os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "README.md", self.source_folder, os.path.join(self.package_folder, "res"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]

    # ---------- Go toolchain helpers (adapted from chkbit 6.6.0) ----------

    def _go_workspace(self):
        # HMDFS tmpfs workspace required on OHOS for Go linker mmap; falls back
        # to build_folder on Linux where /tmp is writable.
        base = os.environ.get("OHC_GO_WORKSPACE")
        if base:
            ws = os.path.join(base, f"wego-{self.version}")
        elif str(self.settings.os) == "OHOS":
            ws = os.path.join("/data/storage/el2/base/haps/entry/files", f"wego-{self.version}-build")
        else:
            ws = os.path.join(self.build_folder, "go-workspace")
        # Pre-create all subdirectories that generate() defines as env vars.
        # Go's linker writes mmap output to TMPDIR/GOTMPDIR and caches to
        # GOCACHE/GOMODCACHE — all must exist before `go build` runs.
        for sub in ("", "tmp", "go-build-cache", "go-mod-cache", "link-out"):
            os.makedirs(os.path.join(ws, sub), exist_ok=True)
        return ws

    def _ensure_go_toolchain(self):
        """Bootstrap official Go 1.24.0 SDK from golang.google.cn with dl.google.com fallback.

        No-op when a usable `go` is already on PATH/GOROOT/GO env. Only unsigned
        SDK runtime tool binaries get signed on OHOS before first use.
        """
        # Prefer an already-signed usable Go on PATH/GO/GOROOT_TMP.
        go = shutil.which("go") or os.environ.get("GO") or os.environ.get("GOROOT_TMP")
        if go and self._go_version_is_supported(go):
            return go
        arch = self._go_host_arch()
        urls, expected_sha = self._go_archives[arch]
        sdk_dir = os.path.join(os.path.expanduser("~"), ".goenv", "versions", self._go_version)
        go_bin = os.path.join(sdk_dir, "bin", "go")
        if not os.path.isfile(go_bin):
            os.makedirs(sdk_dir, exist_ok=True)
            archive_path = os.path.join(sdk_dir, "go.tar.gz")
            downloaded = False
            for url in urls:
                try:
                    self.run(f'curl -fsSL -o "{archive_path}" "{url}"', env=[])
                    downloaded = True
                    break
                except Exception:
                    continue
            if not downloaded:
                raise ConanInvalidConfiguration(f"Failed to download Go {self._go_version} SDK for {arch}")
            actual_sha = self._sha256(archive_path)
            if actual_sha != expected_sha:
                raise ConanInvalidConfiguration(f"Go SDK SHA256 mismatch: {actual_sha} != {expected_sha}")
            self.run(f'tar -xzf "{archive_path}" -C "{sdk_dir}" --strip-components=1', env=[])
            os.remove(archive_path)
        # On OHOS the freshly extracted SDK binaries are unsigned → exec returns
        # 126 (Permission denied) and `go version` is mistaken for "too old".
        # Sign the SDK tool binaries (and go/gofmt) before first use.
        self._sign_go_sdk_if_ohos(sdk_dir)
        return go_bin

    def _sign_go_sdk_if_ohos(self, goroot):
        if str(self.settings.os) != "OHOS":
            return
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(sign_tool):
            return
        tool_dir = os.path.join(goroot, "pkg", "tool", "linux_arm64")
        for name in ("asm", "cgo", "compile", "cover", "fix", "link", "preprofile", "vet"):
            p = os.path.join(tool_dir, name)
            if os.path.isfile(p) and not self._has_ohos_signature(p):
                self._sign_elf(p, sign_tool)
        for name in ("go", "gofmt"):
            p = os.path.join(goroot, "bin", name)
            if os.path.isfile(p) and not self._has_ohos_signature(p):
                self._sign_elf(p, sign_tool)

    def _sign_elf_if_ohos(self, path):
        if str(self.settings.os) != "OHOS":
            return
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(sign_tool):
            raise ConanInvalidConfiguration(f"binary-sign-tool not found: {sign_tool}")
        if not self._is_elf(path):
            return
        if self._has_ohos_signature(path):
            return
        self._sign_elf(path, sign_tool)

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except Exception:
            return False

    @staticmethod
    def _has_ohos_signature(path):
        try:
            r = subprocess.run(
                ["/data/service/hnp/bin/llvm-readelf", "-S", path],
                capture_output=True, text=True, timeout=10,
            )
            return ".codesign" in r.stdout
        except Exception:
            return False

    @staticmethod
    def _sign_elf(path, sign_tool):
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if os.path.isfile(objcopy):
            subprocess.run([objcopy, "--remove-section", ".codesign", path], capture_output=True, timeout=10)
        tmp = path + ".signed.tmp"
        for attempt in range(3):
            r = subprocess.run(
                [sign_tool, "sign", "-inFile", path, "-outFile", tmp, "-selfSign", "1"],
                capture_output=True, text=True, timeout=30,
            )
            if r.returncode == 0 and os.path.isfile(tmp):
                shutil.move(tmp, path)
                os.chmod(path, 0o755)
                return
        raise ConanInvalidConfiguration(f"ELF signing failed for {path}")

    def _goos(self):
        return "linux"  # OHOS pre-adaptation: GOOS=linux, GOARCH=arm64

    def _goarch(self):
        arch = str(self.settings.arch)
        if arch in ("x86_64", "amd64"):
            return "amd64"
        if arch in ("armv8", "aarch64", "arm64"):
            return "arm64"
        return arch

    def _exe_name(self):
        return "wego.exe" if str(self.settings.os) == "Windows" else "wego"

    def _go_executable(self):
        candidates = [
            os.environ.get("GO"),
            os.environ.get("GOROOT_TMP"),
            shutil.which("go"),
        ]
        for c in candidates:
            if c and os.path.isfile(c) and self._go_version_is_supported(c):
                return c
        return self._ensure_go_toolchain()

    def _go_version_is_supported(self, go):
        try:
            return self._go_version_tuple(go) >= (1, 24, 0)
        except Exception:
            return False

    def _check_go_version(self, go):
        if not self._go_version_is_supported(go):
            raise ConanInvalidConfiguration(f"Go toolchain at {go} is older than 1.24.0")

    @staticmethod
    def _go_version_tuple(go, output=None):
        if output is None:
            r = subprocess.run([go, "version"], capture_output=True, text=True, timeout=10)
            output = r.stdout
        m = re.search(r"go(\d+)\.(\d+)\.(\d+)", output)
        if not m:
            raise ValueError(f"cannot parse go version: {output!r}")
        return tuple(int(x) for x in m.groups())

    @staticmethod
    def _goroot_for_go(go):
        # GOROOT is the parent of the bin/ dir holding `go`.
        return os.path.dirname(os.path.dirname(go))

    @staticmethod
    def _go_host_arch():
        import platform
        m = platform.machine()
        if m in ("x86_64", "amd64"):
            return "amd64"
        if m in ("aarch64", "arm64"):
            return "arm64"
        return m

    @staticmethod
    def _sha256(path):
        import hashlib
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()
