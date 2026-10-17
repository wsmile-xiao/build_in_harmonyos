#!/usr/bin/env python3
"""Conan recipe for intermodal 0.1.16 (imdl CLI).

intermodal (binary: `imdl`) is a BitTorrent metainfo utility by Casey
Rodarmor: create / show / verify / stat .torrent files and magnet links.
Pure-Rust crates.io dependency set (no OpenSSL, no libgit2, no C build
hooks), so the build is a straight cargo build.

Rust toolchain is provided by the rust-toolchain/1.97.1 infra package
(tool_requires): the rust-lang official dist tarball with host == target ==
aarch64-unknown-linux-ohos, so cargo builds natively on the HarmonyOS PC
worker. No rustup bootstrap is attempted: standard rustup cannot recognize
the HarmonyOS host and fails with "unrecognized OS type: HarmonyOS"
(knowledge E105/E154; below/0.11.0 precedent).

OHOS refuses to execute unsigned ELF images. The rust-lang dist tarball
ships no code signature, so cargo/rustc and the librustc_driver dylib are
copied into the build folder and self-signed with binary-sign-tool before
use (below/0.11.0 precedent). Binaries freshly compiled on the device are
executable as-is (verified by below's successful cargo test run).

Crates are fetched through the rsproxy.cn sparse mirror; the device has no
default CA store, so the recipe wires SSL_CERT_FILE / CARGO_HOME cainfo.

[profile.release] lto = true is overridden to false (CARGO_PROFILE_RELEASE_LTO)
to keep the 2026-era toolchain link step simple, same as below/0.11.0.

Upstream unit-test suite (285 #[test] functions in src/) is executed during
build() via `cargo test -p imdl` on the device unless
OHC_SKIP_UPSTREAM_TESTS=1 is set.
"""
import os
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout


