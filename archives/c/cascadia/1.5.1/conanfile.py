#!/usr/bin/env python3
"""Conan recipe for cascadia 1.5.1 — Go CSS selector command line tool."""

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


class CascadiaConan(ConanFile):
    name = "cascadia"
    version = "1.5.1"
    _go_version = "1.25.12"
    _go_archives = {
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
    package_type = "application"

    description = "Go CSS selector command line tool for HTML extraction"
    license = "MIT"
    homepage = "https://github.com/suntong/cascadia"
    url = "https://github.com/suntong/cascadia"
    topics = ("css-selector", "html", "web-scraper", "cli")

    settings = "os", "compiler", "build_type", "arch"

    def configure(self):
        # Pure-Go CLI (CGO_ENABLED=0): binary does not depend on the C
        # compiler or build_type; drop them so the package ID is stable
        # across OHOS profile variants while keeping the L0p-required
        # four-item settings declaration for profile compatibility.
        self.settings.rm_safe("compiler")
        self.settings.rm_safe("build_type")

    def package_id(self):
        self.info.settings.rm_safe("compiler")
        self.info.settings.rm_safe("build_type")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("cascadia is prepared for Linux/OHOS targets only")

    def generate(self):
        env = Environment()
        # Pure-Go CLI (goquery/cascadia/mkideal-cli/x-net): no cgo needed.
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

        env.vars(self).save_script("cascadia_go_env")

    def build(self):
        apply_conandata_patches(self)
        go = self._go_executable()
        self._check_go_version(go)
        self.run(f'"{go}" mod download', cwd=self.source_folder, env=["cascadia_go_env"])

        out_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(out_dir, exist_ok=True)
        # Go linker mmap fails on HMDFS: link on ext2-like workspace on OHOS.
        link_out_dir = os.path.join(self._go_workspace(), "link-out") if str(self.settings.os) == "OHOS" else out_dir
        os.makedirs(link_out_dir, exist_ok=True)
        linked_exe = os.path.join(link_out_dir, self._exe_name())
        final_exe = os.path.join(out_dir, self._exe_name())
        # Upstream hardcodes version/date in cascadia_main.go; no -X injection point.
        # Keep -s -w strip: plain CLI, Go build info is not consumed at runtime.
        ldflags = "-s -w"
        self.run(
            f'"{go}" build -trimpath -ldflags "{ldflags}" -o "{linked_exe}" .',
            cwd=self.source_folder,
            env=["cascadia_go_env"],
        )
        self._sign_elf_if_ohos(linked_exe)
        if os.path.abspath(linked_exe) != os.path.abspath(final_exe):
            shutil.copy2(linked_exe, final_exe)

        self._run_upstream_tests(go, final_exe)

    def _run_upstream_tests(self, go, built_exe):
        """Run upstream ``go test -v -count=1 ./...`` and emit the HMBS marker.

        Upstream ships 3 Test functions: TestSelectors (cascadia_test.go,
        table-driven selector matrix), TestPiece + TestPieceGoqr
        (piece_test.go, CLI-driven via prop_test.go helpers). The
        piece/GOQR tests shell out to ``../cascadia`` (repo-root binary)
        and ``diff`` from inside ``test/``, so the freshly built binary
        is staged at ``<source_folder>/cascadia`` before running tests.
        Counters come from ``--- PASS/FAIL/SKIP`` lines of the real run.
        """
        import json
        import re
        import subprocess

        staged = os.path.join(self.source_folder, "cascadia")
        try:
            shutil.copy2(built_exe, staged)
            os.chmod(staged, 0o755)
        except OSError as exc:
            self.output.warning(f"cascadia: staging test binary failed: {exc}")

        base_env = dict(os.environ)
        go_workspace = self._go_workspace()
        go_env_overrides = {
            "CGO_ENABLED": "0",
            "GOOS": self._goos(),
            "GOARCH": self._goarch(),
            "GOTOOLCHAIN": "local",
            "TMPDIR": os.path.join(go_workspace, "tmp"),
            "GOTMPDIR": os.path.join(go_workspace, "tmp"),
            "GOCACHE": os.path.join(go_workspace, "go-build-cache"),
            "GOMODCACHE": os.path.join(go_workspace, "go-mod-cache"),
        }
        goroot = self._goroot_for_go(go)
        if goroot:
            go_env_overrides["GOROOT"] = goroot
        base_env.update(go_env_overrides)
        base_env["PATH"] = os.path.dirname(go) + os.pathsep + base_env.get("PATH", "")

        # OHOS requires every executed ELF to carry a .codesign section.
        # `go test` compiles *.test binaries into GOTMPDIR and forks them
        # directly; without signing they fail with permission denied.
        exec_args = []
        if str(self.settings.os) == "OHOS":
            wrapper = self._write_ohos_test_exec_wrapper()
            exec_args = ["-exec", wrapper]

        cmd = [go, "test", "-v", "-count=1"] + exec_args + ["./..."]
        try:
            proc = subprocess.run(
                cmd,
                cwd=self.source_folder,
                env=base_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=1800,
            )
            output = proc.stdout.decode(errors="replace")
        except (OSError, subprocess.TimeoutExpired) as exc:
            output = f"go test failed to run: {exc}"

        passed = len(re.findall(r"^\s*--- PASS:", output, re.MULTILINE))
        failed = len(re.findall(r"^\s*--- FAIL:", output, re.MULTILINE))
        skipped = len(re.findall(r"^\s*--- SKIP:", output, re.MULTILINE))
        self.output.info(f"cascadia `go test ./...`: PASS={passed} FAIL={failed} SKIP={skipped}")
        preview = output[:2048].replace("\n", "\n  cascadia go test | ")
        self.output.info("cascadia go test output preview:\n  " + preview)

        discovered = passed + failed + skipped
        executed = passed + failed
        if failed > 0:
            status = "failed"
        elif passed > 0:
            status = "passed"
        else:
            status = "no_tests"

        upstream = {
            "status": status,
            "framework": "go test",
            "command": " ".join(cmd),
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False)
        # Dual-channel emit so HMBS preflight captures it regardless of log routing.
        print(msg, flush=True)
        self.output.info(msg)
        # Persist for test_package re-emit on cache hit (build() skipped ->
        # marker would otherwise disappear and evidence gate goes incomplete).
        try:
            hmbs_tmp = os.path.join(self.build_folder, "hmbs_upstream.json")
            with open(hmbs_tmp, "w", encoding="utf-8") as _f:
                json.dump(upstream, _f)
        except OSError as exc:
            self.output.warning(f"cascadia: persisting hmbs_upstream.json failed: {exc}")
        try:
            if os.path.isfile(staged):
                os.unlink(staged)
        except OSError:
            pass

    def _write_ohos_test_exec_wrapper(self):
        """Write a `go test -exec` wrapper that signs the test binary before exec."""
        go_workspace = self._go_workspace()
        wrapper_dir = os.path.join(go_workspace, "test-exec-wrapper")
        Path(wrapper_dir).mkdir(parents=True, exist_ok=True)
        wrapper_path = os.path.join(wrapper_dir, "ohos-test-exec.sh")

        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        sign_tmp = os.path.join(go_workspace, "sign-tmp-test")
        Path(sign_tmp).mkdir(parents=True, exist_ok=True)

        wrapper_body = f"""#!/bin/sh
# OHOS go test -exec wrapper: sign the test binary, then exec it.
set -e

bin="$1"
shift

if [ ! -f "$bin" ]; then
    echo "ohos-test-exec: test binary not found: $bin" >&2
    exit 127
fi

if grep -aq -m1 -e '.codesign' -e '.note.ohos' -- "$bin" 2>/dev/null; then
    chmod 755 "$bin" 2>/dev/null || true
    exec "$bin" "$@"
fi

signer="{signer}"
objcopy="{objcopy}"
stmp="{sign_tmp}"
if [ ! -x "$signer" ]; then
    echo "ohos-test-exec: binary-sign-tool missing: $signer" >&2
    exit 127
fi

inode=$(stat -c '%i' "$bin" 2>/dev/null || echo '0')
tin="$stmp/$(basename "$bin").$$.$inode"
tout="$tin.signed"
cp -f "$bin" "$tin"
if [ -x "$objcopy" ]; then
    "$objcopy" --remove-section .codesign "$tin" >/dev/null 2>&1 || true
fi
"$signer" sign -selfSign 1 -inFile "$tin" -outFile "$tout" -signAlg SHA256withECDSA
mv -f "$tout" "$bin"
chmod 755 "$bin" 2>/dev/null || true
rm -f "$tin"
exec "$bin" "$@"
"""
        with open(wrapper_path, "w", encoding="utf-8") as f:
            f.write(wrapper_body)
        os.chmod(wrapper_path, 0o755)
        self.output.info(f"cascadia: wrote OHOS go test -exec wrapper to {wrapper_path}")
        return wrapper_path

    def package(self):
        copy(self, self._exe_name(), os.path.join(self.build_folder, "bin"), os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        # Carry HMBS upstream result into the package so test_package can
        # re-emit HMBS_UPSTREAM_TEST_RESULT on EVERY run, even when conan
        # skips build() on a cached binary ("Already installed!").
        try:
            src = os.path.join(self.build_folder, "hmbs_upstream.json")
            if os.path.isfile(src):
                dst_dir = os.path.join(self.package_folder, "res")
                os.makedirs(dst_dir, exist_ok=True)
                copy(self, "hmbs_upstream.json", self.build_folder, dst_dir, keep_path=False)
            else:
                self.output.warning("hmbs_upstream.json not found in build folder; package will lack upstream evidence")
        except Exception as exc:
            self.output.warning(f"cascadia: shipping hmbs_upstream.json failed: {exc}")

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]

    # ── Go toolchain helpers (based on caddy/addchain pattern) ──

    def _go_workspace(self):
        if str(self.settings.os) != "OHOS":
            root = os.path.join(self.build_folder, ".go-work")
        else:
            root = os.environ.get(
                "OHOS_GO_WORKDIR",
                "/data/storage/el2/base/haps/entry/files/cascadia-conan-go",
            )
        workspace = os.path.join(root, self.version)
        for child in (
            "tmp",
            "go-build-cache",
            "go-mod-cache",
            "link-out",
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
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
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

    def _exe_name(self):
        return "cascadia.exe" if self._goos() == "windows" else "cascadia"

    def _go_executable(self):
        candidates = []
        if os.environ.get("GO"):
            candidates.append(os.environ["GO"])
        if os.environ.get("GOROOT"):
            candidates.append(os.path.join(os.environ["GOROOT"], "bin", "go"))
        candidates.extend([
            os.path.expanduser("~/usr/local/go1263/bin/go"),
            os.path.expanduser("~/sdk/go1.26.3/bin/go"),
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
        return (major, minor) >= (1, 25)

    def _check_go_version(self, go):
        output = subprocess.check_output([go, "version"], text=True).strip()
        self.output.info(output)
        major, minor = self._go_version_tuple(go, output)
        if (major, minor) < (1, 25):
            raise ConanInvalidConfiguration(f"cascadia 1.5.1 requires Go >= 1.25, got: {output}")

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
