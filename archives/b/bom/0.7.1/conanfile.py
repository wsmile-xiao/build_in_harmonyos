#!/usr/bin/env python3
"""Conan recipe for bom 0.7.1 — Kubernetes SIGS SPDX SBOM command line tool.

Go toolchain supply follows the merged chkbit/caddy precedent: the official
CI runner (AppSpawn sandbox, minimal PATH) has no usable preinstalled go, so
the recipe first probes GO/GOROOT/standard local install locations and, if
none satisfies go.mod (go 1.24.0), bootstraps a pinned Go SDK from fixed
mirror URLs with a hard-coded SHA256 into a sandbox-writable workspace
(OHOS_GO_WORKDIR, default /data/storage/el2/base/haps/entry/files/bom-conan-go).
Every ELF inside the SDK is self-signed with binary-sign-tool before use
(E318: HarmonyOS refuses to execute unsigned ELF).

Upstream Go test packages are executed in build() (Layer 1,
TEST_QUALITY_SPEC) per knowledge entry E318: compile each package test
binary with "go test -c", self-sign it, then run it from the original
package source directory.
"""

import os
import platform
import re
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.env import Environment
from conan.tools.files import chdir, copy, get
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"

UPSTREAM_TEST_PACKAGES = [
    "pkg/license",
    "pkg/osinfo",
    "pkg/provenance",
    "pkg/query",
    "pkg/spdx",
]

# These spdx tests require direct egress to Google endpoints
# (registry: *.docker.pkg.dev; vanity import: golang.org ?go-get=1 metadata).
# On the OHOS build device that network path is unavailable (dial tcp i/o
# timeout), so they are skipped with an explicit -test.skip pattern and
# declared in test_package/MANIFEST.yml. Everything else runs unmodified.
NETWORK_BLOCKED_TESTS = {
    "pkg/spdx": "^(TestPullImagesToArchive|TestGetImageReferences|TestToSPDXPackage)$",
}

# Pinned bootstrap SDK (same values as the merged caddy 2.11.2-r1 recipe;
# arm64 SHA256 re-verified against golang.google.cn on the build device).
_GO_VERSION = "1.25.12"
_GO_ARCHIVES = {
    "amd64": (
        [
            "https://golang.google.cn/dl/go1.25.12.linux-amd64.tar.gz",
            "https://dl.google.com/go/go1.25.12.linux-amd64.tar.gz",
        ],
        "234828b7a89e0e303d2556310ee549fbcf253d28de937bac3da13d6294262ac1",
    ),
    "arm64": (
        [
            "https://golang.google.cn/dl/go1.25.12.linux-arm64.tar.gz",
            "https://dl.google.com/go/go1.25.12.linux-arm64.tar.gz",
        ],
        "8b5884aef89600aef5b0b051fb971f11f49bb996521e911f30f02a66884f7bd2",
    ),
}

# Generic tool locations on OHOS build hosts, probed when a tool is not on
# PATH and not contributed by the profile [buildenv].
GENERIC_TOOL_DIRS = [
    os.path.expanduser("~/usr/local/bin"),
    "/data/service/hnp/bin",
    "/usr/local/bin",
    "/usr/bin",
]


