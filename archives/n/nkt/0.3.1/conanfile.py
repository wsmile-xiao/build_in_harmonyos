#!/usr/bin/env python3
"""Conan recipe for nkt 0.3.1 — terminal note-taking tool.

nkt 是 Zig 项目（build.zig + build.zig.zon，Zig 0.15）：跟踪笔记、日志、
任务清单与习惯链的命令行工具。build.zig.zon 声明 6 个 zig 包依赖
（termui/datetime/farbe/clippy/fuzzig/kronos），其中 kronos 还有传递依赖
zeit。CI 真机无法直连 github.com（ConnectionResetByPeer），配方把 7 个
依赖包下载到 deps/ 并把 nkt 与 kronos 的 build.zig.zon 改写为 .path 本地
依赖，`zig build` 与 `zig build test` 全程离线（fancy-cat 0.6.0.1 已验证
方案；../ 相对路径经 vaxis→zigimg 先例真机验证可行）。

OHOS 适配要点：
- 需要 Zig 0.15（build.zig.zon 带 .fingerprint，std.Io.Writer 新 API）；
  使用已发布的 zig/0.15.2 工具包（tool_requires，PR #5562），其内置
  build_runner AccessDenied 自动签名重试与 stdlib test_server_mode=false
  补丁，`zig build test` 可直接在真机运行（ncdu 2.9.2 已验证）。
- 原生 OHOS 构建时 zig 的 libc 探测只保留 sysroot 通用 include 目录，
  musl 的 bits/ 头在架构专属目录，经 CPATH 前置（ncdu 2.9.2 同款）。
- 编译产物 bin/nkt 需 binary-sign-tool 签名后才能在 OHOS 执行。
- 上游测试：build.zig 有 test step，21 个 test 声明分布在 9 个源文件
  （src/test/main.zig 含 readme/smoke 两个集成测试，覆盖 init/new tag/
  log/task/read/ls/edit 全命令面）。kronos 在测试构建（builtin.is_test）
  下使用固定时间戳，测试输出确定。build() 运行 `zig build test` 并输出
  HMBS_UPSTREAM_TEST_RESULT 标记（R51）。
- zeit TZDIR 补丁：kronos 测试路径硬编码 zeit.loadTimeZone(alloc,
  .@"Australia/Perth", null)，env=null 时 zeit 不查 TZDIR，设备无系统
  tzdata 下 3 个测试 FileNotFound 失败（本 PR 首轮 CI 实证）。补丁让
  env=null 时回退查进程 TZDIR；配方 vendor 446 字节 Perth tzfile（IANA
  2024b，公有领域数据文件）。GitCode 的 PR .diff 不携带二进制补丁数据
  （checkout-pr 步骤 git apply 必然失败，clzip 1.16 先例同因），tzfile
  以 Base64 文本 zoneinfo/Australia/Perth.b64 存储，build() 解码到
  build 目录并校验 sha256，测试运行时 TZDIR 指向解码后的 zoneinfo/，
  测试时序数据与系统 tzdata 完全一致。
- zeit local() UTC 回退（同补丁第二 hunk）：kronos 非测试路径经
  zeit.local(alloc, null) 初始化本地时区，env=null 时 zeit 不查 TZ，
  直接 openFile("/etc/localtime")，OHOS 无该文件 → FileNotFound 从
  main 逸出，二进制任何子命令都退出码 1（第三轮 CI test_package 实证：
  `nkt config` stderr "[error]: (default) FileNotFound"，经 Zig 0.15
  std.start 的 std.log.err + nkt 自定义 logFn 打印）。补丁让
  /etc/localtime 打开失败时回退固定 UTC 时区（kronos 自身 local()
  访问器同款降级语义），真机全命令面恢复可用；本地 WSL 移除
  /etc/localtime 复现并验证修复，21/21 上游测试与消费者测试全绿。
- 注意：`nkt --version`/`--help` 因上游缓冲 writer 未 flush 的缺陷输出为空
  （rc=0）；版本信息经 `nkt config` 子命令获取（"nkt version : 0.3.1"），
  CI L2 冒烟门禁只检查退出码不受影响，test_package 据此设计。
- settings 声明 os/compiler/build_type/arch 四项（L0p 门禁要求）。
"""
import base64
import glob
import hashlib
import json
import os
import re
import shlex
import shutil
import stat
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class NktConan(ConanFile):
    name = "nkt"
    version = "0.3.1"
    package_type = "application"

    description = "Terminal note-taking tool for journals, tasklists, notes and tags"
    license = "GPL-3.0-or-later"
    homepage = "https://git.sr.ht/~fjebaker/nkt"
    url = "https://git.sr.ht/~fjebaker/nkt"

    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv"
    # vendored tzdata 数据文件（Australia/Perth，kronos 测试路径硬编码的
    # 时区）：设备无系统 zoneinfo，测试经补丁后的 zeit 从 TZDIR 加载。
    # GitCode 的 PR .diff 不携带二进制补丁数据，故以 Base64 文本存储
    # （clzip 1.16 同款方案），build() 解码并校验 sha256；补丁文件本身
    # 经 export_conandata_patches 导出。
    exports_sources = "zoneinfo/Australia/Perth.b64"

    def build_requirements(self):
        # nkt 0.3.1 targets Zig 0.15 (build.zig.zon .fingerprint,
        # std.Io.Writer/std.process.Child 0.15 APIs). The matching OHOS tool
        # package zig/0.15.2 is published on ohpcd (PR #5562).
        self.tool_requires("zig/0.15.2")

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.ref} supports native Linux/OHOS builds only"
            )

    def export_sources(self):
        # 导出 conandata 补丁（patches/zeit-tzdir-fallback.patch，见
        # conandata.yml patches: 键）；zoneinfo/Australia/Perth 经
        # exports_sources 属性导出。
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # zig 包依赖（build.zig.zon 声明的 url 依赖及 kronos 的传递依赖
        # zeit；真机无法直连 github.com，改为下载到 deps/ 并改写为本地
        # .path 依赖，zig build 全程离线）
        for dep in ("termui", "datetime", "farbe", "clippy", "fuzzig", "kronos", "zeit"):
            get(
                self,
                **self.conan_data[dep],
                strip_root=True,
                destination=os.path.join("deps", dep),
            )
        # 应用 conandata 补丁（zeit TZDIR 回退）。补丁目标
        # deps/zeit/src/zeit.zig 在依赖下载后才存在，必须在依赖下载
        # 之后应用。
        apply_conandata_patches(self)
        self._patch_zig_zon_to_local_deps()

    def _patch_zig_zon_to_local_deps(self):
        """把 build.zig.zon 的 url 依赖改写为本地 .path 依赖（真机离线构建）。

        真机无法直连 github.com（ConnectionResetByPeer），`zig build` 按
        build.zig.zon 的 url+hash 自动拉取必然失败。配方已在 source() 下载
        7 个依赖包到 deps/，这里把根 build.zig.zon 的 6 个 url+hash 条目
        与 deps/kronos/build.zig.zon 的 zeit 条目整体替换为 .path 相对路径
        （fancy-cat 0.6.0.1 同款；../ 相对路径经其 vaxis→zigimg 改写真机
        验证可行；本机 zig 0.15.2 + WSL Linux 实测通过，依赖解析零网络）。
        """
        root_zon = os.path.join(self.source_folder, "build.zig.zon")
        kronos_zon = os.path.join(
            self.source_folder, "deps", "kronos", "build.zig.zon"
        )
        replacements = [
            (
                root_zon,
                '''        .termui = .{
            .url = "git+https://github.com/fjebaker/termui#9dc6d2fabb2a7305b07f2fc91f12770a321dded0",
            .hash = "termui-0.2.2-2zSn4btcAABhXjNsk-qzsHLSyryLLmJRoENpgylYHMQC",
        },''',
                '''        .termui = .{ .path = "deps/termui" },''',
            ),
            (
                root_zon,
                '''        .datetime = .{
            .url = "git+https://github.com/frmdstryr/zig-datetime#3a39a21e6e34dcb0ade0ff828d0914d40ba535f3",
            .hash = "datetime-0.8.0-cJNXzP_YAQBxQ5hkNNP6ScnG5XsqciJmeP5RVV4xwCBA",
        },''',
                '''        .datetime = .{ .path = "deps/datetime" },''',
            ),
            (
                root_zon,
                '''        .farbe = .{
            .url = "git+https://github.com/fjebaker/farbe#fa60dfeaaf049467a9158731bfbf930f0ca29f4e",
            .hash = "farbe-0.3.1-AmrQL6FWAADAEK1n2yCGDjA1Et6zVyoBuvceDFLA0mip",
        },''',
                '''        .farbe = .{ .path = "deps/farbe" },''',
            ),
            (
                root_zon,
                '''        .clippy = .{
            .url = "git+https://github.com/fjebaker/clippy#4eb7b412ce11e89314c3e83feeff9421292b4274",
            .hash = "clippy-0.4.0-BgbUoF9lAQDW6wA3sXfDQrRGX9vyIBLK8HitsF25FrCh",
        },''',
                '''        .clippy = .{ .path = "deps/clippy" },''',
            ),
            (
                root_zon,
                '''        .fuzzig = .{
            .url = "git+https://github.com/fjebaker/fuzzig#4251fe4230d38e721514394a485db62ee1667ff3",
            .hash = "fuzzig-0.1.1-Ji0xivxIAQBD0g8O_NV_0foqoPf3elsg9Sc3pNfdVH4D",
        },''',
                '''        .fuzzig = .{ .path = "deps/fuzzig" },''',
            ),
            (
                root_zon,
                '''        .kronos = .{
            .url = "git+https://git.sr.ht/~fjebaker/kronos#a1d77455aeefe0656965548707ceeb6b85ff765e",
            .hash = "kronos-0.0.0-QEk43JpsAAB52HQ6nhX9MwTH5Eph-NKvef1p7VrLs6fK",
        },''',
                '''        .kronos = .{ .path = "deps/kronos" },''',
            ),
            (
                kronos_zon,
                '''        .zeit = .{
            .url = "git+https://github.com/rockorager/zeit#ade14edb2025f5e4a57b683f81c915f70a904e88",
            .hash = "zeit-0.6.0-5I6bk7V8AgAY0-hM-vUYtKZUFYhXct-VRkqISNNTfEfb",
        },''',
                '''        .zeit = .{ .path = "../zeit" },''',
            ),
        ]
        for zon_path, old, new in replacements:
            with open(zon_path, encoding="utf-8") as f:
                content = f.read()
            if old not in content:
                raise ConanInvalidConfiguration(
                    f"build.zig.zon dependency block not found in {zon_path}"
                )
            with open(zon_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(content.replace(old, new))

    def _zig(self):
        package_folder = self.dependencies.build["zig"].package_folder
        executable = os.path.join(package_folder, "bin", "zig")
        if os.path.isfile(executable):
            return executable
        found = shutil.which("zig")
        if found:
            return found
        raise ConanInvalidConfiguration(
            "zig/0.15.2 is required but no zig executable was found"
        )

    def _ohos_arch_include(self):
        if str(self.settings.os) != "OHOS":
            return None

        candidates = []
        configured = os.environ.get("OHOS_SYSROOT")
        if configured:
            candidates.append(configured)

        executables = self.conf.get(
            "tools.build:compiler_executables", default={}
        )
        compiler = (
            os.environ.get("CC")
            or executables.get("c")
            or shutil.which("clang")
        )
        if compiler:
            compiler = shlex.split(compiler)[0]
            try:
                result = subprocess.run(
                    [compiler, "--print-sysroot"],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                if result.stdout.strip():
                    candidates.append(result.stdout.strip())
            except (OSError, subprocess.CalledProcessError):
                pass

            compiler = os.path.realpath(compiler)
            candidates.append(
                os.path.normpath(
                    os.path.join(
                        os.path.dirname(compiler), "..", "..", "sysroot"
                    )
                )
            )

        candidates.extend(
            reversed(
                sorted(
                    glob.glob(
                        "/data/service/hnp/ohos-sdk.org/"
                        "ohos-sdk_*/ohos/native/sysroot"
                    )
                )
            )
        )

        for sysroot in candidates:
            include = os.path.join(
                sysroot, "usr", "include", "aarch64-linux-ohos"
            )
            if os.path.isfile(os.path.join(include, "bits", "alltypes.h")):
                return include

        raise ConanInvalidConfiguration(
            "OHOS architecture headers were not found under the compiler sysroot"
        )

    def _find_ohos_tool(self, env_name, command, fallback):
        configured = os.environ.get(env_name)
        if configured:
            found = shutil.which(configured)
            if found:
                return found
            if os.path.exists(configured):
                return configured
        found = shutil.which(command)
        if found:
            return found
        if os.path.exists(fallback):
            return fallback
        return None

    def _sign_ohos_executable(self, path):
        if str(self.settings.os) != "OHOS":
            return
        objcopy = self._find_ohos_tool(
            "OHOS_LLVM_OBJCOPY",
            "llvm-objcopy",
            "/storage/Users/currentUser/usr/local/bin/llvm-objcopy",
        )
        signer = self._find_ohos_tool(
            "OHOS_BINARY_SIGN_TOOL",
            "binary-sign-tool",
            "/storage/Users/currentUser/usr/local/bin/binary-sign-tool",
        )
        if objcopy:
            self.run(
                f'{shlex.quote(objcopy)} --remove-section .codesign '
                f'{shlex.quote(path)} 2>/dev/null || true'
            )
        if not signer:
            raise ConanInvalidConfiguration(
                "binary-sign-tool is required to package nkt on OHOS"
            )
        signed = f"{path}.signed"
        self.run(
            f'{shlex.quote(signer)} sign -inFile {shlex.quote(path)} '
            f'-outFile {shlex.quote(signed)} -selfSign 1'
        )
        shutil.move(signed, path)
        os.chmod(
            path,
            os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH,
        )

    def build(self):
        zig = self._zig()
        install_prefix = os.path.join(self.build_folder, "zig-out")
        global_cache = os.path.join(self.build_folder, "zig-global-cache")
        local_cache = os.path.join(self.build_folder, "zig-local-cache")
        for path in (install_prefix, global_cache, local_cache):
            os.makedirs(path, exist_ok=True)

        # kronos 测试路径硬编码 Australia/Perth（env=null），补丁后的 zeit
        # 回退查进程 TZDIR；设备无系统 tzdata。Perth tzfile 以 Base64 文本
        # 存储（GitCode PR .diff 不携带二进制补丁数据，checkout-pr 的
        # git apply 无法创建二进制文件，clzip 1.16 同款方案），这里解码
        # 到 build 目录的 zoneinfo/ 并校验 sha256，测试运行时 TZDIR 指向
        # 该目录（解码字节与 WSL 全绿验证所用文件完全一致）。
        zoneinfo_dir = os.path.join(self.build_folder, "zoneinfo")
        perth_path = os.path.join(zoneinfo_dir, "Australia", "Perth")
        os.makedirs(os.path.dirname(perth_path), exist_ok=True)
        b64_path = os.path.join(
            self.source_folder, "zoneinfo", "Australia", "Perth.b64"
        )
        if not os.path.isfile(b64_path):
            raise ConanInvalidConfiguration(
                f"vendored zoneinfo/Australia/Perth.b64 is missing from {b64_path}"
            )
        with open(b64_path, "r", encoding="ascii") as f:
            perth_bytes = base64.b64decode(f.read().strip())
        perth_sha256 = hashlib.sha256(perth_bytes).hexdigest()
        expected_sha256 = (
            "025d4339487853fa1f3144127959734b20f7c7b4948cff5d72149a0541a67968"
        )
        if perth_sha256 != expected_sha256:
            raise ConanException(
                f"decoded zoneinfo/Australia/Perth sha256 mismatch: {perth_sha256}"
            )
        with open(perth_path, "wb") as f:
            f.write(perth_bytes)
        environment = Environment()
        environment.define_path("TZDIR", zoneinfo_dir)
        environment.define_path("ZIG_GLOBAL_CACHE_DIR", global_cache)
        environment.define_path("ZIG_LOCAL_CACHE_DIR", local_cache)
        environment.define(
            "ZIG_OHOS_SIGN_ROOTS",
            " ".join((global_cache, local_cache, install_prefix)),
        )
        arch_include = self._ohos_arch_include()
        if arch_include:
            # Zig treats OHOS as native Linux, but its libc probe only keeps the
            # generic sysroot include directory. musl's bits/ headers live in
            # the target-specific directory and must precede it.
            environment.prepend_path("CPATH", arch_include)
        command = " ".join(
            (
                shlex.quote(zig),
                "build",
                "-j1",
                "--prefix",
                shlex.quote(install_prefix),
                "-Doptimize=ReleaseFast",
            )
        )
        test_command = " ".join(
            (
                shlex.quote(zig),
                "build",
                "test",
                "-j1",
                "--summary",
                "all",
            )
        )

        with environment.vars(self).apply():
            self.run(f"{shlex.quote(zig)} version", env="conanbuild")
            self.run(command, cwd=self.source_folder, env="conanbuild")
            # 上游 zig build test 用 subprocess 捕获输出以解析测试计数
            # （R51 三步法：盘点 21 声明 → 真机运行 → HMBS 标记报告）。
            result = subprocess.run(
                shlex.split(test_command),
                cwd=self.source_folder,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=1800,
            )

        if result.stdout:
            self.output.info(result.stdout)
        if result.returncode != 0:
            raise ConanException(
                f"zig build test failed with exit code {result.returncode}"
            )

        # 解析 zig 测试计数（--summary all 输出 "N/N tests passed"）
        executed = None
        passed = None
        summary_match = re.search(r"(\d+)/(\d+) tests passed", result.stdout)
        if summary_match:
            passed = int(summary_match.group(1))
            executed = int(summary_match.group(2))
        else:
            all_match = re.search(r"All (\d+) tests passed", result.stdout)
            if all_match:
                executed = int(all_match.group(1))
                passed = executed
        if executed is None:
            raise ConanException(
                "zig build test output did not contain a test summary line"
            )

        marker = {
            "status": "passed",
            "framework": "zig",
            "command": "zig build test -j1 --summary all",
            "discovered": 21,
            "executed": executed,
            "passed": passed,
            # returncode==0 保证无失败；executed-passed 即跳过数
            # （"All N passed" 时 executed==passed，跳过数为 0）
            "failed": 0,
            "skipped": executed - passed,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker))

        binary = os.path.join(install_prefix, "bin", "nkt")
        if not os.path.isfile(binary):
            raise ConanInvalidConfiguration(
                f"zig build did not produce the expected binary: {binary}"
            )
        self._sign_ohos_executable(binary)

    def package(self):
        install_prefix = os.path.join(self.build_folder, "zig-out")
        copy(
            self,
            "nkt",
            src=os.path.join(install_prefix, "bin"),
            dst=os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
