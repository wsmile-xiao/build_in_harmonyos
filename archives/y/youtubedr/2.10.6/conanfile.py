#!/usr/bin/env python3
"""Conan recipe for youtubedr 2.10.6 (github.com/kkdai/youtube/v2, Go).

youtubedr 是一个纯 Go 项目：既是 Go 库（github.com/kkdai/youtube/v2），也是
CLI 工具（cmd/youtubedr）。官方 `make test-unit` 即 `go test -v -cover ./...`。

激进环境说明（参照 murex/aliae/signal-tlsd 先例）：
- hmbs 预检沙盒不注入 go，配方自包含下载 Go 1.26.3 工具链（aliyun 镜像）。
- CGO_ENABLED=0 + GOOS=linux + GOARCH=arm64 交叉编译，产物在 OHOS aarch64 直接运行。
- GOPROXY=https://goproxy.cn,direct 拉取 Go 模块依赖。
- OHOS 可执行文件（产物 + go test 测试二进制）需 binary-sign-tool 签名后才能 exec，
  测试用 `go test -exec=<wrapper>` 先签名再运行（murex 同法）。

上游测试处理（据实上报，不伪造通过）：
- 在 build() 内运行官方命令 `go test ./... -timeout 30m -v`。
- 结果计数来自 go test -v 确定性输出行 `--- PASS|FAIL|SKIP`（顶层层级，子测试有
  缩进被排除），discovered = passed+failed+skipped、executed = passed+failed，
  单一数据源，不数数相减、不做猜测修正；发出前自检恒等式。
- 上游部分单元测试直接访问 YouTube 网络端点（真实 GetVideo/GetPlaylist/字幕/下载），
  在无外网或 YouTube 受限的 OHOS 沙盒里必然失败/超时；这类以 `test_failure` /
  `ohos_feature` gap 如实上报，不把环境缺口包装成通过。
- go test 整包编译失败（无任何 `--- PASS|FAIL|SKIP` 结果行）视为硬故障，抛
  ConanException；仅运行时测试失败/跳过不抛，让 hmbs 读到真实标记。
"""
import json
import os
import platform
import re
import shlex
import shutil
import stat
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, download, get
from conan.tools.layout import basic_layout


UPSTREAM_TOTAL = 31  # 非 integration 的 func Test 总数（27 root + 4 downloader）
UPSTREAM_FRAMEWORK = "go-test"
UPSTREAM_COMMAND = "go test ./... -timeout 30m -v"

# 从上游源码审计确认直接访问 YouTube 网络端点的顶层测试（真实 GetVideo/GetPlaylist/
# GetStream/字幕/下载），在无外网或 YouTube 受限的 OHOS 沙盒无法执行。这些用例若在
# 真机 go test 中失败/跳过，按 ohos_feature gap 如实上报；其余失败按 test_failure 上报。
NETWORK_TESTS = {
    # client_test.go
    "TestParseVideo", "TestGetVideoWithoutManifestURL",
    "TestWebClientGetVideoWithoutManifestURL", "TestGetVideoWithManifestURL",
    "TestGetVideo_MultiLanguage", "TestGetStream", "TestGetPlaylist",
    "TestGetBigPlaylist", "TestClient_httpGetBodyBytes",
    # video_test.go
    "TestSimpleTest", "TestDownload_Regular",
    "TestDownload_WhenPlayabilityStatusIsNotOK", "TestDownload_SensitiveContent",
    "TestParse_PublishDate",
    # transcript_test.go
    "TestTranscript", "TestTranscriptOtherLanguage",
    # downloader_test.go
    "TestDownload_FirstStream",
}


