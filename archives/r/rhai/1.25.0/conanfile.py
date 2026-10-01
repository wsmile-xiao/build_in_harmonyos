#!/usr/bin/env python3
"""Conan 2.x recipe for rhai 1.25.0 on Linux and HarmonyOS.

rhai is a pure-Rust embedded scripting engine. Upstream is a Cargo workspace
(members: `.`, `codegen`, `codegen/tests/custom_root`) that builds a library
plus three optional CLI binaries. This recipe cross-compiles the CLI for
HarmonyOS PC (aarch64-unknown-linux-ohos) with the Rust toolchain provided by
the rust-toolchain/1.97.1 infrastructure package (tool_requires). No rustup
bootstrap is attempted: standard rustup cannot recognize the HarmonyOS host
and fails with "unrecognized OS type: HarmonyOS" (knowledge E105/E154).

The whole dependency closure is pure Rust (no `-sys` crate, no external
C/C++ library), so only the OHOS SDK clang is needed as the linker.

HarmonyOS specifics handled here (all verified on device, see notes.md):

1. Unsigned ELF cannot be executed (EACCES/errno 13). The rust-lang dist
   tarball inside rust-toolchain/1.97.1 carries no code signature, so cargo,
   rustc and the librustc_driver dylib that rustc dlopens are copied into the
   build folder and signed with `binary-sign-tool -selfSign 1`. The signer's
   output loses the executable bit, so +x is re-applied afterwards.

2. `rustlib/` must be a *real* directory, not a symlink. rustc silently fails
   to find `core`/`std` when the sysroot's `lib/rustlib` is a symlink
   ("can't find crate for `std`" — misleading rustup hint). The host==target
   standard library is therefore copied physically (bin/ and analysis/ are
   skipped to keep the copy small).

3. cargo links libssl.so/libcrypto.so/libz.so at runtime; the OHOS loader
   ignores DT_RUNPATH and — unlike glibc — does not resolve symlinked
   DT_NEEDED entries, so real files for every needed SONAME are installed from
   Harmonybrew OHOS bottles (libssl.so, libssl.so.3, libcrypto.so,
   libcrypto.so.3, libz.so, libz.so.1).

4. The OHOS SDK clang wrapper (a shell script using readlink/dirname) needs
   /usr/bin on PATH; /tmp is read-only (E002) so a writable TMPDIR is used.

5. The upstream `[patch.crates-io]` redirects rustyline to a third-party git
   fork; it is dropped (patches/0001) because git deps are not reproducible
   and the fork only matters for the optional rhai-repl (bin-features) which
   this recipe does not build.

The upstream test suite is executed during build() with
`cargo test --release --tests --features testing-environ,decimal,serde,metadata,internals,debugging`
unless OHC_SKIP_UPSTREAM_TESTS=1 is set.
"""
import os
import shlex
import shutil
import subprocess
import tarfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy, download,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout

# 上游 CI 使用的 feature 子集（覆盖 tests/ 下绝大多数用例）
TEST_FEATURES = ("testing-environ,decimal,serde,metadata,internals,debugging")
# 打包产物：rhai-run（默认）+ rhai-dbg（debugging）；rhai-repl 需 bin-features/rustyline，不构建
BUILD_FEATURES = "debugging"


