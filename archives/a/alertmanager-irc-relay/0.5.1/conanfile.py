#!/usr/bin/env python3

import os
import platform
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class AlertmanagerIrcRelayConan(ConanFile):
    name = "alertmanager-irc-relay"
    version = "0.5.1"
    description = "Bot that relays Prometheus Alertmanager webhook alerts to IRC"
    license = "Apache-2.0"
    homepage = "https://github.com/google/alertmanager-irc-relay"
    url = "https://github.com/google/alertmanager-irc-relay"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    _go_version = "1.23.8"
    _go_archives = {
        "arm64": (
            [
                "https://golang.google.cn/dl/go1.23.8.linux-arm64.tar.gz",
                "https://mirrors.aliyun.com/golang/go1.23.8.linux-arm64.tar.gz",
                "https://dl.google.com/go/go1.23.8.linux-arm64.tar.gz",
            ],
            "9d6d938422724a954832d6f806d397cf85ccfde8c581c201673e50e634fdc992",
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
            raise ConanInvalidConfiguration(
                "alertmanager-irc-relay is prepared for Linux/OHOS targets only"
            )

    def generate(self):
        env = Environment()
        env.define("CGO_ENABLED", "0")
        env.define("GOOS", self._goos())
        env.define("GOARCH", self._goarch())
        env.define("GOTOOLCHAIN", "local")
        # proxy.golang.org is unreachable from the HarmonyOS PC CI network; route
        # module fetches through the China mirror and fall back to direct for
        # anything not present locally.
        env.define("GOPROXY", "https://goproxy.cn,direct")

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
        env.vars(self).save_script("air_go_env")

    def build(self):
        apply_conandata_patches(self)
        go = self._go_executable()

        # Always download module dependencies before building; tests are run
        # separately by the verify pipeline (see notes.md) because some OHOS
        # build hosts do not allow the Go linker to mmap its test-binary
        # output under the default GOTMPDIR.
        self._run_go_mod_download(go)

        out_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(out_dir, exist_ok=True)

        if str(self.settings.os) == "OHOS":
            link_out_dir = os.path.join(self._go_workspace(), "link-out")
        else:
            link_out_dir = out_dir

        os.makedirs(link_out_dir, exist_ok=True)

        linked_exe = os.path.join(link_out_dir, self._exe_name())
        final_exe = os.path.join(out_dir, self._exe_name())

        self.run(
            f'"{go}" build -trimpath -ldflags "-s -w" '
            f'-o "{linked_exe}" .',
            cwd=self.source_folder,
            env=["air_go_env"],
        )

        self._sign_elf_if_ohos(linked_exe)

        if os.path.abspath(linked_exe) != os.path.abspath(final_exe):
            shutil.copy2(linked_exe, final_exe)

    def _run_go_mod_download(self, go):
        self.output.info("Downloading Go module dependencies")
        self.run(
            f'"{go}" mod download',
            cwd=self.source_folder,
            env=["air_go_env"],
        )

    def package(self):
        copy(
            self,
            self._exe_name(),
            src=os.path.join(self.build_folder, "bin"),
            dst=os.path.join(self.package_folder, "bin"),
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        copy(
            self,
            "README.md",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "res"),
        )
        copy(
            self,
            "CONTRIBUTING.md",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "res"),
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]

    def _go_workspace(self):
        if str(self.settings.os) == "OHOS":
            root = os.environ.get(
                "OHOS_GO_WORKDIR",
                "/data/storage/el2/base/haps/entry/files/alertmanager-irc-relay-conan-go",
            )
        else:
            root = os.path.join(self.build_folder, ".go-work")

        workspace = os.path.join(root, self.version)

        for child in (
            "tmp",
            "go-build-cache",
            "go-mod-cache",
            "link-out",
            "go-sdk",
            "sign-tmp",
        ):
            Path(workspace, child).mkdir(parents=True, exist_ok=True)

        return workspace

    def _ensure_go_toolchain(self):
        host_arch = self._go_host_arch()

        if host_arch not in self._go_archives:
            raise ConanInvalidConfiguration(
                f"Go SDK bootstrap is not prepared for host arch: {host_arch}"
            )

        sdk_root = os.path.join(
            self._go_workspace(),
            "go-sdk",
            f"go{self._go_version}-{host_arch}",
        )
        goroot = os.path.join(sdk_root, "go")
        go = os.path.join(goroot, "bin", "go")

        if not os.path.isfile(go):
            urls, sha256 = self._go_archives[host_arch]
            self.output.info(
                f"Go >= {self._go_version} not found; downloading {urls[0]}"
            )
            get(
                self,
                url=urls,
                sha256=sha256,
                destination=sdk_root,
                strip_root=False,
            )

        self._sign_go_sdk_if_ohos(goroot)
        return go

    def _sign_go_sdk_if_ohos(self, goroot):
        if str(self.settings.os) != "OHOS":
            return

        marker = os.path.join(goroot, ".ohos-signed")
        if os.path.isfile(marker):
            return

        tool_dir = os.path.join(
            goroot,
            "pkg",
            "tool",
            f"linux_{self._go_host_arch()}",
        )

        candidates = [
            os.path.join(goroot, "bin", "go"),
            os.path.join(goroot, "bin", "gofmt"),
        ]

        if os.path.isdir(tool_dir):
            candidates.extend(
                os.path.join(tool_dir, name)
                for name in os.listdir(tool_dir)
            )

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

        signer = (
            shutil.which("binary-sign-tool")
            or "/data/service/hnp/bin/binary-sign-tool"
        )

        if not os.path.isfile(signer):
            raise ConanInvalidConfiguration(
                "binary-sign-tool is required to sign OHOS Go executables"
            )

        tmp_dir = os.path.join(self._go_workspace(), "sign-tmp")
        Path(tmp_dir).mkdir(parents=True, exist_ok=True)

        tmp_in = os.path.join(tmp_dir, os.path.basename(path))
        tmp_out = f"{tmp_in}.signed"

        shutil.copy2(path, tmp_in)

        objcopy = (
            shutil.which("llvm-objcopy")
            or "/data/service/hnp/bin/llvm-objcopy"
        )

        subprocess.run(
            [objcopy, "--remove-section", ".codesign", tmp_in],
            capture_output=True,
            timeout=10,
        )

        subprocess.check_call(
            [
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
            ]
        )

        shutil.move(tmp_out, path)
        os.chmod(path, 0o755)

        if os.path.isfile(tmp_in):
            os.unlink(tmp_in)

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
        return "alertmanager-irc-relay.exe" if self._goos() == "windows" else "alertmanager-irc-relay"

    def _go_executable(self):
        candidates = []

        if os.environ.get("GO"):
            candidates.append(os.environ["GO"])

        if os.environ.get("GOROOT"):
            candidates.append(
                os.path.join(os.environ["GOROOT"], "bin", "go")
            )

        candidates.extend(
            [
                os.path.expanduser("~/usr/local/go/bin/go"),
                os.path.expanduser(f"~/sdk/go{self._go_version}/bin/go"),
            ]
        )

        found = shutil.which("go")
        if found:
            candidates.append(found)

        for candidate in candidates:
            if (
                candidate
                and os.path.isfile(candidate)
                and self._go_version_is_supported(candidate)
            ):
                return candidate

        return self._ensure_go_toolchain()

    def _go_version_is_supported(self, go):
        try:
            output = subprocess.run(
                [go, "version"],
                capture_output=True,
                timeout=10,
            ).stdout.decode()
        except OSError:
            return False

        token = output.split("go version ")[-1].split(" ")[0]
        version = token[2:]

        try:
            current = [int(x) for x in version.split(".")]
            required = [int(x) for x in self._go_version.split(".")]
            return current >= required
        except ValueError:
            return False

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

    @staticmethod
    def _goroot_for_go(go):
        go = os.path.realpath(go)
        goroot = os.path.dirname(os.path.dirname(go))

        if os.path.isfile(os.path.join(goroot, "bin", "go")):
            return goroot

        return ""
