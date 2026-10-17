#!/usr/bin/env python3
"""Conan recipe for kubeadm 1.36.2 — Kubernetes cluster bootstrap tool (Go).

Kubernetes v1.36.2, module k8s.io/kubernetes, build ./cmd/kubeadm with
CGO_ENABLED=0 -mod=vendor (the source archive ships a complete vendor/ tree).
Adapted for HarmonyOS OHOS (GOOS=linux GOARCH=arm64).

The CI worker has no preinstalled Go toolchain, so the recipe bootstraps
Go 1.26.4 (kubeadm's go.mod requires go >= 1.26.0) from dl.google.com,
self-signs every ELF in the toolchain with binary-sign-tool (OHOS refuses
to load unsigned ELF), then links the kubeadm binary into a writable
workspace dir and self-signs it as well. Pattern follows the published
adbtuifm / abbtr Go recipes (E318: unsigned-ELF-on-OHOS).
"""

import hashlib
import os
import platform
import re
import shutil
import subprocess
import tarfile
import urllib.request

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class KubeadmConan(ConanFile):
    name = "kubeadm"
    version = "1.36.2"
    description = "kubeadm — Kubernetes cluster bootstrap tool (k8s.io/kubernetes cmd/kubeadm)"
    license = "Apache-2.0"
    homepage = "https://kubernetes.io/docs/reference/setup-tools/kubeadm/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    # kubeadm go.mod declares "go 1.26.0" — toolchain must be >= 1.26.0
    _go_version = "1.26.4"
    _go_archives = {
        "arm64": (
            [
                "https://golang.google.cn/dl/go1.26.4.linux-arm64.tar.gz",
                "https://dl.google.com/go/go1.26.4.linux-arm64.tar.gz",
            ],
            "ef758ae7c6cf9267c9c0ef080b8965f453d89ab2d25d9eb22de4405925238768",
        ),
        "amd64": (
            [
                "https://golang.google.cn/dl/go1.26.4.linux-amd64.tar.gz",
                "https://dl.google.com/go/go1.26.4.linux-amd64.tar.gz",
            ],
            "1153d3d50e0ac764b447adfe05c2bcf08e889d42a02e0fe0259bd47f6733ad7f",
        ),
    }

    # kubernetes source archive mirrors, tried in order. The gitee mirror
    # and the official codeload archive produce DIFFERENT tar bytes (archive
    # metadata differs) → different sha256; source content is identical
    # (same v1.36.2 tag, both ship the full vendor/ tree).
    # gitee only serves the real tarball to a curl-style User-Agent.
    _source_archive = (
        ("https://gitee.com/mirrors/kubernetes/repository/archive/v1.36.2.tar.gz",
         "dbfd3b50644f2e14046110901d032986e829d2726de19b8aedbf3b1f7389f732"),
        ("https://codeload.github.com/kubernetes/kubernetes/tar.gz/refs/tags/v1.36.2",
         "ffbc46612cf32ad08a3b606de064b63afc350ae1dd1a691e99b5cd127d716c26"),
    )

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        # CI sets CONAN_REQUEST_TIMEOUT=300 + CONAN_RETRY=10, and conan's
        # get() honors them: a single slow URL can retry 10*(300+30)s=3300s
        # and blow the default 3600s build window. Also the CI worker has
        # no curl, so the CI pre-download phase always fails there (Errno 2).
        # Use the bounded downloader instead (2 attempts x 120s per mirror):
        # gitee first (~15s measured), codeload as fallback.
        urls = self.conan_data.get("sources", {}).get("url")
        if isinstance(urls, (list, tuple)):
            urls = urls[0] if urls else None
        if urls and str(urls).startswith("file://"):
            # CI pre-download cache hit: the archive is already on disk.
            self._verify_and_unpack(
                str(urls)[len("file://"):],
                [sha for _, sha in self._source_archive])
            return
        archive = os.path.join(self.source_folder, "kubernetes-1.36.2.tar.gz")
        self._bounded_download(self._source_archive, archive)
        self._verify_and_unpack(
            archive, [sha for _, sha in self._source_archive])

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "kubeadm is prepared for Linux/OHOS targets only")

    def generate(self):
        env = Environment()
        env.define("CGO_ENABLED", "0")
        env.define("GOOS", self._goos())
        env.define("GOARCH", self._goarch())
        env.define("GO111MODULE", "on")
        env.define("GOPROXY", "off")
        env.define("GOFLAGS", "-mod=vendor")
        env.define("GOSANDBOX", "off")
        env.define("GOTOOLCHAIN", "local")

        workspace = self._go_workspace()
        env.define("TMPDIR", os.path.join(workspace, "tmp"))
        env.define("GOTMPDIR", os.path.join(workspace, "tmp"))
        env.define("GOCACHE", os.path.join(workspace, "go-build-cache"))
        env.define("GOMODCACHE", os.path.join(workspace, "go-mod-cache"))

        gobin = self._go_executable()
        goroot = self._goroot_for_go(gobin)
        if goroot:
            env.define("GOROOT", goroot)
        env.prepend_path("PATH", os.path.dirname(gobin))

        env.vars(self).save_script("kubeadm_go_env")

    def build(self):
        apply_conandata_patches(self)

        go = self._go_executable()
        output = subprocess.check_output([go, "version"], text=True).strip()
        self.output.info(output)
        match = re.search(r"go(\d+)\.(\d+)", output)
        if not match or (int(match.group(1)), int(match.group(2))) < (1, 26):
            raise ConanInvalidConfiguration(
                f"kubeadm requires Go >= 1.26.0, found: {output}")

        ldflags = [
            "-w", "-s",
            "-X k8s.io/component-base/version.gitVersion=v1.36.2",
            "-X k8s.io/component-base/version.gitCommit=unknown",
            "-X k8s.io/component-base/version.gitTreeState=clean",
            "-X k8s.io/component-base/version.buildDate=2026-09-23",
        ]

        out_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(out_dir, exist_ok=True)

        # OHOS: link output must go into the writable workspace (the
        # linker's RWX mmap of the output file fails on the default
        # /tmp); the binary is signed afterwards and copied to bin/.
        link_out_dir = (
            os.path.join(self._go_workspace(), "link-out")
            if str(self.settings.os) == "OHOS" else out_dir
        )
        os.makedirs(link_out_dir, exist_ok=True)

        linked_exe = os.path.join(link_out_dir, "kubeadm")
        final_exe = os.path.join(out_dir, "kubeadm")

        self.run(
            f'"{go}" build -trimpath '
            f'-ldflags "{ " ".join(ldflags) }" -o "{linked_exe}" ./cmd/kubeadm',
            cwd=self.source_folder,
            env=["kubeadm_go_env"],
        )

        self._sign_elf_if_ohos(linked_exe, self._signer())

        if os.path.abspath(linked_exe) != os.path.abspath(final_exe):
            shutil.copy2(linked_exe, final_exe)

    def package(self):
        copy(self, "kubeadm", os.path.join(self.build_folder, "bin"),
             os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]

    # ── Bounded source/toolchain download ─────────────────────────────────

    # Worst case: source archive 2 mirrors x 2 attempts x 120s = 8min,
    # plus Go SDK 2 mirrors x 2 attempts x 120s = 8min → 16min total,
    # well inside the default 3600s build window; no framework timeout
    # override is required for this package.
    _dl_timeout = 120
    _dl_attempts = 2

    def _bounded_download(self, entries, dest):
        errors = []
        for url, sha256 in entries:
            for attempt in range(1, self._dl_attempts + 1):
                try:
                    self._download_one(url, sha256, dest)
                    self.output.info(
                        f"Downloaded {os.path.basename(url)} "
                        f"({os.path.getsize(dest) // 1048576}MB) from {url}")
                    return
                except Exception as e:
                    errors.append(f"{url} attempt {attempt}: {e}")
                    self.output.warning(f"download failed {url}: {e}")
        raise ConanException(
            "all download mirrors failed:\n  " + "\n  ".join(errors))

    def _download_one(self, url, sha256, dest):
        # gitee serves the real tarball only to a curl-style User-Agent
        # (python-requests/urllib default UAs get an HTML block page);
        # golang.google.cn / dl.google.com / codeload accept any UA.
        req = urllib.request.Request(url, headers={
            "User-Agent": "curl/8.5.0",
            "Accept": "*/*",
        })
        tmp = dest + ".part"
        try:
            with urllib.request.urlopen(req, timeout=self._dl_timeout) as resp:
                with open(tmp, "wb") as f:
                    while True:
                        chunk = resp.read(1 << 20)
                        if not chunk:
                            break
                        f.write(chunk)
            with open(tmp, "rb") as f:
                head = f.read(2)
                f.seek(0)
                digest = hashlib.sha256()
                while True:
                    chunk = f.read(1 << 20)
                    if not chunk:
                        break
                    digest.update(chunk)
            if head != b"\x1f\x8b":
                raise ConanException("not a gzip archive (HTML block page?)")
            if digest.hexdigest() != sha256:
                raise ConanException(f"sha256 mismatch for {url}")
            os.replace(tmp, dest)
        except Exception:
            if os.path.exists(tmp):
                os.remove(tmp)
            raise

    def _verify_and_unpack(self, archive, expected_shas):
        with open(archive, "rb") as f:
            digest = hashlib.sha256()
            while True:
                chunk = f.read(1 << 20)
                if not chunk:
                    break
                digest.update(chunk)
        if digest.hexdigest() not in expected_shas:
            raise ConanException(
                f"unexpected source archive sha256 {digest.hexdigest()}")
        with tarfile.open(archive) as tf:
            names = tf.getnames()
            roots = {n.split("/", 1)[0] for n in names}
            if len(roots) != 1:
                raise ConanException(f"unexpected archive layout: {roots}")
            prefix = roots.pop() + "/"
            for member in tf.getmembers():
                if not member.name.startswith(prefix):
                    continue
                member.name = member.name[len(prefix):]
                tf.extract(member, self.source_folder, filter="tar")

    # ── Go toolchain management ──────────────────────────────────────────

    def _go_workspace(self):
        if str(self.settings.os) != "OHOS":
            root = os.path.join(self.build_folder, ".go-work")
        else:
            root = os.environ.get(
                "OHOS_GO_WORKDIR",
                "/data/storage/el2/base/haps/entry/files/kubeadm-conan-go",
            )
        workspace = os.path.join(root, self.version)
        for child in ("tmp", "go-build-cache", "go-mod-cache", "link-out", "go-sdk"):
            os.makedirs(os.path.join(workspace, child), exist_ok=True)
        return workspace

    def _signer(self):
        signer = (
            shutil.which("binary-sign-tool")
            or "/data/service/hnp/bin/binary-sign-tool"
            or "/storage/Users/currentUser/usr/local/bin/binary-sign-tool"
        )
        if not signer or not os.path.isfile(signer):
            raise ConanInvalidConfiguration(
                "binary-sign-tool is required to sign OHOS Go executables")
        return signer

    def _ensure_go_toolchain(self):
        host_arch = self._go_host_arch()
        if host_arch not in self._go_archives:
            raise ConanInvalidConfiguration(
                f"Go SDK bootstrap is not prepared for host arch: {host_arch}")

        sdk_root = os.path.join(
            self._go_workspace(), "go-sdk", f"go{self._go_version}-{host_arch}")
        goroot = os.path.join(sdk_root, "go")
        gobin = os.path.join(goroot, "bin", "go")
        if not os.path.isfile(gobin):
            urls, sha256 = self._go_archives[host_arch]
            self.output.info(f"Go {self._go_version} not found; downloading {urls[0]}")
            dl_dir = os.path.join(self._go_workspace(), "go-sdk-download")
            os.makedirs(dl_dir, exist_ok=True)
            archive = os.path.join(
                dl_dir, f"go{self._go_version}-{host_arch}.tar.gz")
            self._bounded_download([(u, sha256) for u in urls], archive)
            with tarfile.open(archive) as tf:
                tf.extractall(sdk_root, filter="tar")
        self._sign_go_sdk_if_ohos(goroot)
        return gobin

    def _sign_go_sdk_if_ohos(self, goroot):
        if str(self.settings.os) != "OHOS":
            return
        marker = os.path.join(goroot, ".ohos-signed")
        if os.path.isfile(marker):
            return

        host_arch = self._go_host_arch()
        tool_dir = os.path.join(goroot, "pkg", "tool", f"linux_{host_arch}")
        candidates = [
            os.path.join(goroot, "bin", "go"),
            os.path.join(goroot, "bin", "gofmt"),
        ]
        if os.path.isdir(tool_dir):
            candidates.extend(
                os.path.join(tool_dir, name) for name in os.listdir(tool_dir))

        signer = self._signer()
        for candidate in candidates:
            if os.path.isfile(candidate) and self._is_elf(candidate):
                self._sign_elf_if_ohos(candidate, signer)
        with open(marker, "w", encoding="utf-8") as f:
            f.write("signed\n")

    def _is_elf(self, path):
        try:
            with open(path, "rb") as binary:
                return binary.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _has_ohos_signature(self, path):
        try:
            with open(path, "rb") as binary:
                data = binary.read()
        except OSError:
            return False
        return b".codesign" in data or b".note.ohos" in data

    def _sign_elf_if_ohos(self, path, signer):
        if str(self.settings.os) != "OHOS":
            return
        if self._has_ohos_signature(path):
            os.chmod(path, 0o755)
            return
        signed = f"{path}.signed"
        subprocess.check_call([
            signer, "sign", "-selfSign", "1",
            "-inFile", path, "-outFile", signed,
            "-signAlg", "SHA256withECDSA",
        ])
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
            os.path.expanduser("~/usr/local/go1264/bin/go"),
            os.path.expanduser("~/sdk/go1.26.4/bin/go"),
            "/storage/Users/currentUser/usr/local/go1264/bin/go",
            "/storage/Users/currentUser/sdk/go1.26.4/bin/go",
        ])
        found = shutil.which("go")
        if found:
            candidates.append(found)

        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                try:
                    output = subprocess.check_output(
                        [candidate, "version"], text=True).strip()
                    match = re.search(r"go(\d+)\.(\d+)", output)
                    if match and (int(match.group(1)), int(match.group(2))) >= (1, 26):
                        return candidate
                except (OSError, subprocess.SubprocessError):
                    continue
        return self._ensure_go_toolchain()

    @staticmethod
    def _goroot_for_go(go):
        go_path = os.path.abspath(go)
        goroot = os.path.dirname(os.path.dirname(go_path))
        if os.path.basename(os.path.dirname(go_path)) == "bin" \
                and os.path.isdir(os.path.join(goroot, "pkg")):
            return goroot
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
