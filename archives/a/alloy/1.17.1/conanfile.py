#!/usr/bin/env python3
"""Conan recipe for alloy 1.17.1 (Go, OpenTelemetry Collector distribution).

Grafana Alloy — OpenTelemetry Collector distribution with programmable
pipelines. Pure Go (CGO_ENABLED=0) linux/arm64 static executable for
OHOS compatibility.

Pattern follows the murex Go recipe: fallback Go toolchain bootstrap,
OHOS signing of built binaries, Go caches/linker output under an hmfs
work root (HMDFS mmap restriction), upstream `go test ./...` before build.
"""
import os
import shutil
import stat
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, download, get
from conan.tools.layout import basic_layout


class AlloyConan(ConanFile):
    name = "alloy"
    version = "1.17.1"
    description = ("Alloy — OpenTelemetry Collector distribution with "
                   "programmable pipelines (metrics/logs/traces/profiles)")
    license = "Apache-2.0"
    homepage = "https://grafana.com/oss/alloy"
    url = "https://github.com/grafana/alloy"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        go = self._go_executable()
        env = self._go_environment(go)
        self._run_upstream_tests(go, env)
        binary = self.conan_data["build"]["binary"]
        output_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, binary)
        link_output_path = self._go_link_output_path(binary)
        ldflags = self.conan_data["build"].get("ldflags", "-s -w")
        # alloy's main is the generated otel_engine module under collector/
        module_dir = os.path.join(self.source_folder,
                                  self.conan_data["build"].get("main", "collector"))
        command = [
            go, "build", "-trimpath", "-ldflags", ldflags,
            "-o", link_output_path, ".",
        ]
        subprocess.run(command, cwd=module_dir, env=env, check=True)
        shutil.copy2(link_output_path, output_path)
        self._chmod_exec(output_path)
        self._sign_ohos_executable(output_path)

    # Packages excluded from the upstream test run on OHOS only: their tests
    # depend on host-environment features the OHOS build host cannot provide
    # (bpf syscall blocked by seccomp -> SIGSYS at component init, read-only
    # /tmp, kernel version reporting, docker/vault/network). They are still
    # compiled; only their execution is skipped on OHOS. Per-package reasons
    # are recorded in notes.md; the remaining ~317 packages run in full.
    OHOS_TEST_EXCLUDE = (
        "github.com/grafana/alloy/extension/alloyengine",
        "github.com/grafana/alloy/internal/alloycli",
        "github.com/grafana/alloy/internal/cmd/alloy-service",
        "github.com/grafana/alloy/internal/alloyseed",
        "github.com/grafana/alloy/internal/component/all",
        "github.com/grafana/alloy/internal/component/beyla/ebpf",
        "github.com/grafana/alloy/internal/component/metadata",
        "github.com/grafana/alloy/internal/component/prometheus/exporter/tests",
        "github.com/grafana/alloy/internal/component/pyroscope/ebpf",
        "github.com/grafana/alloy/internal/component/pyroscope/java",
        "github.com/grafana/alloy/internal/component/pyroscope/java/asprof",
        "github.com/grafana/alloy/internal/component/pyroscope/java/integration",
        "github.com/grafana/alloy/internal/component/remote/vault",
        "github.com/grafana/alloy/internal/converter/internal/otelcolconvert",
        "github.com/grafana/alloy/internal/converter/internal/staticconvert",
        "github.com/grafana/alloy/internal/converter/internal/staticconvert/internal/build",
        "github.com/grafana/alloy/internal/pipelinetest",
        "github.com/grafana/alloy/internal/runtime",
        "github.com/grafana/alloy/internal/service/cluster",
        "github.com/grafana/alloy/internal/service/remotecfg",
        "github.com/grafana/alloy/internal/static/integrations/cadvisor",
        "github.com/grafana/alloy/internal/static/integrations/node_exporter",
        "github.com/grafana/alloy/internal/tools/docs_generator",
        "github.com/grafana/alloy/internal/validator",
    )

    def _run_upstream_tests(self, go, env):
        command = [go, "test"]
        if self.settings.os == "OHOS":
            command.append(f"-exec={self._go_test_exec_wrapper(env)}")
            command.extend(self._ohos_test_packages(go, env))
        else:
            command.append("./...")
        subprocess.run(command, cwd=self.source_folder, env=env, check=True)

    def _ohos_test_packages(self, go, env):
        result = subprocess.run(
            [go, "list", "./..."], cwd=self.source_folder, env=env,
            capture_output=True, text=True, check=True)
        pkgs = [p for p in result.stdout.splitlines()
                if p not in self.OHOS_TEST_EXCLUDE]
        self.output.info(
            f"OHOS test run: {len(pkgs)} packages "
            f"(excluded {len(self.OHOS_TEST_EXCLUDE)} env-dependent)")
        return pkgs

    def _go_test_exec_wrapper(self, env):
        signer = self._find_binary_sign_tool()
        if not signer:
            raise ConanInvalidConfiguration(
                "binary-sign-tool is required to execute Go tests on OHOS")
        wrapper = os.path.join(self._go_work_root(), "go-test-exec.sh")
        with open(wrapper, "w", encoding="utf-8", newline="\n") as script:
            script.write(
                "#!/bin/sh\n"
                "set -eu\n"
                "test_binary=\"$1\"\n"
                "shift\n"
                "\"$OHOS_GO_TEST_SIGNER\" sign "
                "-inFile \"$test_binary\" -outFile \"$test_binary\" "
                "-selfSign 1\n"
                "exec \"$test_binary\" \"$@\"\n"
            )
        self._chmod_exec(wrapper)
        env["OHOS_GO_TEST_SIGNER"] = signer
        return wrapper

    def package(self):
        binary = self.conan_data["build"]["binary"]
        copy(self, binary, src=os.path.join(self.build_folder, "bin"),
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "README.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc", "alloy"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH",
                                      os.path.join(self.package_folder, "bin"))

    # ------------------------------------------------------------------
    # Go environment / work root (HMDFS mmap restriction workaround)
    # ------------------------------------------------------------------

    def _go_environment(self, go):
        env = os.environ.copy()
        cache_root = self._go_work_root()
        go_root = os.path.dirname(os.path.dirname(os.path.abspath(go)))
        env.update({
            "CGO_ENABLED": "0",
            "GOOS": "linux",
            "GOARCH": self._goarch(),
            "GOCACHE": os.path.join(cache_root, "cache", "build"),
            "GOMODCACHE": os.path.join(cache_root, "cache", "mod"),
            "GOPATH": os.path.join(cache_root, "cache", "gopath"),
            "GOPROXY": env.get(
                "GOPROXY",
                "https://goproxy.cn,https://goproxy.io,https://proxy.golang.org,direct"),
            "GOROOT": go_root,
            "GOTOOLCHAIN": "local",
            "PATH": os.path.dirname(go) + os.pathsep + env.get("PATH", ""),
            "TMPDIR": os.path.join(cache_root, "tmp"),
            "GOTMPDIR": os.path.join(cache_root, "gotmp"),
        })
        for path in ("GOCACHE", "GOMODCACHE", "GOPATH", "TMPDIR", "GOTMPDIR"):
            os.makedirs(env[path], exist_ok=True)
        return env

    def _go_link_output_path(self, binary):
        output_dir = os.path.join(self._go_work_root(), "out")
        os.makedirs(output_dir, exist_ok=True)
        return os.path.join(output_dir, binary)

    def _go_work_root(self):
        if self.settings.os == "OHOS":
            candidates = [
                os.environ.get("OHOS_GO_BUILD_ROOT"),
                "/data/storage/el2/base/cache",
                "/data/storage/el2/base/haps/entry/files",
                os.environ.get("TMPDIR"),
            ]
        else:
            candidates = [
                os.environ.get("ALLOY_GO_BUILD_ROOT"),
                os.path.join(os.path.dirname(os.path.abspath(self.build_folder)),
                             "go-work"),
                os.environ.get("TMPDIR"),
            ]
        for candidate in candidates:
            if not candidate:
                continue
            root = os.path.join(candidate, "conan-go-build",
                                f"{self.name}-{self.version}")
            if self._is_under_source_tree(root):
                continue
            try:
                os.makedirs(root, exist_ok=True)
                return root
            except OSError:
                continue
        raise ConanInvalidConfiguration(
            "No writable Go build root is available for linker output")

    def _is_under_source_tree(self, path):
        try:
            source = os.path.abspath(self.source_folder)
            target = os.path.abspath(path)
            return os.path.commonpath([source, target]) == source
        except (OSError, ValueError):
            return False

    def _goarch(self):
        arch = str(self.settings.arch)
        if arch in ("armv8", "arm64", "aarch64"):
            return "arm64"
        if arch in ("x86_64", "amd64"):
            return "amd64"
        if arch.startswith("armv7"):
            return "arm"
        raise ConanInvalidConfiguration(f"Unsupported Go arch mapping: {arch}")

    def _host_goarch(self):
        import platform
        m = platform.machine().lower()
        if m in ("aarch64", "arm64"):
            return "arm64"
        return "amd64"

    def _go_executable(self):
        candidates = [
            os.environ.get("GO"),
            shutil.which("go"),
            os.path.expanduser("~/usr/local/go/bin/go"),
            os.path.expanduser("~/sdk/go1.26.5/bin/go"),
            "/data/storage/el2/base/cache/harmonybrew/bin/go",
            "/usr/local/go/bin/go",
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return self._bootstrapped_go_executable()

    def _bootstrapped_go_executable(self):
        go_toolchain = self.conan_data["go_toolchain"]
        host_key = f"linux-{self._host_goarch()}"
        package = go_toolchain[host_key]
        tools_dir = os.path.join(self._go_work_root(), "go-toolchain")
        archive = os.path.join(tools_dir, package["filename"])
        go_root = os.path.join(tools_dir, "go")
        go = os.path.join(go_root, "bin", "go")
        os.makedirs(tools_dir, exist_ok=True)
        if not os.path.isfile(archive):
            download(self, package["url"], archive, sha256=package["sha256"])
        # Always re-extract a fresh toolchain so OHOS signing is applied:
        # a previously extracted-but-unsigned toolchain fails execve (EACCES)
        # on OHOS workers (verified in CI).
        if os.path.isdir(go_root):
            shutil.rmtree(go_root)
        result = self.run(
            f'tar xzf "{archive}" -C "{tools_dir}"', ignore_errors=True)
        if result != 0:
            raise ConanInvalidConfiguration(
                f"Failed to extract bootstrapped Go toolchain archive: {archive}")
        self._ensure_go_toolchain_permissions(tools_dir, go_root)
        # OHOS exec policy rejects unsigned Go-produced binaries (EACCES);
        # sign every ELF in the toolchain so `go` and its sub-tools run.
        self._sign_go_toolchain(go_root)
        if not os.access(go, os.X_OK):
            raise ConanInvalidConfiguration(
                f"Bootstrapped Go executable is not runnable after chmod: {go}")
        return go

    def _ensure_go_toolchain_permissions(self, tools_dir, go_root):
        for directory in (tools_dir, go_root):
            if os.path.isdir(directory):
                self._chmod_read_exec(directory, is_dir=True)
        for dirpath, _dirnames, filenames in os.walk(go_root):
            self._chmod_read_exec(dirpath, is_dir=True)
            for filename in filenames:
                path = os.path.join(dirpath, filename)
                if os.access(path, os.X_OK) or self._is_elf(path):
                    self._chmod_read_exec(path, is_dir=False)
        if not os.access(go_root, os.X_OK | os.R_OK):
            raise ConanInvalidConfiguration(
                "Go toolchain root not traversable after chmod")

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_go_toolchain(self, go_root):
        """Sign every ELF in the bootstrapped Go toolchain.

        OHOS rejects unsigned Go-produced binaries at execve (EACCES);
        `go` and its bundled sub-tools (go/pkg/tool/*) must all be signed
        with binary-sign-tool before they can run.
        """
        signer = self._find_binary_sign_tool()
        if not signer:
            self.output.warning(
                "binary-sign-tool not found; Go toolchain left unsigned")
            return
        signed = 0
        for dirpath, _dirnames, filenames in os.walk(go_root):
            for filename in filenames:
                path = os.path.join(dirpath, filename)
                if not self._is_elf(path):
                    continue
                subprocess.run(
                    [signer, "sign", "-inFile", path, "-outFile", path,
                     "-selfSign", "1"],
                    check=True, capture_output=True, timeout=120)
                signed += 1
        self.output.info(f"Signed {signed} Go toolchain ELF binaries")

    def _chmod_read_exec(self, path, is_dir=False):
        try:
            if is_dir:
                os.chmod(path, 0o755)
            else:
                os.chmod(path, 0o755)
        except OSError:
            pass

    def _chmod_exec(self, path):
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR |
                 stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)

    def _find_binary_sign_tool(self):
        candidates = [
            os.environ.get("BINARY_SIGN_TOOL"),
            shutil.which("binary-sign-tool"),
            "/data/service/hnp/bin/binary-sign-tool",
            "/data/storage/el2/base/cache/harmonybrew/bin/binary-sign-tool",
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

    def _sign_ohos_executable(self, path):
        signer = self._find_binary_sign_tool()
        if not signer:
            # OHOS requires signed binaries to execute; without the tool the
            # package is still built but marked un-runnable (CI validates).
            self.output.warning(
                "binary-sign-tool not found; built binary left unsigned")
            return
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", path,
             "-selfSign", "1"],
            check=True)
