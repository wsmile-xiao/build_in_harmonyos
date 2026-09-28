#!/usr/bin/env python3
"""Conan recipe for lemmeknow 0.8.0.

lemmeknow is a pure-Rust cybersecurity/forensics CLI that identifies text
patterns (IP, URL, e-mail, API keys, hashes, ...) via ~140 regex rules.
This recipe cross-compiles it for HarmonyOS PC (aarch64-unknown-linux-ohos)
with the Rust toolchain provided by the rust-toolchain/1.97.1 infra package
(tool_requires), falling back to a system cargo/rustc when present.
Crates are fetched through the rsproxy.cn mirror. No rustup bootstrap is
attempted: standard rustup cannot recognize the HarmonyOS host and fails with
"unrecognized OS type: HarmonyOS" (knowledge E105/E154).

OHOS refuses to execute unsigned ELF images, and the rust-lang dist tarball
shipped inside rust-toolchain/1.97.1 carries no code signature, so its
cargo/rustc fail with EACCES (errno 13) — the exact failure observed when
porting below/0.11.0. The recipe therefore copies the executables into the
build folder, signs them with binary-sign-tool -selfSign 1 (and the
librustc_driver dylib that rustc dlopens), and symlinks the read-only
payload. cargo's runtime OpenSSL/zlib shared libraries come from the
Harmonybrew OHOS bottles, since the OHOS loader ignores DT_RUNPATH
(argc/1.24.0 precedent). The device has no default CA store, so the CA
bundle is located and exported for the rsproxy.cn sparse index.

Unlike below, lemmeknow has no C dependencies at all (no libbpf/libelf/zlib
linkage): the whole dependency closure (123 packages) is pure Rust, so no
target libraries are required — only the OHOS SDK clang as the linker.

The upstream test suite (10 tests: 4 CLI integration + 4 identifier + 1
regex-validation + 1 unit test, fully offline) is executed during build()
with `cargo test --release --locked` unless OHC_SKIP_UPSTREAM_TESTS=1 is set.
HarmonyOS /tmp is read-only (knowledge E002), so TMPDIR is pointed at a
writable directory for cargo temp files and the assert_fs temp files used by
tests/cli.rs.
"""
import os
import shlex
import shutil
import subprocess
import tarfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, download, get
from conan.tools.layout import basic_layout

# cargo 运行期依赖的共享库（OHOS loader 忽略 DT_RUNPATH，须显式进
# LD_LIBRARY_PATH）。Harmonybrew 的 OHOS 预编译 bottle 已在制品仓先例
# （argc/1.24.0、bottom/0.12.3、below/0.11.0 等）中用于同一目的；sha256 为实测值。
RUST_RUNTIME_BOTTLES = (
    # 2026-09 探测：bottle 服务器（OBS 源站）已删除 3.6.4/2.3.3_1 旧修订，
    # 仅 CDN 残留缓存可访问（带 query 绕过缓存即 404），官方 CI 无缓存环境
    # 实测 NotFoundException。改用源站仍在线的 bottle 修订（_1/_2 后缀为
    # bottle revision bump，lib 布局不变，sha256 为实测值）。
    ("openssl3",
     "https://harmonybrew.atomgit.com/bottles/"
     "openssl%403-3.6.4_1.arm64_ohos.bottle.tar.gz",
     "29caefb982dc01671e67232f3862b50ce69a34a4f4135a1495078830bb12b81b"),
    ("zlib",
     "https://harmonybrew.atomgit.com/bottles/"
     "zlib-ng-compat-2.3.3_2.arm64_ohos.bottle.tar.gz",
     "99356b80ddb81e0b8267debb44df459f2b5e27e7800406d3b4cf7f8f744beb89"),
)


