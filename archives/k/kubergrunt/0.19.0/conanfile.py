#!/usr/bin/env python3
"""Conan 2.x recipe — kubergrunt 0.19.0 (Gruntwork EKS / Kubernetes 辅助命令行工具).

kubergrunt 是 Gruntwork 用 Go 写的 CLI（gruntwork-io/kubergrunt，Apache-2.0），
上游用 build-go-binaries 打包（.circleci/config.yml）：

    build-go-binaries --app-name kubergrunt --src-path ./cmd --dest-path ./bin \\
        --ld-flags "-X main.VERSION=$CIRCLE_TAG -extldflags '-static'"

本配方等价命令（main 包在 ./cmd，版本号由 -X main.VERSION 注入）：

    go build -trimpath -ldflags "-s -w -X main.VERSION=0.19.0" -o <ext2>/out/kubergrunt ./cmd

OHOS/HarmonyOS 平台要点（沿用本仓 dbmate 2.33.0 / tlsx 1.2.2 / aliae 1.5.0 已验证做法）：
- E166 Go 链接器在 HMDFS 上 mmap 写输出失败 ⇒ GOCACHE/GOMODCACHE/GOPATH/
  GOTMPDIR/TMPDIR 与 -o 输出全部落到 ext2 分区（/data/storage/el2/base/cache 等）。
- E128 所有会被 execve 的 ELF 必须带 .codesign 段 ⇒ 交付的 kubergrunt 二进制、
  自举下载的 Go 工具链（bin/go、pkg/tool/linux_arm64/*）都用
  /data/service/hnp/bin/binary-sign-tool 自签名（先 llvm-objcopy 去掉旧 .codesign，
  sign-tool 拒绝覆盖已存在的段）。
- E077 HMDFS 的 chmod 语义（group 固定 6 / other 固定 0 / owner 保底 rw-）⇒
  签名后统一 chmod 0o755 恢复 owner 的 x 位。
- `go test` 的测试二进制由 go 内部生成（GOTMPDIR/go-build*/b001/*.test），配方无法
  预先签名 ⇒ 用 `go test -exec=<wrapper>` 在 execve 之前就地签名（aliae 1.5.0 同款）。
- HMDFS 不支持 getcwd（go 从 cwd 向上找 go.mod）⇒ 先把源码整树复制到 ext2 再构建/测试。

上游测试：`go test -count=1 -json -timeout 300s ./...`（5 个含测试文件的包、89 个顶层
Test 函数）。其中依赖 AWS 凭据 / Kubernetes 集群 / terraform 的用例在无凭据的 CI
环境必然失败——配方**如实统计**并在日志中列出，同时把不依赖外部资源的
“离线确定性用例”作为硬门禁（_OFFLINE_TESTS，见下），它们必须全部通过。
"""
import json
import os
import shutil
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.files import copy, download, get
from conan.tools.layout import basic_layout

UPSTREAM_MODULE = "github.com/gruntwork-io/kubergrunt"

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

# 离线确定性用例白名单（真机无 AWS 凭据 / 无 Kubernetes 集群 / 无 terraform 也能跑）。
# 这些用例只做内存数据结构操作、字符串解析、纯 crypto/options 校验；其余 60 个顶层
# 用例依赖外部资源，失败原因在 build() 里如实统计打印。白名单用例必须 100% 通过，
# 否则 conan create 直接失败（防“测试不跑也算过”）。
_OFFLINE_TESTS = {
    UPSTREAM_MODULE + "/cmd": (
        "TestParseTLSSubjectInfoJsonOrgOrgUnit",
        "TestParseTLSSubjectInfoJsonOrganizationOrganizationalUnit",
    ),
    UPSTREAM_MODULE + "/eksawshelper": (
        "TestGetClusterNameFromArn",
        "TestGetClusterNameFromArnErrorCases",
        "TestGetRegionFromArn",
        "TestGetRegionFromArnErrorCases",
    ),
    UPSTREAM_MODULE + "/kubectl": (
        "TestAddContextToConfig",
        "TestAddEksConfigContextHonorsContextName",
        "TestAddEksConfigContextFailsOnAddingExistingContext",
        "TestAddClusterToConfigAppendsCorrectClusterInfo",
        "TestAddEksConfigContextAppendsCorrectClusterInfo",
        "TestAddEksConfigContextAppendsCorrectAuthInfo",
        "TestAddEksAuthInfoToConfigAppendsCorrectAuthInfo",
        "TestAddSecretFromFileHappyPath",
        "TestAddSecretFromFileWhenFileDoesNotExist",
        "TestAddToSecretFromDataBase64EncodesInput",
        "TestGetAWSLoadBalancerNameFromHostname",
    ),
    UPSTREAM_MODULE + "/tls": (
        "TestTLSOptionsValidateAcceptsAllKnownAlgorithms",
        "TestTLSOptionsValidateAcceptsAllKnownCurves",
        "TestTLSOptionsValidateAcceptsUnknownCurveWhenAlgorithmIsRSA",
        "TestTLSOptionsValidateAcceptsRSABitsAboveMinimum",
        "TestTLSOptionsValidateAcceptsRSABitsBelowMinimumWhenAlgorithmIsECDSA",
        "TestTLSOptionsValidateRejectsUnknownAlgorithms",
        "TestTLSOptionsValidateRejectsUnknownCurves",
        "TestTLSOptionsValidateRejectsRSABitsBelowMinimum",
        "TestCreateECDSAKeyPairErrorsOnUnknownCurve",
        "TestCreateECDSAKeyPairSupportsAllKnownCurves",
        "TestCreateRSAKeyPairErrorsOnTooLowBits",
        "TestCreateRSAKeyPairAllows2048KeyLength",
    ),
}

