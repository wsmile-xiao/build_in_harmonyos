#!/usr/bin/env python3
"""Conan recipe for algernon 1.17.10."""

import os
import platform
import shlex
import shutil
import stat
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    download,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class AlgernonConan(ConanFile):
    name = "algernon"
    version = "1.17.10"
    description = "Small self-contained pure-Go web server with Lua, Markdown, HTTP/2, QUIC, Redis and PostgreSQL support"
    license = "BSD-3-Clause"
    homepage = "https://github.com/xyproto/algernon"
    url = "https://github.com/xyproto/algernon"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")
        self._goarch()

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

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
        command = [
            go,
            "build",
            "-mod=vendor",
            "-trimpath",
            "-ldflags",
            ldflags,
            "-buildvcs=false",
            "-o",
            link_output_path,
            self.conan_data["build"].get("main", "."),
        ]
        subprocess.run(command, cwd=self.source_folder, env=env, check=True)
        shutil.copy2(link_output_path, output_path)
        os.chmod(output_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR |
                 stat.S_IRGRP | stat.S_IXGRP |
                 stat.S_IROTH | stat.S_IXOTH)
        self._sign_ohos_executable(output_path)

    def _run_upstream_tests(self, go, env):
        command = [go, "test", "-mod=vendor"]
        if self.settings.os == "OHOS":
            command.append(f"-exec={self._go_test_exec_wrapper(env)}")
        command.append("./...")
        subprocess.run(command, cwd=self.source_folder, env=env, check=True)

    def _go_test_exec_wrapper(self, env):
        signer = self._find_binary_sign_tool()
        if not signer:
            raise ConanInvalidConfiguration(
                "binary-sign-tool is required to execute Go tests on OHOS"
            )
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
        os.chmod(
            wrapper,
            stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR |
            stat.S_IRGRP | stat.S_IXGRP |
            stat.S_IROTH | stat.S_IXOTH,
        )
        env["OHOS_GO_TEST_SIGNER"] = signer
        return wrapper

    def package(self):
        binary = self.conan_data["build"]["binary"]
        copy(self, binary, src=os.path.join(self.build_folder, "bin"),
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "README.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc", "algernon"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))

    def _go_environment(self, go):
        env = os.environ.copy()
        cache_root = os.path.join(self._go_work_root(), "cache")
        go_root = os.path.dirname(os.path.dirname(os.path.abspath(go)))
        env.update({
            "CGO_ENABLED": "0",
            "GOOS": "linux",
            "GOARCH": self._goarch(),
            "GOCACHE": os.path.join(cache_root, "build"),
            "GOMODCACHE": os.path.join(cache_root, "mod"),
            "GOPATH": os.path.join(cache_root, "gopath"),
            "GOPROXY": env.get("GOPROXY", "https://goproxy.cn,direct"),
            "GOROOT": go_root,
            "GOTOOLCHAIN": "local",
            "TMPDIR": os.path.join(cache_root, "tmp"),
            "GOTMPDIR": os.path.join(cache_root, "gotmp"),
        })
        for path in ("GOCACHE", "GOMODCACHE", "GOPATH", "TMPDIR", "GOTMPDIR"):
            os.makedirs(env[path], exist_ok=True)
        # Upstream plugin tests compile helper binaries with
        # exec.Command("go", "build", "-o", ...) and then fork/exec them.
        # `go test` prepends $GOROOT/bin to the test process PATH, so a plain
        # PATH shim never wins. Instead we point GOROOT at a shim GOROOT whose
        # bin/go signs every `go build -o` output (including plugin helpers)
        # with binary-sign-tool before the OS executes it on OHOS. Everything
        # else in the shim GOROOT is a symlink to the real toolchain.
        if self.settings.os == "OHOS":
            signer = self._find_binary_sign_tool()
            if signer:
                shim_goroot = self._install_goroot_shim(go)
                env["GOROOT"] = shim_goroot
                env["ALGERNON_REAL_GOROOT"] = go_root
                env["ALGERNON_GO_SIGNER"] = signer
                env["PATH"] = os.path.join(shim_goroot, "bin") + os.pathsep + \
                    env.get("PATH", "")
            else:
                env["PATH"] = os.path.dirname(go) + os.pathsep + env.get("PATH", "")
        else:
            env["PATH"] = os.path.dirname(go) + os.pathsep + env.get("PATH", "")
        return env

    def _install_goroot_shim(self, go):
        real_goroot = os.path.dirname(os.path.dirname(os.path.abspath(go)))
        shim_goroot = os.path.join(self._go_work_root(), "goroot-shim")
        bin_dir = os.path.join(shim_goroot, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        # Symlink every top-level entry except bin/.
        for name in os.listdir(real_goroot):
            if name == "bin":
                continue
            link = os.path.join(shim_goroot, name)
            if not os.path.lexists(link):
                os.symlink(os.path.join(real_goroot, name), link)
        # Symlink every bin entry except go; keep the real go as go.real.
        for name in os.listdir(os.path.join(real_goroot, "bin")):
            if name == "go":
                continue
            link = os.path.join(bin_dir, name)
            if not os.path.lexists(link):
                os.symlink(os.path.join(real_goroot, "bin", name), link)
        real_go_link = os.path.join(bin_dir, "go.real")
        if not os.path.lexists(real_go_link):
            os.symlink(go, real_go_link)
        wrapper = os.path.join(bin_dir, "go")
        with open(wrapper, "w", encoding="utf-8", newline="\n") as script:
            script.write(
                "#!/bin/sh\n"
                "set -u\n"
                "real_go=\"$(dirname \"$0\")/go.real\"\n"
                "signer=\"${ALGERNON_GO_SIGNER:-}\"\n"
                "real_goroot=\"${ALGERNON_REAL_GOROOT:-}\"\n"
                "out=\"\"\n"
                "prev=\"\"\n"
                "for arg in \"$@\"; do\n"
                "  if [ \"$prev\" = \"-o\" ]; then out=\"$arg\"; fi\n"
                "  prev=\"$arg\"\n"
                "done\n"
                "if [ -n \"$real_goroot\" ]; then\n"
                "  GOROOT=\"$real_goroot\" \"$real_go\" \"$@\"\n"
                "else\n"
                "  \"$real_go\" \"$@\"\n"
                "fi\n"
                "rc=$?\n"
                "if [ \"$rc\" -eq 0 ] && [ -n \"$out\" ] && "
                "[ -f \"$out\" ] && [ -n \"$signer\" ]; then\n"
                "  \"$signer\" sign -inFile \"$out\" -outFile \"$out\" "
                "-selfSign 1 >/dev/null 2>&1\n"
                "fi\n"
                "exit $rc\n"
            )
        os.chmod(wrapper, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR |
                 stat.S_IRGRP | stat.S_IXGRP |
                 stat.S_IROTH | stat.S_IXOTH)
        return shim_goroot

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
                os.environ.get("ALGERNON_GO_BUILD_ROOT"),
                os.path.join(os.path.dirname(os.path.abspath(self.source_folder)),
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
            "No writable Go build root is available for linker output"
        )

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

    def _go_executable(self):
        candidates = [
            os.environ.get("GO"),
            shutil.which("go"),
            os.path.expanduser("~/usr/local/go1263/bin/go"),
            os.path.expanduser("~/sdk/go1.26.3/bin/go"),
            os.path.expanduser("~/.goenv/versions/1.26.5/bin/go"),
            os.path.expanduser("~/.goenv/versions/1.26.3/bin/go"),
            "/data/storage/el2/base/cache/harmonybrew/bin/go",
            "/data/storage/el2/base/cache/usr/local/go1263/bin/go",
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
        if not os.path.isfile(go):
            os.makedirs(tools_dir, exist_ok=True)
            download(self, package["url"], archive, sha256=package["sha256"])
            result = self.run(
                f'tar xzf "{archive}" -C "{tools_dir}"',
                ignore_errors=True,
            )
            if result != 0:
                raise ConanInvalidConfiguration(
                    f"Failed to extract bootstrapped Go toolchain archive: {archive}"
                )
        self._ensure_go_toolchain_permissions(tools_dir, go_root)
        if not os.access(go, os.X_OK):
            raise ConanInvalidConfiguration(
                f"Bootstrapped Go executable is not runnable after chmod: {go}"
            )
        return go

    def _ensure_go_toolchain_permissions(self, tools_dir, go_root):
        for directory in (tools_dir, go_root):
            if os.path.isdir(directory):
                self._chmod_read_exec(directory, is_dir=True)
        executable_prefixes = (
            os.path.join(go_root, "bin"),
            os.path.join(go_root, "pkg", "tool"),
        )
        for dirpath, dirnames, filenames in os.walk(go_root):
            self._chmod_read_exec(dirpath, is_dir=True)
            for dirname in dirnames:
                self._chmod_read_exec(os.path.join(dirpath, dirname), is_dir=True)
            for filename in filenames:
                path = os.path.join(dirpath, filename)
                executable = any(
                    os.path.commonpath([path, root]) == root
                    for root in executable_prefixes
                    if os.path.isdir(root)
                )
                self._chmod_read_exec(path, executable=executable)
                if executable:
                    self._sign_ohos_executable(path)

    def _chmod_read_exec(self, path, is_dir=False, executable=False):
        mode = os.stat(path).st_mode
        read_exec = stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH
        if executable or is_dir:
            read_exec |= stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        if is_dir:
            mode |= stat.S_IWUSR
        if not is_dir:
            mode |= stat.S_IWUSR
        os.chmod(path, mode | read_exec)

    def _sign_ohos_executable(self, path):
        if self.settings.os != "OHOS" or not os.path.isfile(path):
            return
        signer = self._find_binary_sign_tool()
        if not signer:
            self.output.warning(
                "binary-sign-tool not found; OHOS may reject executable: "
                f"{path}"
            )
            return
        result = self.run(
            f"{shlex.quote(signer)} sign "
            f"-inFile {shlex.quote(path)} "
            f"-outFile {shlex.quote(path)} -selfSign 1",
            ignore_errors=True,
            quiet=True,
        )
        if result != 0:
            raise ConanInvalidConfiguration(
                f"binary-sign-tool failed with exit code {result}: {path}"
            )

    def _find_binary_sign_tool(self):
        candidates = [
            os.environ.get("OHOS_BINARY_SIGN_TOOL"),
            os.environ.get("BINARY_SIGN_TOOL"),
            "/data/service/hnp/bin/binary-sign-tool",
            "/storage/Users/currentUser/usr/local/bin/binary-sign-tool",
            shutil.which("binary-sign-tool"),
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

    def _host_goarch(self):
        machine = platform.machine().lower()
        if machine in ("x86_64", "amd64"):
            return "amd64"
        if machine in ("aarch64", "arm64"):
            return "arm64"
        raise ConanInvalidConfiguration(f"Unsupported Go host architecture: {machine}")
