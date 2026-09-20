#!/usr/bin/env python3
"""Conan recipe for buildah 1.44.0 — Go-based OCI container image builder.

Adapted for HarmonyOS PC (arm64) following the self-bootstrapped Go toolchain
pattern of wego/tlsx: no pre-installed Go is assumed on the build host. The
recipe downloads the official Go SDK (1.25.8 — go.mod requires >= 1.25.6),
signs its toolchain ELFs (HarmonyOS E128: unsigned ELFs cannot be execve'd),
and routes the Go linker workspace to an ext2 partition (E166: HMDFS does not
support the linker's mmap MAP_SHARED; /data/storage/el2/... is tmpfs-backed).

Build is CGO_ENABLED=0 producing a static binary. All features normally
gated behind cgo libraries (seccomp, apparmor, btrfs, libsubid, systemd,
sqlite) are excluded via upstream build tags, matching the exclusion set of
distroless/pure-Go builds. The mkcw embed is switched from entrypoint_amd64
to entrypoint_arm64 (patches 0001/0002) because the embedded entrypoint must
match the target architecture.

Patch 0003 makes the binary actually usable on HarmonyOS: the HongMeng kernel
delivers SIGSYS (killing the process) for unimplemented syscall numbers such
as open_tree(2)/openat2(2) instead of returning -ENOSYS, so the upstream
availability probes in filepath-securejoin/pathrs-lite would crash buildah at
startup (buildah --version died with SIGSYS before this patch). With the
probe patched to detect the HongMeng kernel at runtime (uname release) and
take the upstream legacy code path, `buildah --version` / `--help` run
cleanly. Plain-Linux behaviour is unchanged.

Known platform limitation (needs expert follow-up, see notes.md): rootless
container storage requires user namespaces; creating them (fork +
CLONE_NEWUSER) is denied by the HarmonyOS kernel policy, so commands that
touch container storage (images/from/build) cannot complete as an
unprivileged user.
"""
import hashlib
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class BuildahConan(ConanFile):
    name = "buildah"
    version = "1.44.0"
    description = "A tool that facilitates building OCI container images"
    license = "Apache-2.0"
    homepage = "https://github.com/containers/buildah"
    url = "https://github.com/containers/buildah"
    package_type = "application"
    topics = ("containers", "oci", "image", "builder", "go")

    # All four settings declared (L0p): compiler/build_type do not drive the
    # Go build but are required by the OHOS profile gate.
    settings = "os", "compiler", "build_type", "arch"

    _go_version = "1.25.8"  # go.mod requires >= 1.25.6
    _go_archives = {
        "amd64": (
            [
                "https://golang.google.cn/dl/go1.25.8.linux-amd64.tar.gz",
                "https://dl.google.com/go/go1.25.8.linux-amd64.tar.gz",
            ],
            "ceb5e041bbc3893846bd1614d76cb4681c91dadee579426cf21a63f2d7e03be6",
        ),
        "arm64": (
            [
                "https://golang.google.cn/dl/go1.25.8.linux-arm64.tar.gz",
                "https://dl.google.com/go/go1.25.8.linux-arm64.tar.gz",
            ],
            "7d137f59f66bb93f40a6b2b11e713adc2a9d0c8d9ae581718e3fad19e5295dc7",
        ),
    }

    # Feature tags excluded because the cgo/system libraries they require are
    # not available on HarmonyOS (btrfs, libseccomp, libapparmor, libsubid,
    # systemd, sqlite) — see notes.md.
    _build_tags = (
        "containers_image_openpgp "
        "exclude_graphdriver_btrfs "
        "exclude_seccomp "
        "exclude_apparmor "
        "no_libsubid "
        "no_systemd "
        "no_sqlite "
        "nolinkednet"
    )

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        env = Environment()
        # Pure-Go static build (verified: all cgo-gated features are excluded
        # via build tags), matching the merged wego/tlsx/bbrew Go recipes.
        env.define("CGO_ENABLED", "0")
        env.define("GOOS", "linux")  # OHOS pre-adaptation: linux triplet
        env.define("GOARCH", self._goarch())
        env.define("GOPROXY", os.environ.get("GOPROXY", "https://goproxy.cn,https://proxy.golang.org,direct"))
        env.define("GOSUMDB", os.environ.get("GOSUMDB", "sum.golang.google.cn"))
        env.define("GOTOOLCHAIN", "local")

        ws = self._go_workspace()
        env.define("TMPDIR", os.path.join(ws, "tmp"))
        env.define("GOTMPDIR", os.path.join(ws, "tmp"))
        env.define("GOCACHE", os.path.join(ws, "go-build-cache"))
        env.define("GOMODCACHE", os.path.join(ws, "go-mod-cache"))

        go = self._go_executable()
        env.define("GOROOT", self._goroot_for_go(go))
        env.prepend_path("PATH", os.path.dirname(go))
        env.vars(self).save_script("buildah_go_env")

    def build(self):
        apply_conandata_patches(self)
        go = self._go_executable()
        self._check_go_version(go)
        self.run(f'"{go}" mod download', cwd=self.source_folder, env=["buildah_go_env"])

        # 1) mkcw entrypoint for arm64 (go:embed pulls in the .gz artifact).
        #    Upstream Makefile cross-builds the amd64 variant by default; on
        #    arm64 we must embed the matching architecture (patches 0001/0002).
        self.run(
            f'"{go}" build -buildvcs=false -ldflags "-E _start -s" '
            f'-o internal/mkcw/embed/entrypoint_arm64 ./internal/mkcw/embed',
            cwd=self.source_folder, env=["buildah_go_env"],
        )
        self.run("gzip -k9nf internal/mkcw/embed/entrypoint_arm64",
                 cwd=self.source_folder, env=["buildah_go_env"])

        # 2) Main buildah binary. The linker output goes to the ext2
        #    workspace first (E166), then is signed and copied back.
        ws = self._go_workspace()
        link_out = os.path.join(ws, "link-out", "buildah")
        self.run(
            f'"{go}" build -buildvcs=false '
            f'-ldflags "-X main.GitCommit=v{self.version} -X main.buildInfo=1747804800" '
            f'-tags "{self._build_tags}" -o "{link_out}" ./cmd/buildah',
            cwd=self.source_folder, env=["buildah_go_env"],
        )
        self._sign_elf_if_ohos(link_out)
        out_bin = os.path.join(self.build_folder, "bin")
        os.makedirs(out_bin, exist_ok=True)
        shutil.copy2(link_out, os.path.join(out_bin, "buildah"))

    def package(self):
        copy(self, "buildah", os.path.join(self.build_folder, "bin"),
             os.path.join(self.package_folder, "bin"))
        completions = os.path.join(self.source_folder, "share", "bash-completion", "completions")
        if os.path.isdir(completions):
            copy(self, "buildah", completions,
                 os.path.join(self.package_folder, "share", "bash-completion", "completions"))
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]

    # ---------- Go toolchain helpers (pattern from wego 2.4 / tlsx 1.2.2) ----------

    def _go_workspace(self):
        # E166: the Go linker needs mmap-capable tmpfs on OHOS; the ext2
        # partition /data/storage/el2/... works. Falls back to the Conan
        # build folder on Linux where /tmp is writable.
        base = os.environ.get("OHC_GO_WORKSPACE")
        if base:
            ws = os.path.join(base, f"buildah-{self.version}")
        elif str(self.settings.os) == "OHOS":
            ws = os.path.join("/data/storage/el2/base/haps/entry/files", f"buildah-{self.version}-build")
        else:
            ws = os.path.join(self.build_folder, "go-workspace")
        for sub in ("", "tmp", "go-build-cache", "go-mod-cache", "link-out"):
            os.makedirs(os.path.join(ws, sub), exist_ok=True)
        return ws

    def _ensure_go_toolchain(self):
        """Download the official Go SDK with SHA256 verification; sign its
        tool binaries on OHOS (E128). No-op when a usable `go` already
        exists on PATH/GO/GOROOT_TMP."""
        go = shutil.which("go") or os.environ.get("GO") or os.environ.get("GOROOT_TMP")
        if go and self._go_version_is_supported(go):
            return go
        arch = self._go_host_arch()
        urls, expected_sha = self._go_archives[arch]
        sdk_dir = os.path.join(os.path.expanduser("~"), ".goenv", "versions", f"go{self._go_version}")
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
                raise ConanInvalidConfiguration(
                    f"Failed to download Go {self._go_version} SDK for {arch}")
            actual_sha = self._sha256(archive_path)
            if actual_sha != expected_sha:
                raise ConanInvalidConfiguration(
                    f"Go SDK SHA256 mismatch: {actual_sha} != {expected_sha}")
            self.run(f'tar -xzf "{archive_path}" -C "{sdk_dir}" --strip-components=1', env=[])
            os.remove(archive_path)
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
            # Linux CI/builders without the OHOS sign tool still produce a
            # valid package (the binary just needs re-signing before use).
            self.output.warning(f"binary-sign-tool not found: {sign_tool}; skipping ELF signing")
            return
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
            r = subprocess.run([objcopy, "--remove-section", ".codesign", path],
                               capture_output=True, timeout=10)
            if r.returncode not in (0, 1):
                raise ConanInvalidConfiguration(
                    f"llvm-objcopy failed for {path}: rc={r.returncode}")
        tmp = path + ".signed.tmp"
        for _attempt in range(3):
            r = subprocess.run(
                [sign_tool, "sign", "-inFile", path, "-outFile", tmp, "-selfSign", "1"],
                capture_output=True, text=True, timeout=30,
            )
            if r.returncode == 0 and os.path.isfile(tmp):
                shutil.move(tmp, path)
                os.chmod(path, 0o755)
                return
        raise ConanInvalidConfiguration(f"ELF signing failed for {path}")

    def _goarch(self):
        arch = str(self.settings.arch)
        if arch in ("x86_64", "amd64"):
            return "amd64"
        if arch in ("armv8", "aarch64", "arm64"):
            return "arm64"
        return arch

    def _go_executable(self):
        for c in (os.environ.get("GO"), os.environ.get("GOROOT_TMP"), shutil.which("go")):
            if c and os.path.isfile(c) and self._go_version_is_supported(c):
                return c
        return self._ensure_go_toolchain()

    def _go_version_is_supported(self, go):
        try:
            return self._go_version_tuple(go) >= (1, 25, 6)
        except Exception:
            return False

    def _check_go_version(self, go):
        if not self._go_version_is_supported(go):
            raise ConanInvalidConfiguration(
                f"Go toolchain at {go} is older than 1.25.6 (required by go.mod)")

    @staticmethod
    def _go_version_tuple(go):
        r = subprocess.run([go, "version"], capture_output=True, text=True, timeout=10)
        m = re.search(r"go(\d+)\.(\d+)\.(\d+)", r.stdout)
        if not m:
            raise ValueError(f"cannot parse go version: {r.stdout!r}")
        return tuple(int(x) for x in m.groups())

    @staticmethod
    def _goroot_for_go(go):
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
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()