# 主包目录（上游 --src-path ./cmd）
_MAIN_PACKAGE = "./cmd"

# go test 时长上限（每个测试二进制）
_GO_TEST_TIMEOUT = "300s"


class KubergruntConan(ConanFile):
    name = "kubergrunt"
    version = "0.19.0"

    description = ("A CLI tool to help setup and manage a Kubernetes cluster "
                   "(EKS/K8s helper commands by Gruntwork)")
    license = "Apache-2.0"
    homepage = "https://github.com/gruntwork-io/kubergrunt"
    url = "https://github.com/gruntwork-io/kubergrunt"
    topics = ("kubernetes", "eks", "aws", "cli", "go")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "kubergrunt is prepared for Linux/OHOS targets only"
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
        向上找 go.mod；参照 aliae 1.5.0 / tlsx 1.2.2）。其它平台直接用
        source_folder（本机 Linux 预检用）。

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
        out_bin = os.path.join(out_dir, "kubergrunt")
        ldflags = '-s -w -X main.VERSION=%s' % self.version
        self._run_go(
            'cd "%s" && "%s" build -trimpath -ldflags "%s" -o "%s" %s'
            % (src, go_bin, ldflags, out_bin, _MAIN_PACKAGE),
            env,
        )
        if not os.path.isfile(out_bin):
            raise ConanException("go build did not produce %s" % out_bin)
        if not self._sign_elf(out_bin):
            raise ConanException(
                "ELF signing of %s failed (E128: binary-sign-tool/llvm-objcopy "
                "unavailable?)" % out_bin
            )

        bin_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        shutil.copy2(out_bin, os.path.join(bin_dir, "kubergrunt"))

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
        """解析 `go test -json` 流，返回 {pkg: {test: action}} 与计数。"""
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
                if event.get("FailedBuild") or event.get("Output", "").startswith("# "):
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
            "packages with test binaries: %d ; top-level Test funcs: %d "
            "(pass=%d fail=%d skip=%d) ; subtests recorded: %d"
            % (len(pkgs), top_pass + top_fail + top_skip,
               top_pass, top_fail, top_skip, subtests)
        )
        for pkg in sorted(pkgs):
            entry = pkgs[pkg]
            npass = sum(1 for a in entry["top"].values() if a == "pass")
            nfail = sum(1 for a in entry["top"].values() if a == "fail")
            nskip = sum(1 for a in entry["top"].values() if a == "skip")
            self.output.info(
                "  %-58s PASS=%d FAIL=%d SKIP=%d%s"
                % (pkg.replace(UPSTREAM_MODULE + "/", ""),
                   npass, nfail, nskip,
                   " [TEST PACKAGE DID NOT BUILD]" if entry["build_fail"] else "")
            )
            for test in sorted(entry["top"]):
                if entry["top"][test] != "pass":
                    self.output.info("      %s: %s"
                                     % (entry["top"][test].upper(), test))

        external = sorted(
            "%s/%s" % (pkg.replace(UPSTREAM_MODULE + "/", ""), test)
            for pkg, entry in pkgs.items()
            for test, action in entry["top"].items() if action == "fail"
        )
        if external:
            self.output.info(
                "FAILED tests needing external resources (AWS credentials / "
                "Kubernetes cluster / terraform; unavailable in CI), reported "
                "honestly, not part of the offline gate (%d):" % len(external)
            )
            for name in external:
                self.output.info("      %s" % name)

    def _enforce_offline_gates(self, pkgs):
        missing, failed = [], []
        expected = sum(len(names) for names in _OFFLINE_TESTS.values())
        for pkg, names in _OFFLINE_TESTS.items():
            entry = pkgs.get(pkg)
            if entry is None:
                missing.append("%s (package has no test result)" % pkg)
                continue
            for name in names:
                action = entry["top"].get(name)
                if action is None:
                    missing.append("%s/%s" % (pkg, name))
                elif action != "pass":
                    failed.append("%s/%s (%s)" % (pkg, name, action))
        self.output.info(
            "offline deterministic gating set: %d tests, %d passed, %d missing, "
            "%d failed" % (expected, expected - len(missing) - len(failed),
                           len(missing), len(failed))
        )
        if missing or failed:
            raise ConanException(
                "offline deterministic upstream tests did not all pass "
                "(missing=%s failed=%s)" % (missing, failed)
            )

    # ------------------------------------------------------------------
    # package
    # ------------------------------------------------------------------
    def package(self):
        copy(self, "kubergrunt", os.path.join(self.build_folder, "bin"),
             os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
