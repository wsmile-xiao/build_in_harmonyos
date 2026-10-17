#!/usr/bin/env python3
"""Conan recipe — argc 1.24.0 (cargo)

argc is a bash CLI framework and bash-based command runner written in Rust.
Builds the `argc` executable with `cargo build --release`; upstream tests
(13 #[test] unit tests in src/, 183 #[test] + 25 #[rstest] integration
tests in tests/) run via `cargo test --release` in the test_package phase
(tlsx/1.2.2 precedent: hmbs preflight only collects the
HMBS_UPSTREAM_TEST_RESULT marker from the test_package phase stdout, and
a cached binary skips build() entirely), reported with counts parsed from
the real cargo framework output.

Toolchain handling follows archives/m/martin/1.13.0 (compiled): probe
well-known cargo locations first; if absent, bootstrap the OHOS Rust
toolchain from the Harmonybrew bottles with Python urllib (the device curl
has no CA bundle and cannot verify TLS). The Rust binary is statically
linked; no RPATH needed.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class ArgcConan(ConanFile):
    name = "argc"
    version = "1.24.0"
    description = "A bash cli framework, also a bash-based command runner"
    license = "MIT OR Apache-2.0"
    homepage = "https://github.com/sigoden/argc"
    url = "https://github.com/sigoden/argc"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # .cargo/config.toml: clang 链接器（OHOS 无 cc 符号）+ rsproxy.cn
        # sparse 镜像（设备无 crates.io CA bundle，直达 crates.io 会 TLS 失败）
        cargo_dir = os.path.join(self.build_folder, ".cargo")
        os.makedirs(cargo_dir, exist_ok=True)
        config_path = os.path.join(cargo_dir, "config.toml")
        with open(config_path, "w") as f:
            f.write('[build]\ntarget-dir = "target"\n')
            if str(self.settings.os) == "OHOS":
                f.write(
                    "\n[target.aarch64-unknown-linux-ohos]\n"
                    'linker = "/data/service/hnp/bin/clang"\n'
                )
            # 真机实测：rsproxy.cn 可达（多数 crate 下载成功），但存在
            # 单文件慢速卡顿（smawk/0.3.2 "transfer too slow: 30s 内
            # 0 字节"）。放宽 cargo 网络容错：重试 10 次、单请求超时
            # 600s、低速阈值降到 1 B/s，避免慢速抖动被误判为失败。
            f.write(
                "\n[source.crates-io]\n"
                'replace-with = "rsproxy-sparse"\n'
                "\n[source.rsproxy-sparse]\n"
                'registry = "sparse+https://rsproxy.cn/index/"\n'
                "\n[net]\n"
                "retry = 10\n"
                "\n[http]\n"
                "timeout = 600\n"
                "low-speed-limit = 1\n"
            )

    @staticmethod
    def _find_cargo():
        """Probe well-known OHOS locations for the cargo binary (HNP
        toolchain, Harmonybrew, rustup, usr/local).

        Harmonybrew bottles ship ``bin/cargo`` as a wrapper script that
        execs ``cargo.real`` at the hardcoded Cellar absolute path; once
        the bottle is unpacked into the build folder that path does not
        exist (rc=127). Always prefer a ``.real`` sibling next to a
        candidate so the real binary is executed, never the wrapper.
        """
        candidates = [
            shutil.which("cargo"),
            "/storage/Users/currentUser/.harmonybrew/bin/cargo",
            "/storage/Users/currentUser/.cargo/bin/cargo",
            os.path.expanduser("~/.harmonybrew/bin/cargo"),
            os.path.expanduser("~/.cargo/bin/cargo"),
            "/data/service/hnp/bin/cargo",
            "/storage/Users/currentUser/usr/local/bin/cargo",
        ]
        for cand in candidates:
            if not cand:
                continue
            if not cand.endswith(".real") and os.path.isfile(cand + ".real"):
                cand = cand + ".real"
            if os.path.isfile(cand) and os.access(cand, os.X_OK):
                return cand
        return None

    def _download_bottle(self, url, tgz):
        """Download a Harmonybrew bottle with Python urllib.

        The device Python has no default CA bundle, so urllib fails with
        SSL: CERTIFICATE_VERIFY_FAILED. Point SSL_CERT_FILE at the first
        available system CA store (usr/local/ssl cert.pem is the store
        verified on the real machine by astra/boolector/boost-build) so
        the download stays TLS-verified. Only when no CA store exists at
        all, fall back to an unverified context for the fixed internal
        Harmonybrew mirror (E185 / kosli-cli precedent); the package
        cannot build without the toolchain.
        """
        import ssl
        import urllib.error
        import urllib.request

        if not os.environ.get("SSL_CERT_FILE"):
            for ca in (
                "/storage/Users/currentUser/usr/local/ssl/cert.pem",
                "/etc/ssl/certs/cacert.pem",
                "/etc/ssl/cert.pem",
                os.path.expanduser("~/.harmonybrew/etc/ca-certificates/cert.pem"),
            ):
                if os.path.isfile(ca):
                    os.environ["SSL_CERT_FILE"] = ca
                    os.environ["CURL_CA_BUNDLE"] = ca
                    break
        try:
            urllib.request.urlretrieve(url, tgz)
        except (urllib.error.URLError, ssl.SSLError) as exc:
            if "CERTIFICATE_VERIFY_FAILED" not in str(exc):
                raise
            os.environ.pop("SSL_CERT_FILE", None)
            os.environ.pop("CURL_CA_BUNDLE", None)
            self.output.warning(
                "no CA bundle on device, downloading %s with an "
                "unverified TLS context (fixed internal mirror)" % url
            )
            ctx = ssl._create_unverified_context()
            with urllib.request.urlopen(url, context=ctx) as resp, \
                    open(tgz, "wb") as out:
                shutil.copyfileobj(resp, out)

    def _bootstrap_rust_toolchain(self):
        """Download and unpack the Harmonybrew OHOS Rust toolchain bottles.

        The device curl has no CA bundle (SSL: unable to get local issuer
        certificate), so fetch the official OHOS bottles with Python urllib
        (martin/1.13.0 precedent); _download_bottle points SSL_CERT_FILE at
        a system CA store before connecting so urllib TLS also verifies.
        """
        import tarfile

        base = os.path.join(self.build_folder, "rust-toolchain")
        os.makedirs(base, exist_ok=True)
        bottles = {
            "rust": "https://harmonybrew.atomgit.com/bottles/rust-1.97.1.arm64_ohos.bottle.tar.gz",
            "openssl3": "https://harmonybrew.atomgit.com/bottles/openssl%403-3.6.3.arm64_ohos.bottle.tar.gz",
            "zlib": "https://harmonybrew.atomgit.com/bottles/zlib-ng-compat-2.3.3_1.arm64_ohos.bottle.tar.gz",
        }
        for name, url in bottles.items():
            tgz = os.path.join(base, name + ".tar.gz")
            if not os.path.isfile(tgz):
                self._download_bottle(url, tgz)
            with tarfile.open(tgz, "r:gz") as tf:
                tf.extractall(base)

        cargo_real = None
        for root, _dirs, files in os.walk(base):
            if "cargo.real" in files:
                cargo_real = os.path.join(root, "cargo.real")
                break
        if not cargo_real:
            raise ConanInvalidConfiguration(
                "failed to bootstrap Rust toolchain from Harmonybrew bottles"
            )

        # 修复 bottle 内的 wrapper 脚本：bin/cargo 等是硬编码 Cellar 绝对
        # 路径（/storage/Users/currentUser/.harmonybrew/Cellar/rust/...）的
        # sh 脚本，解包到 build 目录后该路径不存在（rc=127）。把每个带
        # `.real` 同级的 `#!` 脚本 wrapper 重写为执行本地解包的 `.real`
        # 二进制（open("w") 保留原文件权限位，不触碰符号链接与真实 ELF）。
        bin_dir = os.path.dirname(cargo_real)
        for name in sorted(os.listdir(bin_dir)):
            if name.endswith(".real"):
                continue
            wrapper = os.path.join(bin_dir, name)
            real = os.path.join(bin_dir, name + ".real")
            if os.path.islink(wrapper) or not os.path.isfile(wrapper) \
                    or not os.path.isfile(real):
                continue
            try:
                with open(wrapper, "rb") as f:
                    head = f.read(512)
            except OSError:
                continue
            if not head.startswith(b"#!"):
                continue  # 真实二进制，不是 wrapper 脚本
            with open(wrapper, "w") as f:
                f.write("#!/bin/sh\n")
                f.write("# repaired by argc recipe: exec local .real binary\n")
                f.write('exec "%s" "$@"\n' % real)

        # cargo.real 动态链接 libssl/libcrypto/libz；OHOS loader 忽略
        # DT_RUNPATH，需把解包出的 openssl/zlib lib 目录放进 LD_LIBRARY_PATH
        lib_dirs = []
        for root, _dirs, files in os.walk(base):
            if os.path.basename(root) == "lib":
                libs = set(files)
                if libs & {"libssl.so", "libcrypto.so", "libz.so"}:
                    lib_dirs.append(root)
        if lib_dirs:
            prev = os.environ.get("LD_LIBRARY_PATH", "")
            os.environ["LD_LIBRARY_PATH"] = ":".join(lib_dirs + ([prev] if prev else []))
        return cargo_real

    def _ensure_cargo(self):
        """Return the absolute path to cargo, bootstrapping the OHOS Rust
        toolchain from the Harmonybrew bottles if none is installed."""
        cargo = self._find_cargo()
        if not cargo:
            cargo = self._bootstrap_rust_toolchain()
        if cargo:
            os.environ["PATH"] = os.path.dirname(cargo) + os.pathsep + os.environ.get("PATH", "")
            return cargo
        raise ConanInvalidConfiguration("cargo toolchain is required to build argc")

    def _build_env(self):
        """Build env: clang as the C linker for cargo build scripts, a
        writable TMPDIR (OHOS /tmp is read-only), and a CA bundle for
        cargo's TLS when the system provides one."""
        env = dict(os.environ)
        clang = shutil.which("clang") or "/data/service/hnp/bin/clang"
        clangxx = shutil.which("clang++") or "/data/service/hnp/bin/clang++"
        env["CC"] = clang
        env["CXX"] = clangxx
        env.setdefault("CFLAGS", "-fPIC -O2")
        env.setdefault("CXXFLAGS", "-fPIC -O2")
        env["RUSTFLAGS"] = f"-C linker={clang}"
        tmpdir = os.environ.get("HMBS_TMPDIR") or os.environ.get("TMPDIR")
        if not tmpdir:
            tmpdir = os.path.join(os.path.expanduser("~"), "tmp", "argc")
            os.makedirs(tmpdir, exist_ok=True)
        for var in ("TMPDIR", "TMP", "TEMP"):
            env[var] = tmpdir
        # bash (used by generated scripts during tests) is not on PATH by default
        hnp_bin = "/data/service/hnp/bin"
        if os.path.isdir(hnp_bin):
            env["PATH"] = hnp_bin + os.pathsep + env.get("PATH", "")
        # 设备无 CA bundle：把系统 CA 存储指给 SSL_CERT_FILE/CURL_CA_BUNDLE
        if not env.get("SSL_CERT_FILE"):
            for ca in ("/storage/Users/currentUser/usr/local/ssl/cert.pem",
                       "/etc/ssl/certs/cacert.pem",
                       os.path.expanduser("~/.harmonybrew/etc/ca-certificates/cert.pem")):
                if os.path.isfile(ca):
                    env["SSL_CERT_FILE"] = ca
                    env["CURL_CA_BUNDLE"] = ca
                    break
        return env

    def build(self):
        cargo = self._ensure_cargo()
        env = self._build_env()
        saved_env = dict(os.environ)
        os.environ.update(env)
        try:
            # Build the release binary (Cargo resolves the full Rust dep graph
            # from Cargo.lock; no configure step for Cargo projects)
            self.run(f'"{cargo}" build --release --bin argc')
            # NOTE: upstream official tests (cargo test --release) run in
            # test_package/conanfile.py's test() method, where hmbs preflight
            # collects the HMBS_UPSTREAM_TEST_RESULT marker from the
            # test_package phase stdout (tlsx/1.2.2 precedent). build() only
            # produces the argc binary.
        finally:
            os.environ.clear()
            os.environ.update(saved_env)

    def package(self):
        # Cargo creates target/ next to Cargo.toml (source folder), not in
        # the Conan build subfolder
        target_dir = os.path.join(self.build_folder, "target", "release")
        if not os.path.exists(os.path.join(target_dir, "argc")):
            target_dir = os.path.join(self.source_folder, "target", "release")
        copy(self, "argc", src=target_dir, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
