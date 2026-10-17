#!/usr/bin/env python3
"""Conan recipe for cek 0.2.0, a pure-Go OCI image exploration CLI."""

import io
import json
import os
import platform
import re
import shlex
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class CekConan(ConanFile):
    name = "cek"
    version = "0.2.0"
    description = "Explore OCI container image filesystems and layers without running containers"
    license = "MIT"
    homepage = "https://github.com/bschaatsbergen/cek"
    url = "https://github.com/bschaatsbergen/cek"
    topics = ("oci", "container", "docker", "filesystem", "cli")
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    _go_version = "1.25.7"
    _go_archives = {
        "amd64": (
            [
                "https://go.dev/dl/go1.25.7.linux-amd64.tar.gz",
                "https://golang.google.cn/dl/go1.25.7.linux-amd64.tar.gz",
                "https://dl.google.com/go/go1.25.7.linux-amd64.tar.gz",
            ],
            "12e6d6a191091ae27dc31f6efc630e3a3b8ba409baf3573d955b196fdf086005",
        ),
        "arm64": (
            [
                "https://go.dev/dl/go1.25.7.linux-arm64.tar.gz",
                "https://golang.google.cn/dl/go1.25.7.linux-arm64.tar.gz",
                "https://dl.google.com/go/go1.25.7.linux-arm64.tar.gz",
            ],
            "ba611a53534135a81067240eff9508cd7e256c560edd5d8c2fef54f083c07129",
        ),
    }

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("cek is prepared for Linux/OHOS targets only")

    def generate(self):
        self._save_go_environment(self._find_go())

    def build(self):
        go = self._go_executable()
        self._save_go_environment(go)

        self.run(
            f'"{go}" mod download',
            cwd=self.source_folder,
            env=["cek_go_env"],
        )
        self._run_upstream_tests(go)

        out_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(out_dir, exist_ok=True)
        link_dir = (
            os.path.join(self._go_exec_workspace(), "link-out")
            if str(self.settings.os) == "OHOS"
            else out_dir
        )
        os.makedirs(link_dir, exist_ok=True)

        linked_exe = os.path.join(link_dir, self._exe_name())
        final_exe = os.path.join(out_dir, self._exe_name())
        ldflags = (
            "-s -w "
            "-X github.com/bschaatsbergen/cek/version.Version=0.2.0"
        )
        self.run(
            f'"{go}" build -trimpath -ldflags "{ldflags}" '
            f'-p 1 -o "{linked_exe}" .',
            cwd=self.source_folder,
            env=["cek_go_env"],
        )
        self._sign_elf_if_ohos(linked_exe)
        if os.path.abspath(linked_exe) != os.path.abspath(final_exe):
            shutil.copy2(linked_exe, final_exe)

    def _run_upstream_tests(self, go):
        """Run the official Go suite and persist counts for test_package."""
        output_buffer = io.StringIO()
        mode = self._upstream_test_mode()
        result = self._run_go_test_commands(go, mode, output_buffer)
        output = output_buffer.getvalue()
        for line in output.splitlines():
            self.output.info(f"[go test] {line}")

        passed = len(re.findall(r"^\s*--- PASS:", output, re.MULTILINE))
        failed = len(re.findall(r"^\s*--- FAIL:", output, re.MULTILINE))
        skipped = len(re.findall(r"^\s*--- SKIP:", output, re.MULTILINE))
        executed = passed + failed
        discovered = executed + skipped
        status = "passed" if result == 0 and passed > 0 else "failed"
        if result == 0 and discovered == 0:
            status = "no_tests"

        evidence = {
            "status": status,
            "framework": "go test",
            "mode": mode,
            "command": self._upstream_test_command_description(mode),
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "reason": (
                "Official cek tests are run during Conan build. "
                "The suite includes hermetic command/view tests and "
                "registry-backed OCI image tests."
            ),
        }
        if mode == "smoke":
            evidence["deferred"] = (
                "OCI registry tests are network-gated; run with "
                "CEK_UPSTREAM_TEST_MODE=full when Docker Hub and gcr.io are reachable."
            )
        result_path = os.path.join(self.build_folder, "upstream_test_result.json")
        Path(self.build_folder).mkdir(parents=True, exist_ok=True)
        with open(result_path, "w", encoding="utf-8") as stream:
            json.dump(evidence, stream, ensure_ascii=False)
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT="
            + json.dumps(evidence, separators=(",", ":"), ensure_ascii=False)
        )

        if result != 0:
            raise ConanException(
                f"cek upstream Go tests failed: {failed} failed, "
                f"{passed} passed, {skipped} skipped"
            )

    def _upstream_test_mode(self):
        mode = os.environ.get("CEK_UPSTREAM_TEST_MODE", "smoke").strip().lower()
        if mode not in ("smoke", "full"):
            raise ConanInvalidConfiguration(
                "CEK_UPSTREAM_TEST_MODE must be either 'smoke' or 'full'"
            )
        return mode

    def _run_go_test_commands(self, go, mode, output_buffer):
        result = 0
        if mode == "smoke":
            commands = [
                self._go_test_command(
                    go,
                    "github.com/bschaatsbergen/cek/internal/command",
                    run_regex=self._command_smoke_test_regex(),
                    timeout="5m",
                ),
                self._go_test_command(
                    go,
                    "github.com/bschaatsbergen/cek/internal/view",
                    timeout="5m",
                ),
            ]
        elif str(self.settings.os) == "OHOS":
            list_command = [go, "list", "./..."]
            list_result = self.run(
                " ".join(self._quote_command_part(part) for part in list_command),
                cwd=self.source_folder,
                env=["cek_go_env"],
                stdout=output_buffer,
                stderr=output_buffer,
                ignore_errors=True,
            )
            if list_result != 0:
                return list_result
            commands = [
                self._go_test_command(go, package)
                for package in output_buffer.getvalue().splitlines()
                if package.strip()
            ]
        else:
            commands = [self._go_test_command(go, "./...")]

        for command in commands:
            command_result = self.run(
                " ".join(self._quote_command_part(part) for part in command),
                cwd=self.source_folder,
                env=["cek_go_env"],
                stdout=output_buffer,
                stderr=output_buffer,
                ignore_errors=True,
            )
            if command_result != 0:
                result = command_result
        return result

    def _go_test_command(self, go, package, run_regex=None, timeout="10m"):
        command = [
            go,
            "test",
            "-v",
            f"-timeout={timeout}",
            "-p",
            "1",
        ]
        if run_regex:
            command.extend(["-run", run_regex])
        if str(self.settings.os) == "OHOS":
            wrapper = self._write_ohos_test_exec_wrapper()
            command.extend(["-vet=off", "-exec", f"/bin/sh {wrapper}"])
        command.append(package)
        return command

    @staticmethod
    def _command_smoke_test_regex():
        tests = [
            "TestNewRootCommand",
            "TestNewRootCommand_HasJSONFlag",
            "TestNewRootCommand_VersionFlag",
            "TestNewRootCommand_NoArgs_ShowsHelp",
            "TestAddCommands",
            "TestAddCommands_Count",
            "TestVersionCommand",
            "TestVersionCommand_Execute",
            "TestVersionCommand_WithPath",
            "TestVersionCommand_TooManyArgs",
            "TestNewInspectCommand",
            "TestInspectCommand_Flags",
            "TestInspectCommand_RequiresImageArg",
            "TestInspectCommand_TooManyArgs",
            "TestNewLsCommand",
            "TestLsCommand_Flags",
            "TestLsCommand_RequiresImageArg",
            "TestLsCommand_TooManyArgs",
        ]
        return "^(" + "|".join(tests) + ")$"

    def _upstream_test_command_description(self, mode):
        ohos_exec = ""
        if str(self.settings.os) == "OHOS":
            ohos_exec = " -vet=off -exec '/bin/sh <signed-test-wrapper>'"
        if mode == "smoke":
            command = (
                "go test -v -timeout=5m -p 1 -run <deterministic command tests>"
                f"{ohos_exec} "
                "github.com/bschaatsbergen/cek/internal/command && "
                f"go test -v -timeout=5m -p 1{ohos_exec} "
                "github.com/bschaatsbergen/cek/internal/view"
            )
        elif str(self.settings.os) == "OHOS":
            command = (
                "go list ./... && "
                "go test -v -timeout=10m -p 1 -vet=off <each package>"
            )
        else:
            command = "go test -v -timeout=10m -p 1 ./..."
        return command

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
            "upstream_test_result.json",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "res"),
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]

    def _save_go_environment(self, go):
        env = Environment()
        env.define("CGO_ENABLED", "0")
        env.define("GOOS", self._goos())
        env.define("GOARCH", self._goarch())
        env.define("GOTOOLCHAIN", "local")
        env.define(
            "GOPROXY",
            os.environ.get(
                "GOPROXY",
                "https://goproxy.cn,https://proxy.golang.org,direct",
            ),
        )
        env.define(
            "GOSUMDB",
            os.environ.get("GOSUMDB", "sum.golang.google.cn"),
        )

        workspace = self._go_workspace()
        exec_workspace = self._go_exec_workspace()
        env.define("TMPDIR", os.path.join(exec_workspace, "tmp"))
        env.define("GOTMPDIR", os.path.join(exec_workspace, "gotmp"))
        env.define("GOCACHE", os.path.join(workspace, "go-build-cache"))
        env.define("GOMODCACHE", os.path.join(workspace, "go-mod-cache"))

        if go:
            goroot = self._goroot_for_go(go)
            if goroot:
                env.define("GOROOT", goroot)
            env.prepend_path("PATH", os.path.dirname(go))
        env.vars(self).save_script("cek_go_env")

    def _go_workspace(self):
        if str(self.settings.os) == "OHOS":
            root = os.environ.get(
                "OHOS_GO_WORKDIR",
                "/data/storage/el2/base/haps/entry/files/cek-conan-go",
            )
        else:
            root = os.path.join(self.build_folder, ".go-work")
        workspace = os.path.join(root, self.version)
        for child in ("tmp", "gotmp", "go-build-cache", "go-mod-cache", "go-sdk", "link-out"):
            Path(workspace, child).mkdir(parents=True, exist_ok=True)
        return workspace

    def _go_exec_workspace(self):
        if str(self.settings.os) != "OHOS":
            return self._go_workspace()
        root = os.environ.get(
            "OHOS_GO_EXEC_WORKDIR",
            "/data/storage/el2/base/cache/cek-conan-go",
        )
        workspace = os.path.join(root, self.version)
        for child in ("tmp", "gotmp", "link-out", "test-exec-wrapper", "test-sign-tmp"):
            Path(workspace, child).mkdir(parents=True, exist_ok=True)
        return workspace

    def _find_go(self):
        candidates = []
        if os.environ.get("GO"):
            candidates.append(os.environ["GO"])
        if os.environ.get("GOROOT"):
            candidates.append(os.path.join(os.environ["GOROOT"], "bin", "go"))
        candidates.extend(
            [
                "/data/service/hnp/bin/go",
                os.path.expanduser("~/usr/local/go/bin/go"),
                os.path.expanduser("~/sdk/go/bin/go"),
                "/storage/Users/currentUser/usr/local/go/bin/go",
                "/storage/Users/currentUser/sdk/go/bin/go",
            ]
        )
        path_go = shutil.which("go")
        if path_go:
            candidates.append(path_go)

        seen = set()
        for candidate in candidates:
            if not candidate or candidate in seen or not os.path.isfile(candidate):
                continue
            seen.add(candidate)
            if self._go_version_is_supported(candidate):
                return candidate
        return None

    def _go_executable(self):
        go = self._find_go()
        return go or self._ensure_go_toolchain()

    def _ensure_go_toolchain(self):
        host_arch = self._go_host_arch()
        if host_arch not in self._go_archives:
            raise ConanInvalidConfiguration(
                f"no Go {self._go_version} bootstrap archive for host arch {host_arch}"
            )
        if platform.system().lower() not in ("linux", "ohos", "harmonyos"):
            raise ConanInvalidConfiguration(
                "Go bootstrap archive is Linux-only; provide a runnable Go "
                "toolchain through PATH or GOROOT on non-Linux build hosts"
            )

        workspace = self._go_workspace()
        sdk_root = os.path.join(
            workspace, "go-sdk", f"go{self._go_version}-{host_arch}"
        )
        goroot = os.path.join(sdk_root, "go")
        go = os.path.join(goroot, "bin", "go")
        if not os.path.isfile(go):
            urls, sha256 = self._go_archives[host_arch]
            self.output.info(
                f"Go {self._go_version} not found; downloading official SDK"
            )
            get(self, url=urls, sha256=sha256, destination=sdk_root, strip_root=False)

        if not os.path.isfile(go):
            raise ConanInvalidConfiguration(f"Go SDK extraction did not produce {go}")
        self._sign_go_sdk_if_ohos(goroot)
        if not self._go_version_is_supported(go):
            raise ConanInvalidConfiguration(f"Go SDK is not runnable: {go}")
        return go

    def _run_go_version(self, go):
        try:
            completed = subprocess.run(
                [go, "version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=15,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return ""
        return completed.stdout.decode(errors="replace").strip()

    def _go_version_is_supported(self, go):
        output = self._run_go_version(go)
        match = re.search(r"\bgo(\d+)\.(\d+)(?:\.(\d+))?", output)
        if not match:
            return False
        actual = tuple(int(part or 0) for part in match.groups())
        required = tuple(int(part) for part in self._go_version.split("."))
        return actual >= required

    @staticmethod
    def _quote_command_part(part):
        if os.name == "nt":
            return subprocess.list2cmdline([part])
        return shlex.quote(part)

    def _write_ohos_test_exec_wrapper(self):
        workspace = self._go_exec_workspace()
        wrapper_dir = os.path.join(workspace, "test-exec-wrapper")
        Path(wrapper_dir).mkdir(parents=True, exist_ok=True)
        wrapper = os.path.join(wrapper_dir, "sign-and-exec.sh")
        sign_tmp = os.path.join(workspace, "test-sign-tmp")
        Path(sign_tmp).mkdir(parents=True, exist_ok=True)
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"

        body = f"""#!/bin/sh
set -eu
bin="$1"
shift
if [ ! -f "$bin" ]; then
    echo "cek test wrapper: test binary not found: $bin" >&2
    exit 127
fi
if grep -aq -m1 -e '.codesign' -e '.note.ohos' -- "$bin" 2>/dev/null; then
    chmod 755 "$bin" 2>/dev/null || true
    exec "$bin" "$@"
fi
signer="{signer}"
objcopy="{objcopy}"
tmpdir="{sign_tmp}"
tmp="$tmpdir/$(basename "$bin").$$"
cp -f "$bin" "$tmp"
if [ -x "$objcopy" ]; then
    "$objcopy" --remove-section .codesign "$tmp" >/dev/null 2>&1 || true
fi
"$signer" sign -selfSign 1 -inFile "$tmp" -outFile "$tmp.signed" -signAlg SHA256withECDSA
mv -f "$tmp.signed" "$bin"
chmod 755 "$bin" 2>/dev/null || true
rm -f "$tmp"
exec "$bin" "$@"
"""
        Path(wrapper).write_text(body, encoding="utf-8")
        os.chmod(wrapper, 0o755)
        return wrapper

    def _sign_go_sdk_if_ohos(self, goroot):
        if str(self.settings.os) != "OHOS":
            return
        marker = os.path.join(goroot, ".ohos-signed")
        if os.path.isfile(marker):
            return
        candidates = [
            os.path.join(goroot, "bin", "go"),
            os.path.join(goroot, "bin", "gofmt"),
        ]
        tool_dir = os.path.join(
            goroot, "pkg", "tool", f"linux_{self._go_host_arch()}"
        )
        if os.path.isdir(tool_dir):
            candidates.extend(
                os.path.join(tool_dir, name) for name in os.listdir(tool_dir)
            )
        for candidate in candidates:
            if self._is_elf(candidate):
                self._sign_elf_if_ohos(candidate)
        Path(marker).write_text("signed\n", encoding="utf-8")

    def _sign_elf_if_ohos(self, path):
        if str(self.settings.os) != "OHOS" or not self._is_elf(path):
            return
        if self._has_ohos_signature(path):
            os.chmod(path, 0o755)
            return
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            raise ConanInvalidConfiguration(
                f"binary-sign-tool is required to execute OHOS ELF: {path}"
            )
        signed = f"{path}.signed"
        subprocess.check_call(
            [
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
            ]
        )
        shutil.move(signed, path)
        os.chmod(path, 0o755)

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as stream:
                return stream.read(4) == b"\x7fELF"
        except OSError:
            return False

    @staticmethod
    def _has_ohos_signature(path):
        try:
            with open(path, "rb") as stream:
                contents = stream.read()
                return b".codesign" in contents or b".note.ohos" in contents
        except OSError:
            return False

    @staticmethod
    def _goroot_for_go(go):
        path = Path(go).resolve()
        if path.parent.name == "bin" and (path.parent.parent / "pkg").is_dir():
            return str(path.parent.parent)
        return ""

    def _goos(self):
        if str(self.settings.os) == "OHOS":
            return "linux"
        return str(self.settings.os).lower()

    def _goarch(self):
        return {
            "x86_64": "amd64",
            "x86": "386",
            "armv8": "arm64",
            "armv8_32": "arm",
            "armv7": "arm",
            "armv7hf": "arm",
            "armv6": "arm",
        }.get(str(self.settings.arch), str(self.settings.arch))

    def _go_host_arch(self):
        return {
            "x86_64": "amd64",
            "amd64": "amd64",
            "aarch64": "arm64",
            "arm64": "arm64",
        }.get(platform.machine().lower(), platform.machine().lower())

    def _exe_name(self):
        return "cek.exe" if self._goos() == "windows" else "cek"
