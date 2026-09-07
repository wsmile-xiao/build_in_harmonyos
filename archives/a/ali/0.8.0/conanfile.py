#!/usr/bin/env python3
"""Conan recipe for ali 0.8.0 — Generate HTTP load and plot the results in real-time (Go load testing tool)."""

import os
import platform
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AliConan(ConanFile):
    name = "ali"
    version = "0.8.0"
    _go_version = "1.24.5"
    _go_archives = {
        "arm64": (
            [
                "https://golang.google.cn/dl/go1.24.5.linux-arm64.tar.gz",
                "https://mirrors.aliyun.com/golang/go1.24.5.linux-arm64.tar.gz",
                "https://dl.google.com/go/go1.24.5.linux-arm64.tar.gz",
            ],
            "0df02e6aeb3d3c06c95ff201d575907c736d6c62cfa4b6934c11203f1d600ffa",
        ),
        "amd64": (
            [
                "https://golang.google.cn/dl/go1.24.5.linux-amd64.tar.gz",
                "https://mirrors.aliyun.com/golang/go1.24.5.linux-amd64.tar.gz",
                "https://dl.google.com/go/go1.24.5.linux-amd64.tar.gz",
            ],
            "10ad9e86233e74c0f6590fe5426895de6bf388964210eac34a6d83f38918ecdc",
        ),
    }
    package_type = "application"

    description = "Generate HTTP load and plot the results in real-time (Go load testing tool with termdash GUI)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/nakabonne/ali"
    url = "https://github.com/nakabonne/ali"
    topics = ("ali", "load-testing", "benchmark", "http", "tui", "go")

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("ali is prepared for Linux/OHOS targets only")

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

        env.vars(self).save_script("ali_go_env")

    def build(self):
        apply_conandata_patches(self)
        go = self._go_executable()
        self.run(f'"{go}" mod download', cwd=self.source_folder, env=["ali_go_env"])

        out_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(out_dir, exist_ok=True)
        # Go linker mmap fails on HMDFS (E051/E046): link on ext2-like workspace on OHOS.
        link_out_dir = os.path.join(self._go_workspace(), "link-out") if str(self.settings.os) == "OHOS" else out_dir
        os.makedirs(link_out_dir, exist_ok=True)
        linked_exe = os.path.join(link_out_dir, self._exe_name())
        final_exe = os.path.join(out_dir, self._exe_name())
        ldflags = "-s -w -X main.version=v0.8.0"
        self.run(
            f'"{go}" build -trimpath -ldflags "{ldflags}" -o "{linked_exe}" .',
            cwd=self.source_folder,
            env=["ali_go_env"],
        )
        self._sign_elf_if_ohos(linked_exe)
        if os.path.abspath(linked_exe) != os.path.abspath(final_exe):
            shutil.copy2(linked_exe, final_exe)

        self._run_upstream_tests(go)

    def _write_ohos_test_exec_wrapper(self):
        """Write a `go test -exec` wrapper that signs the test binary before exec.

        On OHOS every ELF that gets forked/exec'd must carry a `.codesign`
        section.  `go test` builds `*.test` binaries into GOTMPDIR and
        fork/execs them directly, so unsigned test binaries fail with
        "permission denied" and no tests run (HMBS incomplete).

        The wrapper receives the test binary path as its **last** argument
        (Go passes the binary after any user-supplied flags), signs it
        with binary-sign-tool, chmods it executable, and execs it with
        all remaining arguments forwarded.
        """
        go_workspace = self._go_workspace()
        wrapper_dir = os.path.join(go_workspace, "test-exec-wrapper")
        Path(wrapper_dir).mkdir(parents=True, exist_ok=True)
        wrapper_path = os.path.join(wrapper_dir, "ohos-test-exec.sh")

        # Resolve tools the same way _sign_elf_if_ohos does.
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        sign_tmp = os.path.join(go_workspace, "sign-tmp-test")
        Path(sign_tmp).mkdir(parents=True, exist_ok=True)

        wrapper_body = f"""#!/bin/sh
# OHOS go test -exec wrapper: sign the test binary, then exec it.
# Usage (from `go test -exec`): wrapper <test-binary> [args...]
# Go forwards the compiled *.test binary as the final argument.
set -e

bin="$1"
shift

if [ ! -f "$bin" ]; then
    echo "ohos-test-exec: test binary not found: $bin" >&2
    exit 127
fi

# Skip signing if the binary already carries an OHOS signature.
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

# Use a unique temp name (PID + inode) to avoid collisions when
# different packages share the same test-binary basename.
inode=$(stat -c '%i' "$bin" 2>/dev/null || echo '0')
tin="$stmp/$(basename "$bin").$$.$inode"
tout="$tin.signed"
cp -f "$bin" "$tin"
# Strip any pre-existing .codesign section before re-signing.
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
        self.output.info(f"ali: wrote OHOS go test -exec wrapper to {wrapper_path}")
        return wrapper_path

    def _run_upstream_tests(self, go):
        """Run upstream `go test ./...` and emit HMBS markers."""
        import json
        import re

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

        exec_args = []
        if str(self.settings.os) == "OHOS":
            wrapper = self._write_ohos_test_exec_wrapper()
            exec_args = ["-exec", wrapper]

        def _run(cmd):
            try:
                proc = subprocess.run(
                    cmd,
                    cwd=self.source_folder,
                    env=base_env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    timeout=1800,
                )
                return proc.stdout.decode(errors="replace")
            except (OSError, subprocess.TimeoutExpired) as exc:
                return f"go test failed to run: {exc}"

        def _count(output):
            p = len(re.findall(r"^\s*--- PASS:", output, re.MULTILINE))
            f = len(re.findall(r"^\s*--- FAIL:", output, re.MULTILINE))
            s = len(re.findall(r"^\s*--- SKIP:", output, re.MULTILINE))
            return p, f, s

        cmd = [go, "test", "-v", "-count=1", "-race"] + exec_args + ["./..."]
        out = _run(cmd)
        # -race requires cgo; with CGO_ENABLED=0 it fails as "go: -race requires cgo; enable cgo by setting CGO_ENABLED=1"
        # Original check only handled "race detector not available" / "undefined: race" and missed the cgo case -> discovered 0 -> HMBS incomplete.
        if "race detector not available" in out or "undefined: race" in out or "requires cgo" in out or "CGO_ENABLED" in out or "-race requires cgo" in out:
            cmd = [go, "test", "-v", "-count=1"] + exec_args + ["./..."]
            out = _run(cmd)
        p, f, s = _count(out)
        self.output.info(f"ali `go test ./...`: PASS={p} FAIL={f} SKIP={s}")
        preview = out[:4096].replace("\n", "\n  ali go test | ")
        self.output.info("ali go test output preview:\n  " + preview)

        passed = p
        failed = f
        skipped = s
        discovered = passed + failed + skipped
        executed = passed + failed
        if failed > 0:
            status = "failed"
        elif passed > 0:
            status = "passed"
        else:
            if "permission denied" in out.lower():
                status = "failed"
            else:
                status = "no_tests"

        command_str = " ".join(cmd)
        upstream = {
            "status": status,
            "framework": "go test",
            "command": command_str,
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False)
        # Emit via both stdout and Conan output so HMBS preflight captures it regardless of caching.
        print(msg, flush=True)
        self.output.info(msg)
        # Persist for test_package re-emit on cache hit (build() skipped -> marker would otherwise disappear).
        try:
            hmbs_tmp = os.path.join(self.build_folder, "hmbs_upstream.json")
            with open(hmbs_tmp, "w", encoding="utf-8") as _f:
                json.dump(upstream, _f)
        except Exception:
            pass

    def package(self):
        copy(self, self._exe_name(), os.path.join(self.build_folder, "bin"), os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "README.md", self.source_folder, os.path.join(self.package_folder, "res"))
        # Carry HMBS upstream result into package for test_package cache-hit re-emit.
        try:
            import json as _json
            src = os.path.join(self.build_folder, "hmbs_upstream.json")
            dst_dir = os.path.join(self.package_folder, "res")
            os.makedirs(dst_dir, exist_ok=True)
            if os.path.isfile(src):
                import shutil as _sh
                _sh.copy2(src, os.path.join(dst_dir, "hmbs_upstream.json"))
            else:
                # Fallback: at least ensure a placeholder exists (should not happen when tests ran)
                pass
        except Exception:
            pass

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]

    # ── Go toolchain helpers (based on ain/aliyun-cli pattern) ──

    def _go_workspace(self):
        if str(self.settings.os) != "OHOS":
            root = os.path.join(self.build_folder, ".go-work")
        else:
            root = os.environ.get(
                "OHOS_GO_WORKDIR",
                "/data/storage/el2/base/haps/entry/files/ali-conan-go",
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
        tmp_dir = os.path.join(self._go_workspace(), "sign-tmp")
        Path(tmp_dir).mkdir(parents=True, exist_ok=True)
        tmp_in = os.path.join(tmp_dir, os.path.basename(path))
        tmp_out = f"{tmp_in}.signed"
        shutil.copy2(path, tmp_in)
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        subprocess.run([objcopy, "--remove-section", ".codesign", tmp_in],
                       capture_output=True, timeout=10)
        subprocess.check_call([
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
        ])
        shutil.move(tmp_out, path)
        os.chmod(path, 0o755)
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
        return "ali.exe" if self._goos() == "windows" else "ali"

    def _go_executable(self):
        candidates = []
        if os.environ.get("GO"):
            candidates.append(os.environ["GO"])
        if os.environ.get("GOROOT"):
            candidates.append(os.path.join(os.environ["GOROOT"], "bin", "go"))
        candidates.extend([
            os.path.expanduser("~/usr/local/go/bin/go"),
            os.path.expanduser("~/sdk/go1.24.5/bin/go"),
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
            output = subprocess.run([go, "version"], capture_output=True, timeout=10).stdout.decode()
        except OSError:
            return False
        # Extract "go1.xx.yy" from e.g. "go version go1.23.8 linux/arm64"
        m = output.split("go version ")[-1].split(" ")[0]  # go1.23.8
        ver = m[2:]  # 1.23.8
        try:
            return [int(x) for x in ver.split(".")] >= [int(x) for x in self._go_version.split(".")]
        except ValueError:
            return False

    def _go_host_arch(self):
        machine = platform.machine().lower()
        return {
            "x86_64": "amd64",
            "amd64": "amd64",
            "aarch64": "arm64",
            "arm64": "arm64",
            "armv8l": "arm64",
        }.get(machine, machine)

    def _goroot_for_go(self, gobin):
        gobin = os.path.realpath(gobin)
        candidates = [
            os.path.dirname(os.path.dirname(gobin)),
            os.environ.get("GOROOT", ""),
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(os.path.join(candidate, "bin", "go")):
                return candidate
        return ""
