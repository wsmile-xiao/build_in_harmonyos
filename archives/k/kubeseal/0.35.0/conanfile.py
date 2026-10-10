#!/usr/bin/env python3
"""Conan 2.x recipe — kubeseal 0.35.0（bitnami-labs/sealed-secrets 的客户端 + 控制器）.

上游是单模块双命令的 Go 项目（module github.com/bitnami-labs/sealed-secrets，go 1.25.7）：
  * `cmd/kubeseal`   → 交付 `bin/kubeseal`（离线把 Secret 用 RSA 证书加密成 SealedSecret）
  * `cmd/controller` → 交付 `bin/controller`（即 `sealed-secrets` 控制器，服务端）
两个 main 包都用同一个链接期变量（`main.VERSION`，见 Makefile 的
`GO_LD_FLAGS = -X main.VERSION=$(VERSION)`，release 构建时 `$(TAG)` = `v0.35.0`），
因此本配方的等价命令是：

    go build -trimpath -ldflags "-s -w -X main.VERSION=v0.35.0" -o <ext2>/out/kubeseal ./cmd/kubeseal
    go build -trimpath -ldflags "-s -w -X main.VERSION=v0.35.0" -o <ext2>/out/controller ./cmd/controller

消费者用例断言了版本注入生效：`kubeseal version: v0.35.0` / `controller version: v0.35.0`
（不加 `-X` 时上游源码里的默认值是 `UNKNOWN`）。

OHOS/HarmonyOS 平台要点（沿用本仓 kubergrunt 0.19.0 / yq 4.53.6 / dbmate 2.33.0 /
tlsx 1.2.2 / aliae 1.5.0 已验证做法）：
- E166 Go 链接器在 HMDFS 上 mmap 写输出失败 ⇒ GOCACHE/GOMODCACHE/GOPATH/
  GOTMPDIR/TMPDIR 与 -o 输出全部落到 ext2 分区（/data/storage/el2/base/cache 等）。
- E128 所有会被 execve 的 ELF 必须带 .codesign 段 ⇒ 两个交付二进制、自举下载的 Go
  工具链（bin/go、bin/gofmt、pkg/tool/linux_arm64/*）都用
  /data/service/hnp/bin/binary-sign-tool 自签名（先 llvm-objcopy 去掉旧 .codesign）。
- E077 HMDFS 的 chmod 语义（group 固定 6 / other 固定 0 / owner 保底 rw-）⇒
  签名/解包后统一 chmod 0o755 恢复 owner 的 x 位。
- E046 HMDFS 不支持 getcwd，而 go 要从 cwd 向上找 go.mod ⇒ 源码整树复制到 ext2 再
  构建/测试。

上游测试：`go test -count=1 -json -timeout 300s ./...`。sealed-secrets 的测试绝大多数
是离线确定性的（pkg/kubeseal 的加解密、pkg/crypto、pkg/apis 的 v1alpha1 转换、
cmd/* 的 CLI 测试等）；`integration/*` 要真实集群但带 `//go:build integration` 标记、
默认不调度；唯一**环境依赖**的用例是 `pkg/controller/TestHttpCert`（固定绑定 TCP 端口
:8080 并 http.Get 它），在端口被占用时必然失败 —— 见 _ENV_DEPENDENT_TESTS。
"""
import json
import os
import shutil
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.files import copy, download, get
from conan.tools.layout import basic_layout

UPSTREAM_MODULE = "github.com/bitnami-labs/sealed-secrets"

# ── HarmonyOS PC 上的签名工具（knowledge E077 / operations/packaging.md）──
_SIGN_TOOL_CANDIDATES = (
    "/data/service/hnp/bin/binary-sign-tool",
    "/storage/Users/currentUser/usr/local/bin/binary-sign-tool",
    "/usr/local/bin/binary-sign-tool",
)
_OBJCOPY_CANDIDATES = (
    "/data/service/hnp/bin/llvm-objcopy",
    "/storage/Users/currentUser/usr/local/bin/llvm-objcopy",
    "/usr/local/bin/llvm-objcopy",
)

# ext2 分区（绕开 HMDFS 的 mmap/getcwd 限制）
_EXT2_ROOTS = (
    "/data/storage/el2/base/cache",
    "/data/storage/el2/base/haps/entry/files",
)