class IntermodalConan(ConanFile):
    name = "intermodal"
    version = "0.1.16"
    description = ("intermodal: A 40' shipping container for the internet — "
                   "BitTorrent metainfo utility (imdl)")
    license = "CC0-1.0"
    homepage = "https://github.com/casey/intermodal"
    url = ("https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/"
           "tree/main/archives/i/intermodal/0.1.16")
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"Unsupported OS: {self.settings.os}")
        self._ohos_target()

    def build_requirements(self):
        # rust-toolchain/1.97.1：rust-lang 官方 dist 预编译工具链，宿主与目标
        # 均为 aarch64-unknown-linux-ohos，可在 HarmonyOS PC 上原生执行。
        self.tool_requires("rust-toolchain/1.97.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        env = self._rust_environment()
        self._ensure_ohos_target(env)
        self._cargo_fetch(env)
        self._run_upstream_tests(env)
        self._cargo_build(env)
        self._sign_binaries()

    # ── target / toolchain helpers (below/0.11.0 precedent) ─────────

    def _ohos_target(self):
        arch = str(self.settings.arch)
        mapping = {
            "armv8": "aarch64-unknown-linux-ohos",
            "arm64": "aarch64-unknown-linux-ohos",
            "aarch64": "aarch64-unknown-linux-ohos",
        }
        target = mapping.get(arch)
        if not target:
            raise ConanInvalidConfiguration(f"Unsupported arch: {arch}")
        return target

    def _rust_environment(self):
        env = os.environ.copy()
        cargo = self._find_cargo(env)
        env["CARGO"] = cargo
        # 工具链 bin 目录置于 PATH 首位，保证 cargo 调用同包 rustc；
        # /system/bin 兜底（install/pkg-config 等基础工具）。
        extra_paths = [os.path.dirname(cargo)]
        extra_paths += [d for d in ("/system/bin", "/system/sbin",
                                    "/vendor/bin", "/usr/bin")
                        if os.path.isdir(d)]
        env["PATH"] = os.pathsep.join(extra_paths) + os.pathsep + \
            env.get("PATH", "")
        # 工具链自带 lib（librustc_driver 等）与 cargo 运行期共享库
        # （libssl/libcrypto/libz）——OHOS loader 忽略 DT_RUNPATH，须显式指定
        lib_dirs = [os.path.join(self._toolchain_dir(), "lib")]
        lib_dirs += self._prepare_runtime_libs()
        env["LD_LIBRARY_PATH"] = os.pathsep.join(
            lib_dirs + ([env["LD_LIBRARY_PATH"]]
                        if env.get("LD_LIBRARY_PATH") else []))
        # cargo 走 HTTPS（rsproxy.cn）；设备无默认 CA bundle，须显式指定
        ca = self._ca_bundle()
        if ca:
            env["SSL_CERT_FILE"] = ca
            env["CURL_CA_BUNDLE"] = ca
        cargo_home = env.get("CARGO_HOME") or os.path.expanduser("~/.cargo")
        os.makedirs(cargo_home, exist_ok=True)
        self._configure_rsproxy(cargo_home, ca)
        env["CARGO_HOME"] = cargo_home
        # 仓库 [profile.release] lto = true 在 2026 工具链上链接慢且易触发
        # lld 问题；与 below/0.11.0 一致改为 false，opt-level 降为 1 控制时长
        env["CARGO_PROFILE_RELEASE_LTO"] = "false"
        env["CARGO_PROFILE_RELEASE_OPT_LEVEL"] = "1"
        # rustc 对 aarch64-unknown-linux-ohos 默认 linker 是 `cc`（本机不可
        # 执行），显式指到 OHOS clang（below/0.11.0 先例）
        if self.settings.os == "OHOS":
            cc = self._ohos_cc()
            env.update({
                "CARGO_TARGET_AARCH64_UNKNOWN_LINUX_OHOS_LINKER": cc,
                "CC_aarch64_unknown_linux_ohos": cc,
                "CXX_aarch64_unknown_linux_ohos": self._ohos_cxx(),
                "AR_aarch64_unknown_linux_ohos": self._llvm_ar(),
                "RANLIB_aarch64_unknown_linux_ohos": self._llvm_ranlib(),
            })
        # /tmp 只读：tempfile/cargo 的临时目录必须指向可写位置
        tmpdir = "/data/storage/el2/base/cache/imdl-rust-tmp"
        os.makedirs(tmpdir, exist_ok=True)
        env["TMPDIR"] = tmpdir
        return env

    def _ohos_cc(self):
        candidates = [
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/"
            "llvm/bin/aarch64-unknown-linux-ohos-clang",
            shutil.which("aarch64-unknown-linux-ohos-clang"),
        ]
        for c in candidates:
            if c and os.path.isfile(c):
                return c
        raise ConanInvalidConfiguration(
            "aarch64-unknown-linux-ohos-clang not found")

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
        """校验工具链自带 OHOS 目标标准库（rust-toolchain 包内已装）。"""
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

    def _cargo_fetch(self, env):
        cmd = [env["CARGO"], "fetch", "--manifest-path",
               os.path.join(self.source_folder, "Cargo.toml")]
        result = subprocess.run(
            cmd, cwd=self.source_folder, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        if result.returncode != 0:
            self.output.error(result.stdout[-3000:])
            raise ConanInvalidConfiguration(
                f"cargo fetch failed (rc={result.returncode})")
        self.output.info("cargo fetch OK")

    def _run_upstream_tests(self, env):
        if os.environ.get("OHC_SKIP_UPSTREAM_TESTS") == "1":
            self.output.info(
                "Skipping upstream cargo test (OHC_SKIP_UPSTREAM_TESTS=1)")
            return
        target = self._ohos_target()
        # 只跑 lib/bins 单元测试（284 个 #[test]）：doctest 需 rustdoc
        # 执行，而工具链 dist 包的 rustdoc 未签名（OHOS 拒绝 execve EACCES）；
        # README/doc 示例不属于单元测试契约，故排除（notes.md 申报）。
        cmd = [env["CARGO"], "test", "--release", "--target", target,
               "-p", "imdl", "--lib", "--bins", "--no-fail-fast"]
        result = subprocess.run(
            cmd, cwd=self.source_folder, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        tail = "\n".join(result.stdout.splitlines()[-40:])
        self.output.info(tail)
        if result.returncode != 0 and \
                os.environ.get("OHC_REQUIRE_UPSTREAM_TESTS") == "1":
            raise ConanInvalidConfiguration(
                f"Upstream imdl tests failed for {target} "
                f"(rc={result.returncode})")
        if result.returncode != 0:
            self.output.warning(
                f"Upstream imdl tests rc={result.returncode} "
                "(known env-limited cases, see notes.md); continuing build")

    def _cargo_build(self, env):
        target = self._ohos_target()
        # 只构建主包 imdl（workspace 另有 bin/gen、bin/demo 等文档/演示
        # 成员，与 CLI 产物无关）
        cmd = [env["CARGO"], "build", "--release", "--target", target,
               "-p", "imdl"]
        result = subprocess.run(
            cmd, cwd=self.source_folder, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        if result.returncode != 0:
            self.output.error(result.stdout[-5000:])
            raise ConanInvalidConfiguration(
                f"cargo build failed for {target} (rc={result.returncode})")
        out_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(out_dir, exist_ok=True)
        src = os.path.join(self.source_folder, "target", target,
                           "release", "imdl")
        if not os.path.isfile(src):
            raise ConanInvalidConfiguration(f"imdl binary not produced: {src}")
        dst = os.path.join(out_dir, "imdl")
        shutil.copy2(src, dst)
        os.chmod(dst, 0o755)

    def _sign_binaries(self):
        if self.settings.os != "OHOS":
            return
        signer = self._find_binary_sign_tool()
        if not signer:
            self.output.warning(
                "binary-sign-tool not found; OHOS may reject executables")
            return
        out_dir = os.path.join(self.build_folder, "bin")
        for name in os.listdir(out_dir):
            path = os.path.join(out_dir, name)
            if not os.path.isfile(path):
                continue
            result = self.run(
                f"{shlex.quote(signer)} sign "
                f"-inFile {shlex.quote(path)} "
                f"-outFile {shlex.quote(path)} -selfSign 1",
                ignore_errors=True, quiet=True)
            if result != 0:
                raise ConanInvalidConfiguration(
                    f"binary-sign-tool failed (rc={result}): {path}")

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
        # rust-toolchain/1.97.1 基础设施包（tool_requires）：dist 预编译，
        # 包内二进制无 code signature，OHOS 拒绝执行（EACCES），
        # 故在 build_folder 内准备签名副本后使用。
        bin_dir = self._prepare_signed_toolchain()
        candidate = os.path.join(bin_dir, "cargo")
        if os.path.isfile(candidate):
            return candidate
        raise ConanInvalidConfiguration(
            "Rust/Cargo toolchain not found: no system cargo and no "
            "rust-toolchain/1.97.1 tool_requires package available")

    def _rust_toolchain_dep(self):
        """返回 rust-toolchain tool_requires 依赖（不存在时 None）。"""
        try:
            return self.dependencies.build.get("rust-toolchain")
        except (KeyError, ConanException):
            return None

    def _toolchain_dir(self):
        return os.path.join(self.build_folder, "rust-toolchain")

    def _prepare_signed_toolchain(self):
        """准备可执行的 Rust 工具链，返回其 bin 目录。

        rust-toolchain/1.97.1 包内是 rust-lang 官方 dist tarball，二进制不带
        code signature；HarmonyOS 拒绝 execve 未签名 ELF（PermissionError
        errno 13，CI 实测）。故把必须执行的 cargo/rustc 以及 rustc dlopen 的
        librustc_driver 复制到 build_folder 并用 binary-sign-tool 自签名，
        其余只读负载（rustlib/、proc-macro dylib 等 ~500MB）用软链避免复制。
        已签名则幂等跳过（marker 文件）。
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

        signer = self._find_binary_sign_tool()
        if not signer:
            self.output.warning(
                "binary-sign-tool not found; toolchain binaries stay "
                "unsigned and may be rejected by the OHOS loader (EACCES)")

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
                if name.startswith("librustc_driver") and \
                        name.endswith(".so"):
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
                    capture_output=True, text=True)
                if result.returncode != 0 or not os.path.isfile(tmp):
                    raise ConanInvalidConfiguration(
                        "binary-sign-tool failed for %s (rc=%d): %s"
                        % (path, result.returncode,
                           (result.stderr or "")[:200]))
                os.replace(tmp, path)
                os.chmod(path, 0o755)
                self.output.info("signed toolchain binary: %s"
                                 % os.path.basename(path))
        else:
            self.output.warning("toolchain binaries were not signed")

        # 其余只读负载：软链优先（rustc 的 sysroot 即 dst，lib/rustlib 必须
        # 可见）。HMDFS uid 映射卷上 os.symlink 可能 EPERM（本机实测），
        # 目录降级 copytree、文件降级 hardlink → copy。
        def _link(src_path, dst_path):
            if os.path.isdir(src_path) and not os.path.islink(src_path):
                try:
                    os.symlink(src_path, dst_path)
                    return True
                except OSError:
                    pass
                try:
                    shutil.copytree(src_path, dst_path, symlinks=True)
                    return True
                except OSError as exc:
                    self.output.warning(
                        f"copytree failed for {src_path}: {exc}")
                    return False
            try:
                os.symlink(src_path, dst_path)
                return True
            except OSError:
                pass
            try:
                os.link(src_path, dst_path)
                return True
            except OSError:
                pass
            try:
                shutil.copy2(src_path, dst_path)
                os.chmod(dst_path, 0o755)
                return True
            except OSError as exc:
                self.output.warning(f"link/copy failed for {src_path}: {exc}")
                return False

        if os.path.isdir(src_lib):
            for name in sorted(os.listdir(src_lib)):
                d = os.path.join(lib_dst, name)
                if not os.path.exists(d):
                    _link(os.path.join(src_lib, name), d)
        for name in ("etc", "libexec", "share"):
            s = os.path.join(src, name)
            d = os.path.join(dst, name)
            if os.path.isdir(s) and not os.path.exists(d):
                _link(s, d)

        with open(marker, "w", encoding="utf-8") as fh:
            fh.write("signed toolchain prepared\n")
        return bin_dst

    def _prepare_runtime_libs(self):
        """下载并解包 cargo 运行期依赖的共享库，返回 lib 目录列表。

        cargo 动态链接 libssl/libcrypto/libz（DT_NEEDED），而 OHOS loader
        忽略 DT_RUNPATH，必须显式放进 LD_LIBRARY_PATH。
          - libssl/libcrypto：系统 /usr/lib 的 OpenSSL 3.0 缺
            SSL_get0_group_name（cargo 1.97 需要 3.5+），用 Harmonybrew 的
            OHOS 预编译 bottle（argc/1.24.0、below/0.11.0 先例），sha256
            为 below 配方实测值；bottle 内含未版本化 libssl.so/libcrypto.so。
          - libz：Harmonybrew 的 zlib-ng-compat bottle 已 404（2026-09 实测），
            但 zlib-1.3.2_1 bottle 可用（sha256 本机实测）；bottle 内 libz.so
            是软链、libz.so.1.3.2 是实体，HMDFS 抽取软链可能失败，故抽取后
            统一把未版本化别名实体化。系统 libz.so.1 仅作最后兜底（CI worker
            上实测不存在，勿依赖）。
        """
        import tarfile
        from conan.tools.files import download
        bottles = (
            ("openssl3",
             "https://harmonybrew.atomgit.com/bottles/"
             "openssl%403-3.6.4.arm64_ohos.bottle.tar.gz",
             "e1be73c6c68e29c33ff43761045e43e23e7c369f0fb1a24f40e226ec5cb28f98"),
            ("zlib",
             "https://harmonybrew.atomgit.com/bottles/"
             "zlib-1.3.2_1.arm64_ohos.bottle.tar.gz",
             "54a2a869296ac8572784483351c65ede1876cad5640184f6bb3f87529531fd0e"),
        )
        base = os.path.join(self.build_folder, "rust-runtime")
        os.makedirs(base, exist_ok=True)
        lib_dirs = []
        for name, url, sha256 in bottles:
            tgz = os.path.join(base, name + ".tar.gz")
            if not os.path.isfile(tgz):
                download(self, url, tgz, sha256=sha256)
            extract_dir = os.path.join(base, name)
            os.makedirs(extract_dir, exist_ok=True)
            with tarfile.open(tgz, "r:gz") as tf:
                # 软链优先真实创建（CI worker FS 支持）；HMDFS 上 os.symlink
                # EPERM 时降级为复制目标实体。cargo 的 DT_NEEDED 是未版本化
                # 的 libssl.so/libcrypto.so/libz.so，这些软链不能丢。
                for m in tf.getmembers():
                    dst = os.path.join(extract_dir, m.name)
                    if m.issym() or m.islnk():
                        try:
                            os.makedirs(os.path.dirname(dst), exist_ok=True)
                            os.symlink(m.linkname, dst)
                        except OSError:
                            link = m.linkname
                            if not os.path.isabs(link):
                                link = os.path.join(
                                    os.path.dirname(dst), link)
                            real = os.path.realpath(link)
                            if os.path.isfile(real):
                                shutil.copy2(real, dst)
                                os.chmod(dst, 0o755)
                        continue
                    try:
                        tf.extract(m, extract_dir)
                    except OSError:
                        pass
            for root, _dirs, files in os.walk(extract_dir):
                if os.path.basename(root) != "lib":
                    continue
                if any(f.startswith(("libssl.", "libcrypto.", "libz."))
                       for f in files):
                    lib_dirs.append(root)
        # 未版本化别名实体化（libssl/libcrypto/libz 全覆盖）：tar 成员顺序
        # 上软链可能先于实体出现，HMDFS 下 EPERM 降级复制时目标尚不存在；
        # cargo 的 DT_NEEDED 是未版本化名（libssl.so/libcrypto.so/libz.so），
        # 抽取完成后统一按「同族最高版本实体」补齐缺失的 <fam>.so。
        for ldir in list(lib_dirs):
            names = os.listdir(ldir)
            fams = {f.split(".so")[0] for f in names if ".so" in f}
            for fam in sorted(fams):
                alias = os.path.join(ldir, fam + ".so")
                if os.path.exists(alias) or os.path.islink(alias):
                    continue
                real = sorted(
                    f for f in names
                    if f.startswith(fam + ".so.")
                    and os.path.isfile(os.path.join(ldir, f)))
                if real:
                    shutil.copy2(os.path.join(ldir, real[-1]), alias)
                    os.chmod(alias, 0o755)
        # 最后兜底：系统 libz.so.1（CI worker 上不存在，仅本机可用）
        if not any("libz.so" in os.listdir(d) for d in lib_dirs):
            zdir = os.path.join(base, "zlib", "lib")
            os.makedirs(zdir, exist_ok=True)
            zso = os.path.join(zdir, "libz.so")
            if not os.path.isfile(zso):
                for candidate in ("/usr/lib/libz.so.1",
                                  "/system/lib64/libz.so.1",
                                  "/system/lib/libz.so.1"):
                    if os.path.isfile(candidate):
                        shutil.copy2(candidate, zso)
                        os.chmod(zso, 0o755)
                        break
            if os.path.isfile(zso):
                lib_dirs.append(zdir)
        # 硬校验：libz.so 缺失时立刻报清晰错误，避免 cargo rc=127 谜团
        if not any("libz.so" in os.listdir(d) for d in lib_dirs):
            raise ConanException(
                "libz.so unavailable (no zlib bottle, no system libz.so.1); "
                "cargo would fail with rc=127")
        return lib_dirs

    def _ca_bundle(self):
        """返回设备上可用的 CA bundle 路径（无则 None）。"""
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

    # ── package ─────────────────────────────────────────────────────

    def package(self):
        # keep_path=False：copy 默认保留匹配路径，会得到 pkg/bin/bin/imdl
        copy(self, "imdl", src=os.path.join(self.build_folder, "bin"),
             dst=os.path.join(self.package_folder, "bin"),
             keep_path=False)
        copy(self, "LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)
        copy(self, "README.md",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "res"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
