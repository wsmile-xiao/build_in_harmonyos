#!/usr/bin/env python3
"""Conan recipe — zram 1.2.1（上游 systemd/zram-generator，Rust 纯 crate）

zram-generator 读取 zram-generator.conf，为 zram 压缩交换设备生成 systemd
单元并在开机时完成 mkswap/swapon。OHOS 无 systemd 且设备内核当前无 zram
（/sys/class/zram-control、/dev/zram* 均不存在），故以独立 CLI 形态交付
zram-generator 可执行文件：--setup-device/--reset-device/生成单元目录模式
全部保留；systemd unit 与 man 页不安装（不调用 systemd-service/install
目标，NOMAN=1 跳过 ronn）。

构建走上游 Makefile 的 program 目标，全部用 make 命令行变量覆盖、零补丁：
- SYSTEMD_UTIL_DIR=<占位>：Makefile 顶部
  `SYSTEMD_UTIL_DIR := $(shell pkg-config --variable=systemdutildir systemd)`
  是硬门（OHOS 无 systemd pc 模块）；GNU make 命令行变量优先级高于文件内
  := 赋值，pkg-config 根本不会执行。该值同时经 Makefile `export` 进入
  cargo 环境——src/setup.rs 以 env!("SYSTEMD_UTIL_DIR") 编译期内联（缺失即
  编译失败），占位 /usr/lib/systemd 为发行版惯用 util 目录，仅影响 --help
  内嵌文本与 systemd-makefs 拼接路径（OHOS 上该文件本就不存在）。
- NOMAN=1：man 页需 ronn，OHOS 无该工具，跳过。
- CARGO=<探测到的 cargo>：显式指定，不依赖 PATH。

补丁（patches/0001-gate-nix-devdep-for-ohos.patch，经 conandata 声明应用）：
- dev-dependencies 的 nix 按 cfg(not(target_env = "ohos")) 门控。nix 0.23 的
  pre-ohos cfg 门（not(target_env = "musl")）在 aarch64-unknown-linux-ohos 上
  误启用 glibc-only 符号（O_FSYNC/mqueue/aio 等，真机实测 51 个编译错误），
  任何 libc 版本都无法满足（musl 模块本就无这些符号）；上游声明范围 <0.24 内
  无 ohos 感知版本，ohos 修复出现在已移除 mount API 的 nix >=0.27。该补丁仅
  调整依赖解析的目标适用范围，不改动任何上游测试用例；非 OHOS 平台行为与
  上游完全一致（nix 仍生效）。集成测试目标（tests/，依赖 nix）在 OHOS 上
  无法编译也无法运行（见 test_package/MANIFEST.yml 审计），单元测试 41 个
  （cargo 结果行 lib 18 + bin 23）经 cargo test --lib --bins 真实运行。

工具链处理遵循 archives/a/argc/1.24.0 先例：探测已知 cargo 位置（优先
.real 真身，绕开 Harmonybrew Cellar 硬编码 wrapper）；缺失时引导（详见
_bootstrap_rust_toolchain）：rustc/std 取自 Harmonybrew rust 1.99.0
bottle（预签名 ELF 自洽），cargo 取自官方 rust dist 的 ohos 组件并用
binary-sign-tool selfSign 签名——HMDFS 只执行带 .codesign 的 ELF（E264），
而 1.99.0 起 Harmonybrew bottle 的 cargo 依赖 libgit2/sqlite/curl 闭包
（nghttp 系列 formula 缺失不可满足）且旧版 bottle 已全部下架。下载器无
CA bundle 时 urllib 侧指 CA 后走 TLS 校验。cargo 依赖经 .cargo/config.toml
切 rsproxy.cn sparse 镜像（设备直达 crates.io TLS 失败，真机实测镜像可
达），并以放宽的 retry/timeout 容忍慢速抖动。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.layout import basic_layout

# OHOS 无 systemd：SYSTEMD_UTIL_DIR 编译期占位（仅被 env!() 内联为字符串，
# 见模块 docstring；真实 mkswap 依赖的 systemd-makefs 在 OHOS 不存在）
_SYSTEMD_UTIL_DIR = "/usr/lib/systemd"
# OHOS 无 systemd pc 模块：三个安装目录变量全部用 make 命令行占位覆盖，
# pkg-config 完全不执行（program 目标只 require SYSTEMD_UTIL_DIR，其余两个
# 仅消除 $(shell pkg-config ...) 的日志噪音）
_SYSTEMD_SYSTEM_GENERATOR_DIR = "/usr/lib/systemd/system-generators"
_SYSTEMD_SYSTEM_UNIT_DIR = "/usr/lib/systemd/system"


class ZramConan(ConanFile):
    name = "zram"
    version = "1.2.1"
    description = "Systemd unit generator for zram swap devices (OHOS: standalone CLI)"
    license = "MIT"
    homepage = "https://github.com/systemd/zram-generator"
    url = "https://github.com/systemd/zram-generator"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    exports_sources = "patches/*"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    # ------------------------------------------------------------------
    # cargo 工具链解析（argc/1.24.0 先例）
    # ------------------------------------------------------------------
    @staticmethod
    def _find_cargo():
        """探测 OHOS 设备上已知位置的 cargo（HNP、Harmonybrew、rustup、
        usr/local）。

        Harmonybrew bottles 的 ``bin/cargo`` 是 exec 硬编码 Cellar 绝对路径
        的 wrapper 脚本，解包到别处后该路径失效（rc=127）。优先取同级
        ``.real`` 真身，确保执行真实二进制而非 wrapper。
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
        """用 Python urllib 下载工具链压缩包（Harmonybrew bottle 或官方 rust dist）。

        设备 Python 无默认 CA bundle，urllib 直接连会
        SSL: CERTIFICATE_VERIFY_FAILED。先把 SSL_CERT_FILE 指向系统 CA 存储
        （usr/local/ssl cert.pem 经 astra/boolector/boost-build 真机验证），
        保持 TLS 校验下载；仅当设备完全没有 CA 存储时，才对固定的内部
        Harmonybrew 镜像用不校验上下文兜底（E185 / kosli-cli 先例）——没有
        工具链包就无法构建。
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
        """下载并解包 OHOS Rust 工具链（buildbot 沙箱 PATH 探测不到 cargo
        时的兜底，返回可执行的 cargo 绝对路径）。

        2026-10 实证：Harmonybrew 只剩 rust 1.99.0 bottle（旧版全部下架），
        且该 bottle 的 bin/cargo 直接链接 libgit2/sqlite/libssh2/openssl@4/
        libcurl 闭包，而 libcurl 依赖的 nghttp2/nghttp3/ngtcp2 在
        Harmonybrew 无 formula，闭包不可满足——bottle 内 cargo 不可执行。
        故拆分来源：rustc/std 取自 Harmonybrew bottle（预签名、ELF 自洽，
        仅需 bottle 内 librustc_driver 与 zlib-ng-compat/zstd 提供的
        libz.so.1/libzstd.so.1）；cargo 取自官方 rust dist 的
        aarch64-unknown-linux-ohos 组件（static.rust-lang.org 按版本归档、
        永不剪除；NEEDED 仅 libssl.so/libcrypto.so/libz.so/libc.so，由
        openssl3/zlib-ng-compat bottle 精确提供）。HMDFS 只执行带
        .codesign 的 ELF（E264；官方 dist 二进制未签名，直接 exec 报
        EACCES），下载后用 binary-sign-tool selfSign 签名（abbtr/1.0.4 的
        Go SDK 签名同款 argv）。"""
        import subprocess
        import tarfile

        base = os.path.join(self.build_folder, "rust-toolchain")
        os.makedirs(base, exist_ok=True)
        sources = {
            "rust": "https://harmonybrew.atomgit.com/bottles/rust-1.99.0.arm64_ohos.bottle.tar.gz",
            "openssl3": "https://harmonybrew.atomgit.com/bottles/openssl%403-3.6.5_1.arm64_ohos.bottle.tar.gz",
            "zlib": "https://harmonybrew.atomgit.com/bottles/zlib-ng-compat-2.3.3_2.arm64_ohos.bottle.1.tar.gz",
            "zstd": "https://harmonybrew.atomgit.com/bottles/zstd-1.5.7_2.arm64_ohos.bottle.1.tar.gz",
            "cargo": "https://static.rust-lang.org/dist/2026-10-01/cargo-1.99.0-aarch64-unknown-linux-ohos.tar.gz",
        }
        for name, url in sources.items():
            tgz = os.path.join(base, name + ".tar.gz")
            if not os.path.isfile(tgz):
                self._download_bottle(url, tgz)
            # cargo dist 解到独立子目录，避免与 bottle 的 bin/cargo 同名混淆
            dest = base if name != "cargo" else os.path.join(base, "cargo-dist")
            os.makedirs(dest, exist_ok=True)
            with tarfile.open(tgz, "r:gz") as tf:
                tf.extractall(dest)

        # cargo：官方 dist 包内的真实 ELF
        cargo_bin = None
        for root, _dirs, files in os.walk(os.path.join(base, "cargo-dist")):
            if os.path.basename(root) == "bin" and "cargo" in files:
                cargo_bin = os.path.join(root, "cargo")
                break
        if not cargo_bin:
            raise ConanInvalidConfiguration(
                "failed to bootstrap Rust toolchain: cargo not found in dist"
            )
        with open(cargo_bin, "rb") as f:
            if b".codesign" not in f.read():
                signer = (shutil.which("binary-sign-tool")
                          or "/data/service/hnp/bin/binary-sign-tool")
                if not os.path.isfile(signer):
                    raise ConanInvalidConfiguration(
                        "binary-sign-tool is required to sign the "
                        "bootstrapped cargo ELF"
                    )
                tmp_out = cargo_bin + ".signed"
                subprocess.check_call(
                    [signer, "sign", "-selfSign", "1",
                     "-inFile", cargo_bin, "-outFile", tmp_out,
                     "-signAlg", "SHA256withECDSA"]
                )
                os.replace(tmp_out, cargo_bin)
        os.chmod(cargo_bin, 0o755)

        # rustc：Harmonybrew bottle 的 bin/rustc（真实 ELF，Harmonybrew 预
        # 签名；经 RUSTC 显式指定，避免 PATH 顺序歧义）
        rustc_bin = None
        for root, _dirs, files in os.walk(base):
            if os.path.basename(root) == "bin" and "rustc" in files:
                rustc_bin = os.path.join(root, "rustc")
                break
        if not rustc_bin:
            raise ConanInvalidConfiguration(
                "failed to bootstrap Rust toolchain: rustc not found in bottles"
            )
        os.environ["RUSTC"] = rustc_bin
        os.environ["PATH"] = (os.path.dirname(rustc_bin) + os.pathsep
                              + os.environ.get("PATH", ""))

        # OHOS loader 忽略 DT_RUNPATH：dist cargo 需 libssl/libcrypto/libz
        # （openssl3/zlib-ng-compat），librustc_driver 需 libz.so.1/
        # libzstd.so.1（zlib-ng-compat/zstd）——收集全部含 lib*.so* 的
        # lib 目录放进 LD_LIBRARY_PATH
        lib_dirs = []
        for root, _dirs, files in os.walk(base):
            if os.path.basename(root) == "lib" and any(
                    f.startswith("lib") and ".so" in f for f in files):
                lib_dirs.append(root)
        if lib_dirs:
            prev = os.environ.get("LD_LIBRARY_PATH", "")
            os.environ["LD_LIBRARY_PATH"] = ":".join(lib_dirs + ([prev] if prev else []))
        return cargo_bin

    def _ensure_cargo(self):
        """返回 cargo 绝对路径；设备无 cargo 时引导工具链（Harmonybrew
        bottle rustc/std + 官方 dist cargo，见 _bootstrap_rust_toolchain）。"""
        cargo = self._find_cargo()
        if not cargo:
            cargo = self._bootstrap_rust_toolchain()
        if cargo:
            os.environ["PATH"] = os.path.dirname(cargo) + os.pathsep + os.environ.get("PATH", "")
            return cargo
        raise ConanInvalidConfiguration("cargo toolchain is required to build zram-generator")

    def _build_env(self):
        """构建环境：clang 作为 C 链接器（build script 用）、可写 TMPDIR
        （OHOS /tmp 只读）、make/clang 在 PATH、cargo TLS 用系统 CA 存储。"""
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
            tmpdir = os.path.join(os.path.expanduser("~"), "tmp", "zram")
            os.makedirs(tmpdir, exist_ok=True)
        for var in ("TMPDIR", "TMP", "TEMP"):
            env[var] = tmpdir
        # make（GNU Make，HNP）与 clang 默认不在 PATH 上
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

    @staticmethod
    def _cargo_config_text(target_dir):
        """.cargo/config.toml 内容：OHOS clang 链接器 + rsproxy.cn sparse
        镜像 + 网络容错（与 argc/1.24.0 generate() 一致）。target-dir 用
        源码根绝对路径，保证 Makefile 相对路径 target/release 与 package()
        探测一致。"""
        return (
            "[build]\n"
            'target-dir = "%s"\n'
            "\n[target.aarch64-unknown-linux-ohos]\n"
            'linker = "/data/service/hnp/bin/clang"\n'
            "\n[source.crates-io]\n"
            'replace-with = "rsproxy-sparse"\n'
            "\n[source.rsproxy-sparse]\n"
            'registry = "sparse+https://rsproxy.cn/index/"\n'
            "\n[net]\n"
            "retry = 10\n"
            "\n[http]\n"
            "timeout = 600\n"
            "low-speed-limit = 1\n"
        ) % target_dir

    def _write_cargo_config(self, src_root, target_dir):
        """把 .cargo/config.toml 写入源码根（cargo 从 make -C 的 cwd=<src>
        起向上查找配置；cargo 运行目录即源码根）。"""
        cargo_dir = os.path.join(src_root, ".cargo")
        os.makedirs(cargo_dir, exist_ok=True)
        config_path = os.path.join(cargo_dir, "config.toml")
        with open(config_path, "w") as f:
            f.write(self._cargo_config_text(target_dir))
        return config_path

    def _run_with_retry(self, cmd, what):
        """执行命令，失败时重试一次。

        HMDFS 上出现过 ETXTBSY（os error 26, Text file busy）：cargo 并发写
        出 build-script 二进制后立即 exec，FUSE 写回仍持有 fd 导致偶发失败
        （真机预检第一轮实测命中一次，重跑即过）。 genuine 编译错误在第二轮
        照样失败并抛出，不受影响。
        """
        try:
            self.run(cmd)
        except ConanException:
            self.output.warning(
                "%s failed once (possible HMDFS ETXTBSY flake), retrying" % what
            )
            self.run(cmd)

    def build(self):
        cargo = self._ensure_cargo()
        # cargo 的 target/ 固定在源码根（绝对路径 target-dir，见上）
        target_dir = os.path.join(self.source_folder, "target")
        self._write_cargo_config(self.source_folder, target_dir)
        env = self._build_env()
        saved_env = dict(os.environ)
        os.environ.update(env)
        try:
            # 上游 Makefile program 目标 = cargo build --release（BUILDTYPE
            # 默认 release，override CARGOFLAGS 自动补 --release）。
            # make 命令行变量覆盖绕开 pkg-config systemd 硬门（零补丁，三个
            # SYSTEMD_* 变量全量覆盖，pkg-config 不再执行）；NOMAN=1 跳过
            # ronn man 页；SYSTEMD_UTIL_DIR 经 Makefile export 进入 cargo
            # 环境（src/setup.rs env!() 编译期内联必需）。
            self._run_with_retry(
                'make -C "%s" program NOMAN=1 CARGO="%s" '
                'SYSTEMD_UTIL_DIR="%s" '
                'SYSTEMD_SYSTEM_GENERATOR_DIR="%s" '
                'SYSTEMD_SYSTEM_UNIT_DIR="%s"'
                % (self.source_folder, cargo,
                   _SYSTEMD_UTIL_DIR, _SYSTEMD_SYSTEM_GENERATOR_DIR,
                   _SYSTEMD_SYSTEM_UNIT_DIR),
                "make program",
            )
        finally:
            os.environ.clear()
            os.environ.update(saved_env)

    def package(self):
        # cargo target/ 在源码根（见 build()）；兼容 build 目录命中
        target_dir = os.path.join(self.source_folder, "target", "release")
        if not os.path.isfile(os.path.join(target_dir, "zram-generator")):
            target_dir = os.path.join(self.build_folder, "target", "release")
        copy(self, "zram-generator", src=target_dir,
             dst=os.path.join(self.package_folder, "bin"))
        # 示例配置随包保留（文档级；上游 install 装到 share/doc/zram-generator）
        copy(self, "zram-generator.conf.example", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc", "zram-generator"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
