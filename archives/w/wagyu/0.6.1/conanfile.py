#!/usr/bin/env python3
"""Conan recipe — wagyu 0.6.1 (Cargo)

wagyu 是 Rust workspace（根 crate 同时产出 lib 与 `wagyu` 可执行文件；成员 crate
bitcoin/ethereum/model/monero/zcash）。**不是 header-only、不产出 .so/.a 的 C 库**：
交付物是单个 OHOS aarch64 可执行文件 `bin/wagyu`（G4/L2/L4 按可执行产物检查）。

工具链：tool_requires rust-toolchain/1.97.1（rust-lang 官方 dist 预编译、宿主与目标
均为 aarch64-unknown-linux-ohos 的基础设施包，ohpcd 制品仓真实可装：2026-09-23
`conan install --tool-requires=rust-toolchain/1.97.1 --build=never` rc=0 实测）。
不使用 rustup（标准 rustup 无法识别 HarmonyOS 宿主，E105/E154）。

两个平台事实（均设备实测 2026-09-23）：
1. 包内 cargo/rustc 无 code signature，OHOS 拒绝 execve 未签名 ELF（errno 13）→
   build() 把 cargo/rustc/librustc_driver 复制进 build folder 自签名后使用；
2. cargo 动态链接 libssl.so/libcrypto.so/libz.so，OHOS loader 忽略 DT_RUNPATH →
   用 conandata `rust_runtime` 的 Harmonybrew OHOS bottle（openssl3 3.6.4 +
   zlib-ng-compat 2.3.3_2，sha256 设备实测）注入 LD_LIBRARY_PATH。

源适配（2019 年 Cargo.lock × 现代 rustc × ohos 目标，探索轮实测）：
- patches/0001-Cargo.lock.patch：libc 0.2.61→0.2.189（662 个 E0425/E0573）、
  cc 1.0.40→1.0.41 —— **保持 v1 锁格式的最小改动（20 行改动，diff ±40 行）**，交给
  cargo update 会把整文件重写成 v4 格式（diff 上千行且 --locked 需重新验证）；
- patches/0002-main.rs-version-string.patch：CLI 自报版本 v0.6.0→v0.6.1
  （上游 0.6.1 tag 漏 bump，且 DisableVersion 禁了 --version）；
- build() 内 registry 源补丁（cargo fetch 之后、编译之前，幂等锚点校验）：
  · getrandom 0.1.9 加 target_os="ohos"（否则 compile_error! "target is not
    supported"；rand 0.7 传递依赖，0.1 系列无 ohos 支持，无法靠 bump 解决）；
  · rustc-serialize 0.3.24 的 `impl Decodable for Cow` 补 `+ 'static`
    （rustc 建议的最小修复，0.3.25 仍未修）。
  补丁落在**构建目录内的 CARGO_HOME**（不污染共享 ~/.cargo，也不改 .crate 校验）。

上游测试：`cargo test --release --target aarch64-unknown-linux-ohos --workspace
--locked --all-targets` 在 build() 内执行（`--all-targets` 不含 doctest：
rust-toolchain/1.97.1 包缺 rustdoc 组件；探索轮用含 rustdoc 的完整工具链实证
7 个 Doc-tests 套件注册 0 用例，排除不漏用例），逐套件解析 `running N tests` /
`test result:` 汇总并输出 `HMBS_UPSTREAM_TEST_RESULT` 机器可读标记（用例数由
最终设备日志复算）。
"""

import json
import os
import shlex
import shutil
import subprocess
import tarfile

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy, download,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout

