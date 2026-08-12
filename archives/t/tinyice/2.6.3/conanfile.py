#!/usr/bin/env python3
"""Conan recipe for tinyice 2.6.3."""
import os
import platform
import re
import shlex
import shutil
import stat
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    download,
    export_conandata_patches,
    get,
    unzip,
)
from conan.tools.layout import basic_layout


class TinyiceConan(ConanFile):
    name = "tinyice"
    version = "2.6.3"
    description = "Icecast-compatible streaming server with RTMP, SRT, WebRTC, HLS, and AutoDJ support"
    license = "Apache-2.0"
    homepage = "https://github.com/DatanoiseTV/tinyice"
    url = "https://github.com/DatanoiseTV/tinyice"
    package_type = "application"
    _minimum_go_version = (1, 25, 1)

    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self)

    def configure(self):
        self.settings.rm_safe("compiler")
        self.settings.rm_safe("build_type")
        self.settings.rm_safe("os.version")

    def package_id(self):
        self.info.settings.rm_safe("compiler")
        self.info.settings.rm_safe("build_type")
        self.info.settings.rm_safe("os.version")

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        os_name = str(self.settings.os)
        arch = str(self.settings.arch)
        if os_name not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"tinyice 2.6.3 source build does not support {os_name}")
        if arch not in ("armv8", "armv8.3"):
            raise ConanInvalidConfiguration(f"tinyice 2.6.3 source build requires aarch64/armv8, got {arch}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        os.makedirs(self.build_folder, exist_ok=True)

        binary = os.path.join(self.build_folder, "tinyice-real")
        go = self._find_go()
        go_env = self._go_environment(go)
        go_output_dir = self._go_output_dir()
        os.makedirs(go_output_dir, exist_ok=True)
        tmp_binary = os.path.join(
            tempfile.mkdtemp(prefix="tinyice-go-", dir=go_output_dir),
            "tinyice-real",
        )

        self.output.info(f"Building tinyice with {go}")
        subprocess.run(
            [
                go,
                "build",
                "-trimpath",
                "-ldflags=-s -w",
                "-o",
                tmp_binary,
                ".",
            ],
            cwd=self.source_folder,
            env=go_env,
            check=True,
        )
        self._copy_executable(tmp_binary, binary)
        self._make_executable(binary)
        if str(self.settings.os) == "OHOS":
            self._sign_ohos_elf(binary)

        wrapper_src = os.path.join(self.build_folder, "tinyice-wrapper.c")
        wrapper_bin = os.path.join(self.build_folder, "tinyice")
        self._write_wrapper_source(wrapper_src)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c")
        if not cc:
            raise ConanException("tools.build:compiler_executables must define the C compiler for tinyice wrapper")
        tmp_dir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        tmp_prefix = os.path.join(tmp_dir, "tinyice")
        self.run(f'TMPDIR="{tmp_dir}" TMPPREFIX="{tmp_prefix}" "{cc}" -O2 -o "{wrapper_bin}" "{wrapper_src}"')
        self._make_executable(wrapper_bin)

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        libexec_dir = os.path.join(self.package_folder, "libexec", "tinyice")
        os.makedirs(bin_dir, exist_ok=True)
        os.makedirs(libexec_dir, exist_ok=True)

        self._copy_executable(os.path.join(self.build_folder, "tinyice-real"), os.path.join(libexec_dir, "tinyice-real"))
        self._copy_executable(os.path.join(self.build_folder, "tinyice"), os.path.join(bin_dir, "tinyice"))

    def _make_executable(self, path):
        mode = os.stat(path).st_mode
        os.chmod(path, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    def _copy_executable(self, src, dst):
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        fd = os.open(dst, flags, 0o755)
        try:
            with os.fdopen(fd, "wb") as output, open(src, "rb") as input_file:
                while True:
                    chunk = input_file.read(1024 * 1024)
                    if not chunk:
                        break
                    output.write(chunk)
        finally:
            self._make_executable(dst)

    def _find_go(self):
        candidates = []
        for name in ("GO", "GO_BINARY"):
            value = os.environ.get(name)
            if value:
                candidates.append(value)
        resolved = shutil.which("go")
        if resolved:
            candidates.append(resolved)
        for dep in self.dependencies.build.values():
            package_folder = dep.package_folder
            for bindir in dep.cpp_info.bindirs:
                if not os.path.isabs(bindir):
                    bindir = os.path.join(package_folder, bindir)
                candidates.append(os.path.join(bindir, "go"))
        home = os.path.expanduser("~")
        candidates.extend(
            [
                os.path.join(home, ".local", "opt", "go", "bin", "go"),
                os.path.join(home, ".local", "bin", "go"),
                os.path.join(home, "usr", "local", "go", "bin", "go"),
                os.path.join(home, "usr", "local", "go1.26", "go", "bin", "go"),
                os.path.join(home, "usr", "local", "go1263", "bin", "go"),
                os.path.join(home, "sdk", "go1.26.3", "bin", "go"),
                os.path.join(home, ".harmonybrew", "bin", "go"),
            ]
        )
        checked = []
        seen = set()
        for candidate in candidates:
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            checked.append(candidate)
            if not os.path.isfile(candidate):
                continue
            usable, detail = self._probe_go(candidate)
            if usable:
                return candidate
            checked[-1] = f"{candidate} ({detail})"

        if checked:
            self.output.warning(
                "No usable preinstalled Go toolchain found; checked: "
                + ", ".join(checked)
            )
        go = self._bootstrapped_go_executable()
        usable, detail = self._probe_go(go)
        if not usable:
            raise ConanException(
                f"Bootstrapped Go toolchain is not usable: {go} ({detail})"
            )
        return go

    def _probe_go(self, candidate):
        try:
            env = os.environ.copy()
            env["GOTOOLCHAIN"] = "local"
            result = subprocess.run(
                [candidate, "version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                check=False,
            )
        except OSError as error:
            return False, error.strerror or str(error)
        output = (result.stdout or result.stderr).strip()
        if result.returncode != 0:
            return False, output or f"exit code {result.returncode}"
        version = self._parse_go_version(output)
        if not version:
            return False, f"unrecognized version output: {output}"
        if version < self._minimum_go_version:
            return False, f"{output}; requires go1.25.1 or newer"
        self.output.info(output)
        return True, output

    def _parse_go_version(self, output):
        match = re.search(r"go version go(\d+)\.(\d+)(?:\.(\d+))?", output)
        if not match:
            return None
        major = int(match.group(1))
        minor = int(match.group(2))
        patch = int(match.group(3) or 0)
        return (major, minor, patch)

    def _bootstrapped_go_executable(self):
        package = self.conan_data["go_toolchain"][
            f"linux-{self._host_goarch()}"
        ]
        tools_dir = os.path.join(self._go_work_root(), "go-toolchain")
        go_root = os.path.join(tools_dir, "go")
        go = os.path.join(go_root, "bin", "go")
        marker = os.path.join(
            go_root,
            ".tinyice-ready-"
            f"{self.conan_data['go_toolchain']['version']}-"
            f"{self._build_os().lower()}-{self._host_goarch()}",
        )
        if os.path.isfile(go) and os.path.isfile(marker):
            self.output.info(f"Reusing bootstrapped Go toolchain: {go}")
            return go

        if os.path.isdir(go_root):
            shutil.rmtree(go_root)
        os.makedirs(tools_dir, exist_ok=True)
        archive = os.path.join(tools_dir, package["filename"])
        self.output.info(
            "No suitable Go toolchain is installed; downloading verified "
            f"Go {self.conan_data['go_toolchain']['version']}"
        )
        download(
            self,
            package["url"],
            archive,
            sha256=package["sha256"],
        )
        unzip(self, archive, destination=tools_dir)
        try:
            os.remove(archive)
        except OSError:
            pass
        if not os.path.isfile(go):
            raise ConanException(
                f"Go archive extracted without the expected executable: {go}"
            )
        self._prepare_go_toolchain(go_root)
        with open(marker, "w", encoding="utf-8", newline="\n") as output:
            output.write(
                f"go {self.conan_data['go_toolchain']['version']} ready\n"
            )
        return go

    def _prepare_go_toolchain(self, go_root):
        executable_roots = (
            os.path.join(go_root, "bin"),
            os.path.join(
                go_root,
                "pkg",
                "tool",
                f"linux_{self._host_goarch()}",
            ),
        )
        prepared = 0
        for executable_root in executable_roots:
            if not os.path.isdir(executable_root):
                continue
            for dirpath, _, filenames in os.walk(executable_root):
                for filename in filenames:
                    path = os.path.join(dirpath, filename)
                    self._make_executable(path)
                    if self._build_os() == "OHOS" and self._is_elf(path):
                        self._sign_ohos_elf(path)
                    prepared += 1
        if not prepared:
            raise ConanException(
                f"Go archive contains no executable tools under {go_root}"
            )
        self.output.info(f"Prepared {prepared} Go toolchain executables")

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as binary:
                return binary.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _host_goarch(self):
        machine = platform.machine().lower()
        if machine in ("aarch64", "arm64"):
            return "arm64"
        if machine in ("x86_64", "amd64"):
            return "amd64"
        raise ConanInvalidConfiguration(
            f"No portable Go toolchain is configured for build host {machine}"
        )

    def _build_os(self):
        settings_build = getattr(self, "settings_build", None)
        if settings_build is not None:
            return str(settings_build.os)
        return str(self.settings.os)

    def _go_environment(self, go):
        work_root = self._go_work_root()
        cache_root = os.path.join(work_root, "cache")
        env = os.environ.copy()
        go_root = self._go_root(go)
        env.update(
            {
                "CGO_ENABLED": "0",
                "GOOS": "linux",
                "GOARCH": "arm64",
                "GOCACHE": os.path.join(cache_root, "build"),
                "GOMODCACHE": os.path.join(cache_root, "mod"),
                "GOPATH": os.path.join(cache_root, "gopath"),
                "GOPROXY": env.get(
                    "GOPROXY", "https://goproxy.cn,direct"
                ),
                "GOSUMDB": env.get("GOSUMDB", "sum.golang.google.cn"),
                "GOROOT": go_root,
                "GOTOOLCHAIN": "local",
                "GOTMPDIR": os.path.join(cache_root, "gotmp"),
                "TMPDIR": os.path.join(cache_root, "tmp"),
            }
        )
        env["PATH"] = os.path.dirname(go) + os.pathsep + env.get("PATH", "")
        for name in ("GOCACHE", "GOMODCACHE", "GOPATH", "GOTMPDIR", "TMPDIR"):
            os.makedirs(env[name], exist_ok=True)
        return env

    def _go_root(self, go):
        env = os.environ.copy()
        env["GOTOOLCHAIN"] = "local"
        result = subprocess.run(
            [go, "env", "GOROOT"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            check=False,
        )
        go_root = result.stdout.strip()
        if result.returncode != 0 or not os.path.isdir(go_root):
            detail = (result.stderr or result.stdout).strip()
            raise ConanException(
                f"Unable to resolve GOROOT from {go}: "
                f"{detail or f'exit code {result.returncode}'}"
            )
        return go_root

    def _go_output_dir(self):
        output = os.path.join(self._go_work_root(), "out")
        os.makedirs(output, exist_ok=True)
        return output

    def _go_work_root(self):
        if self._build_os() == "OHOS":
            candidates = (
                os.environ.get("TINYICE_GO_TMPDIR"),
                os.environ.get("OHOS_GO_BUILD_ROOT"),
                "/data/storage/el2/base/cache",
                "/data/storage/el2/base/haps/entry/files",
                "/dev/shm",
                os.environ.get("TMPDIR"),
            )
        else:
            candidates = (
                os.environ.get("TINYICE_GO_TMPDIR"),
                os.environ.get("TMPDIR"),
                os.path.dirname(os.path.abspath(self.build_folder)),
            )
        for candidate in candidates:
            if not candidate:
                continue
            root = os.path.join(
                candidate,
                "conan-go-build",
                f"{self.name}-{self.version}",
            )
            try:
                os.makedirs(root, exist_ok=True)
                probe = os.path.join(root, ".write-probe")
                with open(probe, "wb") as output:
                    output.write(b"ok")
                os.remove(probe)
                return root
            except OSError:
                continue
        raise ConanInvalidConfiguration(
            "No writable directory is available for the Go toolchain, "
            "cache, and linker output"
        )

    def _sign_ohos_elf(self, path):
        objcopy = self._find_ohos_tool("llvm-objcopy")
        sign_tool = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not sign_tool:
            raise ConanInvalidConfiguration(
                "OHOS ELF signing requires llvm-objcopy and binary-sign-tool"
            )
        self.run(
            f"{shlex.quote(objcopy)} --remove-section .codesign "
            f"{shlex.quote(path)}",
            ignore_errors=True,
            quiet=True,
        )
        result = self.run(
            f"{shlex.quote(sign_tool)} sign -inFile {shlex.quote(path)} "
            f"-outFile {shlex.quote(path)} -selfSign 1",
            ignore_errors=True,
            quiet=True,
        )
        if result != 0:
            raise ConanException(f"Failed to sign OHOS ELF: {path}")
        self._make_executable(path)

    @staticmethod
    def _find_ohos_tool(name):
        candidates = (
            shutil.which(name),
            os.path.join("/data/service/hnp/bin", name),
            os.path.join(
                "/storage/Users/currentUser/usr/local/bin", name
            ),
        )
        return next(
            (
                candidate
                for candidate in candidates
                if candidate and os.path.isfile(candidate)
            ),
            None,
        )

    def _write_wrapper_source(self, path):
        source = r'''#include <stdio.h>
#include <string.h>
#include <unistd.h>

#ifndef PATH_MAX
#define PATH_MAX 4096
#endif

int main(int argc, char **argv) {
    char self_path[PATH_MAX];
    ssize_t len = readlink("/proc/self/exe", self_path, sizeof(self_path) - 1);
    if (len <= 0 || len >= (ssize_t)sizeof(self_path)) {
        fprintf(stderr, "tinyice wrapper: cannot resolve executable path\n");
        return 126;
    }
    self_path[len] = '\0';

    char *slash = strrchr(self_path, '/');
    if (slash == NULL) {
        fprintf(stderr, "tinyice wrapper: invalid executable path\n");
        return 126;
    }
    *slash = '\0';

    char real_path[PATH_MAX];
    int written = snprintf(real_path, sizeof(real_path), "%s/../libexec/tinyice/tinyice-real", self_path);
    if (written <= 0 || written >= (int)sizeof(real_path)) {
        fprintf(stderr, "tinyice wrapper: real binary path is too long\n");
        return 126;
    }

    argv[0] = real_path;
    execv(real_path, argv);
    perror("tinyice wrapper: exec tinyice-real");
    return 126;
}
'''
        with open(path, "w", encoding="utf-8", newline="\n") as output:
            output.write(source)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
