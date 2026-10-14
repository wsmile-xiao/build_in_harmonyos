#!/usr/bin/env python3
"""Conan 2.x recipe for kustomizer 2.2.1.

kustomizer is a pure-Go command line utility for publishing, fetching,
customizing, validating and applying Kubernetes configuration as OCI
artifacts. Neither the host nor the CI worker provides a system Go
toolchain and the ohpcd repository carries no golang package, so this
recipe bootstraps the official Go toolchain at build time:

  1. read upstream go.mod for the minimum Go directive (go 1.19);
  2. cross-check the pinned release against the official version list
     from https://go.dev/dl/?mode=json (&include=all);
  3. download go<ver>.linux-arm64.tar.gz into a private build_folder
     directory and verify the official sha256;
  4. build a fully static binary with the internal linker
     (CGO_ENABLED=0 GOOS=linux GOARCH=arm64).

The produced binary is static and depends on no OHOS system library.
"""

import hashlib
import json
import os
import shutil
import tarfile

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get

# Official Go release manifest (JSON listing every release with sha256).
GO_MANIFEST_URLS = (
    "https://go.dev/dl/?mode=json&include=all",
    "https://golang.google.cn/dl/?mode=json&include=all",
)
# Base URLs for the toolchain tarball (official source + official mirror).
GO_DL_URLS = (
    "https://go.dev/dl/{filename}",
    "https://golang.google.cn/dl/{filename}",
)
# Go module proxies injected by the recipe (never the host global config).
GO_PROXY = "https://goproxy.cn,https://goproxy.io,direct"

# Toolchain chosen for this adaptation. Upstream go.mod declares "go 1.19";
# the go1.19.x official linux/arm64 binaries are dynamically linked against
# glibc (/lib/ld-linux-aarch64.so.1 + libc.so.6) which OHOS does not provide
# (it ships musl only). Go >= 1.20 publishes fully static linux/arm64
# toolchains, and Go 1.24.13 compiles this go-1.19-era module unchanged.
GO_BOOTSTRAP_VERSION = "1.24.13"
GO_BOOTSTRAP_SHA256 = "74d97be1cc3a474129590c67ebf748a96e72d9f3a2b6fef3ed3275de591d49b3"

# HarmonyOS native program location.
HNP_BIN = "/data/service/hnp/bin"