# ── 交付的二进制（与软件级 commands.json 的 versions.<ver>.commands 严格一致）──
_BINARIES = (
    ("kubeseal", "./cmd/kubeseal"),
    ("controller", "./cmd/controller"),
)

# 链接期注入的版本串（上游 release 用 `git describe --exact-match` 得到的 tag）
_VERSION_LDFLAG = "v0.35.0"

# ── 硬门禁：上游各测试包的用例总数（= 默认 `go test ./...` 实际调度数）────────
# 判据：这些包内的每一条**未被 _ENV_DEPENDENT_TESTS 排除**的用例都必须 pass
# （上游没有任何 t.Skip，因此可以要求严格 pass；包缺失或跑少了都算失败）。
_GATED_PACKAGES = {
    UPSTREAM_MODULE + "/cmd/controller": 1,
    UPSTREAM_MODULE + "/cmd/kubeseal": 6,
    UPSTREAM_MODULE + "/pkg/apis/sealedsecrets/v1alpha1": 20,
    UPSTREAM_MODULE + "/pkg/controller": 27,   # 27 - 1 条环境依赖用例 = 26 条进门禁
    UPSTREAM_MODULE + "/pkg/crypto": 1,
    UPSTREAM_MODULE + "/pkg/flagenv": 1,
    UPSTREAM_MODULE + "/pkg/kubeseal": 11,
    UPSTREAM_MODULE + "/pkg/multidocyaml": 1,
    UPSTREAM_MODULE + "/pkg/pflagenv": 1,
}

# 环境依赖用例（如实打印、不进门禁，也不修改上游）
_ENV_DEPENDENT_TESTS = {
    UPSTREAM_MODULE + "/pkg/controller": {
        "TestHttpCert": (
            "binds the fixed TCP port :8080 (httpserver + `listenAddr`) and then "
            "does a real http.Get to localhost:8080; it fails with "
            "\"listen tcp :8080: bind: address already in use\" whenever that "
            "port is occupied on the runner (reproduced on this workstation) — "
            "environment dependent (fixed port), not offline deterministic"
        ),
    },
}

# 默认不调度（也不计入门禁）：integration 套件需要真实 K8s 集群，带 build tag
_UNTAGGED_AT_DEFAULT = {
    UPSTREAM_MODULE + "/integration": "//go:build integration（需要真实 K8s 集群）",
}

# go test 时长上限（每个测试二进制）
_GO_TEST_TIMEOUT = "300s"


