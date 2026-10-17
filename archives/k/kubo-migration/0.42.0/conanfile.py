#!/usr/bin/env python3
"""Conan recipe for kubo-migration 0.42.0 (fs-repo-15-to-16).

kubo-migration 是 Alpine kubo 0.42.0 包的 kubo-migration 子包，对应上游
fs-repo-migrations 仓库 tag `fs-repo-15-to-16/v1.0.0`（仓库内 `fs-repo-15-to-16/`
目录，module github.com/ipfs/fs-repo-migrations/fs-repo-15-to-16, go 1.22）。
它是纯 Go CLI：把 IPFS repo 从 v15 迁移到 v16（config 中为 /quic-v1 监听追加
/webrtc-direct，同时保留可回退的 config.15-to-16.bak 备份），无 C/C++ 代码。

构建要点（参考 abbtr/1.0.4、aliae/1.5.0 Go 应用配方）：
- CGO_ENABLED=0 + GOOS=linux + GOARCH=arm64 静态交叉编译；vendor/ 已内置，
  构建全程离线（GOPROXY 仅在无 vendor 时兜底）。
- OHOS/HMDFS 上 Go link 阶段 mmap 输出文件失败（permission denied），
  链接输出放到可写本地文件系统（/data/storage/el2/base/... 等），再复制回包目录。
- OHOS 上 ELF 需 binary-sign-tool 签名才能执行；go 工具链本身也需签名。
"""
import os
import shutil
import stat
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class KuboMigrationConan(ConanFile):
    name = "kubo-migration"
    version = "0.42.0"
    description = (
        "IPFS repo migration tool 15-to-16 (fs-repo-15-to-16) shipped as "
        "the kubo-migration subpackage of Alpine kubo 0.42.0"
    )
    license = "MIT"
    homepage = "https://github.com/ipfs/fs-repo-migrations"
    url = "https://github.com/ipfs/fs-repo-migrations"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    _go_version = "1.26.3"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "kubo-migration is prepared for Linux/OHOS targets only"
            )

    def generate(self):
        env = Environment()
        env.define("CGO_ENABLED", "0")
        env.define("GOOS", "linux")
        env.define("GOARCH", self._goarch())
        env.define("GOTOOLCHAIN", "local")

        workspace = self._go_workspace()
        cache_root = os.path.join(workspace, "cache")
        for child in ("tmp", "build", "mod", "gopath"):
            os.makedirs(os.path.join(cache_root, child), exist_ok=True)

        env.define("TMPDIR", os.path.join(cache_root, "tmp"))
        env.define("GOTMPDIR", os.path.join(cache_root, "tmp"))
        env.define("GOCACHE", os.path.join(cache_root, "build"))
        env.define("GOMODCACHE", os.path.join(cache_root, "mod"))
        env.define("GOPATH", os.path.join(cache_root, "gopath"))
        # vendor/ 已完整，构建不联网；此处仅作离线失败时的兜底镜像
        env.define("GOPROXY", "https://goproxy.cn,direct")

        go = self._go_executable()
        goroot = self._goroot_for_go(go)
        if goroot:
            env.define("GOROOT", goroot)

        env.prepend_path("PATH", os.path.dirname(go))
        env.vars(self).save_script("kubo_migration_go_env")

    def build(self):
        apply_conandata_patches(self)
        go = self._go_executable()

        out_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(out_dir, exist_ok=True)

        if str(self.settings.os) == "OHOS":
            link_out_dir = os.path.join(self._go_workspace(), "link-out")
        else:
            link_out_dir = out_dir
        os.makedirs(link_out_dir, exist_ok=True)

        linked_exe = os.path.join(link_out_dir, self._exe_name())
        final_exe = os.path.join(out_dir, self._exe_name())

        # 与 Alpine APKBUILD 一致：cd fs-repo-15-to-16 && go build
        # （go.mod 声明 go 1.22；vendor/ 已内置，-mod=vendor 保证离线）
        self.run(
            f'"{go}" build -mod=vendor -trimpath '
            f'-o "{linked_exe}" .',
            cwd=os.path.join(self.source_folder, "fs-repo-15-to-16"),
            env=["kubo_migration_go_env"],
        )

        if str(self.settings.os) == "OHOS":
            os.chmod(linked_exe, os.stat(linked_exe).st_mode | 0o111)
            self._sign_ohos_executable(linked_exe)

        if os.path.abspath(linked_exe) != os.path.abspath(final_exe):
            shutil.copy2(linked_exe, final_exe)

        # 上游 Go 单元测试（fs-repo-15-to-16 上游无 *_test.go，go test ./...
        # 仅编译三个包并报告 no test files；真正可运行的上游测试是
        # test-e2e/test.sh，已由 test_package 用安装后的二进制完整执行）
        self.run(
            f'"{go}" test ./...',
            cwd=os.path.join(self.source_folder, "fs-repo-15-to-16"),
            env=["kubo_migration_go_env"],
        )

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

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]

    # ─── Go 工具链 ─────────────────────────────────────────────────────

    def _go_executable(self):
        candidates = []

        if os.environ.get("GO"):
            candidates.append(os.environ["GO"])
        if os.environ.get("GOROOT"):
            candidates.append(
                os.path.join(os.environ["GOROOT"], "bin", "go")
            )

        candidates.extend(
            [
                os.path.expanduser("~/usr/local/go/bin/go"),
                os.path.expanduser(f"~/sdk/go{self._go_version}/bin/go"),
                os.path.expanduser(f"~/tmp/go-toolchain/go/bin/go"),
            ]
        )

        found = shutil.which("go")
        if found:
            candidates.append(found)

        for candidate in candidates:
            if (
                candidate
                and os.path.isfile(candidate)
                and self._go_version_is_supported(candidate)
            ):
                return candidate

        return self._ensure_go_toolchain()

    def _ensure_go_toolchain(self):
        host_key = f"linux-{self._goarch()}"
        tc = self.conan_data["go_toolchain"]
        package = tc[host_key]

        sdk_root = os.path.join(
            self._go_workspace(), "go-sdk", f"go{self._go_version}-{host_key}"
        )
        goroot = os.path.join(sdk_root, "go")
        go = os.path.join(goroot, "bin", "go")

        if not os.path.isfile(go):
            os.makedirs(sdk_root, exist_ok=True)
            archive = os.path.join(sdk_root, package["filename"])
            self.output.info(
                f"Go >= {self._go_version} not found; downloading {package['url']}"
            )
            get(
                self,
                url=package["url"],
                sha256=package["sha256"],
                filename=package["filename"],
                destination=sdk_root,
                strip_root=False,
            )

        self._fix_and_sign_go_sdk(goroot)
        return go

    def _fix_and_sign_go_sdk(self, goroot):
        """解压后修复权限位；OHOS 上给 go/gofmt/pkg/tool 下的 ELF 签名。

        HMDFS 上 os.chmod 可能被拒（SELinux 限制），但 tar 解压已保留正确
        权限位；chmod 失败仅告警不阻塞（参照 aliae/murex 配方）。
        """
        for dirpath, dirnames, filenames in os.walk(goroot):
            for name in dirnames + filenames:
                path = os.path.join(dirpath, name)
                try:
                    mode = os.stat(path).st_mode | stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH
                    os.chmod(path, mode)
                except OSError:
                    pass

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
            goroot, "pkg", "tool", f"linux_{self._goarch()}"
        )
        if os.path.isdir(tool_dir):
            candidates.extend(
                os.path.join(tool_dir, name) for name in os.listdir(tool_dir)
            )

        for candidate in candidates:
            if os.path.isfile(candidate) and self._is_elf(candidate):
                os.chmod(candidate, os.stat(candidate).st_mode | 0o111)
                self._sign_ohos_executable(candidate)

        try:
            with open(marker, "w", encoding="utf-8") as stream:
                stream.write("signed\n")
        except OSError:
            pass

    def _go_version_is_supported(self, go):
        try:
            output = subprocess.run(
                [go, "version"], capture_output=True, timeout=20
            ).stdout.decode()
        except OSError:
            return False

        try:
            token = output.split("go version ")[-1].split(" ")[0]
            version = token[2:]
            current = [int(x) for x in version.split(".")]
            required = [int(x) for x in self._go_version.split(".")]
            return current >= required
        except (IndexError, ValueError):
            return False

    @staticmethod
    def _goroot_for_go(go):
        go = os.path.realpath(go)
        goroot = os.path.dirname(os.path.dirname(go))
        if os.path.isfile(os.path.join(goroot, "bin", "go")):
            return goroot
        return ""

    # ─── OHOS 适配：可写工作根 / ELF 签名 ──────────────────────────────

    def _go_workspace(self):
        """Go 工作根。OHOS 下 link 输出必须避开 HMDFS（mmap 失败）。

        参考 aliae/murex 配方：候选顺序 OHOS_GO_BUILD_ROOT 环境变量 >
        /data/storage/el2/base/cache > /data/storage/el2/base/haps/entry/files
        > $TMPDIR；Linux 下用 build_folder 同级目录。
        """
        if str(self.settings.os) == "OHOS":
            candidates = [
                os.environ.get("OHOS_GO_BUILD_ROOT"),
                "/data/storage/el2/base/cache",
                "/data/storage/el2/base/haps/entry/files",
                os.environ.get("TMPDIR"),
            ]
        else:
            candidates = [
                os.path.join(
                    os.path.dirname(os.path.abspath(self.build_folder)),
                    f"go-work-{self.name}-{self.version}",
                ),
                os.environ.get("TMPDIR"),
            ]

        for candidate in candidates:
            if not candidate:
                continue
            root = os.path.join(candidate, "conan-go-build", f"{self.name}-{self.version}")
            try:
                os.makedirs(os.path.join(root, "tmp"), exist_ok=True)
                os.makedirs(os.path.join(root, "link-out"), exist_ok=True)
                os.makedirs(os.path.join(root, "cache"), exist_ok=True)
                return root
            except OSError:
                continue

        raise ConanInvalidConfiguration(
            "No writable Go build root is available for linker output"
        )

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as binary:
                return binary.read(4) == b"\x7fELF"
        except OSError:
            return False

    @staticmethod
    def _has_ohos_signature(path):
        try:
            with open(path, "rb") as binary:
                data = binary.read()
        except OSError:
            return False
        return b".codesign" in data or b".note.ohos" in data

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

    def _find_objcopy(self):
        for candidate in (
            os.environ.get("OHOS_LLVM_OBJCOPY"),
            "/data/service/hnp/bin/llvm-objcopy",
            shutil.which("llvm-objcopy"),
        ):
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

    def _sign_ohos_executable(self, path):
        if str(self.settings.os) != "OHOS" or not os.path.isfile(path):
            return

        if self._has_ohos_signature(path):
            try:
                os.chmod(path, os.stat(path).st_mode | 0o111)
            except OSError:
                pass
            return

        signer = self._find_binary_sign_tool()
        if not signer:
            self.output.warning(
                "binary-sign-tool not found; OHOS may reject executable: %s" % path
            )
            return

        objcopy = self._find_objcopy()
        if objcopy:
            self.run(
                f'"{objcopy}" --remove-section .codesign "{path}" 2>/dev/null || true',
                ignore_errors=True,
                quiet=True,
            )

        self.run(
            f'"{signer}" sign -inFile "{path}" -outFile "{path}" '
            f'-selfSign 1 -signAlg SHA256withECDSA',
            ignore_errors=True,
            quiet=True,
        )
        try:
            os.chmod(path, os.stat(path).st_mode | 0o111)
        except OSError:
            pass

    def _goarch(self):
        arch = str(self.settings.arch)
        if arch in ("armv8", "arm64", "aarch64"):
            return "arm64"
        if arch in ("x86_64", "amd64"):
            return "amd64"
        if arch in ("x86", "i386", "i686"):
            return "386"
        raise ConanInvalidConfiguration(f"Unsupported Go arch mapping: {arch}")

    def _exe_name(self):
        return "fs-repo-15-to-16"