class YoutubedrConan(ConanFile):
    name = "youtubedr"
    version = "2.10.6"
    description = "YouTube video downloader (Go): library github.com/kkdai/youtube/v2 plus youtubedr CLI"
    license = "MIT"
    homepage = "https://github.com/kkdai/youtube"
    url = "https://github.com/kkdai/youtube"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")
        self._goarch()

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        go = self._go_executable()
        env = self._go_environment(go)
        self._run_upstream_tests(go, env)
        self._build_binary(go, env)

    # ------------------------------------------------------------------ *
    # Build
    # ------------------------------------------------------------------ *

    def _build_binary(self, go, env):
        binary = "youtubedr"
        output_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, binary)
        link_output_path = self._go_link_output_path(binary)
        cmd = [
            go, "build", "-trimpath",
            "-ldflags", "-s -w -X main.version=%s" % self.version,
            "-o", link_output_path,
            "./cmd/youtubedr",
        ]
        proc = subprocess.run(cmd, cwd=self.source_folder, env=env,
                              capture_output=True, text=True)
        if proc.stdout:
            print(proc.stdout, flush=True)
        if proc.stderr:
            print(proc.stderr, flush=True, file=__import__("sys").stderr)
        if proc.returncode != 0:
            from conan.errors import ConanException
            raise ConanException(
                "go build ./cmd/youtubedr failed: returncode=%s\n%s"
                % (proc.returncode, (proc.stderr or proc.stdout))
            )
        shutil.copy2(link_output_path, output_path)
        if self._platform_supports_chmod():
            os.chmod(output_path,
                     stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR |
                     stat.S_IRGRP | stat.S_IXGRP |
                     stat.S_IROTH | stat.S_IXOTH)
        self._sign_ohos_executable(output_path)

    # ------------------------------------------------------------------ *
    # Upstream tests (honest HMBS marker)
    # ------------------------------------------------------------------ *

    def _run_upstream_tests(self, go, env):
        command = [go, "test"]
        if self.settings.os == "OHOS":
            command.append(f"-exec={self._go_test_exec_wrapper(env)}")
        command.append("./...")
        command.append("-timeout")
        command.append("30m")
        command.append("-v")

        proc = subprocess.run(command, cwd=self.source_folder, env=env,
                              capture_output=True, text=True)
        if proc.stdout:
            print(proc.stdout, flush=True)
        if proc.stderr:
            print(proc.stderr, flush=True, file=__import__("sys").stderr)

        stdout = proc.stdout or ""
        (discovered, passed, failed, skipped,
         failed_names, skipped_names) = self._parse_go_test_counts(stdout)

        if discovered == 0:
            # No test binary produced any per-test result line -> compile error
            # or toolchain failure. This is a hard recipe problem, raise it.
            from conan.errors import ConanException
            raise ConanException(
                "go test ./... produced no per-test output (compile/toolchain "
                "failure). returncode=%s\n%s"
                % (proc.returncode, (proc.stderr or stdout))
            )

        status = "passed" if failed == 0 else "failed"
        # Single deterministic source: `--- PASS/FAIL/SKIP` result lines.
        # executed = passed + failed; discovered = executed + skipped. This
        # satisfies passed+failed==executed and executed+skipped<=discovered.
        executed = passed + failed
        if executed <= 0:
            # All tests skipped: nothing actually executed.
            executed = 0

        # Identity self-check (hmbs hard gate): never emit an inconsistent marker.
        if not (
            passed + failed == executed
            and executed + skipped <= discovered
            and executed <= discovered
            and discovered >= 0 and executed >= 0 and passed >= 0
            and failed >= 0 and skipped >= 0
        ):
            from conan.errors import ConanException
            raise ConanException(
                "upstream test count identity violated: discovered=%s executed=%s "
                "passed=%s failed=%s skipped=%s" % (
                    discovered, executed, passed, failed, skipped)
            )

        # Honest gaps: classify each failed/skipped test by whether it is one of
        # the known network-bound tests (source-audited) vs an unexpected failure.
        gaps = []
        if failed + skipped > 0:
            net = sorted(
                name for name in (failed_names | skipped_names)
                if name in NETWORK_TESTS
            )
            other = sorted(
                name for name in (failed_names | skipped_names)
                if name not in NETWORK_TESTS
            )
            if net:
                gaps.append({
                    "count": len(net),
                    "category": "ohos_feature",
                    "detail": (
                        "上游测试直接访问 YouTube 网络端点（GetVideo/GetPlaylist/"
                        "GetStream/GetTranscript/下载），OHOS 沙盒无外网或 YouTube 受限，"
                        "无法执行: %s" % ", ".join(net)
                    ),
                    "evidence": "go test ./... 真机输出 --- FAIL/SKIP 行 + 上游源码网络调用审计",
                })
            if other:
                gaps.append({
                    "count": len(other),
                    "category": "test_failure",
                    "detail": "非网络类用例失败/跳过（真机实测）: %s" % ", ".join(other),
                    "evidence": "go test ./... 真机输出 --- FAIL/SKIP 行",
                })

        self._emit_upstream_marker(
            status=status, discovered=discovered, executed=executed,
            passed=passed, failed=failed, skipped=skipped, gaps=gaps,
        )

        if failed > 0:
            self.output.warning(
                "Upstream `go test ./...` reported %d failed / %d skipped test(s) "
                "on the OHOS device. See HMBS_UPSTREAM_TEST_RESULT; failures are "
                "reported honestly as gaps (mostly network-bound tests)."
                % (failed, skipped)
            )

    @staticmethod
    def _parse_go_test_counts(stdout):
        """Parse `go test -v` stdout deterministically.

        go test -v prints one result line per top-level test, unindented:
            --- PASS: TestFoo (0.00s)
            --- FAIL: TestBar (0.00s)
            --- SKIP: TestBaz (0.00s)
        Subtests are indented by 4 spaces (`    --- PASS: TestFoo/sub`), so we
        only match lines with no leading whitespace to count top-level tests.
        These result lines are the single deterministic count source:
        discovered = passed + failed + skipped, executed = passed + failed.
        """
        pass_names = set(re.findall(r"^--- PASS:\s+(\S+)", stdout, flags=re.M))
        fail_names = set(re.findall(r"^--- FAIL:\s+(\S+)", stdout, flags=re.M))
        skip_names = set(re.findall(r"^--- SKIP:\s+(\S+)", stdout, flags=re.M))

        passed = len(pass_names)
        failed = len(fail_names)
        skipped = len(skip_names)
        discovered = passed + failed + skipped
        return discovered, passed, failed, skipped, fail_names, skip_names

    def _emit_upstream_marker(self, *, status, discovered, executed,
                              passed, failed, skipped, gaps=None):
        ut = {
            "status": status,
            "framework": UPSTREAM_FRAMEWORK,
            "command": UPSTREAM_COMMAND,
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        if gaps:
            ut["gaps"] = gaps
        print(f"HMBS_UPSTREAM_TEST_RESULT={json.dumps(ut)}", flush=True)

    # ------------------------------------------------------------------ *
    # Go toolchain / environment (murex-proven)
    # ------------------------------------------------------------------ *

    def _go_executable(self):
        candidates = [
            os.environ.get("GO"),
            shutil.which("go"),
            os.path.expanduser("~/usr/local/go1263/bin/go"),
            os.path.expanduser("~/sdk/go1.26.3/bin/go"),
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

    def _platform_supports_chmod(self):
        """Whether the OHOS HMFS/fuse filesystem allows os.chmod().

        hmbs reports filesystem capabilities via HMBS_CAP_* env vars. When
        `chmod` is 0 (HMFS fuse denies chmod with EPERM -> Python raises
        PermissionError), we must not call os.chmod() at all: the mode bits
        under such a mount are fixed at creation time (tar extraction already
        preserved the Go toolchain's exec bits), so forcing a chmod is both
        impossible and unnecessary. Absent evidence to the contrary we assume
        chmod is supported (Linux-native / ext4 workers), keeping old behavior.
        """
        val = os.environ.get("HMBS_CAP_CHMOD")
        if val is None or val == "":
            return True
        return val.strip().lower() not in ("0", "false", "no")

    def _chmod_read_exec(self, path, is_dir=False, executable=False):
        if not self._platform_supports_chmod():
            # HMFS fuse filesystem rejects chmod (PermissionError). Mode bits
            # are fixed at extraction; the archive already stores exec bits, so
            # skip chmod rather than crash the build.
            self.output.debug(
                "HMBS_CAP_CHMOD=0: skipping chmod on %s (filesystem-fixed mode)"
                % path
            )
            return
        mode = os.stat(path).st_mode
        read_exec = stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH
        if executable or is_dir:
            read_exec |= stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        if not is_dir:
            read_exec |= stat.S_IWUSR
        os.chmod(path, mode | read_exec)

    def _sign_ohos_executable(self, path):
        if self.settings.os != "OHOS" or not os.path.isfile(path):
            return
        signer = self._find_binary_sign_tool()
        if not signer:
            self.output.warning(
                "binary-sign-tool not found; OHOS may reject executable: %s" % path
            )
            return
        self.run(
            f"{shlex.quote(signer)} sign "
            f"-inFile {shlex.quote(path)} "
            f"-outFile {shlex.quote(path)} -selfSign 1",
            ignore_errors=True, quiet=True,
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
        if self._platform_supports_chmod():
            os.chmod(wrapper,
                     stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR |
                     stat.S_IRGRP | stat.S_IXGRP |
                     stat.S_IROTH | stat.S_IXOTH)
            exec_cmd = wrapper
        else:
            # HMFS fuse worker with chmod disabled: a freshly written wrapper
            # has no exec bit and chmod is forbidden, so run it through /bin/sh
            # (go's -exec value is split on whitespace into an argv).
            exec_cmd = f"/bin/sh {shlex.quote(wrapper)}"
        env["OHOS_GO_TEST_SIGNER"] = signer
        return exec_cmd

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
                os.environ.get("YOUTUBEDR_GO_BUILD_ROOT"),
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

    def _host_goarch(self):
        machine = platform.machine().lower()
        if machine in ("x86_64", "amd64"):
            return "amd64"
        if machine in ("aarch64", "arm64"):
            return "arm64"
        raise ConanInvalidConfiguration(f"Unsupported Go host architecture: {machine}")

    # ------------------------------------------------------------------ *
    # Package
    # ------------------------------------------------------------------ *

    def package(self):
        output_path = os.path.join(self.build_folder, "bin", "youtubedr")
        if os.path.isfile(output_path):
            copy(self, "youtubedr", src=os.path.join(self.build_folder, "bin"),
                 dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "README.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc", "youtubedr"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
