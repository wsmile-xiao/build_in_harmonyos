#!/usr/bin/env python3
"""Conan recipe for leaps 0.9.1 — Go toolchain self-bootstrap.

leaps is a collaborative web-based pair-programming editor (operational
transform server) written in pure Go (73 .go files, 0 C/C++). go.mod
requires go 1.12; the whole dependency tree is CGO-free, so
`CGO_ENABLED=0` produces a static binary of the platform-whitelisted
shape.

Go toolchain bootstrap follows the caddy/2.11.2-r1 precedent (in-repo,
CI-proven; same pinned go1.25.12 sha256): the official
go1.25.12.linux-arm64 distribution tarball (golang.google.cn +
dl.google.com, sha256 pinned) is extracted into the build folder, every
ELF is self-signed with the SDK's binary-sign-tool (E549: HarmonyOS PC
enforces .codesign on executables), and the built leaps binary is signed
again in build().

E549/E331 hard constraint (AGENTS.md, 2026-09-07): the Go linker mmaps
its output with PROT_EXEC, which hmdfs denies ("mapping output file
failed"). The whole link domain (GOTMPDIR + -o output) lives in the el2
app-files path (leaps-conan-go), then the binary is copied back for
signing. Module downloads go through goproxy.cn with
GOSUMDB=sum.golang.google.cn; module integrity is verified by go.sum.
"""

import glob
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, download, export_conandata_patches, get, unzip
from conan.tools.layout import basic_layout


