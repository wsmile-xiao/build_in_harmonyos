#!/usr/bin/env python3
"""Conan recipe — libsignal-core 0.103.1 (cargo, Rust rlib)

Signal Messenger 的 libsignal monorepo 中的核心身份/密钥原语库
（rust/core crate，crate 名 libsignal-core，AGPL-3.0）。workspace 根在
仓库根：rust/core 不在 [workspace].members 列表（25 个成员均未含它），
而是靠 workspace.dependencies 的 path 依赖隐式入图，因此必须
``cargo build -p libsignal-core`` 切片选建，避免构建 25 个成员。

交付物 = Rust rlib 闭包：liblibsignal_core.rlib + liblibsignal_debug.rlib
+ 全部传递依赖 rlib（libcurve25519_dalek-*.rlib 等哈希后缀名），Rust
消费者用 rustc --extern libsignal_core=<rlib> -L dependency=<libdir>
即可链接。本仓库首个 Rust「库」包（argc 等 8 个已合入 Rust 包均为
application），rlib 交付语义见 notes.md 与路径 B 知识草稿。

工具链处理沿用 archives/a/argc/1.24.0（已合入）：探测已知 cargo 位置，
无则用 Python urllib 从 Harmonybrew bottles 自举 OHOS Rust 工具链
（设备 curl 无 CA bundle 不能验 TLS），并修复 bottle 内硬编码 Cellar
路径的 wrapper 脚本。自举 bottle 即上游 rust-toolchain 文件钉的
1.98.1（依赖 MSRV ≤ 1.93.1，见 notes.md）。

补丁 0001（仅 manifest hunk，84 行）：把 workspace 缩容到只剩
rust/core 切片；重生成的 Cargo.lock（80 包，701 行）作为独立文件随
配方交付（exports_sources），source() 在打补丁后整体覆盖上游锁。
锁与补丁拆分的根因：老全量补丁把 6575 行锁替换整个塞进一个 hunk
（6718 行），主配方与 test_package 各存一份 → 可审 diff 达 1.5 万行；
拆分后语义不变——随附锁与老补丁用 patch-ng（strip=0，conan 2.29 语
义）在原锁上的应用结果逐字节一致（本地 verify_lock_split 实证），
补丁瘦身为纯 manifest 修改。

真机/CI 一次 github 都不碰的根因（真机第 4/5 轮实证）：上游
workspace 有 25 个成员，bridge/* 成员经 workspace.dependencies 直接
git 依赖 signalapp/boring（含 boringssl 子模块）与
SparsePostQuantumRatchet——只要 Cargo.lock 与 manifest 有任何失配，
cargo 就重解析**整个 workspace**，解析器必克隆上述 git 仓库取
manifest（设备/CI 无法访问 github，卡死在 "Updating git submodule
boringssl"）。因此：(1) members 缩到 ["rust/core"]、删 3 个 git
workspace 依赖与 [patch.crates-io] 段、删 rust/core 4 个零引用
dev-deps（boring/boring-sys/clap/criterion，0.103.1 tag 全树 grep
实证）→ 解析图零 git 依赖，即使重解析也只走 rsproxy registry；
(2) 随附对缩容后 manifest 重生成的 Cargo.lock（Windows 侧以原锁为
偏好逐包 --precise 钉回上游版本，cargo check --locked 实证锁即当前）
→ 真机零重解析、版本零漂移，build/test 因此加 --locked 兜底。
上游 tarball 的 Cargo.toml 为 CRLF：source() 先把 2 个待补丁
manifest 文件统一成 LF 再打补丁（LF↔LF 在 git apply/GNU patch/
patch-ng 三系 patcher 下全部实证通过；上一版 CRLF/LF 混写补丁被
git apply 以 "patch does not apply" 拒绝的根因即此）。

上游测试 = cargo test -p libsignal-core --lib --release（25 个 src 单测，
core 无 tests/ 目录；--lib 不含 doc-tests 阶段——OHOS Harmonybrew
工具链无 rustdoc，martin/1.13.0 同仓库先例判定为平台限制），在
test_package 阶段执行并打印 HMBS_UPSTREAM_TEST_RESULT（tlsx/1.2.2
先例：hmbs 只从 test_package stdout 采集标记）。
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.layout import basic_layout


class LibsignalCoreConan(ConanFile):
    name = "libsignal-core"
    version = "0.103.1"
    description = "Signal Messenger core identity and key primitives (rust/core crate)"
    license = "AGPL-3.0-only"
    homepage = "https://github.com/signalapp/libsignal"
    url = "https://github.com/signalapp/libsignal"
    topics = ("signal", "rust", "cryptography", "x25519")

    package_type = "static-library"

    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "patches/*", "Cargo.lock"
    no_copy_source = True

    def layout(self):
        basic_layout(self, src_folder="src")

    def _normalize_line_endings(self):
        """Convert the patch-target files to LF before patching.

        The upstream tarball ships Cargo.toml / rust/core/Cargo.toml with
        CRLF endings. The patch is authored with LF-only context lines
        (git apply and patch-ng are both byte-strict about endings; a
        CRLF/LF mismatch made an earlier hand-written patch fail with a
        confusing "patch does not apply"). Normalizing first makes
        LF<->LF apply under git apply, GNU patch and patch-ng alike (all
        three verified). Cargo is indifferent to line endings, so the
        normalized tree behaves identically. Cargo.lock is not patched
        anymore — it is replaced wholesale by the shipped lock in
        source() — so it is not normalized here.
        """
        for rel in ("Cargo.toml", "rust/core/Cargo.toml"):
            path = os.path.join(self.source_folder, rel)
            if not os.path.isfile(path):
                continue
            with open(path, "rb") as f:
                data = f.read()
            normalized = data.replace(b"\r\n", b"\n")
            if normalized != data:
                with open(path, "wb") as f:
                    f.write(normalized)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        self._normalize_line_endings()
        apply_conandata_patches(self)
        # 补丁 0001 只改 manifest；Cargo.lock 用仓库内随附的重生成锁整体
        # 覆盖上游锁（上游 6577 行锁对缩容后 workspace 无效，任何残余都会
        # 触发 --locked 失配）。随附锁与老全量补丁以 patch-ng strip=0 应用
        # 的结果逐字节一致（本地 verify_lock_split 实证）。
        shutil.copy(
            os.path.join(self.export_sources_folder, "Cargo.lock"),
            os.path.join(self.source_folder, "Cargo.lock"),
        )

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libsignal-core is validated on Linux and OHOS only"
            )

    def generate(self):
        # 与 argc 1.24.0 一致（已合入）：clang 链接器（OHOS 无 cc 符号）+
        # rsproxy.cn sparse 镜像（设备无 crates.io CA bundle）+ 网络容错。
        # 必须写进 source_folder：build() 用 cwd=self.source_folder 调
        # cargo，cargo 只从 cwd 及祖先目录发现 .cargo/config.toml——
        # 只写 build_folder 永远不被发现（CI #63478 实证：回退官方
        # crates.io，syn 下载 transfer too slow 30 次重试用尽挂掉；
        # 真机此前因 crates.io 链路好侥幸全绿）。build_folder 副本保留
        # 以兼容不同 conan 版本布局。
        content = '[build]\ntarget-dir = "target"\n'
        if str(self.settings.os) == "OHOS":
            content += (
                "\n[target.aarch64-unknown-linux-ohos]\n"
                'linker = "/data/service/hnp/bin/clang"\n'
            )
        content += (
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
        for base in (self.source_folder, self.build_folder):
            cargo_dir = os.path.join(base, ".cargo")
            os.makedirs(cargo_dir, exist_ok=True)
            with open(os.path.join(cargo_dir, "config.toml"), "w") as f:
                f.write(content)

    # ------------------------------------------------------------------
    # cargo 工具链（照搬 argc 1.24.0，已合入验证）
    # ------------------------------------------------------------------
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
            # rust 取 r0 而非 formula current revision r2：r2 的 cargo 动态
            # 链 libgit2/libssh2/libcurl/libsqlite3（NEEDED 实测），需补
            # 12+ 个 bottle 传递闭包；r0 仅链 libc/libcrypto/libssl/libz，
            # 3 瓶集（openssl3 + zlib-ng-compat）即全覆盖（见 notes.md）
            "rust": "https://harmonybrew.atomgit.com/bottles/rust-1.98.1.arm64_ohos.bottle.tar.gz",
            "openssl3": "https://harmonybrew.atomgit.com/bottles/openssl%403-3.6.4_1.arm64_ohos.bottle.tar.gz",
            "zlib": "https://harmonybrew.atomgit.com/bottles/zlib-ng-compat-2.3.3_2.arm64_ohos.bottle.tar.gz",
        }
        for name, url in bottles.items():
            tgz = os.path.join(base, name + ".tar.gz")
            if not os.path.isfile(tgz):
                self._download_bottle(url, tgz)
            with tarfile.open(tgz, "r:gz") as tf:
                tf.extractall(base)

        # 旧版 bottle（rust-1.97.1 及更早）：bin/cargo 是 wrapper 脚本，真实
        # 二进制叫 cargo.real；新版（1.98.1_2 起）直接放 ELF。先找 .real
        # 拆分层（旧布局），再回退到非 #! 的 cargo（新布局直接 ELF）。
        cargo_real = None
        for root, _dirs, files in os.walk(base):
            if "cargo.real" in files:
                cargo_real = os.path.join(root, "cargo.real")
                break
        if not cargo_real:
            for root, _dirs, files in os.walk(base):
                if "cargo" not in files:
                    continue
                cand = os.path.join(root, "cargo")
                if os.path.islink(cand) or not os.path.isfile(cand):
                    continue
                with open(cand, "rb") as f:
                    if f.read(2) == b"#!":
                        continue  # wrapper 脚本（旧布局且 .real 缺失）
                cargo_real = cand
                break
        if not cargo_real:
            raise ConanInvalidConfiguration(
                "failed to bootstrap Rust toolchain from Harmonybrew bottles"
            )

        # 修复 bottle 内的 wrapper 脚本：bin/cargo 等是硬编码 Cellar 绝对
        # 路径（/storage/Users/currentUser/.harmonybrew/Cellar/rust/...）的
        # sh 脚本，解包到 build 目录后该路径不存在（rc=127）。把每个带
        # `.real` 同级的 `#!` 脚本 wrapper 重写为执行本地解包的 `.real`
        # 二进制（不触碰符号链接与真实 ELF）。bottle 的 bin 包装脚本可能
        # 带 0555（无写位）——OHOS 对 owner 也严格按权限位拒绝写入
        # （真机第 16 轮实证 PermissionError EACCES），重写前补上写位。
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
            try:
                os.chmod(wrapper, os.stat(wrapper).st_mode | 0o200)
            except OSError:
                pass  # 若 chmod 也受限，让下面的 open 报错暴露真实原因
            with open(wrapper, "w") as f:
                f.write("#!/bin/sh\n")
                f.write("# repaired by libsignal-core recipe: exec local .real binary\n")
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
        raise ConanInvalidConfiguration("cargo toolchain is required to build libsignal-core")

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
            tmpdir = os.path.join(os.path.expanduser("~"), "tmp", "libsignal-core")
            os.makedirs(tmpdir, exist_ok=True)
        for var in ("TMPDIR", "TMP", "TEMP"):
            env[var] = tmpdir
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
        self.output.info("building libsignal-core with cargo: %s" % cargo)
        # 上游 rust-toolchain 文件要求 1.98.1：直接调用 cargo 二进制（不经
        # rustup）时该文件仅被 rustup 强制、cargo 忽略；自举 bottle 即 1.98.1。
        # 补丁 0001 随附与缩容后 manifest 完全匹配的 Cargo.lock（Windows
        # 侧 cargo check --locked 实证），--locked 保证真机零重解析：一旦
        # 有失配立即报错，而不是重解析整个 workspace 去克隆 github 卡死。
        subprocess.check_call(
            [cargo, "build", "--release", "--locked", "-p", "libsignal-core"],
            cwd=self.source_folder,
            env=env,
        )

    def package(self):
        # [build] target-dir 相对 config.toml 所在目录（build_folder）解析；
        # 若 cargo 实际落在 source 下（不同 conan 版本布局差异）则回退。
        target_dir = os.path.join(self.build_folder, "target", "release")
        if not os.path.isdir(os.path.join(target_dir, "deps")):
            target_dir = os.path.join(self.source_folder, "target", "release")
        core = os.path.join(target_dir, "liblibsignal_core.rlib")
        if not os.path.isfile(core):
            raise ConanInvalidConfiguration(
                "cargo build produced no liblibsignal_core.rlib under %s" % target_dir
            )
        # rlib 闭包整体交付：liblibsignal_core.rlib + deps/ 下全部依赖 rlib
        # （哈希后缀名，rustc -L dependency 按 crate 名解析）。deps/ 的
        # 哈希 rlib 必须平铺进 lib/：rustc -L dependency 只在单一目录解析
        # 哈希名（真机第 6 轮实证：conan copy 保序放进 lib/deps/ 后 probe
        # 报 rlib closure incomplete），平铺后 test.sh 的 glob 与 -L
        # dependency 搜索均直通。
        copy(self, "*.rlib", src=target_dir,
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "*.rlib", src=os.path.join(target_dir, "deps"),
             dst=os.path.join(self.package_folder, "lib"))
        # proc-macro crate（zerocopy_derive/derive_more_derive/thiserror_impl
        # 等）在 deps/ 里是哈希后缀 .so：--crate-type proc-macro 只产 .so、
        # 元数据在 .so 内。消费者 rustc 解析 rlib 闭包时对每个传递依赖
        # （含 proc-macro）做全图元数据加载——真机第 7 轮实证：缺
        # libzerocopy_derive-*.so 时 probe 报 "can't find crate for
        # `zerocopy_derive` which `libsignal_core` depends on"。与 rlib
        # 一起平铺进 lib/ 交付。
        copy(self, "*.so", src=os.path.join(target_dir, "deps"),
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # 随附重生成锁随包分发（package 根）：test_package 的上游测试从
        # package_folder 取同一份锁覆盖 pristine 上游锁——锁在 MR 里只有
        # 主配方一份副本，语义同源从"两份相同文件"变成字面上的同一份
        copy(self, "Cargo.lock", src=self.source_folder,
             dst=self.package_folder)

    def package_info(self):
        # Rust rlib（静态归档）：C/C++ 消费者不能直接链接（需 Rust 运行时
        # 与 panic 处理），面向 Rust 消费者交付：
        #   rustc --edition 2024 \
        #     --extern libsignal_core=$pkg/lib/liblibsignal_core.rlib \
        #     -L dependency=$pkg/lib probe.rs
        # 依赖闭包 rlib（哈希后缀名）一并放在 lib/。
        self.cpp_info.libdirs = ["lib"]