class RhaiConan(ConanFile):
    name = "rhai"
    version = "1.25.0"
    description = ("rhai: an embedded scripting language and engine for Rust "
                   "(CLI: rhai-run, rhai-dbg)")
    license = "MIT OR Apache-2.0"
    homepage = "https://rhai.rs"
    url = "https://github.com/rhaiscript/rhai"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("rhai for OHOS currently supports armv8 only")
        self._ohos_target()

    def build_requirements(self):
        # Rust 工具链由制品仓基础设施包提供（R36：依赖先发布再构建下游）
        self.tool_requires("rust-toolchain/1.97.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ── target / toolchain helpers ─────────────────────────────────

    def _ohos_target(self):
        mapping = {
            "armv8": "aarch64-unknown-linux-ohos",
            "arm64": "aarch64-unknown-linux-ohos",
            "aarch64": "aarch64-unknown-linux-ohos",
            "armv7": "armv7-unknown-linux-ohos",
            "x86_64": "x86_64-unknown-linux-ohos",
        }
        target = mapping.get(str(self.settings.arch))
        if not target:
            raise ConanInvalidConfiguration(f"Unsupported arch: {self.settings.arch}")
        return target

    def _toolchain_dir(self):
        return os.path.join(self.build_folder, "rust-toolchain")

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

    def _sign(self, paths, keep_exec=True):
        """就地签名（binary-sign-tool -selfSign 1）。

        签名输出会丢失可执行位，keep_exec 时重新 chmod +x —— 否则 OHOS
        loader 以 EACCES 拒绝（实测：仅签名不 chmod 仍 permission denied）。
        """
        signer = self._find_binary_sign_tool()
        if not signer:
            self.output.warning("binary-sign-tool not found; OHOS may reject ELF")
            return
        for path in paths:
            tmp = path + ".signed"
            result = subprocess.run(
                [signer, "sign", "-inFile", path, "-outFile", tmp, "-selfSign", "1"],
                capture_output=True, text=True,
            )
            if result.returncode != 0 or not os.path.isfile(tmp):
                raise ConanInvalidConfiguration(
                    "binary-sign-tool failed for %s (rc=%d): %s"
                    % (path, result.returncode, result.stderr[:200])
                )
            os.replace(tmp, path)
            if keep_exec:
                os.chmod(path, 0o755)

    def _toolchain_package_folder(self):
        try:
            return self.dependencies.build["rust-toolchain"].package_folder
        except Exception:
            return None

    def _prepare_signed_toolchain(self):
        """把 rust-toolchain 包整理成可用 sysroot，返回其 bin 目录。

        - bin/cargo、bin/rustc：复制 + 签名 + chmod +x
        - lib/librustc_driver-*.so：rustc dlopen，复制 + 签名
        - lib/rustlib/<target>/{lib,etc}：**真实复制**（软链会导致 rustc 找不到 std）
        marker 幂等：重复构建不再处理。
        """
        dst = self._toolchain_dir()
        bin_dst = os.path.join(dst, "bin")
        lib_dst = os.path.join(dst, "lib")
        marker = os.path.join(dst, ".prepared")
        if os.path.isfile(marker):
            return bin_dst
        src = self._toolchain_package_folder()
        if not src:
            raise ConanInvalidConfiguration(
                "rust-toolchain/1.97.1 tool_requires package not available"
            )
        os.makedirs(bin_dst, exist_ok=True)
        os.makedirs(lib_dst, exist_ok=True)

        executables = []
        for name in ("cargo", "rustc"):
            s = os.path.join(src, "bin", name)
            if os.path.isfile(s):
                d = os.path.join(bin_dst, name)
                shutil.copy2(s, d)
                os.chmod(d, 0o755)
                executables.append(d)
        src_lib = os.path.join(src, "lib")
        if os.path.isdir(src_lib):
            for name in sorted(os.listdir(src_lib)):
                if name.startswith("librustc_driver") and name.endswith(".so"):
                    d = os.path.join(lib_dst, name)
                    shutil.copy2(os.path.join(src_lib, name), d)
                    os.chmod(d, 0o755)
                    executables.append(d)
        self._sign(executables, keep_exec=True)

        # 真实复制 rustlib（bin/ 与 analysis/ 跳过：链接用 OHOS SDK clang）
        target = self._ohos_target()
        src_rustlib = os.path.join(src_lib, "rustlib")
        dst_rustlib = os.path.join(lib_dst, "rustlib")
        for sub in ("etc",):
            s = os.path.join(src_rustlib, sub)
            if os.path.isdir(s):
                shutil.copytree(s, os.path.join(dst_rustlib, sub), dirs_exist_ok=True)
        s_target = os.path.join(src_rustlib, target)
        d_target = os.path.join(dst_rustlib, target)
        for sub in ("lib",):
            s = os.path.join(s_target, sub)
            if os.path.isdir(s):
                shutil.copytree(s, os.path.join(d_target, sub), dirs_exist_ok=True)

        with open(marker, "w", encoding="utf-8") as fh:
            fh.write("signed toolchain + real rustlib prepared\n")
        return bin_dst

    def _prepare_runtime_libs(self):
        """下载 harmonybrew OHOS bottle，安装 cargo 运行期共享库（实体文件 + 签名）。

        OHOS loader 不解析软链 DT_NEEDED、系统 OpenSSL 3.0 缺 cargo 1.97 需要的
        符号，故按 SONAME 提供实体文件。
        """
        base = os.path.join(self.build_folder, "rust-runtime")
        lib_dir = os.path.join(base, "lib")
        os.makedirs(lib_dir, exist_ok=True)
        for entry in self.conan_data["rust_runtime_bottles"]:
            name = entry["name"]
            tgz = os.path.join(base, name + ".tar.gz")
            if not os.path.isfile(tgz):
                download(self, entry["url"], tgz, sha256=entry["sha256"])
            extract = os.path.join(base, name)
            os.makedirs(extract, exist_ok=True)
            with tarfile.open(tgz, "r:gz") as tf:
                tf.extractall(extract)
            for root, _dirs, files in os.walk(extract):
                if os.path.basename(root) != "lib":
                    continue
                for fname in files:
                    if fname.startswith(("libssl.", "libcrypto.", "libz.")):
                        shutil.copy2(os.path.join(root, fname),
                                     os.path.join(lib_dir, fname))
        # cargo DT_NEEDED 为不带版本后缀的名字（libssl.so/libcrypto.so/libz.so）：
        # OHOS loader 不跟随软链，必须提供实体文件（真实内容相同）。
        aliases = [("libssl.so.3", "libssl.so"),
                   ("libcrypto.so.3", "libcrypto.so"),
                   ("libz.so.1", "libz.so")]
        for src_name, alias in aliases:
            s = os.path.join(lib_dir, src_name)
            if os.path.isfile(s):
                shutil.copy2(s, os.path.join(lib_dir, alias))
        libs = [os.path.join(lib_dir, f) for f in sorted(os.listdir(lib_dir))
                if ".so" in f]
        self._sign(libs, keep_exec=True)
        return lib_dir

    def _ca_bundle(self):
        candidates = [
            os.environ.get("SSL_CERT_FILE"),
            os.environ.get("CURL_CA_BUNDLE"),
            "/storage/Users/currentUser/usr/local/ssl/cert.pem",
            "/etc/ssl/certs/cacert.pem",
            "/etc/ssl/cert.pem",
            os.path.expanduser("~/.harmonybrew/etc/ca-certificates/cert.pem"),
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

    def _configure_cargo(self, cargo_home, ca_bundle):
        os.makedirs(cargo_home, exist_ok=True)
        content = (
            '[source.crates-io]\n'
            'replace-with = "rsproxy-sparse"\n\n'
            '[source.rsproxy-sparse]\n'
            'registry = "sparse+https://rsproxy.cn/index/"\n\n'
            '[net]\n'
            'git-fetch-with-cli = true\n'
            'retry = 3\n'
        )
        if ca_bundle:
            content += '\n[http]\ncainfo = "%s"\n' % ca_bundle
        with open(os.path.join(cargo_home, "config.toml"), "w",
                  encoding="utf-8", newline="\n") as fh:
            fh.write(content)

    def _ohos_cc(self):
        candidates = [
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/"
            "aarch64-unknown-linux-ohos-clang",
            shutil.which("aarch64-unknown-linux-ohos-clang"),
        ]
        for c in candidates:
            if c and os.path.isfile(c):
                return c
        raise ConanInvalidConfiguration("aarch64-unknown-linux-ohos-clang not found")

    def _ensure_writable_tmpdir(self, env):
        current = env.get("TMPDIR")
        if current and os.path.isdir(current) and os.access(current, os.W_OK):
            return
        fallback = os.path.expanduser("~/tmp/rhai")
        try:
            os.makedirs(fallback, exist_ok=True)
        except OSError:
            fallback = os.path.join(self.build_folder, "tmp")
            os.makedirs(fallback, exist_ok=True)
        env["TMPDIR"] = fallback

    def _build_environment(self):
        env = os.environ.copy()
        bin_dir = self._prepare_signed_toolchain()
        runtime_lib = self._prepare_runtime_libs()
        # PATH：签名工具链 bin 最前；/usr/bin 必须保留（SDK clang 包装脚本用
        # readlink/dirname）
        extra_paths = [bin_dir, "/usr/bin", "/bin", "/data/service/hnp/bin",
                       "/storage/Users/currentUser/usr/local/bin"]
        env["PATH"] = os.pathsep.join(
            [p for p in extra_paths if os.path.isdir(p)] + [env.get("PATH", "")]
        )
        env["CARGO"] = os.path.join(bin_dir, "cargo")
        env["RUSTC"] = os.path.join(bin_dir, "rustc")
        lib_dirs = [os.path.join(self._toolchain_dir(), "lib"), runtime_lib,
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"]
        prev = env.get("LD_LIBRARY_PATH", "")
        env["LD_LIBRARY_PATH"] = os.pathsep.join(
            [d for d in lib_dirs if os.path.isdir(d)] + ([prev] if prev else [])
        )
        ca = self._ca_bundle()
        if ca:
            env["SSL_CERT_FILE"] = ca
            env["CURL_CA_BUNDLE"] = ca
        cargo_home = env.get("CARGO_HOME") or os.path.expanduser("~/.cargo")
        self._configure_cargo(cargo_home, ca)
        env["CARGO_HOME"] = cargo_home
        self._ensure_writable_tmpdir(env)
        if str(self.settings.os) == "OHOS":
            cc = self._ohos_cc()
            env["CARGO_TARGET_AARCH64_UNKNOWN_LINUX_OHOS_LINKER"] = cc
            env["CC_aarch64_unknown_linux_ohos"] = cc
        return env

    # ── build ──────────────────────────────────────────────────────

    def build(self):
        apply_conandata_patches(self)
        env = self._build_environment()
        target = self._ohos_target()
        self._ensure_no_git_patch()
        self._run_upstream_tests(env, target)
        self._cargo_build(env, target)

    def _ensure_no_git_patch(self):
        """防御：确认 [patch.crates-io] git 重定向已被 patches/0001 去除。

        残留 git 依赖会让 cargo 在解析阶段访问 github.com（构建网络不可达，
        且非可复现）。
        """
        cargo_toml = os.path.join(self.source_folder, "Cargo.toml")
        with open(cargo_toml, encoding="utf-8") as fh:
            content = fh.read()
        if "[patch.crates-io]" in content:
            self.output.warning(
                "Cargo.toml still contains [patch.crates-io]; applying runtime fixup"
            )
            lines, out, skip = content.splitlines(keepends=True), [], False
            for line in lines:
                if line.strip() == "[patch.crates-io]":
                    skip = True
                    continue
                if skip:
                    if line.startswith("[") and line.strip() != "[patch.crates-io]":
                        skip = False
                    else:
                        continue
                out.append(line)
            with open(cargo_toml, "w", encoding="utf-8", newline="\n") as fh:
                fh.write("".join(out))

    def _run_upstream_tests(self, env, target):
        if os.environ.get("OHC_SKIP_UPSTREAM_TESTS") == "1":
            self.output.info(
                "Skipping upstream cargo test (OHC_SKIP_UPSTREAM_TESTS=1); "
                "suite validated separately (see notes.md)."
            )
            return
        cmd = [env["CARGO"], "test", "--release", "--tests",
               "--features", TEST_FEATURES, "--target", target]
        self.output.info("Running upstream tests: %s" % " ".join(cmd))
        rc = subprocess.run(cmd, cwd=self.source_folder, env=env).returncode
        if rc != 0:
            raise ConanInvalidConfiguration(
                f"Upstream rhai tests failed for {target} (rc={rc})"
            )

    def _cargo_build(self, env, target):
        cmd = [env["CARGO"], "build", "--release", "--bins",
               "--features", BUILD_FEATURES, "--target", target]
        rc = subprocess.run(cmd, cwd=self.source_folder, env=env).returncode
        if rc != 0:
            raise ConanInvalidConfiguration(f"cargo build failed for {target} (rc={rc})")
        release_dir = os.path.join(self.source_folder, "target", target, "release")
        out_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(out_dir, exist_ok=True)
        produced = []
        for name in ("rhai-run", "rhai-dbg"):
            src = os.path.join(release_dir, name)
            if os.path.isfile(src):
                dst = os.path.join(out_dir, name)
                shutil.copy2(src, dst)
                os.chmod(dst, 0o755)
                produced.append(dst)
        if not produced:
            raise ConanInvalidConfiguration(
                f"no rhai CLI binary produced under {release_dir}"
            )
        if str(self.settings.os) == "OHOS":
            self._sign(produced, keep_exec=True)

    def package(self):
        copy(self, "rhai-run", src=os.path.join(self.build_folder, "bin"),
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "rhai-dbg", src=os.path.join(self.build_folder, "bin"),
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "LICENSE-*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "README.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "res"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
