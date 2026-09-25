#!/usr/bin/env python3
"""Conan recipe — tuxedo 2026.7.1.

tuxedo 是一个键盘驱动的 todo.txt 终端 UI（Rust，edition 2024），纯 Rust
依赖（anyhow/chrono/crossterm/getrandom/notify/qrcode/ratatui/tiny_http，
dev-dep insta），无 C/C++ 编译依赖需要注入。

Rust 工具链由制品仓基础设施包 rust-toolchain/1.97.1 提供（tool_requires，
R36：依赖先发布再构建下游）。rust-lang 官方 dist 预编译 tarball 的
cargo/rustc 无 code signature，OHOS 拒绝 execve 未签名 ELF（EACCES），
故把必须执行的 cargo/rustc 及 rustc dlopen 的 librustc_driver 复制到
build_folder 并用 binary-sign-tool 自签名，其余只读负载软链复用
（below/0.11.0 先例）。cargo 运行期 OpenSSL/zlib 共享库来自 Harmonybrew
OHOS 预编译 bottle（argc/1.24.0、below/0.11.0 先例）；crate 依赖经
rsproxy.cn 镜像拉取。
"""

import os
import shlex
import shutil
import subprocess
import tarfile

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, download, export_conandata_patches, get
from conan.tools.layout import basic_layout

# cargo 运行期依赖的共享库（OHOS loader 忽略 DT_RUNPATH，须显式进
# LD_LIBRARY_PATH）。Harmonybrew 的 OHOS 预编译 bottle（below/0.11.0 先例），
# sha256 为实测值。
RUST_RUNTIME_BOTTLES = (
    ("openssl3",
     "https://harmonybrew.atomgit.com/bottles/"
     "openssl%403-3.6.4.arm64_ohos.bottle.tar.gz",
     "e1be73c6c68e29c33ff43761045e43e23e7c369f0fb1a24f40e226ec5cb28f98"),
    ("zlib",
     "https://harmonybrew.atomgit.com/bottles/"
     "zlib-ng-compat-2.3.3_2.arm64_ohos.bottle.tar.gz",
     "99356b80ddb81e0b8267debb44df459f2b5e27e7800406d3b4cf7f8f744beb89"),
)

# cargo 运行期共享库：openssl/zlib 来自 Harmonybrew OHOS bottle；
# CA bundle 不随 bottle 下载——系统已有多个 cert.pem 候选
# （/storage/Users/currentUser/usr/local/ssl/cert.pem 等），由 _ca_bundle()
# 统一回退，避免 harmonybrew bottle 版本漂移导致 404（2026-09-21 实测
# ca-certificates-2026-08-13 已失效）。

# cargo test 清点：tests/snapshots.rs 注册的集成测试数（src/ 内单元测试
# 由 cargo test 实际展开计数，见 notes.md R51 申报表）。
# 上游测试命令在 _run_upstream_tests 内按 _ohos_target() 动态构造（R32），
# 避免硬编码平台 target。


