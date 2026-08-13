#!/usr/bin/env python3
"""Conan recipe for aliae 1.5.0 — cross shell and platform alias management.

aliae 是 Go 项目（src/ 目录，go.mod 需 go 1.25.0），构建产物 bin/aliae 可执行。
本地无 Go 工具链，配方自包含下载 go 1.26.3（aliyun 镜像，参照 murex 配方）。
Go 模块依赖（goccy/go-yaml、shirou/gopsutil、spf13/cobra、golang.org/x/term 等）
通过 GOPROXY（goproxy.cn）拉取。

OHOS 适配要点：
- CGO_ENABLED=0 + GOOS=linux + GOARCH=arm64 交叉编译
- GOPROXY 指向 goproxy.cn（CI 内网可访问的 Go 模块代理）
- 测试：go test ./...（config/shell 等包共 15 个测试文件）
"""
import os
import shutil
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, download, get
from conan.tools.layout import basic_layout


class AliaeConan(ConanFile):
    name = "aliae"
    version = "1.5.0"
    description = "Cross shell and platform alias management"
    license = "MIT"
    homepage = "https://github.com/JanDeDobbeleer/aliae"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        # URL 无 .tar.gz 扩展名（codeload /tar.gz/ 路径），需 filename 指定以便 conan 正确解压
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="aliae-1.5.0.tar.gz")

    def _goarch(self):
        arch = str(self.settings.arch)
        if arch in ("armv8", "arm64", "aarch64"):
            return "arm64"
        if arch in ("x86_64", "amd64"):
            return "amd64"
        raise ConanInvalidConfiguration(f"Unsupported Go arch mapping: {arch}")

    def _go_work_root(self):
        # go link 在 HMDFS 的 conan build 目录 mmap 写失败（permission denied），
        # 参照 murex：OHOS 下把 go 构建根放到 /data/storage/el2/base/cache 等可写位置
        if self.settings.os == "OHOS":
            candidates = [
                os.environ.get("OHOS_GO_BUILD_ROOT"),
                "/data/storage/el2/base/cache",
                "/data/storage/el2/base/haps/entry/files",
                os.environ.get("TMPDIR"),
            ]
        else:
            candidates = [
                os.path.join(os.path.dirname(os.path.abspath(self.source_folder)),
                             "go-work"),
                os.environ.get("TMPDIR"),
            ]
        for candidate in candidates:
            if not candidate:
                continue
            root = os.path.join(candidate, "conan-go-build",
                                f"{self.name}-{self.version}")
            try:
                os.makedirs(root, exist_ok=True)
                return root
            except OSError:
                continue
        raise ConanInvalidConfiguration(
            "No writable Go build root is available for linker output"
        )

    def _go_link_output_path(self):
        output_dir = os.path.join(self._go_work_root(), "out")
        os.makedirs(output_dir, exist_ok=True)
        return os.path.join(output_dir, "aliae")

    def _go_toolchain(self):
        """自包含下载并解压 Go 工具链（参照 murex 配方）。"""
        tc = self.conan_data["go_toolchain"]
        host_key = f"linux-{self._goarch()}"
        package = tc[host_key]
        tools_dir = os.path.join(self._go_work_root(), "go-toolchain")
        archive = os.path.join(tools_dir, package["filename"])
        go_root = os.path.join(tools_dir, "go")
        go = os.path.join(go_root, "bin", "go")
        if not os.path.isfile(go):
            os.makedirs(tools_dir, exist_ok=True)
            download(self, package["url"], archive, sha256=package["sha256"])
            self.run(f'tar xzf "{archive}" -C "{tools_dir}"', ignore_errors=True)
        # OHOS/HMDFS 解包后目录/文件位可能不可遍历/不可执行，统一修复权限
        # （参照 murex：bin 与 pkg/tool 下文件加 X 位并签名，其余只读）
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
        return go

    def _chmod_read_exec(self, path, is_dir=False, executable=False):
        # HMDFS 上 os.chmod 可能被拒（PermissionError），但 tar 解压已保留正确
        # 权限位；chmod 失败仅告警，不阻塞（本地实测 go 二进制直接可执行）
        try:
            mode = os.stat(path).st_mode
            read_exec = stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH
            if executable or is_dir:
                read_exec |= stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
            mode |= stat.S_IWUSR
            os.chmod(path, mode | read_exec)
        except OSError as exc:
            self.output.info(f"chmod skipped on {path}: {exc}")

    def _sign_ohos_executable(self, path):
        """OHOS 需签名才能执行 ELF（binary-sign-tool + llvm-objcopy 移除 .codesign）。"""
        if self.settings.os != "OHOS" or not os.path.isfile(path):
            return
        signer = self._find_binary_sign_tool()
        objcopy = None
        for candidate in (
            os.environ.get("OHOS_LLVM_OBJCOPY"),
            "/data/service/hnp/bin/llvm-objcopy",
            shutil.which("llvm-objcopy"),
        ):
            if candidate and os.path.isfile(candidate):
                objcopy = candidate
                break
        if objcopy:
            self.run(f'"{objcopy}" --remove-section .codesign "{path}" 2>/dev/null || true',
                     ignore_errors=True, quiet=True)
        if not signer:
            self.output.warning("binary-sign-tool not found; OHOS may reject executable: %s" % path)
            return
        self.run(f'"{signer}" sign -inFile "{path}" -outFile "{path}" -selfSign 1',
                 ignore_errors=True, quiet=True)

    def _find_binary_sign_tool(self):
        for candidate in (
            os.environ.get("OHOS_BINARY_SIGN_TOOL"),
            os.environ.get("BINARY_SIGN_TOOL"),
            "/data/service/hnp/bin/binary-sign-tool",
            shutil.which("binary-sign-tool"),
        ):
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

    def _go_test_exec_wrapper(self, env):
        """go test -exec wrapper：运行测试二进制前先签名（OHOS 需签名才能 exec）。"""
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
            "PATH": os.path.dirname(go) + os.pathsep + env.get("PATH", ""),
            "TMPDIR": os.path.join(cache_root, "tmp"),
            "GOTMPDIR": os.path.join(cache_root, "gotmp"),
        })
        for path in ("GOCACHE", "GOMODCACHE", "GOPATH", "TMPDIR", "GOTMPDIR"):
            os.makedirs(env[path], exist_ok=True)
        return env

    def _run_go(self, command, env):
        """带 Go 环境的 shell 命令执行（env 为 dict，转成内联 export 防重置）。"""
        exports = " ".join(f'export {k}="{v}";' for k, v in env.items())
        self.run(f"{exports} {command}")

    def build(self):
        go = self._go_toolchain()
        env = self._go_environment(go)
        src_dir = os.path.join(self.source_folder, "src")
        # go build 编译 aliae（main.go 在 src/），输出到 go-work/out（HMDFS 可写）
        out_bin = self._go_link_output_path()
        self._run_go(f'cd "{src_dir}" && go build -trimpath -ldflags "-s -w -X main.Version=1.5.0" -o "{out_bin}" .', env)
        # 产物签名（OHOS 需签名才能执行）
        if self.settings.os == "OHOS" and os.path.isfile(out_bin):
            os.chmod(out_bin, os.stat(out_bin).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            self._sign_ohos_executable(out_bin)
        # 上游测试：go test ./...（config/shell 等包 15 个测试）。
        # OHOS 下测试二进制需签名才能 exec，用 -exec wrapper 先签名再运行（参照 murex）
        test_exec = ""
        if self.settings.os == "OHOS":
            test_exec = f'-exec={self._go_test_exec_wrapper(env)}'
        self._run_go(f'cd "{src_dir}" && go test {test_exec} ./...', env)

    def package(self):
        out_bin = os.path.join(self._go_work_root(), "out", "aliae")
        copy(self, "aliae", src=os.path.dirname(out_bin),
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