# cargo fetch 后注册表源码内需要打的 OHOS 兼容补丁（幂等；锚点来自锁定版本源码）。
# 每项 = (相对 registry/src/<index>/ 的路径, 原文, 新文)。
REGISTRY_PATCHES = [
    # getrandom 0.1.9：三处目标门 + util_libc/use_file 的 linux 分支加 ohos
    ("getrandom-0.1.9/src/lib.rs",
     '    target_os = "freebsd",\n    target_os = "haiku",',
     '    target_os = "freebsd",\n    target_os = "haiku",\n    target_os = "ohos",'),
    ("getrandom-0.1.9/src/lib.rs",
     '#[cfg(any(\n    target_os = "android",\n    target_os = "linux",\n'
     '    target_os = "macos",\n    target_os = "solaris",\n'
     '    target_os = "illumos",\n))]\nmod use_file;',
     '#[cfg(any(\n    target_os = "android",\n    target_os = "linux",\n'
     '    target_os = "ohos",\n    target_os = "macos",\n'
     '    target_os = "solaris",\n    target_os = "illumos",\n))]\nmod use_file;'),
    ("getrandom-0.1.9/src/lib.rs",
     '} else if #[cfg(target_os = "linux")] {',
     '} else if #[cfg(any(target_os = "linux", target_os = "ohos"))] {'),
    ("getrandom-0.1.9/src/util_libc.rs",
     '} else if #[cfg(any(target_os = "linux", target_os = "emscripten", '
     'target_os = "redox"))] {',
     '} else if #[cfg(any(target_os = "linux", target_os = "ohos", '
     'target_os = "emscripten", target_os = "redox"))] {'),
    ("getrandom-0.1.9/src/util_libc.rs",
     'if #[cfg(any(target_os = "linux", target_os = "emscripten"))] {',
     'if #[cfg(any(target_os = "linux", target_os = "ohos", '
     'target_os = "emscripten"))] {'),
    ("getrandom-0.1.9/src/util_libc.rs",
     '#[cfg(target_os = "linux")]',
     '#[cfg(any(target_os = "linux", target_os = "ohos"))]'),
    ("getrandom-0.1.9/src/use_file.rs",
     'if #[cfg(any(target_os = "android", target_os = "linux", '
     'target_os = "netbsd"))] {',
     'if #[cfg(any(target_os = "android", target_os = "linux", '
     'target_os = "ohos", target_os = "netbsd"))] {'),
    # rustc-serialize 0.3.24：Cow 的 Decodable 实现缺 'static 约束（E0310）
    ("rustc-serialize-0.3.24/src/serialize.rs",
     "impl<'a, T: ?Sized> Decodable for Cow<'a, T>",
     "impl<'a, T: ?Sized + 'static> Decodable for Cow<'a, T>"),
]