class BomConan(ConanFile):
    name = "bom"
    version = "0.7.1"
    description = "Kubernetes SIGS tool for creating and working with SPDX SBOM documents"
    license = "Apache-2.0"
    homepage = "https://github.com/kubernetes-sigs/bom"
    url = "https://github.com/kubernetes-sigs/bom"
    topics = ("spdx", "sbom", "supply-chain", "cli")
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("bom is prepared for Linux/OHOS targets only")

    # ── environment ──

    def generate(self):
        env = Environment()
        # Pure Go; CGO_ENABLED=0 keeps the binary static and self-contained.
        env.define("CGO_ENABLED", "0")
        env.define("GOOS", self._goos())
        env.define("GOARCH", self._goarch())
        env.define("GOPROXY", os.environ.get("GOPROXY", "https://goproxy.cn,https://proxy.golang.org,direct"))
        env.define("GOSUMDB", os.environ.get("GOSUMDB", "sum.golang.google.cn"))
        env.define("GOTOOLCHAIN", "local")
        env.define("GOFLAGS", "-mod=mod")

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

        env.vars(self).save_script("bom_go_env")

    # ── build ──

    def build(self):
        go = self._go_executable()
        self._check_go_version(go)
        sign_tool = self._find_tool(
            "binary-sign-tool",
            "HarmonyOS refuses to execute unsigned ELF binaries (E318); the produced "
            "binaries must be self-signed before they can run.",
        )

        out_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(out_dir, exist_ok=True)
        # Link into the non-conan workspace on OHOS (HMDFS mmap workaround,
        # chkbit/caddy precedent), then copy the signed binary back.
        if str(self.settings.os) == "OHOS":
            link_out_dir = os.path.join(self._go_workspace(), "link-out")
        else:
            link_out_dir = out_dir
        os.makedirs(link_out_dir, exist_ok=True)
        linked_exe = os.path.join(link_out_dir, "bom")
        final_exe = os.path.join(out_dir, "bom")

        # 1) the product itself
        with chdir(self, self.source_folder):
            self.run('"%s" build -o "%s" ./cmd/bom' % (go, linked_exe), env=["bom_go_env"])
        self._sign_elf(sign_tool, linked_exe)
        if os.path.abspath(linked_exe) != os.path.abspath(final_exe):
            shutil.copy2(linked_exe, final_exe)

        # 2) upstream Go test suite (E318: compile-sign-run per package)
        if str(self.settings.os) == "OHOS":
            testbin = os.path.join(self._go_workspace(), "test-out")
        else:
            testbin = os.path.join(self.build_folder, "testbin")
        os.makedirs(testbin, exist_ok=True)
        for pkg in UPSTREAM_TEST_PACKAGES:
            name = pkg.rsplit("/", 1)[-1]
            test_bin = os.path.join(testbin, name + ".test")
            self.output.info("upstream test package: %s" % pkg)
            with chdir(self, self.source_folder):
                self.run('"%s" test -c -o "%s" ./%s' % (go, test_bin, pkg), env=["bom_go_env"])
            self._sign_elf(sign_tool, test_bin)
            skip = NETWORK_BLOCKED_TESTS.get(pkg, "")
            cmd = '"%s" -test.count=1 -test.timeout=15m' % test_bin
            if skip:
                cmd = '%s -test.skip="%s"' % (cmd, skip)
            with chdir(self, os.path.join(self.source_folder, pkg)):
                self.run(cmd, env=["bom_go_env"])

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        copy(self, "bom", src=os.path.join(self.build_folder, "bin"), dst=bindir, keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []

    # ── generic tool discovery (binary-sign-tool) ──

    def _buildenv_path_dirs(self):
        """PATH directories contributed by the profile [buildenv].

        Conan materializes profile [buildenv] only into shell scripts in the
        generators folder (conanbuild.sh sourcing the conanbuildenv-*.sh
        aggregates); it does not inject those values into this recipe's
        Python process. Controlled CI environments (e.g. a buildbot runner
        starting from a minimal PATH) therefore expose the profile tool
        directories only through those materialized files, so parse them
        back out. Aggregated env files are generated before build() runs.
        """
        dirs = []
        folder = self.generators_folder
        if not folder or not os.path.isdir(folder):
            return dirs
        for name in sorted(os.listdir(folder)):
            if not name.startswith("conanbuild") or not name.endswith(".sh"):
                continue
            script = os.path.join(folder, name)
            if not os.path.isfile(script):
                continue
            try:
                with open(script, "r", encoding="utf-8", errors="replace") as handle:
                    content = handle.read()
            except OSError as exc:
                self.output.warning("bom: cannot read %s: %s" % (script, exc))
                continue
            for line in content.splitlines():
                stripped = line.strip()
                if not stripped.startswith("export PATH="):
                    continue
                value = stripped[len("export PATH="):].strip().strip("'\"")
                for entry in value.split(os.pathsep):
                    entry = entry.strip()
                    # Skip shell placeholders such as ${PATH:+:$PATH} / $PATH.
                    if not entry or "$" in entry or "{" in entry or "}" in entry:
                        continue
                    if entry not in dirs and os.path.isdir(entry):
                        dirs.append(entry)
        return dirs

    def _find_tool(self, name, hint):
        """Locate an external tool required by build().

        Search order:
        1. OHOS_<NAME> environment override (e.g. OHOS_BINARY_SIGN_TOOL).
        2. shutil.which() on the inherited PATH.
        3. PATH directories the profile [buildenv] materialized into the
           generators folder (conanbuild.sh / conanbuildenv-*.sh) — the only
           place those directories are visible when the CI runner starts
           from a minimal PATH.
        4. A few generic tool locations on OHOS build hosts.

        The go toolchain is intentionally NOT resolved here: official CI has
        no discoverable go, so _go_executable() probes standard locations
        and falls back to the pinned SDK bootstrap instead.
        """
        override = os.environ.get("OHOS_" + name.upper().replace("-", "_"))
        if override:
            return override

        found = shutil.which(name)
        if found:
            return found

        for directory in self._buildenv_path_dirs() + GENERIC_TOOL_DIRS:
            candidate = os.path.join(directory, name)
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                self.output.info("bom: %s resolved to %s" % (name, candidate))
                return candidate

        raise ConanException(
            "%s not found (searched PATH, profile [buildenv] PATH materialized "
            "in the generators folder, and common tool locations). %s" % (name, hint)
        )

    # ── ELF signing (E318) ──

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

    def _sign_elf(self, sign_tool, path):
        """Self-sign an ELF so HarmonyOS will execute it (E318)."""
        if self._has_ohos_signature(path):
            os.chmod(path, 0o755)
            return
        self.run('"%s" sign -inFile "%s" -outFile "%s.signed" -selfSign 1' % (sign_tool, path, path))
        os.replace("%s.signed" % path, path)
        os.chmod(path, 0o755)

    # ── Go toolchain (chkbit/caddy bootstrap precedent) ──

    def _go_workspace(self):
        if str(self.settings.os) != "OHOS":
            root = os.path.join(self.build_folder, ".go-work")
        else:
            root = os.environ.get(
                "OHOS_GO_WORKDIR",
                "/data/storage/el2/base/haps/entry/files/bom-conan-go",
            )
        workspace = os.path.join(root, self.version)
        for child in (
            "tmp",
            "go-build-cache",
            "go-mod-cache",
            "link-out",
            "test-out",
            "go-sdk",
        ):
            Path(workspace, child).mkdir(parents=True, exist_ok=True)
        return workspace

    def _ensure_go_toolchain(self):
        host_arch = self._go_host_arch()
        if host_arch not in _GO_ARCHIVES:
            raise ConanInvalidConfiguration(f"Go SDK bootstrap is not prepared for host arch: {host_arch}")

        sdk_root = os.path.join(self._go_workspace(), "go-sdk", f"go{_GO_VERSION}-{host_arch}")
        goroot = os.path.join(sdk_root, "go")
        gobin = os.path.join(goroot, "bin", "go")
        if not os.path.isfile(gobin):
            urls, sha256 = _GO_ARCHIVES[host_arch]
            self.output.info(f"bom: no usable preinstalled go; bootstrapping Go {_GO_VERSION} from {urls[0]}")
            get(self, url=urls, sha256=sha256, destination=sdk_root, strip_root=False)
        self._sign_go_sdk_if_ohos(goroot)
        return gobin

    def _sign_go_sdk_if_ohos(self, goroot):
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
                self._sign_elf_shallow(candidate)
        Path(marker).write_text("signed\n", encoding="utf-8")

    def _sign_elf_shallow(self, path):
        """Sign an SDK ELF without recursion, bypassing the .codesign skip.

        SDK ELFs are unsigned when freshly extracted, so the plain sign
        command is used directly instead of _sign_elf().
        """
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            raise ConanInvalidConfiguration("binary-sign-tool is required to sign the OHOS Go SDK")
        signed = f"{path}.signed"
        subprocess.check_call([
            signer,
            "sign",
            "-selfSign",
            "1",
            "-inFile",
            path,
            "-outFile",
            signed,
            "-signAlg",
            "SHA256withECDSA",
        ])
        shutil.move(signed, path)
        os.chmod(path, 0o755)

    def _go_executable(self):
        candidates = []
        if os.environ.get("GO"):
            candidates.append(os.environ["GO"])
        if os.environ.get("GOROOT"):
            candidates.append(os.path.join(os.environ["GOROOT"], "bin", "go"))
        candidates.extend([
            os.path.expanduser("~/usr/local/go/bin/go"),
            "/data/service/hnp/bin/go",
        ])
        found = shutil.which("go")
        if found:
            candidates.append(found)

        for candidate in candidates:
            if candidate and os.path.isfile(candidate) and self._go_version_is_supported(candidate):
                self.output.info("bom: go resolved to %s" % candidate)
                return candidate
        return self._ensure_go_toolchain()

    def _go_version_is_supported(self, go):
        try:
            major, minor = self._go_version_tuple(go)
        except (ConanInvalidConfiguration, OSError, subprocess.SubprocessError):
            return False
        return (major, minor) >= (1, 24)

    def _check_go_version(self, go):
        output = subprocess.check_output([go, "version"], text=True).strip()
        self.output.info(output)
        major, minor = self._go_version_tuple(go, output)
        if (major, minor) < (1, 24):
            raise ConanInvalidConfiguration(f"bom 0.7.1 requires Go >= 1.24, got: {output}")

    @staticmethod
    def _go_version_tuple(go, output=None):
        if output is None:
            output = subprocess.check_output([go, "version"], text=True).strip()
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