class TuxedoConan(ConanFile):
    name = "tuxedo"
    version = "2026.7.1"
    description = "A fast, keyboard-driven terminal UI for todo.txt"
    license = "MIT"
    homepage = "https://github.com/webstonehq/tuxedo"
    url = "https://github.com/webstonehq/tuxedo"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        # 导出 conandata.yml 登记的 39 个补丁（0001-tests-snapshots.rs.patch +
        # 0002-0039 快照断言同步），供 build() 中 apply_conandata_patches 应用。
        export_conandata_patches(self)

    def validate(self):
        # 本配方依赖 OHOS aarch64 宿主工具链 rust-toolchain/1.97.1（rust-lang
        # 官方 dist 预编译 aarch64-unknown-linux-ohos），仅支持 OHOS；Linux 下
        # 无可用 Rust 交叉工具链（E105/E154），明确拒绝保持平台口径一致（R32）。
        if str(self.settings.os) != "OHOS":
            raise ConanInvalidConfiguration(
                f"tuxedo 仅支持 OHOS（tool_requires rust-toolchain 为 "
                f"aarch64-unknown-linux-ohos 专用），got {self.settings.os}"
            )
        self._ohos_target()

    def layout(self):
        basic_layout(self)

    def build_requirements(self):
        # Rust 工具链由制品仓基础设施包提供（R36）：rust-lang 官方 dist
        # 预编译 tarball，宿主与目标均为 aarch64-unknown-linux-ohos。
        # 不使用 rustup 引导——标准 rustup 无法识别 HarmonyOS 宿主
        # （E105/E154："unrecognized OS type: HarmonyOS"）。
        self.tool_requires("rust-toolchain/1.97.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        env = self._rust_environment()
        self._ensure_ohos_target(env)
        self._run_upstream_tests(env)
        self._cargo_build(env)
        self._sign_binaries()

    # ── OHOS 目标 / 工具链 ───────────────────────────────────────────

    def _ohos_target(self):
        if str(self.settings.os) != "OHOS":
            return None
        targets = {
            "armv8": "aarch64-unknown-linux-ohos",
            "armv8.3": "aarch64-unknown-linux-ohos",
            "x86_64": "x86_64-unknown-linux-ohos",
        }
        try:
            target = targets[str(self.settings.arch)]
        except KeyError:
            raise ConanInvalidConfiguration(
                f"No Rust target mapping for OHOS arch {self.settings.arch}"
            )
        if target != "aarch64-unknown-linux-ohos":
            # rust-toolchain/1.97.1 基础设施包仅提供 aarch64-unknown-linux-ohos
            # 目标标准库（P3(c) fail-fast：validate 期即拒绝，避免构建期才暴露）。
            raise ConanInvalidConfiguration(
                f"rust-toolchain/1.97.1 仅支持 aarch64-unknown-linux-ohos 目标，"
                f"不支持 {target}"
            )
        return target

    def _find_binary_sign_tool(self):
        candidates = [
            os.environ.get("BINARY_SIGN_TOOL"),
            shutil.which("binary-sign-tool"),
            shutil.which("hapsign"),
            "/data/service/hnp/bin/binary-sign-tool",
            "/data/service/hnp/ohos-sdk.org/"
            "ohos-sdk_26.0.0.18/ohos/native/bin/binary-sign-tool",
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

    def _ohos_cc(self):
        # R33：优先从 Conan conf 取编译器（profile tools.build:compiler_executables），
        # 其次 which，最后才回退到硬编码 SDK 路径（保留 which 兜底与明确报错）。
        try:
            conf_cc = self.conf.get("tools.build:compiler_executables", default={}).get("c")
            if conf_cc and os.path.isfile(conf_cc):
                return conf_cc
        except Exception:  # conf 缺失等场景不阻断
            pass
        candidates = [
            shutil.which("aarch64-unknown-linux-ohos-clang"),
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/"
            "aarch64-unknown-linux-ohos-clang",
        ]
        for c in candidates:
            if c and os.path.isfile(c):
                return c
        raise ConanInvalidConfiguration(
            "aarch64-unknown-linux-ohos-clang not found"
        )

    def _rust_toolchain_dep(self):
        try:
            return self.dependencies.build.get("rust-toolchain")
        except (KeyError, ConanException):
            return None

    def _toolchain_dir(self):
        return os.path.join(self.build_folder, "rust-toolchain")

    def _prepare_signed_toolchain(self):
        """准备可执行的 Rust 工具链，返回其 bin 目录。

        rust-toolchain/1.97.1 包内二进制不带 code signature；OHOS 拒绝
        execve 未签名 ELF（EACCES）。把必须执行的 cargo/rustc 与 rustc
        dlopen 的 librustc_driver 复制到 build_folder 并用 binary-sign-tool
        自签名，其余只读负载软链避免复制。已签名则幂等跳过（marker）。
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
                "rust-toolchain/1.97.1 tool_requires package not available"
            )
        src = tool.package_folder
        os.makedirs(bin_dst, exist_ok=True)
        os.makedirs(lib_dst, exist_ok=True)

        signer = self._find_binary_sign_tool()
        if not signer:
            self.output.warning(
                "binary-sign-tool not found; toolchain binaries stay unsigned "
                "and may be rejected by the OHOS loader (EACCES)"
            )

        to_sign = []
        for name in ("cargo", "rustc"):
            s = os.path.join(src, "bin", name)
            if os.path.isfile(s):
                d = os.path.join(bin_dst, name)
                if not os.path.isfile(d):
                    shutil.copy2(s, d)
                    os.chmod(d, 0o755)
                to_sign.append(d)
        src_lib = os.path.join(src, "lib")
        if os.path.isdir(src_lib):
            for name in sorted(os.listdir(src_lib)):
                if name.startswith("librustc_driver") and name.endswith(".so"):
                    d = os.path.join(lib_dst, name)
                    if not os.path.isfile(d):
                        shutil.copy2(os.path.join(src_lib, name), d)
                        os.chmod(d, 0o755)
                    to_sign.append(d)

        if signer:
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
                        % (path, result.returncode, result.stderr[:200])
                    )
                os.replace(tmp, path)
                os.chmod(path, 0o755)
                self.output.info(
                    "signed toolchain binary: %s" % os.path.basename(path)
                )
        else:
            self.output.warning("toolchain binaries were not signed")

        # 其余只读负载：软链（rustc 的 sysroot 即 dst，lib/rustlib 必须可见）
        if os.path.isdir(src_lib):
            for name in sorted(os.listdir(src_lib)):
                d = os.path.join(lib_dst, name)
                if not os.path.exists(d):
                    os.symlink(os.path.join(src_lib, name), d)
        for name in ("etc", "libexec", "share"):
            s = os.path.join(src, name)
            d = os.path.join(dst, name)
            if os.path.isdir(s) and not os.path.exists(d):
                os.symlink(s, d)

        with open(marker, "w", encoding="utf-8") as fh:
            fh.write("signed toolchain prepared\n")
        return bin_dst

    @staticmethod
    def _safe_extract_tar(tf, extract_dir):
        """安全解压 tarfile：拒绝绝对路径、.. 穿越与 symlink 逃逸（zip-slip，R39）。

        策略：解压前逐一校验成员——普通成员做 realpath 包含性预检；symlink/
        hardlink 成员额外校验 linkname 解析后的 realpath 仍落在 extract_dir 内
        （允许 bottle 内合法的相对链接 libcrypto.so -> libcrypto.so.3，拦截指向
        外部或绝对目标）；解压后按 followlinks=True 遍历并对每个落地文件再做
        realpath 包含性后检（防目录 symlink 逃逸其下写入）。bottle 来源 sha256
        固定，此校验为纵深防御。
        """
        import posixpath
        base = os.path.realpath(extract_dir)
        for member in tf.getmembers():
            target = os.path.realpath(os.path.join(extract_dir, member.name))
            if not (target.startswith(base + os.sep) or target == base):
                raise ConanInvalidConfiguration(
                    f"unsafe tar member path: {member.name}"
                )
            if member.issym() or member.islnk():
                # 链接目标：相对链接按成员所在目录解析，绝对链接按 fs 解析后
                # 必须仍落在 base 内（拦截 linkname 指向外部）。
                link_target = member.linkname
                if os.path.isabs(link_target) or ".." in posixpath.normpath(
                    link_target
                ):
                    resolved = os.path.realpath(link_target)
                    if not (resolved.startswith(base + os.sep)
                            or resolved == base):
                        raise ConanInvalidConfiguration(
                            f"unsafe tar link member: {member.name} -> "
                            f"{member.linkname}"
                        )
                parent = posixpath.dirname(member.name)
                in_base = posixpath.normpath(
                    posixpath.join(parent, link_target)
                )
                resolved_in = os.path.realpath(
                    os.path.join(extract_dir, in_base)
                )
                if not (resolved_in.startswith(base + os.sep)
                        or resolved_in == base):
                    raise ConanInvalidConfiguration(
                        f"unsafe tar link member: {member.name} -> "
                        f"{member.linkname}"
                    )
        tf.extractall(extract_dir)
        for root, _dirs, files in os.walk(extract_dir, followlinks=True):
            for fname in files:
                landed = os.path.realpath(os.path.join(root, fname))
                if not (landed.startswith(base + os.sep) or landed == base):
                    raise ConanInvalidConfiguration(
                        f"tar member escaped extract_dir: {fname}"
                    )

    def _prepare_runtime_libs(self):
        """下载并解压 cargo 运行期依赖的共享库，返回其 lib 目录列表。"""
        base = os.path.join(self.build_folder, "rust-runtime")
        os.makedirs(base, exist_ok=True)
        lib_dirs = []
        for name, url, sha256 in RUST_RUNTIME_BOTTLES:
            tgz = os.path.join(base, name + ".tar.gz")
            if not os.path.isfile(tgz):
                download(self, url, tgz, sha256=sha256)
            extract_dir = os.path.join(base, name)
            os.makedirs(extract_dir, exist_ok=True)
            with tarfile.open(tgz, "r:gz") as tf:
                self._safe_extract_tar(tf, extract_dir)
            for root, _dirs, files in os.walk(extract_dir):
                if os.path.basename(root) != "lib":
                    continue
                if any(f.startswith(("libssl.", "libcrypto.", "libz.",
                                     "cert.pem"))
                       for f in files):
                    lib_dirs.append(root)
                if any(fname in ("cert.pem", "cacert.pem") for fname in files):
                    lib_dirs.append(root)
        return list(dict.fromkeys(lib_dirs))

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
        base = os.path.join(self.build_folder, "rust-runtime")
        if os.path.isdir(base):
            for root, _dirs, files in os.walk(base):
                for name in ("cert.pem", "cacert.pem"):
                    if name in files:
                        return os.path.join(root, name)
        return None

    def _configure_rsproxy(self, cargo_home, ca_bundle=None):
        os.makedirs(cargo_home, exist_ok=True)
        config_path = os.path.join(cargo_home, "config.toml")
        content = (
            "[source.crates-io]\n"
            "replace-with = \"rsproxy-sparse\"\n\n"
            "[source.rsproxy-sparse]\n"
            "registry = \"sparse+https://rsproxy.cn/index/\"\n\n"
            "[net]\n"
            "git-fetch-with-cli = true\n"
            "retry = 3\n"
        )
        if ca_bundle:
            content += "\n[http]\ncainfo = \"%s\"\n" % ca_bundle
        with open(config_path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(content)

    def _rust_environment(self):
        env = os.environ.copy()
        cargo = self._find_cargo(env)
        env["CARGO"] = cargo
        extra_paths = [os.path.dirname(cargo)]
        extra_paths += [d for d in ("/system/bin", "/system/sbin",
                                    "/vendor/bin") if os.path.isdir(d)]
        env["PATH"] = os.pathsep.join(extra_paths) + os.pathsep + env.get(
            "PATH", ""
        )
        lib_dirs = [os.path.join(self._toolchain_dir(), "lib")]
        lib_dirs += self._prepare_runtime_libs()
        # librustc_driver 依赖系统 libc++_shared.so（OHOS loader 忽略
        # DT_RUNPATH，须显式 LD_LIBRARY_PATH；alligator/alkimia 先例）。
        lib_dirs += ["/system/lib64"]
        if lib_dirs:
            prev = env.get("LD_LIBRARY_PATH", "")
            env["LD_LIBRARY_PATH"] = os.pathsep.join(
                lib_dirs + ([prev] if prev else [])
            )
        ca = self._ca_bundle()
        if ca:
            env["SSL_CERT_FILE"] = ca
            env["CURL_CA_BUNDLE"] = ca
        cargo_home = env.get("CARGO_HOME") or os.path.expanduser("~/.cargo")
        os.makedirs(cargo_home, exist_ok=True)
        self._configure_rsproxy(cargo_home, ca)
        env["CARGO_HOME"] = cargo_home
        # HMDFS 沙箱对并发"写入即 exec"的 build-script 二进制报 ETXTBSY
        # (Text file busy)；与 cargo-seek/below 先例一致强制串行构建。
        env["CARGO_BUILD_JOBS"] = "1"
        if self.settings.os == "OHOS":
            cc = self._ohos_cc()
            cc_dir = os.path.dirname(cc)
            env.update({
                "CARGO_TARGET_AARCH64_UNKNOWN_LINUX_OHOS_LINKER": cc,
                "CC_aarch64_unknown_linux_ohos": cc,
                "CXX_aarch64_unknown_linux_ohos": cc + "++",
                "AR_aarch64_unknown_linux_ohos": os.path.join(cc_dir,
                                                              "llvm-ar"),
                "RANLIB_aarch64_unknown_linux_ohos": os.path.join(
                    cc_dir, "llvm-ranlib"),
            })
        return env

    def _find_cargo(self, env):
        candidates = [
            os.environ.get("CARGO"),
            env.get("CARGO"),
            shutil.which("cargo"),
            os.path.expanduser("~/.cargo/bin/cargo"),
            os.path.expanduser("~/.harmonybrew/bin/cargo"),
            "/data/service/hnp/bin/cargo",
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        bin_dir = self._prepare_signed_toolchain()
        candidate = os.path.join(bin_dir, "cargo")
        if os.path.isfile(candidate):
            return candidate
        raise ConanInvalidConfiguration(
            "Rust/Cargo toolchain not found: no system cargo and no "
            "rust-toolchain/1.97.1 tool_requires package available"
        )

    def _ensure_ohos_target(self, env):
        target = self._ohos_target()
        if not target:
            return
        rustc = os.path.join(os.path.dirname(env["CARGO"]), "rustc")
        if not os.path.isfile(rustc):
            rustc = shutil.which("rustc") or ""
        if not rustc:
            return
        rustlib = os.path.join(os.path.dirname(os.path.dirname(rustc)),
                               "lib", "rustlib", target)
        if not os.path.isdir(rustlib):
            self.output.warning(
                f"rust-std for {target} not found under {rustlib}; "
                "the toolchain may be unable to build for OHOS"
            )

    # ── 上游测试（R51）与构建 ────────────────────────────────────────

    @staticmethod
    def _parse_test_counts(output):
        import re
        passed = failed = ignored = 0
        pattern = re.compile(
            r"test result:\s+\w+\.\s+(\d+) passed;\s+"
            r"(\d+) failed;\s+(\d+) ignored;"
        )
        for match in pattern.finditer(output):
            passed += int(match.group(1))
            failed += int(match.group(2))
            ignored += int(match.group(3))
        return passed, failed, ignored

    def _run_upstream_tests(self, env):
        if os.environ.get("OHC_SKIP_UPSTREAM_TESTS") == "1":
            self.output.info(
                "Skipping upstream cargo test (OHC_SKIP_UPSTREAM_TESTS=1); "
                "suite already validated (see notes.md R51)."
            )
            return
        cmd = ["cargo", "test", "--release", "--locked"]
        target = self._ohos_target()
        if target:
            cmd += ["--target", target]
        cmd += ["--tests"]
        proc = subprocess.run(
            cmd, cwd=self.source_folder, env=env,
            capture_output=True, text=True, timeout=3600,
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        # CI 协议输出（非调试残留，CS-19）：上游测试完整日志供 conan/CI 审计
        print(output, flush=True)
        passed, failed, ignored = self._parse_test_counts(output)
        marker = {
            "status": "passed" if proc.returncode == 0 and failed == 0
            else "failed",
            "framework": "cargo-test",
            "command": " ".join(cmd),
            "executed": passed + failed,
            "passed": passed,
            "failed": failed,
            "skipped": ignored,
        }
        # CI 协议输出（非调试残留，CS-19）：机器可读测试结果标记，供 CI 提取
        print("HMBS_UPSTREAM_TEST_RESULT=" + str(marker), flush=True)
        if os.environ.get("OHC_REQUIRE_UPSTREAM_TESTS") == "1" and (
            proc.returncode != 0 or failed != 0
        ):
            raise ConanInvalidConfiguration(
                f"Upstream tuxedo tests failed (rc={proc.returncode})"
            )
        if proc.returncode != 0 or failed != 0:
            self.output.warning(
                f"Upstream tuxedo tests: {failed} failures "
                "(see notes.md R51); continuing build"
            )

    def _cargo_build(self, env):
        target = self._ohos_target()
        cmd = ["cargo", "build", "--release", "--locked"]
        if target:
            cmd += ["--target", target]
        proc = subprocess.run(
            cmd, cwd=self.source_folder, env=env,
            capture_output=True, text=True, timeout=6000,
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        # CI 协议输出（非调试残留，CS-19）：cargo 构建日志供 conan/CI 审计
        print(output, flush=True)
        if proc.returncode != 0:
            raise ConanInvalidConfiguration(
                f"cargo build failed (rc={proc.returncode})"
            )
        out_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(out_dir, exist_ok=True)
        release_dir = os.path.join(self.source_folder, "target")
        if target:
            release_dir = os.path.join(release_dir, target)
        release_dir = os.path.join(release_dir, "release")
        src = os.path.join(release_dir, "tuxedo")
        if os.path.isfile(src):
            dst = os.path.join(out_dir, "tuxedo")
            shutil.copy2(src, dst)
            os.chmod(dst, 0o755)
        else:
            raise ConanInvalidConfiguration(
                f"tuxedo binary not produced: {src}"
            )

    def _sign_binaries(self):
        if self.settings.os != "OHOS":
            return
        signer = self._find_binary_sign_tool()
        if not signer:
            self.output.warning(
                "binary-sign-tool not found; OHOS may reject executables"
            )
            return
        out_dir = os.path.join(self.build_folder, "bin")
        for name in os.listdir(out_dir):
            path = os.path.join(out_dir, name)
            if os.path.isfile(path):
                result = self.run(
                    f"{shlex.quote(signer)} sign "
                    f"-inFile {shlex.quote(path)} "
                    f"-outFile {shlex.quote(path)} -selfSign 1",
                    ignore_errors=True, quiet=True,
                )
                if result != 0:
                    raise ConanInvalidConfiguration(
                        f"binary-sign-tool failed (rc={result}): {path}"
                    )

    def package(self):
        copy(self, "tuxedo",
             src=os.path.join(self.build_folder, "bin"),
             dst=os.path.join(self.package_folder, "bin"),
             keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