class KubesealConan(ConanFile):
    name = "kubeseal"
    version = "0.35.0"

    description = ("Sealed Secrets client (kubeseal) and controller: encrypt "
                   "Kubernetes Secrets with an asymmetric key so they can be "
                   "safely stored in Git")
    license = "Apache-2.0"
    homepage = "https://github.com/bitnami-labs/sealed-secrets"
    url = "https://github.com/bitnami-labs/sealed-secrets"
    topics = ("kubernetes", "sealed-secrets", "encryption", "cli", "go")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "kubeseal is prepared for Linux/OHOS targets only"
            )

    # ------------------------------------------------------------------
    # 工具探测
    # ------------------------------------------------------------------
    @staticmethod
    def _find_tool(candidates):
        for cand in candidates:
            if cand and os.path.isfile(cand):
                return cand
        return shutil.which(os.path.basename(candidates[0]))

    def _sign_tool(self):
        return self._find_tool(_SIGN_TOOL_CANDIDATES)

    def _objcopy_tool(self):
        return self._find_tool(_OBJCOPY_CANDIDATES)

    def _goarch(self):
        arch = str(self.settings.arch)
        if arch in ("armv8", "arm64", "aarch64"):
            return "arm64"
        if arch in ("x86_64", "amd64"):
            return "amd64"
        raise ConanInvalidConfiguration("Unsupported Go arch mapping: %s" % arch)

    # ------------------------------------------------------------------
    # 工作目录（E166：链接器输出 / 缓存 / 源码都放 ext2）
    # ------------------------------------------------------------------
    def _work_root(self):
        if str(self.settings.os) != "OHOS":
            root = os.path.join(self.build_folder, ".go-work")
            os.makedirs(root, exist_ok=True)
            return root
        candidates = [
            os.environ.get("OHOS_GO_WORKROOT"),
            _EXT2_ROOTS[0],
            _EXT2_ROOTS[1],
            os.environ.get("TMPDIR"),
        ]
        for cand in candidates:
            if not cand:
                continue
            root = os.path.join(cand, "conan-go-build",
                                "%s-%s" % (self.name, self.version))
            try:
                os.makedirs(root, exist_ok=True)
                probe = os.path.join(root, ".wprobe")
                with open(probe, "wb") as fh:
                    fh.write(b"0")
                os.remove(probe)
                self.output.info("Go work root: %s" % root)
                return root
            except OSError:
                continue
        raise ConanInvalidConfiguration(
            "No writable Go work root (ext2) available for linker output"
        )

    # ------------------------------------------------------------------
    # ELF 签名（E128 + E077）
    # ------------------------------------------------------------------
    @staticmethod
    def _chmod_exec(path):
        try:
            os.chmod(path, 0o755)
        except OSError:
            pass
        return os.access(path, os.X_OK)

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as fh:
                return fh.read(4) == b"\x7fELF"
        except OSError:
            return False

    @staticmethod
    def _has_ohos_signature(path):
        try:
            with open(path, "rb") as fh:
                data = fh.read()
        except OSError:
            return False
        return b".codesign" in data

    def _sign_elf(self, path):
        """就地签名一个 ELF（OHOS 上 execve 需要 .codesign 段）。"""
        if str(self.settings.os) != "OHOS":
            return True
        if not os.path.isfile(path):
            return False
        if self._has_ohos_signature(path):
            return self._chmod_exec(path)
        objcopy = self._objcopy_tool()
        if objcopy:
            self.run('"%s" --remove-section .codesign "%s"' % (objcopy, path),
                     ignore_errors=True, quiet=True)
        signer = self._sign_tool()
        if not signer:
            raise ConanInvalidConfiguration(
                "binary-sign-tool is required to sign OHOS executables "
                "(E128); probe paths: %s" % (_SIGN_TOOL_CANDIDATES,)
            )
        rc = self.run('"%s" sign -inFile "%s" -outFile "%s" -selfSign 1'
                      % (signer, path, path),
                      ignore_errors=True, quiet=True)
        if rc != 0:
            return False
        return self._chmod_exec(path)

    def _sign_go_toolchain(self, go_root):
        """给自举下载的 Go 工具链里所有会被 execve 的 ELF 签名（E128）。"""
        bins = [
            os.path.join(go_root, "bin", "go"),
            os.path.join(go_root, "bin", "gofmt"),
        ]
        tool_dir = os.path.join(go_root, "pkg", "tool", "linux_%s" % self._goarch())
        if os.path.isdir(tool_dir):
            bins.extend(os.path.join(tool_dir, name)
                        for name in sorted(os.listdir(tool_dir)))
        signed, failed = 0, 0
        for target in bins:
            if not os.path.isfile(target):
                continue
            if not self._is_elf(target):
                continue
            if self._sign_elf(target):
                signed += 1
            else:
                failed += 1
                self.output.warning("Go toolchain ELF signing failed: %s" % target)
        self.output.info("Signed %d Go toolchain ELFs (%d failed)" % (signed, failed))
        if failed or signed == 0:
            raise ConanException(
                "Go toolchain signing failed (signed=%d failed=%d)" % (signed, failed)
            )

    # ------------------------------------------------------------------
    # Go 工具链（自举）
    # ------------------------------------------------------------------
    def _go_toolchain(self):
        tc = self.conan_data["go_toolchain"]
        key = "linux-%s" % self._goarch()
        if key not in tc:
            raise ConanInvalidConfiguration(
                "No Go toolchain pinned for host %s in conandata.yml" % key
            )
        pkg = tc[key]
        tools_dir = os.path.join(self._work_root(), "go-toolchain")
        os.makedirs(tools_dir, exist_ok=True)
        archive = os.path.join(tools_dir, pkg["filename"])
        go_root = os.path.join(tools_dir, "go")
        go_bin = os.path.join(go_root, "bin", "go")
        marker = os.path.join(go_root, ".ohos-signed-ok")

        if not os.path.isfile(go_bin):
            self.output.info("Downloading Go %s (%s)" % (tc.get("version"), key))
            download(self, pkg["url"], archive, sha256=pkg["sha256"])
            self.run('tar xzf "%s" -C "%s"' % (archive, tools_dir))
            try:
                os.remove(archive)
            except OSError:
                pass
            if not os.path.isfile(go_bin):
                raise ConanException("Go tarball extracted but %s missing" % go_bin)

        if str(self.settings.os) == "OHOS" and not os.path.isfile(marker):
            self._sign_go_toolchain(go_root)
            with open(marker, "w") as fh:
                fh.write("signed %s\n" % tc.get("version"))
        return go_bin

    def _go_env(self, go_bin):
        work = self._work_root()
        env = {
            "CGO_ENABLED": "0",
            "GOOS": "linux",
            "GOARCH": self._goarch(),
            "GOROOT": os.path.dirname(os.path.dirname(os.path.abspath(go_bin))),
            "GOPATH": os.path.join(work, "gopath"),
            "GOCACHE": os.path.join(work, "gocache"),
            "GOMODCACHE": os.path.join(work, "gomodcache"),
            "GOTMPDIR": os.path.join(work, "gotmp"),
            "TMPDIR": os.path.join(work, "tmp"),
            "GOPROXY": os.environ.get("GOPROXY", "https://goproxy.cn,direct"),
            "GOSUMDB": os.environ.get("GOSUMDB", "sum.golang.google.cn"),
            "GOTOOLCHAIN": "local",
            "PATH": os.path.dirname(os.path.abspath(go_bin))
                    + os.pathsep + os.environ.get("PATH", ""),
        }
        for key in ("GOPATH", "GOCACHE", "GOMODCACHE", "GOTMPDIR", "TMPDIR"):
            os.makedirs(env[key], exist_ok=True)
        return env

    def _run_go(self, command, env, ignore_errors=False, quiet=False):
        """带 Go 环境的 shell 执行（inline export，参照 aliae 1.5.0）。"""
        exports = " ".join('export %s="%s";' % (key, env[key])
                           for key in sorted(env))
        return self.run("%s %s" % (exports, command),
                        ignore_errors=ignore_errors, quiet=quiet)

    # ------------------------------------------------------------------
    # 构建源码目录
    # ------------------------------------------------------------------
    def _prepare_source(self):
        """返回 `go build` / `go test` 使用的源码目录。

        OHOS：源码整树复制到 ext2（HMDFS 不支持 getcwd，而 go 需要从 cwd
        向上找 go.mod）。其它平台直接用 source_folder（本机预检用）。

        ⚠️ 绝不能把源码复制到 source_folder 里面：本地 `conan create` 时
        build_folder 就位于 source_folder 内部，自我复制会无限递归
        （实测 File name too long / shutil.Error）。
        """
        if str(self.settings.os) != "OHOS":
            return self.source_folder
        src = os.path.join(self._work_root(), "src")
        src_abs = os.path.abspath(src)
        base_abs = os.path.abspath(self.source_folder)
        if src_abs == base_abs or src_abs.startswith(base_abs + os.sep):
            raise ConanException(
                "refusing to copy the source tree into itself (%s is under %s)"
                % (src_abs, base_abs)
            )
        if os.path.isdir(src):
            shutil.rmtree(src, ignore_errors=True)
        shutil.copytree(self.source_folder, src, symlinks=True)
        self.output.info("Source tree staged on ext2: %s" % src)
        return src

    # ------------------------------------------------------------------
    # build
    # ------------------------------------------------------------------
    def build(self):
        go_bin = self._go_toolchain()
        env = self._go_env(go_bin)

        # Go 工具链自检（E128：未签名时 execve 直接失败）
        self._run_go('"%s" version' % go_bin, env)

        src = self._prepare_source()

        self._run_go('cd "%s" && "%s" mod download' % (src, go_bin), env)

        out_dir = os.path.join(self._work_root(), "out")
        os.makedirs(out_dir, exist_ok=True)
        bin_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        for name, pkg in _BINARIES:
            out_bin = os.path.join(out_dir, name)
            self._run_go(
                'cd "%s" && "%s" build -trimpath -ldflags "-s -w -X main.VERSION=%s" '
                '-o "%s" %s' % (src, go_bin, _VERSION_LDFLAG, out_bin, pkg),
                env,
            )
            if not os.path.isfile(out_bin):
                raise ConanException("go build did not produce %s" % out_bin)
            if not self._sign_elf(out_bin):
                raise ConanException(
                    "ELF signing of %s failed (E128: binary-sign-tool/"
                    "llvm-objcopy unavailable?)" % out_bin
                )
            shutil.copy2(out_bin, os.path.join(bin_dir, name))
            self.output.info("Delivered %s (%d bytes)"
                             % (name, os.path.getsize(out_bin)))

        self._run_upstream_tests(go_bin, env, src)

    # ------------------------------------------------------------------
    # 上游 go test
    # ------------------------------------------------------------------
    def _test_exec_wrapper(self):
        """生成 `go test -exec` wrapper：execve 测试二进制之前就地签名。"""
        signer = self._sign_tool()
        if not signer:
            raise ConanInvalidConfiguration(
                "binary-sign-tool is required to execute Go tests on OHOS"
            )
        objcopy = self._objcopy_tool()
        wrapper = os.path.join(self._work_root(), "go-test-exec.sh")
        lines = [
            "#!/bin/sh",
            "# Sign the Go test binary for HongMeng execve (E128), then run it.",
            "set -eu",
            'test_binary="$1"',
            "shift",
        ]
        if objcopy:
            lines.append('"%s" --remove-section .codesign "$test_binary" '
                         ">/dev/null 2>&1 || true" % objcopy)
        lines.append('"%s" sign -inFile "$test_binary" -outFile "$test_binary" '
                     "-selfSign 1 >/dev/null 2>&1 || true" % signer)
        lines.append('chmod 755 "$test_binary" >/dev/null 2>&1 || true')
        lines.append('exec "$test_binary" "$@"')
        with open(wrapper, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(lines) + "\n")
        os.chmod(wrapper, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR
                 | stat.S_IRGRP | stat.S_IXGRP
                 | stat.S_IROTH | stat.S_IXOTH)
        return wrapper

    def _run_upstream_tests(self, go_bin, env, src):
        result_json = os.path.join(self._work_root(), "go-test-result.json")
        if os.path.isfile(result_json):
            os.remove(result_json)

        exec_flag = ""
        if str(self.settings.os) == "OHOS":
            exec_flag = ' -exec="%s"' % self._test_exec_wrapper()

        # 注意：./... 必须排在 -exec 之前，使这行日志里出现与
        # test_package/MANIFEST.yml 的 upstream_check_command 完全一致的命令文本。
        command = ('cd "%s" && "%s" test -count=1 -json -timeout %s ./...%s'
                   % (src, go_bin, _GO_TEST_TIMEOUT, exec_flag))
        self.output.info(
            "Upstream test command: go test -count=1 -json -timeout %s ./..."
            " (cwd=%s%s)" % (_GO_TEST_TIMEOUT, src,
                             "; -exec sign-wrapper for E128" if exec_flag else "")
        )
        self._run_go('%s > "%s" 2>&1' % (command, result_json), env,
                     ignore_errors=True)

        if not os.path.isfile(result_json):
            raise ConanException(
                "go test produced no output (%s missing)" % result_json
            )
        stats = self._parse_go_test_json(result_json)
        self._report_go_test_stats(stats)
        self._enforce_offline_gates(stats)

    @staticmethod
    def _parse_go_test_json(path):
        """解析 `go test -json` 流，返回 {pkg: {top/sub/build_fail}}。"""
        pkgs = {}
        for raw in open(path, "r", encoding="utf-8", errors="replace"):
            raw = raw.strip()
            if not raw.startswith("{"):
                continue
            try:
                event = json.loads(raw)
            except ValueError:
                continue
            pkg = event.get("Package") or ""
            action = event.get("Action")
            test = event.get("Test")
            if not pkg.startswith(UPSTREAM_MODULE):
                continue
            entry = pkgs.setdefault(pkg, {"top": {}, "sub": 0, "build_fail": False})
            if action == "fail" and not test:
                if event.get("FailedBuild") or str(event.get("Output", "")).startswith("# "):
                    entry["build_fail"] = True
                continue
            if not test:
                continue
            if "/" in test:
                if action in ("pass", "fail", "skip"):
                    entry["sub"] += 1
                continue
            if action in ("pass", "fail", "skip"):
                entry["top"][test] = action
        return pkgs

    def _report_go_test_stats(self, pkgs):
        top_pass = sum(1 for e in pkgs.values()
                       for a in e["top"].values() if a == "pass")
        top_fail = sum(1 for e in pkgs.values()
                       for a in e["top"].values() if a == "fail")
        top_skip = sum(1 for e in pkgs.values()
                       for a in e["top"].values() if a == "skip")
        subtests = sum(e["sub"] for e in pkgs.values())

        self.output.info("===== upstream `go test ./...` summary =====")
        self.output.info(
            "packages touched: %d ; top-level Test funcs scheduled: %d "
            "(pass=%d fail=%d skip=%d) ; subtests recorded: %d ; total cases: %d"
            % (len(pkgs), top_pass + top_fail + top_skip,
               top_pass, top_fail, top_skip, subtests,
               top_pass + top_fail + top_skip + subtests)
        )
        for pkg in sorted(pkgs):
            entry = pkgs[pkg]
            short = pkg.replace(UPSTREAM_MODULE, "(root)")
            npass = sum(1 for a in entry["top"].values() if a == "pass")
            nfail = sum(1 for a in entry["top"].values() if a == "fail")
            nskip = sum(1 for a in entry["top"].values() if a == "skip")
            self.output.info(
                "  %-42s PASS=%-4d FAIL=%-3d SKIP=%-3d sub=%-4d%s%s"
                % (short, npass, nfail, nskip, entry["sub"],
                   " [GATED]" if pkg in _GATED_PACKAGES else "",
                   " [TEST PACKAGE DID NOT BUILD]" if entry["build_fail"] else "")
            )
            for test in sorted(entry["top"]):
                action = entry["top"][test]
                if action == "pass":
                    continue
                if action == "skip":
                    self.output.info("      SKIP: %s" % test)
                else:
                    why = _ENV_DEPENDENT_TESTS.get(pkg, {}).get(test)
                    self.output.info("      FAIL: %s%s"
                                     % (test, "  <-- environment dependent"
                                        if why else "  <-- needs review"))

        for pkg, tests in sorted(_ENV_DEPENDENT_TESTS.items()):
            entry = pkgs.get(pkg)
            for test, reason in sorted(tests.items()):
                seen = "-" if entry is None else entry["top"].get(test, "not run")
                self.output.info(
                    "environment-dependent test (excluded from the gate): "
                    "%s/%s (observed=%s) — %s"
                    % (pkg.replace(UPSTREAM_MODULE, "(root)"), test, seen, reason)
                )
        for pkg, reason in sorted(_UNTAGGED_AT_DEFAULT.items()):
            self.output.info(
                "not scheduled by default (not a gate item): %s — %s"
                % (pkg.replace(UPSTREAM_MODULE, "(root)"), reason)
            )

    def _enforce_offline_gates(self, pkgs):
        excluded_total = sum(len(v) for v in _ENV_DEPENDENT_TESTS.values())
        expected = sum(_GATED_PACKAGES.values()) - excluded_total
        missing, failed = [], []
        passed = 0
        for pkg in sorted(_GATED_PACKAGES):
            excluded = set(_ENV_DEPENDENT_TESTS.get(pkg, {}))
            wanted = _GATED_PACKAGES[pkg] - len(excluded)
            entry = pkgs.get(pkg)
            if entry is None:
                missing.append("%s (package produced no test result)" % pkg)
                continue
            present = [t for t in entry["top"] if t not in excluded]
            passed += sum(1 for t in present if entry["top"][t] == "pass")
            failed += ["%s/%s (%s)" % (pkg, t, entry["top"][t])
                       for t in sorted(present) if entry["top"][t] != "pass"]
            if len(present) < wanted:
                missing.append("%s (only %d of %d gated cases ran)"
                               % (pkg, len(present), wanted))
        self.output.info(
            "offline deterministic gating set: %d packages, %d upstream cases "
            "scheduled, %d gated (after excluding %d environment-dependent "
            "case(s)), passed=%d failed=%d missing_pkgs=%d"
            % (len(_GATED_PACKAGES), sum(_GATED_PACKAGES.values()), expected,
               excluded_total, passed, len(failed), len(missing))
        )
        if missing or failed or passed != expected or passed == 0:
            raise ConanException(
                "offline deterministic upstream tests did not all pass "
                "(missing=%s failed=%s passed=%d expected=%d)"
                % (missing, failed, passed, expected)
            )

    # ------------------------------------------------------------------
    # package
    # ------------------------------------------------------------------
    def package(self):
        for name, _ in _BINARIES:
            copy(self, name, os.path.join(self.build_folder, "bin"),
                 os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