class LeapsConan(ConanFile):
    name = "leaps"
    version = "0.9.1"
    description = "Collaborative web-based pair-programming editor (operational transforms, Go)"
    license = "MIT"
    homepage = "https://github.com/Jeffail/leaps"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    _go_version = "1.25.12"
    _go_dist = (
        "https://golang.google.cn/dl/go{v}.linux-arm64.tar.gz",
        "https://dl.google.com/go/go{v}.linux-arm64.tar.gz",
    )
    # Official sha256 (same artifact cc-connect/1.4.1 + caddy/2.11.2-r1 pin, CI-proven).
    _go_sha256 = "8b5884aef89600aef5b0b051fb971f11f49bb996521e911f30f02a66884f7bd2"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"leaps supports Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ── ELF signing (E549) ──────────────────────────────────────────

    def _find_tool(self, name):
        for d in sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/bin")):
            p = os.path.join(d, name)
            if os.path.isfile(p):
                return p
        for d in ("/data/service/hnp/bin",):
            p = os.path.join(d, name)
            if os.path.isfile(p):
                return p
        return shutil.which(name)

    def _sign_elf(self, binary_path):
        objcopy = self._find_tool("llvm-objcopy")
        sign_tool = self._find_tool("binary-sign-tool")
        if not sign_tool:
            raise ConanException("binary-sign-tool not found (required by E549)")
        if not objcopy:
            raise ConanException("llvm-objcopy not found (required by E549)")
        subprocess.run(
            [objcopy, "--remove-section", ".codesign", binary_path],
            capture_output=True, timeout=30,
        )
        tmp = binary_path + ".signed.tmp"
        for _ in range(3):
            r = subprocess.run(
                [sign_tool, "sign", "-inFile", binary_path,
                 "-outFile", tmp, "-selfSign", "1"],
                capture_output=True, text=True, timeout=60,
            )
            if r.returncode == 0 and os.path.isfile(tmp):
                shutil.move(tmp, binary_path)
                os.chmod(binary_path, 0o775)
                return
        if os.path.exists(tmp):
            os.remove(tmp)
        raise ConanException(f"signing failed for {binary_path}")

    def _sign_tree(self, root):
        count = 0
        for current, _, files in os.walk(root):
            for name in files:
                path = os.path.join(current, name)
                try:
                    with open(path, "rb") as handle:
                        if handle.read(4) != b"\x7fELF":
                            continue
                except OSError:
                    continue
                self._sign_elf(path)
                count += 1
        self.output.info(f"signed {count} ELF files under {root}")

    # ── Go toolchain bootstrap ──────────────────────────────────────

    def _bootstrap_go(self):
        archive = os.path.join(
            self.build_folder, f"go{self._go_version}.linux-arm64.tar.gz"
        )
        if not os.path.isfile(archive):
            urls = [m.format(v=self._go_version) for m in self._go_dist]
            download(self, urls, filename=archive,
                     sha256=self._go_sha256, retry=2)
        goroot_parent = os.path.join(self.build_folder, "go-toolchain")
        goroot = os.path.join(goroot_parent, "go")
        if not os.path.isdir(goroot):
            unzip(self, archive, destination=goroot_parent)
        if not os.path.isfile(os.path.join(goroot, "bin", "go")):
            raise ConanException("go-toolchain/go/bin/go missing after bootstrap")
        # E549: sign every ELF of the toolchain (go, gofmt, pkg/tool/*).
        self._sign_tree(goroot)
        return goroot

    def _ca_bundle(self):
        candidates = [
            os.path.expanduser("~/usr/local/ssl/cert.pem"),
            os.path.expanduser(
                "~/usr/local/lib/python3.12/site-packages/certifi/cacert.pem"
            ),
            "/etc/ssl/cert.pem",
            "/system/etc/security/cacerts.pem",
        ]
        for candidate in candidates:
            if os.path.isfile(candidate):
                return candidate
        return None

    # ── build ───────────────────────────────────────────────────────

    def build(self):
        apply_conandata_patches(self)
        goroot = self._bootstrap_go()
        build = self.build_folder
        env = os.environ

        go_cache = os.path.join(build, "gocache")
        go_mod = os.path.join(build, "gomodcache")
        for d in (go_cache, go_mod):
            os.makedirs(d, exist_ok=True)
        # E549 sibling: the Go linker mmaps its output with PROT_EXEC,
        # which hmdfs denies ("mapping output file failed"). Keep the
        # whole link domain (GOTMPDIR + -o output) in the el2 app-files
        # path (writable + linker-proven), then copy the binary back for
        # signing.
        go_work = os.environ.get(
            "OHOS_GO_WORKDIR",
            "/data/storage/el2/base/haps/entry/files/leaps-conan-go",
        )
        go_tmp = os.path.join(go_work, "gotmp")
        os.makedirs(go_tmp, exist_ok=True)
        ca = self._ca_bundle()
        parts = [
            f'PATH="{goroot}/bin:{env.get("PATH", "")}"',
            f'GOROOT="{goroot}"',
            "GOTOOLCHAIN=local",
            "CGO_ENABLED=0",
            'GOPROXY="https://goproxy.cn,direct"',
            'GOSUMDB="sum.golang.google.cn"',
            f'GOCACHE="{go_cache}"',
            f'GOMODCACHE="{go_mod}"',
            f'GOTMPDIR="{go_tmp}"',
            'GOFLAGS="-mod=mod"',
        ]
        if ca:
            parts.append(f'SSL_CERT_FILE="{ca}"')
        env_args = " ".join(parts)

        workspace = self.source_folder
        link_out = os.path.join(go_work, self.version)
        os.makedirs(link_out, exist_ok=True)
        linked = os.path.join(link_out, "leaps")
        ldflags = "-s -w"
        self.run(
            f'{env_args} go build -ldflags "{ldflags}" -o "{linked}" ./cmd/leaps',
            cwd=workspace,
        )
        out = os.path.join(build, "leaps")
        if not os.path.isfile(linked):
            raise ConanException("leaps binary missing after build")
        shutil.copy2(linked, out)
        # E549: the built binary is unsigned — sign before packaging.
        self._sign_elf(out)

    def package(self):
        copy(self, "leaps", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        # Tool package (R38): commands.json at software level declares the
        # leaps command; no libraries, no consumer linkage.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
