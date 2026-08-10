#!/usr/bin/env python3
"""Conan recipe for git-town 16.4.1.

git-town is a Go application that provides branching and workflow support for Git.
Build system: Go (go build with -ldflags="-s -w").

The recipe auto-downloads Go SDK if not found on the system, downloads Go
modules via GOPROXY (goproxy.cn mirror), and produces a static arm64 ELF
binary. On OHOS, all Go SDK and output binaries are signed with
binary-sign-tool.
"""
import os
import platform
import re
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class GitTownConan(ConanFile):
    name = "git-town"
    version = "16.4.1"
    package_type = "application"

    description = "Branching and workflow support for Git"
    license = "MIT"
    homepage = "https://github.com/git-town/git-town"
    url = "https://github.com/git-town/git-town"
    topics = ("git", "workflow", "vcs", "cli")

    settings = "os", "arch"

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

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("git-town is prepared for Linux/OHOS targets only")

    def generate(self):
        env = Environment()
        env.define("CGO_ENABLED", "0")
        env.define("GOOS", self._goos())
        env.define("GOARCH", self._goarch())
        env.define("GOPROXY", os.environ.get("GOPROXY", "https://goproxy.cn,direct"))
        env.define("GOSUMDB", os.environ.get("GOSUMDB", "sum.golang.google.cn"))
        env.define("GOTOOLCHAIN", "local")
        env.define("GOWORK", "off")
        env.define("GOFLAGS", "-mod=mod")

        go_workspace = self._go_workspace()
        # Set TMPDIR and GOTMPDIR to the go workspace (on el2 filesystem for OHOS)
        # This filesystem supports mmap which the Go linker requires.
        env.define("TMPDIR", os.path.join(go_workspace, "tmp"))
        env.define("GOTMPDIR", os.path.join(go_workspace, "tmp"))
        env.define("GOCACHE", os.path.join(go_workspace, "go-build-cache"))
        env.define("GOMODCACHE", os.path.join(go_workspace, "go-mod-cache"))

        gobin = self._go_executable()
        goroot = self._goroot_for_go(gobin)
        if goroot:
            env.define("GOROOT", goroot)
        env.prepend_path("PATH", os.path.dirname(gobin))

        env.vars(self).save_script("git_town_go_env")

    def build(self):
        apply_conandata_patches(self)
        go = self._go_executable()
        self._check_go_version(go)

        # Download Go module dependencies
        self.run(f'"{go}" mod download', cwd=self.source_folder, env=["git_town_go_env"])

        # Build the binary
        out_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(out_dir, exist_ok=True)
        link_out_dir = os.path.join(self._go_workspace(), "link-out") if str(self.settings.os) == "OHOS" else out_dir
        os.makedirs(link_out_dir, exist_ok=True)
        linked_exe = os.path.join(link_out_dir, self._exe_name())
        final_exe = os.path.join(out_dir, self._exe_name())

        ldflags = "-s -w"
        self.run(
            f'"{go}" build -ldflags "{ldflags}" -o "{linked_exe}" .',
            cwd=self.source_folder,
            env=["git_town_go_env"],
        )
        self._sign_elf_if_ohos(linked_exe)
        if os.path.abspath(linked_exe) != os.path.abspath(final_exe):
            shutil.copy2(linked_exe, final_exe)

    def package(self):
        copy(self, self._exe_name(), os.path.join(self.build_folder, "bin"), os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]

    # --- Go SDK bootstrap ---

    def _ensure_go_toolchain(self):
        """Download Go SDK if not found on the system."""
        host_arch = self._go_host_arch()
        if host_arch not in self._go_archives:
            raise ConanInvalidConfiguration(f"Go SDK bootstrap not prepared for host arch: {host_arch}")

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
        """Sign all Go SDK ELF binaries for OHOS execution."""
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

    # --- Helper methods ---

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

    def _exe_name(self):
        return "git-town.exe" if self._goos() == "windows" else "git-town"

    def _go_workspace(self):
        if str(self.settings.os) == "OHOS":
            # On OHOS, conan build folders are on HMDFS which doesn't support
            # mmap needed by the Go linker. Use /data/storage/el2/base/haps/entry/files
            # which is on a different filesystem that supports mmap.
            root = os.environ.get(
                "OHOS_GO_WORKDIR",
                "/data/storage/el2/base/haps/entry/files/git-town-conan-go",
            )
        else:
            root = os.path.join(self.build_folder, ".go-work")
        workspace = os.path.join(root, self.version)
        for child in ("tmp", "go-build-cache", "go-mod-cache", "link-out", "go-sdk"):
            Path(workspace, child).mkdir(parents=True, exist_ok=True)
        return workspace

    def _go_executable(self):
        candidates = []
        if os.environ.get("GO"):
            candidates.append(os.environ["GO"])
        if os.environ.get("GOROOT"):
            candidates.append(os.path.join(os.environ["GOROOT"], "bin", "go"))
        found = shutil.which("go")
        if found:
            candidates.append(found)
        candidates.extend([
            "/storage/Users/currentUser/.harmonybrew/bin/go",
            os.path.expanduser("~/.harmonybrew/bin/go"),
        ])

        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        # Fallback: download Go SDK
        return self._ensure_go_toolchain()

    def _check_go_version(self, go):
        output = subprocess.check_output([go, "version"], text=True).strip()
        self.output.info(output)
        major, minor = self._go_version_tuple(output)
        if (major, minor) < (1, 22):
            raise ConanInvalidConfiguration(f"git-town 16.4.1 requires Go >= 1.22, got: {output}")

    @staticmethod
    def _go_version_tuple(output):
        match = re.search(r"go(\d+)\.(\d+)", output)
        if not match:
            raise ConanInvalidConfiguration(f"Unable to parse Go version from: {output}")
        return int(match.group(1)), int(match.group(2))

    @staticmethod
    def _goroot_for_go(go):
        go_path = Path(go).resolve()
        goroot = go_path.parent.parent
        if go_path.parent.name == "bin" and (goroot / "pkg").is_dir():
            return str(goroot)
        return None

    @staticmethod
    def _go_host_arch():
        machine = platform.machine().lower()
        return {
            "aarch64": "arm64",
            "arm64": "arm64",
            "x86_64": "amd64",
            "amd64": "amd64",
        }.get(machine, machine)

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
        signer = shutil.which("binary-sign-tool") or "/storage/Users/currentUser/usr/local/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            raise ConanInvalidConfiguration("binary-sign-tool is required to sign OHOS Go executables")
        signed = f"{path}.signed"
        subprocess.check_call([
            signer,
            "sign",
            "-selfSign", "1",
            "-inFile", path,
            "-outFile", signed,
            "-signAlg", "SHA256withECDSA",
        ])
        shutil.move(signed, path)
        os.chmod(path, 0o755)
