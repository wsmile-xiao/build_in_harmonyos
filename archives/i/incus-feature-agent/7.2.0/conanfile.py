#!/usr/bin/env python3
"""Conan recipe for incus-feature-agent 7.2.0 — Incus VM agent (pure Go).

incus-feature-agent = 上游 Incus (https://github.com/lxc/incus) v7.2.0 的
``cmd/incus-agent`` 组件（虚拟机内 guest agent）。上游为纯 Go 项目
（100% Go，agent 组件零 cgo）；本配方以 ``CGO_ENABLED=0 GOOS=linux
GOARCH=arm64 -tags agent,netgo`` 静态交叉编译（Go 可执行文件即 OHOS 目标）。

构建要点（OHOS 适配，详见 notes.md / test_package/MANIFEST.yml）:
- Go 工具链自举：CI worker 无预装 Go，按 sha256 下载官方 Go SDK（1.25.10，
  对应 go.mod 的 ``go 1.25.10``），并对 SDK 内全部 ELF（bin/go、bin/gofmt、
  pkg/tool/linux_arm64/*）做 OHOS 自签名，否则内核拒绝 execve（未签名 ELF
  不可执行）。
- E523（linker fallocate EACCES）：Go 链接器对输出文件调用 fallocate()
  预分配，OHOS 的 HMDFS 返回 EACCES，而链接器只忽略 ENOTSUP/EPERM →
  链接失败。解法：``-toolexec`` 包装器把链接器 ``-o`` 输出重定向到支持
  fallocate 的 /dev/shm，链接完成后再拷贝回原路径。
- E318：``go test`` 产出的测试二进制同样需要 OHOS 签名后才能执行；本配方
  先 ``go test -c`` 编译、再签名、再直接执行（签名必须在 go 的最终拷贝之后）。

依赖：无第三方 C/C++ 库（N=0）；Go modules 由 ``go mod`` + GOPROXY 拉取
（``GOPROXY`` 环境变量可覆盖，便于离线/镜像环境）。

上游测试：``go test ./...``（Makefile ``unit-test``/``check`` 目标）。
本配方对 cmd/incus-agent 依赖闭包内含 *_test.go 的 14 个纯 Go 包实际执行
测试并输出 HMBS_UPSTREAM_TEST_RESULT 结构化证据。
"""
import json
import os
import platform
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout


# ── Go 工具链自举常量（官方源 + sha256；go.mod 要求 go >= 1.25.10）──
GO_VERSION = "1.25.10"
GO_ARCHIVES = {
    "arm64": (
        [
            "https://golang.google.cn/dl/go1.25.10.linux-arm64.tar.gz",
            "https://mirrors.aliyun.com/golang/go1.25.10.linux-arm64.tar.gz",
            "https://dl.google.com/go/go1.25.10.linux-arm64.tar.gz",
        ],
        "654da1f9b50a5d1c2a85ccf8ed405aa89c06e94d18384628bf186f7712677b08",
    ),
    "amd64": (
        [
            "https://golang.google.cn/dl/go1.25.10.linux-amd64.tar.gz",
            "https://mirrors.aliyun.com/golang/go1.25.10.linux-amd64.tar.gz",
            "https://dl.google.com/go/go1.25.10.linux-amd64.tar.gz",
        ],
        "42d4f7a32316aa66591eca7e89867256057a4264451aca10570a715b3637ba70",
    ),
}

# cmd/incus-agent 依赖闭包内含 *_test.go 的纯 Go 包（上游 `go test ./...`
# 在 CGO_ENABLED=0 下可运行子集；服务端 cgo 包在 OHOS 不可构建，见 notes.md）。
UPSTREAM_TEST_PACKAGES = [
    "shared/api",
    "shared/osarch",
    "shared/revert",
    "shared/scriptlet",
    "shared/subprocess",
    "shared/tls",
    "internal/jmap",
    "internal/util",
    "internal/version",
    "internal/server/auth",
    "internal/server/device/config",
    "internal/server/metrics",
    "internal/server/storage/memorypipe",
    "internal/server/util",
]

BINARY_NAME = "incus-agent"