class LemmeknowConan(ConanFile):
    name = "lemmeknow"
    version = "0.8.0"
    description = ("lemmeknow: identify any mysterious text or analyze "
                   "strings from a file")
    license = "MIT"
    homepage = "https://github.com/swanandx/lemmeknow"
    url = "https://github.com/swanandx/lemmeknow"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")
        self._ohos_target()

    def layout(self):
        basic_layout(self)

    def build_requirements(self):
        # Rust 工具链由制品仓基础设施包提供（R36：依赖先发布再构建下游）：
        # rust-lang 官方 dist 预编译 tarball，宿主与目标均为
        # aarch64-unknown-linux-ohos，可直接在 HarmonyOS 上执行。
        # 不使用 rustup 引导——标准 rustup 无法识别 HarmonyOS 宿主
        # （E105/E154："unrecognized OS type: HarmonyOS"）。
        self.tool_requires("rust-toolchain/1.97.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        env = self._rust_environment()
        self._ensure_ohos_target(env)
        self._run_upstream_tests(env)
        self._cargo_build(env)
        self._sign_binaries()

    # ── build helpers ──────────────────────────────────────────────

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
        cargo = self._find_cargo(env)
        env["CARGO"] = cargo
        # 工具链 bin 目录（cargo/rustc）置于 PATH 首位，确保 cargo 调用同包 rustc
        extra_paths = [os.path.dirname(cargo)]
        extra_paths += [d for d in ("/system/bin", "/system/sbin", "/vendor/bin")
                        if os.path.isdir(d)]
        env["PATH"] = os.pathsep.join(extra_paths) + os.pathsep + env.get("PATH", "")
        # 工具链自带 lib（librustc_driver 等）与 cargo 运行期共享库
        # （libssl/libcrypto/libz）——OHOS loader 忽略 DT_RUNPATH，须显式指定
        lib_dirs = [os.path.join(self._toolchain_dir(), "lib")]
        lib_dirs += self._prepare_runtime_libs()
        if lib_dirs:
            prev = env.get("LD_LIBRARY_PATH", "")
            env["LD_LIBRARY_PATH"] = os.pathsep.join(
                lib_dirs + ([prev] if prev else [])
            )
        # cargo 走 HTTPS（rsproxy.cn）；设备无默认 CA bundle，须显式指定，
        # 否则 sparse 索引拉取报 CERTIFICATE_VERIFY_FAILED / self-signed chain
        ca = self._ca_bundle()
        if ca:
            env["SSL_CERT_FILE"] = ca
            env["CURL_CA_BUNDLE"] = ca
        cargo_home = env.get("CARGO_HOME") or os.path.expanduser("~/.cargo")
        os.makedirs(cargo_home, exist_ok=True)
        self._configure_rsproxy(cargo_home, ca)
        env["CARGO_HOME"] = cargo_home
        # 上游 [profile.release] 开了 lto="thin"；关闭以缩短 CI 构建时间
        # （below/0.11.0 同款处理），opt-level 降为 1 亦为构建提速。
        env["CARGO_PROFILE_RELEASE_LTO"] = "false"
        env["CARGO_PROFILE_RELEASE_OPT_LEVEL"] = "1"
        self._ensure_writable_tmpdir(env)
        if self.settings.os == "OHOS":
            cc = self._ohos_cc()
            env.update({
                "CARGO_TARGET_AARCH64_UNKNOWN_LINUX_OHOS_LINKER": cc,
                "CC_aarch64_unknown_linux_ohos": cc,
                "CXX_aarch64_unknown_linux_ohos": self._ohos_cxx(),
                "AR_aarch64_unknown_linux_ohos": self._llvm_ar(),
                "RANLIB_aarch64_unknown_linux_ohos": self._llvm_ranlib(),
            })
        return env

    def _ensure_writable_tmpdir(self, env):
        """HarmonyOS /tmp 只读（knowledge E002）：cargo/rustc 的临时文件与
        上游 tests/cli.rs 经 assert_fs::NamedTempFile 写的样本文件都需要
        可写 TMPDIR。已有可写 TMPDIR 则不动，否则落到 ~/tmp（below/0.11.0
        同款做法），再不行用 build_folder 兜底。"""
        current = env.get("TMPDIR")
        if current and os.path.isdir(current) and os.access(current, os.W_OK):
            return
        fallback = os.path.expanduser("~/tmp")
        try:
            os.makedirs(fallback, exist_ok=True)
        except OSError:
            fallback = self.build_folder
        env["TMPDIR"] = fallback
        self.output.info(f"TMPDIR set to {fallback} (OHOS /tmp is read-only)")

    def _ohos_cc(self):
        candidates = [
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/aarch64-unknown-linux-ohos-clang",
            shutil.which("aarch64-unknown-linux-ohos-clang"),
        ]
        for c in candidates:
            if c and os.path.isfile(c):
                return c
        raise ConanInvalidConfiguration("aarch64-unknown-linux-ohos-clang not found")

    def _ohos_cxx(self):
        cc = self._ohos_cc()
        return cc + "++" if not cc.endswith("++") else cc

    def _llvm_ar(self):
        d = os.path.dirname(self._ohos_cc())
        return os.path.join(d, "llvm-ar")

    def _llvm_ranlib(self):
        d = os.path.dirname(self._ohos_cc())
        return os.path.join(d, "llvm-ranlib")

    def _ensure_ohos_target(self, env):
        """校验工具链自带 OHOS 目标标准库（rust-toolchain 包内已装，无需 rustup）。

        不使用 `rustup target add`：标准 rustup 无法识别 HarmonyOS 宿主
        （E105/E154），工具链改由 rust-toolchain/1.97.1 提供。
        """
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
                "the toolchain may be unable to build for OHOS"
            )

    def _run_upstream_tests(self, env):
        """运行上游测试套件（cargo test --release --locked --tests）。

        lemmeknow 上游共 10 个测试（tests/cli.rs 4 个 assert_cmd 集成测试、
        tests/identifier_check.rs 4 个、tests/validate_regexes.rs 1 个、
        src/lib.rs 单元测试 1 个），全部离线、无环境依赖，失败即阻断打包。
        `--tests` 覆盖上述全部 10 个测试目标；doc-test 除外——rust-toolchain/
        1.97.1 包内不含 rustdoc（基础设施包不带该二进制），且上游仅有的 2 个
        rust doc-example 与 tests/identifier_check.rs 覆盖面重复
        （to_json 序列化路径）。OHC_SKIP_UPSTREAM_TESTS=1 仅作为 CI 例外通道。
        """
        if os.environ.get("OHC_SKIP_UPSTREAM_TESTS") == "1":
            self.output.info(
                "Skipping upstream cargo test (OHC_SKIP_UPSTREAM_TESTS=1); "
                "suite validated in Step 2 (see notes.md)."
            )
            return
        target = self._ohos_target()
        cmd = [env["CARGO"], "test", "--release", "--locked",
               "--target", target, "--tests"]
        self.output.info("Running upstream tests: %s" % " ".join(cmd))
        result = subprocess.run(cmd, cwd=self.source_folder, env=env).returncode
        if result != 0:
            raise ConanInvalidConfiguration(
                f"Upstream lemmeknow tests failed for {target} (rc={result})"
            )

    def _cargo_build(self, env):
        target = self._ohos_target()
        cmd = [env["CARGO"], "build", "--release", "--locked",
               "--target", target]
        result = subprocess.run(cmd, cwd=self.source_folder, env=env).returncode
        if result != 0:
            raise ConanInvalidConfiguration(
                f"cargo build failed for {target} (rc={result})"
            )
        out_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(out_dir, exist_ok=True)
        release_dir = os.path.join(self.source_folder, "target", target, "release")
        src = os.path.join(release_dir, "lemmeknow")
        if os.path.isfile(src):
            dst = os.path.join(out_dir, "lemmeknow")
            shutil.copy2(src, dst)
            os.chmod(dst, 0o755)
        else:
            raise ConanInvalidConfiguration(
                f"lemmeknow binary not produced: {src}"
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

    def _find_binary_sign_tool(self):
        """Locate the OHOS binary signing tool if present."""
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

    # ── toolchain discovery / bootstrap ─────────────────────────────

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
        # rust-toolchain/1.97.1 基础设施包（tool_requires）：rust-lang 官方
        # dist 预编译，宿主与目标均为 aarch64-unknown-linux-ohos。
        # 包内二进制无 code signature，OHOS 拒绝执行（EACCES），
        # 故在 build_folder 内准备签名副本后使用。
        bin_dir = self._prepare_signed_toolchain()
        candidate = os.path.join(bin_dir, "cargo")
        if os.path.isfile(candidate):
            return candidate
        raise ConanInvalidConfiguration(
            "Rust/Cargo toolchain not found: no system cargo and no "
            "rust-toolchain/1.97.1 tool_requires package available"
        )

    def _rust_toolchain_dep(self):
        """返回 rust-toolchain tool_requires 依赖（不存在时 None）。"""
        try:
            return self.dependencies.build.get("rust-toolchain")
        except (KeyError, ConanInvalidConfiguration):
            return None

    def _toolchain_dir(self):
        return os.path.join(self.build_folder, "rust-toolchain")

    def _prepare_signed_toolchain(self):
        """准备可执行的 Rust 工具链，返回其 bin 目录。

        rust-toolchain/1.97.1 包内是 rust-lang 官方 dist tarball，二进制不带
        code signature；HarmonyOS 拒绝 execve 未签名 ELF（PermissionError
        errno 13，below/0.11.0 CI 实测）。故把必须执行的 cargo/rustc 以及
        rustc dlopen 的 librustc_driver 复制到 build_folder 并用
        binary-sign-tool 自签名，其余只读负载（rustlib/、proc-macro dylib
        等 ~500MB）用软链避免复制。

        已签名则幂等跳过（marker 文件），重复构建不再签名。
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

        # 必须执行的二进制 + rustc dlopen 的 dylib：复制并签名
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
                self.output.info("signed toolchain binary: %s"
                                 % os.path.basename(path))
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

    def _prepare_runtime_libs(self):
        """下载并解包 cargo 运行期依赖的共享库，返回 lib 目录列表。

        cargo 动态链接 libssl/libcrypto/libz（DT_NEEDED），而 OHOS loader
        忽略 DT_RUNPATH，必须显式放进 LD_LIBRARY_PATH。系统 /usr/lib 的
        OpenSSL 3.0 缺 SSL_get0_group_name（cargo 1.97 需要 3.5+），故用
        Harmonybrew 的 OHOS 预编译 bottle（argc/1.24.0 先例），sha256 校验。
        """
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
                tf.extractall(extract_dir)
            for root, _dirs, files in os.walk(extract_dir):
                if os.path.basename(root) != "lib":
                    continue
                if any(f.startswith(("libssl.", "libcrypto.", "libz."))
                       for f in files):
                    lib_dirs.append(root)
        return lib_dirs

    def _ca_bundle(self):
        """返回设备上可用的 CA bundle 路径（无则 None）。

        OHOS 设备无默认 CA store，cargo 拉 sparse 索引会报
        CERTIFICATE_VERIFY_FAILED / self-signed certificate in chain。
        """
        candidates = [
            os.environ.get("CURL_CA_BUNDLE"),
            os.environ.get("SSL_CERT_FILE"),
            "/storage/Users/currentUser/usr/local/ssl/cert.pem",
            "/etc/ssl/certs/cacert.pem",
            "/etc/ssl/cert.pem",
            os.path.expanduser(
                "~/.harmonybrew/etc/ca-certificates/cert.pem"),
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

    def _configure_rsproxy(self, cargo_home, ca_bundle=None):
        # cargo 读取的是 $CARGO_HOME/config.toml（不是 config/config.toml）
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
            content += ("\n[http]\n"
                        "cainfo = \"%s\"\n" % ca_bundle)
        with open(config_path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(content)

    def package(self):
        # keep_path=False：copy 默认保留匹配路径，会得到 pkg/bin/bin/lemmeknow
        copy(self, "lemmeknow", src=os.path.join(self.build_folder, "bin"),
             dst=os.path.join(self.package_folder, "bin"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