class WagyuConan(ConanFile):
    name = "wagyu"
    version = "0.6.1"
    description = "wagyu: a command-line tool to generate cryptocurrency wallets"
    license = "MIT OR Apache-2.0"
    homepage = "https://github.com/howardwu/wagyu"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"wagyu is only supported on Linux/OHOS, got {self.settings.os}")
        self._ohos_target()

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 纯 Rust 依赖树：无 Conan 运行期依赖（secp256k1 捆绑的 C 源由 cc 直接编译）。
        pass

    def build_requirements(self):
        # 基础设施包（ohpcd 制品仓真实在档，R36：依赖先发布再构建下游）：
        # rust-lang 官方 dist 预编译，宿主与目标均为 aarch64-unknown-linux-ohos。
        # 不使用 rustup 引导——标准 rustup 无法识别 HarmonyOS 宿主（E105/E154）。
        self.tool_requires("rust-toolchain/1.97.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        env = self._rust_environment()
        self._ensure_ohos_target(env)
        self._fetch_cargo_deps(env)
        self._patch_registry_for_ohos(env)
        upstream = self._run_upstream_tests(env)
        self._cargo_build(env)
        self._sign_binaries()
        msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(
            upstream, ensure_ascii=False)
        print(msg, flush=True)
        self.output.info(msg)

    # ── 阶段：依赖获取与源码补丁 ─────────────────────────────────────

    def _fetch_cargo_deps(self, env):
        """cargo fetch --locked：按锁文件物化依赖（fetch 即解包进 registry/src）。
        这是上游测试与构建共用的依赖获取入口（离线锁文件、可复现）。"""
        result = subprocess.run(
            [env["CARGO"], "fetch", "--locked", "--manifest-path",
             os.path.join(self.source_folder, "Cargo.toml")],
            cwd=self.source_folder, env=env,
        ).returncode
        if result != 0:
            raise ConanInvalidConfiguration(f"cargo fetch --locked failed (rc={result})")

    def _patch_registry_for_ohos(self, env):
        """在构建目录 CARGO_HOME 的 registry/src 上打 OHOS 兼容补丁（幂等）。

        getrandom 0.1.9 / rustc-serialize 0.3.24 均已锁死版本，无法靠 bump 解决
        （0.1 系列无 ohos 支持；0.3.25 未修 Cow E0310）。补丁只改解包后的源码，
        不碰 .crate 缓存（其 sha256 受 Cargo.lock checksum 校验），且 CARGO_HOME
        在 build folder 内，不污染共享 ~/.cargo。
        锚点缺失即硬失败——不允许“补丁静默未生效却继续构建”。
        """
        cargo_home = env.get("CARGO_HOME") or os.path.expanduser("~/.cargo")
        src_roots = []
        registry_src = os.path.join(cargo_home, "registry", "src")
        if os.path.isdir(registry_src):
            src_roots = [os.path.join(registry_src, d)
                         for d in sorted(os.listdir(registry_src))]
        if not src_roots:
            raise ConanInvalidConfiguration(
                f"cargo registry src not found under {registry_src}; cargo fetch "
                "did not materialize sources")
        for rel, old, new in REGISTRY_PATCHES:
            hit = None
            for root in src_roots:
                cand = os.path.join(root, rel)
                if os.path.isfile(cand):
                    hit = cand
                    break
            if hit is None:
                raise ConanInvalidConfiguration(
                    f"registry patch target missing (cargo fetch incomplete?): {rel}")
            with open(hit, encoding="utf-8") as fh:
                text = fh.read()
            if new in text:
                self.output.info(f"registry patch already applied: {rel}")
                continue
            if old not in text:
                raise ConanInvalidConfiguration(
                    f"registry patch anchor missing in {rel}: {old[:60]!r}")
            with open(hit, "w", encoding="utf-8") as fh:
                fh.write(text.replace(old, new, 1))
            self.output.info(f"registry patch applied: {rel}")

    # ── 阶段：上游测试 ──────────────────────────────────────────────

    def _run_upstream_tests(self, env):
        """执行上游 `cargo test --workspace`（OHOS 目标、本机直跑）并解析逐套件结果。

        输出逐字落到 conan create 日志（证据可回溯），返回机器可读统计。
        有失败即硬失败——wagyu 测试为纯内存计算（钱包生成/椭圆曲线/助记词），
        不依赖网络、TTY、文件系统特权；探索轮实测全绿（见 notes.md）。
        设置 OHC_SKIP_UPSTREAM_TESTS=1 可显式跳过（应急排障用，PR 正文会体现）。
        """
        if os.environ.get("OHC_SKIP_UPSTREAM_TESTS") == "1":
            self.output.warning(
                "upstream cargo test skipped by OHC_SKIP_UPSTREAM_TESTS=1")
            return {"status": "skipped", "framework": "cargo-test",
                    "reason": "OHC_SKIP_UPSTREAM_TESTS=1"}
        target = self._ohos_target()
        log_path = os.path.join(self.build_folder, "upstream-tests.log")
        # --all-targets：全部单元/集成/bench/example 目标，**不含 doctest**——
        # rust-toolchain/1.97.1 基础设施包不含 rustdoc 组件（bin/ 里没有 rustdoc，
        # 实测），doctest 阶段必然 "could not execute process rustdoc"。探索轮用含
        # rustdoc 的完整工具链实跑过全部 7 个 Doc-tests 套件：注册用例 0（见 notes.md
        # 清点表），故排除 doctest 不漏任何用例；N=608 不受影响。
        cmd = [env["CARGO"], "test", "--release", "--target", target,
               "--workspace", "--locked", "--all-targets"]
        with open(log_path, "w", encoding="utf-8") as log:
            log.write("RUN: " + " ".join(shlex.quote(c) for c in cmd) + "\n")
            log.flush()
            proc = subprocess.Popen(cmd, cwd=self.source_folder, env=env,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT)
            assert proc.stdout is not None
            for raw in proc.stdout:
                line = raw.decode("utf-8", "replace")
                log.write(line)
                print(line, end="", flush=True)
            rc = proc.wait()
        with open(log_path, encoding="utf-8") as fh:
            text = fh.read()

        suites = []
        for line in text.splitlines():
            line = line.strip()
            # cargo 单数形态是 "running 1 test"（field_derive 套件实测），两种都要收
            if line.startswith("running ") and line.endswith((" tests", " test")):
                suites.append({"running": int(line.split()[1])})
            elif line.startswith("test result:"):
                # test result: ok. 175 passed; 0 failed; 0 ignored; ...
                words = line.replace(".", " ").split()
                nums = [(int(tok), words[i + 1])
                        for i, tok in enumerate(words)
                        if tok.isdigit() and i + 1 < len(words)]

                def pick(key):
                    for value, name in nums:
                        if name.startswith(key):
                            return value
                    return 0

                if not suites:
                    suites.append({})
                suites[-1].update({
                    "passed": pick("passed"), "failed": pick("failed"),
                    "ignored": pick("ignored"),
                })
        executed = sum(1 for s in suites if "passed" in s)
        passed = sum(s.get("passed", 0) for s in suites)
        failed = sum(s.get("failed", 0) for s in suites)
        ignored = sum(s.get("ignored", 0) for s in suites)
        registered = sum(s.get("running", 0) for s in suites)
        summary = {
            "status": "ok" if rc == 0 and failed == 0 else "failed",
            "framework": "cargo-test",
            "command": " ".join(cmd),
            "suites": executed,
            "registered": registered,
            "executed": registered,
            "passed": passed,
            "failed": failed,
            "ignored": ignored,
            "log": log_path,
        }
        self.output.info("upstream test summary: " + json.dumps(summary))
        if rc != 0 or failed != 0:
            raise ConanInvalidConfiguration(
                f"upstream cargo test failed (rc={rc}, failed={failed}); "
                f"see {log_path}")
        return summary

    # ── 阶段：构建与签名 ────────────────────────────────────────────

    def _cargo_build(self, env):
        target = self._ohos_target()
        cmd = [env["CARGO"], "build", "--release", "--locked",
               "--target", target]
        result = subprocess.run(cmd, cwd=self.source_folder, env=env).returncode
        if result != 0:
            raise ConanInvalidConfiguration(
                f"cargo build --release --locked failed for {target} (rc={result})")
        out_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(out_dir, exist_ok=True)
        release_dir = os.path.join(self.source_folder, "target", target, "release")
        src = os.path.join(release_dir, "wagyu")
        if not os.path.isfile(src):
            raise ConanInvalidConfiguration(f"wagyu binary not produced: {src}")
        dst = os.path.join(out_dir, "wagyu")
        shutil.copy2(src, dst)
        os.chmod(dst, 0o755)

    def _sign_binaries(self):
        """产物签名：OHOS 拒绝 execve 未签名 ELF（errno 13）。

        OHOS SDK 的 lld 在链接期通常已写入签名（设备实测产物含 codesign 标记）；
        标记缺失时才调用 binary-sign-tool 自签，签不上即硬失败——否则
        test_package 的消费端运行与 CI 的 L2 smoke 都会撞 EACCES。
        """
        if str(self.settings.os) != "OHOS":
            return
        path = os.path.join(self.build_folder, "bin", "wagyu")
        with open(path, "rb") as fh:
            payload = fh.read()
        if b"codesign" in payload:
            self.output.info("wagyu already carries an OHOS code signature")
            return
        signer = self._find_binary_sign_tool()
        if not signer:
            raise ConanInvalidConfiguration(
                "wagyu binary is unsigned and binary-sign-tool was not found; "
                "OHOS would refuse to exec it (EACCES)")
        result = self.run(
            f"{shlex.quote(signer)} sign -inFile {shlex.quote(path)} "
            f"-outFile {shlex.quote(path)} -selfSign 1",
            ignore_errors=True, quiet=True,
        )
        if result != 0:
            raise ConanInvalidConfiguration(
                f"binary-sign-tool failed (rc={result}) for {path}")

    def _find_binary_sign_tool(self):
        candidates = [
            os.environ.get("BINARY_SIGN_TOOL"),
            shutil.which("binary-sign-tool"),
            "/data/service/hnp/bin/binary-sign-tool",
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

    # ── 工具链环境 ──────────────────────────────────────────────────

    def _ohos_target(self):
        arch = str(self.settings.arch)
        mapping = {
            "armv8": "aarch64-unknown-linux-ohos",
            "arm64": "aarch64-unknown-linux-ohos",
            "aarch64": "aarch64-unknown-linux-ohos",
            "armv7": "armv7-unknown-linux-ohos",
            "x86_64": "x86_64-unknown-linux-ohos",
        }
        target = mapping.get(arch)
        if not target:
            raise ConanInvalidConfiguration(f"Unsupported arch: {arch}")
        return target

    def _rust_environment(self):
        env = os.environ.copy()
        cargo = self._find_cargo()
        env["CARGO"] = cargo
        # doc-test 阶段 exec 的 rustdoc 也钉在签名工具链上（缺省会走 PATH 找不到）
        signed_rustdoc = os.path.join(os.path.dirname(cargo), "rustdoc")
        if os.path.isfile(signed_rustdoc):
            env["RUSTDOC"] = signed_rustdoc
        extra_paths = [os.path.dirname(cargo)]
        extra_paths += [d for d in ("/system/bin", "/system/sbin", "/vendor/bin")
                        if os.path.isdir(d)]
        env["PATH"] = os.pathsep.join(extra_paths) + os.pathsep + env.get("PATH", "")

        # CARGO_HOME 固定在 build folder：registry 补丁只作用于本次构建，
        # 不污染共享 ~/.cargo（共享设备并发卫生）。
        cargo_home = os.path.join(self.build_folder, "cargo-home")
        os.makedirs(cargo_home, exist_ok=True)
        env["CARGO_HOME"] = cargo_home
        ca = self._ca_bundle()
        self._configure_rsproxy(cargo_home, ca)
        if ca:
            env["SSL_CERT_FILE"] = ca
            env["CURL_CA_BUNDLE"] = ca
            env["CARGO_HTTP_CAINFO"] = ca

        # 临时目录：设备 /tmp 只读（device-facts §一.1），一律落 build folder。
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env.update({"TMPDIR": tmpdir, "TMP": tmpdir, "TEMP": tmpdir})

        # 工具链自带 lib（librustc_driver）+ cargo 运行期共享库（libssl/libcrypto/libz）：
        # OHOS loader 忽略 DT_RUNPATH，必须显式 LD_LIBRARY_PATH。
        lib_dirs = [os.path.join(os.path.dirname(os.path.dirname(cargo)), "lib")]
        lib_dirs += self._prepare_runtime_libs()
        if lib_dirs:
            prev = env.get("LD_LIBRARY_PATH", "")
            env["LD_LIBRARY_PATH"] = os.pathsep.join(
                lib_dirs + ([prev] if prev else []))

        # host == target == ohos：通用 CC/AR 与 per-target 变量都指向 OHOS clang，
        # 覆盖 rust-crypto/backtrace-sys 这类用老 gcc-0.3.55、不认 CC_<target>
        # 命名的 build script（探索轮实测 "Failed to find tool. Is cc installed?"）。
        cc = self._ohos_cc()
        sdk_bin = os.path.dirname(cc)
        env.update({
            "CC": cc,
            "CXX": cc if cc.endswith("++") else cc + "++",
            "AR": os.path.join(sdk_bin, "llvm-ar"),
            "RANLIB": os.path.join(sdk_bin, "llvm-ranlib"),
            "CARGO_TARGET_AARCH64_UNKNOWN_LINUX_OHOS_LINKER": cc,
            "CC_aarch64_unknown_linux_ohos": cc,
            "CXX_aarch64_unknown_linux_ohos": cc if cc.endswith("++") else cc + "++",
            "AR_aarch64_unknown_linux_ohos": os.path.join(sdk_bin, "llvm-ar"),
            "RANLIB_aarch64_unknown_linux_ohos": os.path.join(sdk_bin, "llvm-ranlib"),
        })
        # 设备 affinity=8、os.cpu_count()=20（device-facts §一.7），限并发防超订。
        env.setdefault("CARGO_BUILD_JOBS", "4")
        env.setdefault("CARGO_NET_RETRY", "10")
        env.setdefault("CARGO_HTTP_TIMEOUT", "600")
        return env

    def _find_cargo(self):
        # 优先 tool_requires 的 rust-toolchain/1.97.1（钉版本：测试统计与产物可复现）；
        # 系统 cargo 仅作兑底。
        tool = self._rust_toolchain_dep()
        if tool:
            bin_dir = self._prepare_signed_toolchain()
            candidate = os.path.join(bin_dir, "cargo")
            if os.path.isfile(candidate):
                return candidate
        for candidate in (shutil.which("cargo"),
                          os.path.expanduser("~/.cargo/bin/cargo")):
            if candidate and os.path.isfile(candidate):
                return candidate
        raise ConanInvalidConfiguration(
            "no cargo: rust-toolchain/1.97.1 tool_requires package unavailable "
            "and no system cargo found")

    def _rust_toolchain_dep(self):
        try:
            return self.dependencies.build.get("rust-toolchain")
        except (KeyError, ConanException):
            return None

    def _toolchain_dir(self):
        return os.path.join(self.build_folder, "rust-toolchain")

    def _prepare_signed_toolchain(self):
        """准备可执行的 Rust 工具链：复制 cargo/rustc/rustdoc/librustc_driver 并
        自签名，镜像 rustlib（`*.so` 复制自签、其余软链）。

        rust-toolchain/1.97.1 包内是 rust-lang 官方 dist 产物、不带 code
        signature（设备实测直接执行报 Permission denied / errno 13），OHOS 拒绝
        execve；rustlib 的 libstd-*.so 同样未签名，loader 在 dlopen 阶段拒绝
        （见 _mirror_rustlib）。只复制需要执行/加载的文件，其余只读负载
        （rustlib rlib 等 ~500MB）软链。以 .prepared marker 保证幂等。
        注：该包 bin/ 可能没有 rustdoc（组件缺失），有则一并复制签名，
        没有也不报错——测试侧用 --all-targets 不依赖 doctest。
        """
        dst = self._toolchain_dir()
        bin_dst = os.path.join(dst, "bin")
        lib_dst = os.path.join(dst, "lib")
        marker = os.path.join(dst, ".prepared")
        if os.path.isfile(marker):
            return bin_dst
        tool = self._rust_toolchain_dep()
        if not tool:
            raise ConanInvalidConfiguration(
                "rust-toolchain/1.97.1 tool_requires package not available")
        src = tool.package_folder
        os.makedirs(bin_dst, exist_ok=True)
        os.makedirs(lib_dst, exist_ok=True)

        signer = self._find_binary_sign_tool() if str(self.settings.os) == "OHOS" else None
        to_sign = []
        # rustdoc 必须一起签：cargo test 的 doc-test 阶段直接 exec `rustdoc`
        # （未签/不在 PATH 都会让最后一个阶段报 "could not execute process
        # rustdoc ... No such file or directory"，前面 8 个单元套件全过也会失败）。
        for name in ("cargo", "rustc", "rustdoc"):
            s = os.path.join(src, "bin", name)
            if os.path.isfile(s):
                d = os.path.join(bin_dst, name)
                if not os.path.isfile(d):
                    shutil.copy2(s, d)
                    os.chmod(d, 0o755)
                with open(d, "rb") as fh:
                    if b"codesign" not in fh.read():
                        to_sign.append(d)
        src_lib = os.path.join(src, "lib")
        if os.path.isdir(src_lib):
            for name in sorted(os.listdir(src_lib)):
                if name.startswith("librustc_driver") and name.endswith(".so"):
                    d = os.path.join(lib_dst, name)
                    if not os.path.isfile(d):
                        shutil.copy2(os.path.join(src_lib, name), d)
                        os.chmod(d, 0o755)
                    with open(d, "rb") as fh:
                        if b"codesign" not in fh.read():
                            to_sign.append(d)

        if to_sign:
            if not signer:
                raise ConanInvalidConfiguration(
                    "toolchain binaries unsigned and binary-sign-tool not found; "
                    "OHOS would refuse to exec cargo/rustc (EACCES)")
            for path in to_sign:
                tmp = path + ".signed"
                result = subprocess.run(
                    [signer, "sign", "-inFile", path, "-outFile", tmp,
                     "-selfSign", "1"],
                    capture_output=True, text=True,
                )
                if result.returncode != 0 or not os.path.isfile(tmp):
                    raise ConanInvalidConfiguration(
                        "binary-sign-tool failed for %s (rc=%d): %s"
                        % (path, result.returncode, result.stderr[:200]))
                os.replace(tmp, path)
                os.chmod(path, 0o755)
                self.output.info("signed toolchain binary: "
                                 + os.path.basename(path))
        else:
            self.output.info("toolchain binaries already signed")

        # 其余只读负载软链（rustc 的 sysroot 即 dst，lib/rustlib 必须可见）。
        # rustlib 例外：`*.so`（libstd 等动态库）必须是**签名副本**——OHOS loader
        # 拒绝加载未签名 .so（官方 dist 的 rustlib 无签名，实测 host 侧 proc-macro
        # 测试 harness 报 "Error loading shared library libstd-*.so"），其余文件软链。
        if os.path.isdir(src_lib):
            for name in sorted(os.listdir(src_lib)):
                if name == "rustlib":
                    continue
                d = os.path.join(lib_dst, name)
                if not os.path.exists(d):
                    os.symlink(os.path.join(src_lib, name), d)
        self._mirror_rustlib(os.path.join(src_lib, "rustlib"),
                             os.path.join(lib_dst, "rustlib"), signer)
        for name in ("etc", "libexec", "share"):
            s = os.path.join(src, name)
            d = os.path.join(dst, name)
            if os.path.isdir(s) and not os.path.exists(d):
                os.symlink(s, d)

        with open(marker, "w", encoding="utf-8") as fh:
            fh.write("signed toolchain prepared\n")
        return bin_dst

    def _mirror_rustlib(self, src, dst, signer):
        """镜像 rustlib：目录建实、非 .so 软链、`*.so` 复制并自签名。

        动态库签名是硬需求：OHOS loader 拒绝加载未签名 .so（loader 报
        "Error loading shared library libstd-*.so"，随后一串 symbol not found）。
        官方 dist 的 rustlib .so 无签名，而 host 侧 proc-macro crate（本工程
        field_derive）的测试 harness 动态链接 libstd —— 不签名则 cargo test
        第一个套件就挂。目标侧产物（bin/wagyu、各 crate 测试 harness）静态链接
        std，NEEDED 只有 libc.so，不受影响。
        """
        if not os.path.isdir(src):
            return
        os.makedirs(dst, exist_ok=True)
        for entry in sorted(os.listdir(src)):
            s = os.path.join(src, entry)
            d = os.path.join(dst, entry)
            if os.path.isdir(s):
                self._mirror_rustlib(s, d, signer)
                continue
            if entry.endswith(".so"):
                if not os.path.isfile(d):
                    shutil.copy2(s, d)
                    os.chmod(d, 0o755)
                with open(d, "rb") as fh:
                    unsigned = b"codesign" not in fh.read()
                if unsigned:
                    if not signer:
                        raise ConanInvalidConfiguration(
                            f"unsigned rustlib dylib and no binary-sign-tool: {entry}")
                    tmp = d + ".signed"
                    result = subprocess.run(
                        [signer, "sign", "-inFile", d,
                         "-outFile", tmp, "-selfSign", "1"],
                        capture_output=True, text=True,
                    )
                    if result.returncode != 0 or not os.path.isfile(tmp):
                        raise ConanInvalidConfiguration(
                            "binary-sign-tool failed for %s (rc=%d): %s"
                            % (entry, result.returncode, result.stderr[:200]))
                    os.replace(tmp, d)
                    os.chmod(d, 0o755)
                    self.output.info("signed rustlib dylib: " + entry)
            elif not os.path.exists(d):
                os.symlink(s, d)

    def _prepare_runtime_libs(self):
        """下载/解包 cargo 运行期共享库（conandata `rust_runtime`），返回 lib 目录。"""
        base = os.path.join(self.build_folder, "rust-runtime")
        os.makedirs(base, exist_ok=True)
        lib_dirs = []
        for item in self.conan_data.get("rust_runtime", []):
            tgz = os.path.join(base, item["name"] + ".tar.gz")
            if not os.path.isfile(tgz):
                download(self, item["url"], tgz, sha256=item["sha256"])
            extract_dir = os.path.join(base, item["name"])
            os.makedirs(extract_dir, exist_ok=True)
            with tarfile.open(tgz, "r:gz") as tf:
                tf.extractall(extract_dir)
            for root, _dirs, files in os.walk(extract_dir):
                if os.path.basename(root) != "lib":
                    continue
                if any(f.startswith(("libssl.", "libcrypto.", "libz."))
                       for f in files):
                    lib_dirs.append(root)
                    self.output.info(f"runtime lib dir: {root}")
        if not lib_dirs:
            self.output.warning("no cargo runtime libs located in bottles")
        return lib_dirs

    def _ohos_cc(self):
        candidates = [
            shutil.which("aarch64-unknown-linux-ohos-clang"),
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/"
            "native/llvm/bin/aarch64-unknown-linux-ohos-clang",
            shutil.which("clang"),
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        raise ConanInvalidConfiguration("OHOS C compiler (clang) not found")

    def _ensure_ohos_target(self, env):
        """校验工具链自带 OHOS 目标标准库（rust-toolchain 包内已装，无需 rustup）。"""
        target = self._ohos_target()
        rustc = os.path.join(os.path.dirname(env["CARGO"]), "rustc")
        if not os.path.isfile(rustc):
            rustc = shutil.which("rustc") or ""
        if not rustc:
            return
        prefix = os.path.dirname(os.path.dirname(rustc))
        rustlib = os.path.join(prefix, "lib", "rustlib", target)
        if not os.path.isdir(rustlib):
            self.output.warning(
                f"rust-std for {target} not found under {rustlib}; "
                "the toolchain may be unable to build for OHOS")

    def _ca_bundle(self):
        candidates = [
            os.environ.get("CURL_CA_BUNDLE"),
            os.environ.get("SSL_CERT_FILE"),
            "/storage/Users/currentUser/usr/local/ssl/cert.pem",
            "/etc/ssl/certs/cacert.pem",
            "/etc/ssl/cert.pem",
            os.path.expanduser("~/.harmonybrew/etc/ca-certificates/cert.pem"),
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

    def _configure_rsproxy(self, cargo_home, ca_bundle=None):
        # cargo 读取 $CARGO_HOME/config.toml；rsproxy 稀疏索引（国内可达实测 200）
        config_path = os.path.join(cargo_home, "config.toml")
        content = (
            "[source.crates-io]\n"
            'replace-with = "rsproxy-sparse"\n\n'
            "[source.rsproxy-sparse]\n"
            'registry = "sparse+https://rsproxy.cn/index/"\n\n'
            "[net]\n"
            "retry = 3\n"
        )
        if ca_bundle:
            content += '\n[http]\ncainfo = "%s"\n' % ca_bundle
        with open(config_path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(content)

    # ── 打包 ────────────────────────────────────────────────────────

    def package(self):
        copy(self, "wagyu",
             src=os.path.join(self.build_folder, "bin"),
             dst=os.path.join(self.package_folder, "bin"),
             keep_path=False)
        for lic in ("LICENSE-MIT", "LICENSE-APACHE"):
            copy(self, lic, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "licenses"),
                 keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