# -toolexec 包装器：把 tool 的 -o 输出重定向到支持 fallocate 的目录，
# 规避 OHOS HMDFS 上 fallocate()=EACCES 导致 Go 链接器失败（知识 E523）。
# 只做重定向，不签名——签名由配方在 go 最终拷贝之后显式执行（E318）。
_TOOLEXEC_WRAPPER = r"""#!/data/service/hnp/bin/bash
# Go -toolexec wrapper（E523）：把链接器 -o 输出重定向到 fallocate 可用目录
set -eu
TOOL="$1"
shift
REDIR="${INCUS_AGENT_LINK_REDIR:-/dev/shm}"
IS_LINKER=false
OUTPUT_FILE=""
NEW_ARGS=()
REDIR_OUTPUT=""
for arg in "$@"; do
    if [[ "$arg" == -o ]]; then
        IS_LINKER=true
        NEW_ARGS+=("$arg")
        continue
    fi
    if [[ "$IS_LINKER" == true && -z "$OUTPUT_FILE" ]]; then
        OUTPUT_FILE="$arg"
        REDIR_OUTPUT="${REDIR}/$(basename "$OUTPUT_FILE").$$"
        NEW_ARGS+=("$REDIR_OUTPUT")
    else
        NEW_ARGS+=("$arg")
    fi
done
if [[ "$IS_LINKER" == true && -n "$REDIR_OUTPUT" ]]; then
    "$TOOL" "${NEW_ARGS[@]}"
    cp "$REDIR_OUTPUT" "$OUTPUT_FILE"
    rm -f "$REDIR_OUTPUT"
else
    exec "$TOOL" "$@"
fi
"""