class KustomizerConan(ConanFile):
    name = "kustomizer"
    version = "2.2.1"
    description = (
        "Kubernetes configuration OCI artifact manager CLI: publish, fetch, "
        "customize, validate and apply Kubernetes configs."
    )
    license = "Apache-2.0"
    homepage = "https://github.com/stefanprodan/kustomizer"
    url = "https://github.com/stefanprodan/kustomizer"
    author = "Stefan Prodan"

    # R38/PF8: this package produces the `kustomizer` executable, so a
    # software-level commands.json with type "tool" is required.
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    # -- Source / patches ------------------------------------------------
    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    # No Conan-level requirements: kustomizer is pure Go. Its Go module
    # dependencies are fetched from the module proxies during the build.
    def requirements(self):
        return

    # -- Helpers ---------------------------------------------------------
    @property
    def _go_root_dir(self):
        """Private GOROOT location inside the build folder."""
        return os.path.join(self.build_folder, "_go", "go")

    @property
    def _go_bin(self):
        return os.path.join(self._go_root_dir, "bin", "go")

    def _writable_tmp(self):
        """Return a writable temp dir on an mmap-capable filesystem.

        HMDFS (/storage/...) does not support the Go linker's mmap and the
        traditional /tmp is not writable; prefer the application cache.
        """
        for candidate in (
            "/data/storage/el2/base/cache",
            os.path.join(os.path.expanduser("~"), "tmp"),
        ):
            if candidate and os.path.isdir(candidate) and os.access(candidate, os.W_OK):
                return candidate
        fallback = os.path.join(os.path.expanduser("~"), "tmp")
        os.makedirs(fallback, exist_ok=True)
        return fallback

    def _read_minimum_go_version(self):
        """Parse the `go` directive from the upstream go.mod."""
        go_mod = os.path.join(self.source_folder, "go.mod")
        with open(go_mod, "r", encoding="utf-8") as fh:
            for line in fh:
                stripped = line.strip()
                if stripped.startswith("go ") and not stripped.startswith("go mod"):
                    return stripped.split()[1]
        return None

    def _verify_go_manifest_entry(self, version):
        """Cross-check the pinned toolchain sha256 against the official JSON.

        Uses the embedded verified pin (with a warning) if the manifest
        cannot be reached.
        """
        import urllib.request

        want = f"go{version}"
        for url in GO_MANIFEST_URLS:
            try:
                with urllib.request.urlopen(url, timeout=30) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
            except Exception as exc:  # network/proxy hiccup, try mirror
                self.output.warning(f"Go manifest unreachable ({url}): {exc}")
                continue
            for release in data:
                if release.get("version") != want:
                    continue
                for entry in release.get("files", []):
                    if (
                        entry.get("os") == "linux"
                        and entry.get("arch") == "arm64"
                        and entry.get("kind") == "archive"
                    ):
                        official_sha = entry.get("sha256", "")
                        if official_sha != GO_BOOTSTRAP_SHA256:
                            raise RuntimeError(
                                f"Official Go sha256 mismatch for {want}: "
                                f"manifest={official_sha} "
                                f"pinned={GO_BOOTSTRAP_SHA256}"
                            )
                        self.output.info(
                            f"Toolchain {want} sha256 verified against go.dev manifest"
                        )
                        return
        self.output.warning(
            "Go release manifest not reachable; using embedded verified sha256 pin"
        )

    def _bootstrap_go(self):
        """Download, verify and unpack the official static Go toolchain."""
        if os.path.isfile(self._go_bin):
            return self._go_root_dir

        minimum = self._read_minimum_go_version()
        self.output.info(f"Upstream go.mod requires Go >= {minimum}")
        self._verify_go_manifest_entry(GO_BOOTSTRAP_VERSION)

        go_parent = os.path.dirname(self._go_root_dir)
        os.makedirs(go_parent, exist_ok=True)
        tarball = os.path.join(
            go_parent, f"go{GO_BOOTSTRAP_VERSION}.linux-arm64.tar.gz"
        )

        if not os.path.isfile(tarball):
            last_error = None
            for url_tmpl in GO_DL_URLS:
                try:
                    filename = f"go{GO_BOOTSTRAP_VERSION}.linux-arm64.tar.gz"
                    self.run(
                        f'curl -fL --retry 3 -o "{tarball}" '
                        f'"{url_tmpl.format(filename=filename)}"'
                    )
                    break
                except Exception as exc:  # try the mirror
                    last_error = exc
                    self.output.warning(f"toolchain download failed: {exc}")
            else:
                raise RuntimeError(f"Unable to download Go toolchain: {last_error}")

        # Verify the downloaded archive against the official sha256.
        digest = hashlib.sha256()
        with open(tarball, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                digest.update(chunk)
        actual_sha = digest.hexdigest()
        if actual_sha != GO_BOOTSTRAP_SHA256:
            raise RuntimeError(
                f"Go toolchain sha256 mismatch: got {actual_sha}, "
                f"expected {GO_BOOTSTRAP_SHA256}"
            )
        self.output.info("Downloaded Go toolchain sha256 OK")

        with tarfile.open(tarball, "r:gz") as tar:
            tar.extractall(go_parent)
        if not os.path.isfile(self._go_bin):
            raise RuntimeError("Go toolchain extraction failed")

        # Remove the tarball to keep the build folder lean (JC friendly).
        try:
            os.remove(tarball)
        except OSError:
            pass
        return self._go_root_dir

    # -- ELF signing (required by HarmonyOS) -----------------------------
    def _is_elf(self, path):
        try:
            with open(path, "rb") as fh:
                return fh.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _strip_file(self, path):
        strip_bin = os.path.join(HNP_BIN, "strip")
        if not os.path.isfile(strip_bin):
            strip_bin = shutil.which("strip")
        if strip_bin and os.path.isfile(strip_bin):
            self.run(f'"{strip_bin}" "{path}"')

    def _signer_path(self):
        """Locate the HarmonyOS ELF self-signing tool."""
        signer = os.path.join(HNP_BIN, "binary-sign-tool")
        if not os.path.isfile(signer):
            signer = shutil.which("binary-sign-tool") or signer
        return signer if signer and os.path.isfile(signer) else None

    def _sign_one(self, signer, path):
        """Self-sign one ELF in place, retrying via GNU strip on failure.

        Older Go-linked ELF layouts make the signer fail with
        "Failed to save 4K data to .codesign section"; running GNU strip
        first normalises the section headers and fixes it.
        """
        tmp = f"{path}.signed"
        try:
            self.run(
                f'"{signer}" sign -inFile "{path}" -outFile "{tmp}" '
                f'-selfSign 1 -signAlg SHA256withECDSA'
            )
            shutil.move(tmp, path)
        except Exception:
            self._strip_file(path)
            self.run(
                f'"{signer}" sign -inFile "{path}" -outFile "{tmp}" '
                f'-selfSign 1 -signAlg SHA256withECDSA'
            )
            shutil.move(tmp, path)
        try:
            os.chmod(path, 0o755)
        except OSError:
            pass

    def _sign_toolchain(self, goroot):
        """OHOS: self-sign every ELF shipped inside the private GOROOT.

        On HarmonyOS unsigned ELF files cannot be executed (execve returns
        EACCES / "Permission denied"). The official Go tarball carries no
        .codesign section, so not only bin/go but also the pkg/tool tools
        (compile, link, asm, vet, ...) must be self-signed before the
        build can run.
        """
        if str(self.settings.os) != "OHOS":
            return
        signer = self._signer_path()
        if not signer:
            self.output.warning(
                "binary-sign-tool not found, GOROOT ELF files left unsigned"
            )
            return

        # Only the executable tools actually invoked at build time need
        # signing: bin/go (and the rest of bin/) plus the compile/link/asm
        # tools under pkg/tool. Test ELF samples under src/**/testdata and
        # race .syso blobs are never executed by the build, so they are
        # deliberately skipped (signing them also mutates Go test fixtures).
        sign_dirs = [os.path.join(goroot, "bin"), os.path.join(goroot, "pkg", "tool")]
        elf_files = []
        for sign_dir in sign_dirs:
            if not os.path.isdir(sign_dir):
                continue
            for dirpath, _, filenames in os.walk(sign_dir):
                for name in filenames:
                    path = os.path.join(dirpath, name)
                    if self._is_elf(path):
                        elf_files.append(path)
        for path in elf_files:
            self._sign_one(signer, path)
        if elf_files:
            self.output.info(
                f"Self-signed {len(elf_files)} GOROOT ELF file(s) in {goroot}"
            )

    def _sign_elf(self, path):
        """Self-sign the packaged kustomizer binary for HarmonyOS execution."""
        if str(self.settings.os) != "OHOS":
            return
        signer = self._signer_path()
        if not signer:
            self.output.warning("binary-sign-tool not found, skipping signing")
            return
        self._sign_one(signer, path)

    # -- Build -----------------------------------------------------------
    def build(self):
        goroot = self._bootstrap_go()
        self._sign_toolchain(goroot)
        tmpdir = self._writable_tmp()

        # Private Go caches inside the build folder (no host-global state).
        gocache = os.path.join(self.build_folder, "_gocache")
        gomodcache = os.path.join(self.build_folder, "_gomodcache")
        os.makedirs(gocache, exist_ok=True)
        os.makedirs(gomodcache, exist_ok=True)

        env_prefix = (
            f'env TMPDIR="{tmpdir}" GOROOT="{goroot}" '
            f'GOPROXY="{GO_PROXY}" GOCACHE="{gocache}" '
            f'GOMODCACHE="{gomodcache}" GOTOOLCHAIN=local GOFLAGS=-mod=mod '
            f'CGO_ENABLED=0 GOOS=linux GOARCH=arm64'
        )

        # Fully static build via the internal linker; -X injects the upstream
        # main.VERSION variable (see cmd/kustomizer/main.go).
        ldflags = "-s -w -X main.VERSION=2.2.1"
        self.run(
            f'{env_prefix} "{self._go_bin}" build -trimpath '
            f'-ldflags="{ldflags}" -o kustomizer ./cmd/kustomizer'
        )

        binary = os.path.join(self.build_folder, "kustomizer")
        if not os.path.isfile(binary):
            raise RuntimeError("kustomizer binary was not produced")
        self.output.info(f"Built static kustomizer ({os.path.getsize(binary)} bytes)")

    # -- Package / info --------------------------------------------------
    def package(self):
        copy(self, "kustomizer", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"))
        self._sign_elf(os.path.join(self.package_folder, "bin", "kustomizer"))

    def package_info(self):
        # Pure CLI tool: no libraries, only the bin directory.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
