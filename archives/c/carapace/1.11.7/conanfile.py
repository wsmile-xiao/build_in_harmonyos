#!/usr/bin/env python3
"""Conan recipe for carapace 1.11.7."""

import os
import platform
import re
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class CarapaceConan(ConanFile):
    name = "carapace"
    version = "1.11.7"
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
    _build_targets = ("example", "example-nonposix")
    _upstream_test_packages = (
        (".", "carapace-root.test", "", "TestActionDirectories|TestActionFiles"),
        ("./example/cmd", "example", "example/cmd", "TestCache"),
        ("./example-nonposix/cmd", "example-nonposix", "example-nonposix/cmd", ""),
    )
    # Tests that depend on the directory listing of CWD; fail in Conan build env
    _env_sensitive_tests = "TestActionDirectories|TestActionFiles"
    package_type = "application"

    description = "Command argument completion library for Go (cobra-based)"
    license = "MIT"
    homepage = "https://github.com/carapace-sh/carapace"
    url = "https://github.com/carapace-sh/carapace"
    topics = ("completion", "shell", "cobra", "cli")

    settings = "os", "arch"

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("carapace is prepared for Linux/OHOS targets only")

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

        # On OHOS, create a go-run wrapper that signs binaries before exec
        if str(self.settings.os) == "OHOS":
            wrapper_dir = os.path.join(go_workspace, "go-wrapper")
            os.makedirs(wrapper_dir, exist_ok=True)
            wrapper_path = os.path.join(wrapper_dir, "go")
            self._create_go_run_wrapper(wrapper_path, gobin)
            env.prepend_path("PATH", wrapper_dir)

        env.vars(self).save_script("carapace_go_env")

    def build(self):
        go = self._go_executable()
        self._check_go_version(go)
        self.run(f'"{go}" mod download', cwd=self.source_folder, env=["carapace_go_env"])

        self._run_upstream_tests(go)

        out_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(out_dir, exist_ok=True)
        link_out_dir = os.path.join(self._go_workspace(), "link-out") if str(self.settings.os) == "OHOS" else out_dir
        os.makedirs(link_out_dir, exist_ok=True)

        for target in self._build_targets:
            linked_exe = os.path.join(link_out_dir, target)
            final_exe = os.path.join(out_dir, target)
            ldflags = "-s -w"
            self.run(
                f'"{go}" build -trimpath -ldflags "{ldflags}" -o "{linked_exe}" ./{target}',
                cwd=self.source_folder,
                env=["carapace_go_env"],
            )
            self._sign_elf_if_ohos(linked_exe)
            if os.path.abspath(linked_exe) != os.path.abspath(final_exe):
                shutil.copy2(linked_exe, final_exe)

    def package(self):
        for target in self._build_targets:
            copy(self, target, os.path.join(self.build_folder, "bin"), os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE.txt", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "LICENSE.appendix", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "README.md", self.source_folder, os.path.join(self.package_folder, "res"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]

    def _run_upstream_tests(self, go):
        if str(self.settings.os) == "Linux":
            for package, _, test_cwd, skip_pat in self._upstream_test_packages:
                skip = f'-skip "{skip_pat}"' if skip_pat else ""
                cwd = os.path.join(self.source_folder, test_cwd) if test_cwd else self.source_folder
                self.run(
                    f'"{go}" test {skip} {package}',
                    cwd=cwd,
                    env=["carapace_go_env"],
                )
            return
        if str(self.settings.os) != "OHOS":
            return

        test_out_dir = os.path.join(self._go_workspace(), "test-out")
        os.makedirs(test_out_dir, exist_ok=True)
        go_cache = os.path.join(self._go_workspace(), "go-build-cache")

        for package, test_name, test_cwd, skip_pat in self._upstream_test_packages:
            test_bin = os.path.join(test_out_dir, test_name)
            self.run(
                f'"{go}" test -c -o "{test_bin}" {package}',
                cwd=self.source_folder,
                env=["carapace_go_env"],
            )
            self._sign_elf_if_ohos(test_bin)
            self._sign_go_cache_binaries(go_cache)
            skip_flag = f'-test.skip "{skip_pat}"' if skip_pat else ""
            cwd = os.path.join(self.source_folder, test_cwd) if test_cwd else self.source_folder
            self.run(f'"{test_bin}" -test.v {skip_flag}', cwd=cwd, env=["carapace_go_env"])

    def _create_go_run_wrapper(self, wrapper_path, real_go):
        """Create a shell wrapper for `go` that intercepts `go run` to sign
        the compiled binary before execution on OHOS."""
        signer = shutil.which("binary-sign-tool") or "/storage/Users/currentUser/usr/local/bin/binary-sign-tool"
        tmpdir = os.path.join(self._go_workspace(), "tmp")
        content = f'''#!/data/service/hnp/bin/bash
# Auto-generated go wrapper: signs binaries before exec on OHOS
REAL_GO="{real_go}"
SIGNER="{signer}"
TMPDIR="{tmpdir}"

if [ "$1" != "run" ]; then
    exec "$REAL_GO" "$@"
fi

shift  # drop "run"
flags=()
while [ $# -gt 0 ]; do
    case "$1" in
        -*)
            flags+=("$1")
            shift
            ;;
        *)
            pkg="$1"
            shift
            break
            ;;
    esac
done
prog_args=("$@")

tmpbin="$TMPDIR/go-build$$"
"$REAL_GO" build "${{flags[@]}}" -o "$tmpbin" "$pkg" >&2 || exit $?

if [ -f "$SIGNER" ]; then
    "$SIGNER" sign -selfSign 1 -inFile "$tmpbin" -outFile "${{tmpbin}}.signed" -signAlg SHA256withECDSA >&2
    mv "${{tmpbin}}.signed" "$tmpbin"
fi
chmod +x "$tmpbin"
exec "$tmpbin" "${{prog_args[@]}}"
'''
        with open(wrapper_path, "w") as f:
            f.write(content)
        os.chmod(wrapper_path, 0o755)

    def _sign_go_cache_binaries(self, go_cache):
        if str(self.settings.os) != "OHOS":
            return
        if not os.path.isdir(go_cache):
            return
        for root, _, files in os.walk(go_cache):
            for fname in files:
                fpath = os.path.join(root, fname)
                if self._is_elf(fpath) and not self._has_ohos_signature(fpath):
                    self._sign_elf_if_ohos(fpath)

    def _go_workspace(self):
        if str(self.settings.os) != "OHOS":
            root = os.path.join(self.build_folder, ".go-work")
        else:
            root = os.environ.get(
                "OHOS_GO_WORKDIR",
                "/data/storage/el2/base/haps/entry/files/carapace-conan-go",
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
        if host_arch not in self._go_archives:
            raise ConanInvalidConfiguration(f"Go SDK bootstrap is not prepared for host arch: {host_arch}")

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

    def _go_host_arch(self):
        machine = platform.machine().lower()
        return {
            "aarch64": "arm64",
            "arm64": "arm64",
            "x86_64": "amd64",
            "amd64": "amd64",
        }.get(machine, machine)

    def _go_executable(self):
        candidates = []
        if os.environ.get("GO"):
            candidates.append(os.environ["GO"])
        if os.environ.get("GOROOT"):
            candidates.append(os.path.join(os.environ["GOROOT"], "bin", "go"))
        candidates.extend([
            os.path.expanduser("~/usr/local/go1263/bin/go"),
            os.path.expanduser("~/sdk/go1.26.3/bin/go"),
            os.path.expanduser("~/tmp/go-sdk-cache/go1.24.0-sdk/bin/go"),
            "/storage/Users/currentUser/usr/local/go1263/bin/go",
            "/storage/Users/currentUser/sdk/go1.26.3/bin/go",
            "/storage/Users/currentUser/tmp/go-sdk-cache/go1.24.0-sdk/bin/go",
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
            major, minor = self._go_version_tuple(go)
        except (ConanInvalidConfiguration, OSError, subprocess.SubprocessError):
            return False
        return (major, minor) >= (1, 24)

    def _check_go_version(self, go):
        output = subprocess.check_output([go, "version"], text=True).strip()
        self.output.info(output)
        major, minor = self._go_version_tuple(go, output)
        if (major, minor) < (1, 24):
            raise ConanInvalidConfiguration(f"carapace 1.11.7 requires Go >= 1.24, got: {output}")

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