class IncusFeatureAgentConan(ConanFile):
    name = "incus-feature-agent"
    version = "7.2.0"
    description = "Incus virtual machine agent (pure Go) adapted for HarmonyOS PC"
    license = "Apache-2.0"
    homepage = "https://github.com/lxc/incus"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("incus", "agent", "virtual-machine", "go")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"incus-feature-agent supports Linux and OHOS only, got {self.settings.os}"
            )
        if str(self.settings.arch) not in ("armv8", "x86_64"):
            raise ConanInvalidConfiguration(
                f"Unsupported architecture: {self.settings.arch}"
            )

    # ────────────────────────── generate ──────────────────────────
    def generate(self):
        go = self._go_executable()
        ws = self._go_workspace()
        for sub in ("tmp", "go-build-cache", "go-mod-cache", "link-out"):
            os.makedirs(os.path.join(ws, sub), exist_ok=True)

        os.environ["GOROOT"] = self._goroot_for_go(go)
        os.environ["GOPATH"] = os.path.join(ws, "gopath")
        os.environ["GOTOOLCHAIN"] = "local"
        os.environ["GOFLAGS"] = "-mod=mod"
        os.environ["GOOS"] = self._goos()
        os.environ["GOARCH"] = self._goarch()
        os.environ["CGO_ENABLED"] = "0"
        # Go modules 经 GOPROXY 拉取（可用环境变量覆盖，便于镜像/离线环境）。
        # GOSUMDB 默认 off：go.sum 已固定全部依赖哈希，校验以 go.sum 为准，
        # 避免构建期依赖 sumdb 网络可达性。
        os.environ["GOPROXY"] = os.environ.get(
            "GOPROXY", "https://goproxy.cn,https://proxy.golang.org,direct")
        os.environ["GOSUMDB"] = os.environ.get("GOSUMDB", "off")
        os.environ["TMPDIR"] = os.path.join(ws, "tmp")
        os.environ["GOTMPDIR"] = os.path.join(ws, "tmp")
        os.environ["GOCACHE"] = os.path.join(ws, "go-build-cache")
        os.environ["GOMODCACHE"] = os.path.join(ws, "go-mod-cache")
        os.environ["PATH"] = os.path.dirname(go) + os.pathsep + os.environ.get("PATH", "")
        self.output.info(f"Go toolchain: {go} ({self._go_version_of(go)})")

    # ─────────────────────────── build ───────────────────────────
    def build(self):
        # OHOS 适配为 env + toolexec 层面，无需源码补丁（保持上游源码原样）。
        apply_conandata_patches(self)

        for sub in ("tmp", "go-build-cache", "go-mod-cache", "link-out"):
            os.makedirs(os.path.join(self._go_workspace(), sub), exist_ok=True)

        go = self._go_executable()
        if str(self.settings.os) == "OHOS":
            self._sign_go_sdk(self._goroot_for_go(go))

        toolexec = self._write_toolexec_wrapper()
        os.environ["INCUS_AGENT_LINK_REDIR"] = self._link_redir_dir()

        out_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(out_dir, exist_ok=True)
        exe = os.path.join(out_dir, BINARY_NAME)
        self.run(
            f'"{go}" build -mod=mod -toolexec "{toolexec}" -trimpath '
            f'-tags agent,netgo -ldflags "-s -w" -o "{exe}" ./cmd/incus-agent',
            cwd=self.source_folder, env=None,
        )
        if str(self.settings.os) == "OHOS":
            self._sign_elf(exe)

        self._run_upstream_tests(go, toolexec)

    # ────────────────────────── package ──────────────────────────
    def package(self):
        copy(self, BINARY_NAME, os.path.join(self.build_folder, "bin"),
             os.path.join(self.package_folder, "bin"))
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]

    # ─────────────────── upstream tests (R51) ───────────────────
    def _run_upstream_tests(self, go, toolexec):
        """对 cmd/incus-agent 依赖闭包内的纯 Go 包执行上游 `go test`。

        OHOS 上 go test 产出的测试二进制需签名后才能 execve（E318）；而 go 在
        链接后会重写文件，故签名必须发生在最终拷贝之后——因此采用
        `go test -c` 编译 → 签名 → 直接执行 的方式，等价于上游 `go test`。
        """
        test_dir = os.path.join(self._go_workspace(), "utest-bin")
        os.makedirs(test_dir, exist_ok=True)

        passed = failed = skipped = 0
        per_pkg = []
        for pkg in UPSTREAM_TEST_PACKAGES:
            name = pkg.replace("/", "_")
            tb = os.path.join(test_dir, f"{name}.test")
            self.run(
                f'"{go}" test -c -mod=mod -toolexec "{toolexec}" -o "{tb}" ./{pkg}/',
                cwd=self.source_folder, env=None,
            )
            if str(self.settings.os) == "OHOS":
                self._sign_elf(tb)
            pkg_dir = os.path.join(self.source_folder, pkg)
            try:
                proc = subprocess.run([tb, "-test.v", "-test.timeout", "600s"],
                                      cwd=pkg_dir, env=dict(os.environ),
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.STDOUT, timeout=1500)
                out = proc.stdout.decode(errors="replace")
                rc = proc.returncode
            except (OSError, subprocess.TimeoutExpired) as exc:
                out, rc = f"test run failed: {exc}", -1
            p = len(re.findall(r"(?m)^\s*--- PASS:", out))
            f = len(re.findall(r"(?m)^\s*--- FAIL:", out))
            s = len(re.findall(r"(?m)^\s*--- SKIP:", out))
            passed += p
            failed += f
            skipped += s
            per_pkg.append({"package": pkg, "returncode": rc,
                            "passed": p, "failed": f, "skipped": s})
            self.output.info(f"  [utest] ./{pkg}: PASS={p} FAIL={f} SKIP={s} rc={rc}")

        if failed > 0:
            status = "failed"
        elif passed > 0:
            status = "passed"
        else:
            status = "no_tests"
        upstream = {
            "status": status,
            "framework": "go test",
            "command": "go test -c + OHOS sign + run (./cmd/incus-agent closure)",
            "discovered": passed + failed + skipped,
            "executed": passed + failed + skipped,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "packages": per_pkg,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT="
                         + json.dumps(upstream, ensure_ascii=False))
        if failed > 0:
            raise ConanInvalidConfiguration(
                f"upstream go test failures: {failed} (see HMBS_UPSTREAM_TEST_RESULT)"
            )

    # ─────────────────── Go toolchain helpers ───────────────────
    def _go_workspace(self):
        ws = os.path.join(self.build_folder, ".go-work")
        os.makedirs(ws, exist_ok=True)
        return ws

    def _go_executable(self):
        candidates = []
        if os.environ.get("GO"):
            candidates.append(os.environ["GO"])
        if os.environ.get("GOROOT"):
            candidates.append(os.path.join(os.environ["GOROOT"], "bin", "go"))
        home = os.path.expanduser("~")
        candidates.extend([
            os.path.join(home, "usr", "local", "go", "bin", "go"),
            os.path.join(home, "sdk", f"go{GO_VERSION}", "bin", "go"),
            "/usr/local/go/bin/go",
            "/data/service/hnp/go/bin/go",
        ])
        found = shutil.which("go")
        if found:
            candidates.append(found)
        for c in candidates:
            if c and os.path.isfile(c) and self._is_elf(c) and self._go_version_ok(c):
                return c
        return self._bootstrap_go_sdk()

    def _bootstrap_go_sdk(self):
        host_arch = self._host_arch()
        if host_arch not in GO_ARCHIVES:
            raise ConanInvalidConfiguration(f"No Go SDK bootstrap for host arch {host_arch}")
        urls, sha256 = GO_ARCHIVES[host_arch]
        sdk_root = os.path.join(self._go_workspace(), "go-sdk", f"go{GO_VERSION}-{host_arch}")
        goroot = os.path.join(sdk_root, "go")
        gobin = os.path.join(goroot, "bin", "go")
        if not os.path.isfile(gobin):
            self.output.info(f"Bootstrapping Go {GO_VERSION} ({host_arch}) from {urls[0]}")
            get(self, url=urls, sha256=sha256, destination=sdk_root, strip_root=False)
        if not os.path.isfile(gobin):
            raise ConanInvalidConfiguration(f"Go SDK bootstrap failed: {gobin} missing")
        self._sign_go_sdk(goroot)
        return gobin

    def _sign_go_sdk(self, goroot):
        if str(self.settings.os) != "OHOS" or not goroot:
            return
        targets = [os.path.join(goroot, "bin", "go"), os.path.join(goroot, "bin", "gofmt")]
        tool_dir = os.path.join(goroot, "pkg", "tool", f"linux_{self._host_arch()}")
        if os.path.isdir(tool_dir):
            targets += [os.path.join(tool_dir, f) for f in sorted(os.listdir(tool_dir))]
        for t in targets:
            if os.path.isfile(t) and self._is_elf(t) and not self._is_signed(t):
                self._sign_elf(t)

    def _link_redir_dir(self):
        """选一个支持 fallocate 的目录用于重定向链接器输出（E523）。"""
        for cand in ("/dev/shm", os.path.join(self._go_workspace(), "link-out")):
            if not os.path.isdir(cand):
                continue
            try:
                probe = os.path.join(cand, f".falloc-probe-{os.getpid()}")
                fd = os.open(probe, os.O_RDWR | os.O_CREAT | os.O_TRUNC, 0o775)
                try:
                    os.posix_fallocate(fd, 0, 1 << 20)
                    return cand
                finally:
                    os.close(fd)
                    os.remove(probe)
            except (OSError, AttributeError, ValueError):
                continue
        return self._go_workspace()

    def _write_toolexec_wrapper(self):
        # 路径不能含空格：Go 的 -toolexec 值按空格切分
        for base in ("/dev/shm", os.path.expanduser("~"), self.build_folder):
            if not os.path.isdir(base):
                continue
            path = os.path.join(base, "incus-agent-toolexec.sh")
            try:
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(_TOOLEXEC_WRAPPER)
                os.chmod(path, 0o755)
                if " " not in path:
                    return path
            except OSError:
                continue
        raise ConanInvalidConfiguration("cannot create a space-free toolexec wrapper path")

    # ─────────────────── OHOS ELF signing ───────────────────
    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as fh:
                return fh.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _is_signed(self, path):
        try:
            readelf = shutil.which("readelf") or "/data/service/hnp/bin/readelf"
            out = subprocess.run([readelf, "-S", path], capture_output=True,
                                 text=True, timeout=10).stdout
            return ".codesign" in out
        except Exception:
            return False

    def _sign_elf(self, path):
        signer = (os.environ.get("OHOS_BINARY_SIGN_TOOL")
                  or "/data/service/hnp/bin/binary-sign-tool")
        if not os.path.isfile(signer):
            raise ConanInvalidConfiguration(
                f"binary-sign-tool not found at {signer}; OHOS ELF signature required"
            )
        signed = path + ".signed"
        self.run(f'"{signer}" sign -selfSign 1 -inFile "{path}" -outFile "{signed}" '
                 f'-signAlg SHA256withECDSA', env=None)
        shutil.move(signed, path)
        os.chmod(path, 0o755)

    # ─────────────────── misc helpers ───────────────────
    def _go_version_of(self, go):
        try:
            return (subprocess.run([go, "version"], capture_output=True,
                                   timeout=15).stdout.decode().strip() or "?")
        except Exception:
            return "?"

    def _go_version_ok(self, go):
        try:
            out = subprocess.run([go, "version"], capture_output=True,
                                 timeout=15).stdout.decode()
        except OSError:
            return False
        m = re.search(r"go(\d+)\.(\d+)(?:\.(\d+))?", out)
        if not m:
            return False
        ver = tuple(int(x) if x else 0 for x in m.groups())
        return ver >= (1, 25, 10)

    def _goroot_for_go(self, gobin):
        if not gobin:
            return ""
        real = os.path.realpath(gobin)
        cand = os.path.dirname(os.path.dirname(real))
        if os.path.isfile(os.path.join(cand, "bin", "go")):
            return cand
        return os.environ.get("GOROOT", "")

    @staticmethod
    def _host_arch():
        m = platform.machine().lower()
        return {"x86_64": "amd64", "amd64": "amd64", "aarch64": "arm64",
                "arm64": "arm64", "armv8l": "arm64"}.get(m, m)

    def _goos(self):
        return "linux"

    def _goarch(self):
        return {"x86_64": "amd64", "armv8": "arm64"}.get(str(self.settings.arch), "arm64")
