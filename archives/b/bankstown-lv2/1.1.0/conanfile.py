#!/usr/bin/env python3
"""Conan recipe — bankstown-lv2 1.1.0 (cargo, Rust cdylib LV2 plugin).

bankstown is a barebones psychoacoustic bass enhancement LV2 plugin by
chadmed, written in Rust. It builds as a ``cdylib`` via ``cargo build
--release`` producing ``libbankstown.so``, which is installed into an
LV2 bundle (``lib/lv2/bankstown.lv2/``) alongside ``manifest.ttl`` and
``bankstown.ttl``.

Upstream has NO test suite (no tests/ dir, no #[test], no dev-dependencies,
no Makefile test target) — verification is done from the test_package phase:
a real C consumer dlopens the packaged ``bankstown.so``, resolves the LV2
``lv2_descriptor(0)`` entry point and drives the plugin's full LV2 C API
(instantiate → connect_port → run → deactivate → cleanup), then audits the
bundle layout. The HMBS_UPSTREAM_TEST_RESULT marker reports
status=no_tests (upstream_tests_exist: false, sipcalc/xsel precedents).

OHOS adaptation notes:
- lv2-sys 2.0.0 (rust-lv2's FFI crate) selects its pre-generated C binding
  modules with ``#[cfg(target_os = "linux")]`` / ``"windows"`` only; on OHOS
  the target reports ``target_os = "ohos"`` so it falls through to
  ``compile_error!("The targeted operation system is not supported by
  rust-lv2!")``.  The crate ships ``src/linux/aarch64.rs`` which is
  arch-generic (no libc dependency, pure type/const bindings), so the fix is
  to add an ``ohos`` cfg-attr alias in the vendored crate: cfg-attr both
  ``target_os = "linux"`` and ``target_os = "ohos"`` to the linux module.
  This is applied to a vendored copy via a Cargo ``[patch.crates-io]`` entry
  in ``.cargo/config.toml``, so the upstream source tree is not touched.
- OHOS Rust target is ``aarch64-unknown-linux-ohos``; no crates.io CA bundle
  on the worker, so crates are fetched through the rsproxy.cn sparse mirror
  and clang is used as the linker.
- Rust toolchain: probe well-known OHOS locations first; if absent bootstrap
  from the Harmonybrew bottles (argc/at51/martin precedents).
"""
import hashlib
import os
import shutil
import tarfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout

# lv2-sys 2.0.0 crate — pinned by Cargo.lock. Downloaded from rsproxy.cn
# (reachable on the device; crates.io direct has no CA bundle) and vendored
# under the build folder so the OHOS target_os patch can be applied.
# sha256 verified against the official crates.io crate.
_LV2_SYS_VERSION = "2.0.0"
_LV2_SYS_URL = "https://rsproxy.cn/api/v1/crates/lv2-sys/{v}/download"
_LV2_SYS_SHA256 = "9dd0f9e7de3649dcec348de51cbf611ab88688b97c0ce038f8c07b996b2a8e30"

_RS_CFG = (
    '[build]\ntarget-dir = "target"\n'
    '\n[source.crates-io]\n'
    'replace-with = "rsproxy-sparse"\n'
    '\n[source.rsproxy-sparse]\n'
    'registry = "sparse+https://rsproxy.cn/index/"\n'
    '\n[net]\n'
    'retry = 10\n'
    '\n[http]\n'
    'timeout = 600\n'
    'low-speed-limit = 1\n'
)


class BankstownLv2Conan(ConanFile):
    name = "bankstown-lv2"
    version = "1.1.0"
    description = "A barebones, fast LV2 bass enhancement plugin (psychoacoustic sub-bass harmonics)"
    license = "MIT"
    homepage = "https://github.com/chadmed/bankstown"
    url = "https://github.com/chadmed/bankstown"

    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if str(self.settings.os) not in ("OHOS", "Linux"):
            raise ConanInvalidConfiguration(
                f"bankstown-lv2 supports OHOS and Linux only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # .cargo/config.toml: clang 链接器（OHOS 无 cc 符号）+ rsproxy.cn
        # sparse 镜像 + 网络容错（argc/martin 先例）。source_folder ==
        # build_folder（basic_layout），cargo 从源码目录运行即读到该配置。
        cargo_dir = os.path.join(self.build_folder, ".cargo")
        os.makedirs(cargo_dir, exist_ok=True)
        config_path = os.path.join(cargo_dir, "config.toml")
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(_RS_CFG)
            if str(self.settings.os) == "OHOS":
                f.write(
                    "\n[target.aarch64-unknown-linux-ohos]\n"
                    'linker = "/data/service/hnp/bin/clang"\n'
                )

    def build(self):
        # /tmp 只读且常满（OHOS worker），用可写 TMPDIR。
        tmpdir = os.environ.get("HMBS_TMPDIR") or os.environ.get("TMPDIR")
        if not tmpdir:
            tmpdir = os.path.join(os.path.expanduser("~"), "tmp", "bankstown-lv2")
            os.makedirs(tmpdir, exist_ok=True)
        for var in ("TMPDIR", "TMP", "TEMP"):
            os.environ[var] = tmpdir

        cargo = self._ensure_cargo()
        self._configure_build_env(cargo)
        self._apply_lv2_sys_patch()

        # 去掉 --locked：Cargo [patch] 会把 Cargo.lock 里 lv2-sys 的 source
        # 记录改写为本地 vendor 路径，--locked 会拒绝这个 lock 更新。
        self.run(
            f'"{cargo}" build --release',
            cwd=self.source_folder,
            env="conanbuild",
        )
        self.output.info("bankstown-lv2 cargo build --release completed")

    def package(self):
        # LV2 bundle: 二进制 libbankstown.so → bankstown.so, 与 manifest.ttl、
        # bankstown.ttl 一起装入 lib/lv2/bankstown.lv2/（LV2 文件系统层级规范）。
        src_so = self._find_release_so()
        if not src_so:
            raise ConanInvalidConfiguration(
                "libbankstown.so not found in cargo release target directories"
            )
        bundle = os.path.join(self.package_folder, "lib", "lv2", "bankstown.lv2")
        os.makedirs(bundle, exist_ok=True)
        copy(self, os.path.basename(src_so), src=os.path.dirname(src_so),
             dst=bundle, keep_path=False)
        os.replace(os.path.join(bundle, os.path.basename(src_so)),
                   os.path.join(bundle, "bankstown.so"))
        copy(self, "bankstown.ttl", src=self.source_folder, dst=bundle, keep_path=False)
        copy(self, "manifest.ttl", src=self.source_folder, dst=bundle, keep_path=False)
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        self.output.info(
            "bankstown-lv2 installed to {}".format(bundle)
        )

    def package_info(self):
        # LV2 插件 bundle: 头文件/库在 bundle 目录内, 无导出 include/lib。
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["lib/lv2"]

    # ------------------------------------------------------------------
    # cargo toolchain resolution + bootstrap
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
            os.path.expanduser("~/.harmonybrew/bin/cargo"),
            os.path.expanduser("~/.cargo/bin/cargo"),
            "/data/service/hnp/bin/cargo",
            "/storage/Users/currentUser/usr/local/bin/cargo",
            "/storage/Users/currentUser/.harmonybrew/bin/cargo",
            "/storage/Users/currentUser/.cargo/bin/cargo",
        ]
        for cand in candidates:
            if not cand:
                continue
            if not cand.endswith(".real") and os.path.isfile(cand + ".real"):
                cand = cand + ".real"
            if os.path.isfile(cand) and os.access(cand, os.X_OK):
                return cand
        return None

    def _download_file(self, url, destination):
        """Download a file with Python urllib.

        The device Python has no default CA bundle, so urllib fails with
        SSL: CERTIFICATE_VERIFY_FAILED. Point SSL_CERT_FILE at the first
        available system CA store; only when no CA store exists at all,
        fall back to an unverified context for the fixed internal mirrors
        (Harmonybrew bottles / rsproxy, argc/at51 precedent).
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
            urllib.request.urlretrieve(url, destination)
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
                    open(destination, "wb") as out:
                shutil.copyfileobj(resp, out)

    def _bootstrap_rust_toolchain(self):
        """Download and unpack the Harmonybrew OHOS Rust toolchain bottles
        (argc/at51/martin precedent)."""
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
                self._download_file(url, tgz)
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
            with open(wrapper, "w", encoding="utf-8") as f:
                f.write("#!/bin/sh\n")
                f.write("# repaired by bankstown-lv2 recipe: exec local .real binary\n")
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
        raise ConanInvalidConfiguration("cargo toolchain is required to build bankstown-lv2")

    # ------------------------------------------------------------------
    # build environment + lv2-sys OHOS patch
    # ------------------------------------------------------------------
    def _configure_build_env(self, cargo):
        """Env for cargo build: clang as the C linker, writable TMPDIR,
        and a CA bundle for cargo's TLS when the system provides one."""
        clang = self._select_clang()
        clangxx = shutil.which("clang++") or "/data/service/hnp/bin/clang++"
        os.environ["CC"] = clang
        os.environ["CXX"] = clangxx
        os.environ.setdefault("CFLAGS", "-fPIC -O2")
        os.environ.setdefault("CXXFLAGS", "-fPIC -O2")
        # cdylib 用 clang 链接；OHOS SDK sysroot 存在时附加 --code-sign
        # （at51 先例：真机 dlopen/加载需要 code-sign，缺少会加载失败）。
        link_args = [f"-C linker={clang}"]
        bin_dir = os.path.dirname(clang)
        sysroot = os.path.abspath(os.path.join(bin_dir, "..", "sysroot"))
        if os.path.isdir(sysroot):
            link_args.append("-C link-arg=-Wl,--code-sign")
        os.environ["RUSTFLAGS"] = " ".join(link_args)

        if not os.environ.get("SSL_CERT_FILE"):
            for ca in ("/storage/Users/currentUser/usr/local/ssl/cert.pem",
                       "/etc/ssl/certs/cacert.pem",
                       "/etc/ssl/cert.pem",
                       os.path.expanduser("~/.harmonybrew/etc/ca-certificates/cert.pem")):
                if os.path.isfile(ca):
                    os.environ["SSL_CERT_FILE"] = ca
                    os.environ["CURL_CA_BUNDLE"] = ca
                    break

    def _select_clang(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        candidates = [
            compilers.get("c"),
            shutil.which("clang"),
            "/data/service/hnp/bin/clang",
            "/storage/Users/currentUser/usr/local/bin/clang",
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        raise ConanInvalidConfiguration("usable OHOS clang toolchain not found")

    def _apply_lv2_sys_patch(self):
        """Vendor lv2-sys-2.0.0 under the build folder, patch the OHOS
        target_os gate, and register it via a Cargo [patch.crates-io]
        entry appended to .cargo/config.toml.

        lv2-sys selects its pre-generated binding modules with
        ``#[cfg(target_os = "linux")]`` / ``"windows"`` in src/lib.rs; on
        OHOS the Rust target reports ``target_os = "ohos"`` so the crate
        falls through to ``compile_error!`` in src/unsupported.rs.  The
        shipped ``src/linux/aarch64.rs`` is pure type/const bindings with
        no libc dependency, so aliasing both linux and ohos cfg-attr to
        the linux module is sufficient.  On Linux (non-OHOS) the patch is
        skipped and the regular crates.io/rsproxy crate is used.
        """
        if str(self.settings.os) != "OHOS":
            return

        vendor_dir = os.path.join(self.build_folder, "vendor", "lv2-sys")
        crate_src = os.path.join(vendor_dir, "src", "lib.rs")

        if not os.path.isfile(crate_src):
            os.makedirs(vendor_dir, exist_ok=True)
            tgz = os.path.join(self.build_folder, "vendor",
                               f"lv2-sys-{_LV2_SYS_VERSION}.crate")
            if not os.path.isfile(tgz):
                self._download_file(_LV2_SYS_URL.format(v=_LV2_SYS_VERSION), tgz)
            with open(tgz, "rb") as f:
                if hashlib.sha256(f.read()).hexdigest() != _LV2_SYS_SHA256:
                    raise ConanInvalidConfiguration(
                        "lv2-sys sha256 mismatch: %s" % tgz
                    )
            with tarfile.open(tgz, "r:gz") as tf:
                # crate tarball 顶层是 lv2-sys-2.0.0/，剥一层放到 vendor/lv2-sys
                for member in tf.getmembers():
                    stripped = member.name.split("/", 1)[-1]
                    if not stripped:
                        continue
                    member.name = stripped
                    tf.extract(member, vendor_dir)
            try:
                os.remove(tgz)
            except OSError:
                pass

            with open(crate_src, "r", encoding="utf-8") as f:
                content = f.read()
            content = content.replace(
                '#[cfg_attr(target_os = "linux", path = "linux/mod.rs")]',
                '#[cfg_attr(target_os = "linux", path = "linux/mod.rs")]\n'
                '#[cfg_attr(target_os = "ohos", path = "linux/mod.rs")]',
            )
            with open(crate_src, "w", encoding="utf-8") as f:
                f.write(content)
            self.output.info(
                "patched lv2-sys-%s for OHOS (target_os=ohos -> linux bindings)" % _LV2_SYS_VERSION
            )

        # 把 [patch.crates-io] 追加到 generate() 写好的 .cargo/config.toml，
        # 指向打过补丁的 vendor 目录（Cargo.lock 锁定 2.0.0，patch 同名同
        # 版本覆盖；[patch] 与 [source] replace-with 可共存，patch 优先）。
        config_path = os.path.join(self.build_folder, ".cargo", "config.toml")
        patch_block = (
            "\n[patch.crates-io]\n"
            f'lv2-sys = {{ path = "{vendor_dir}" }}\n'
        )
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()
        if "patch.crates-io" not in content:
            with open(config_path, "a", encoding="utf-8") as f:
                f.write(patch_block)
            self.output.info("lv2-sys vendored + registered in .cargo/config.toml")

    def _find_release_so(self):
        """Locate libbankstown.so in candidate cargo release dirs.

        cargo build runs with cwd=self.source_folder, so the Cargo.toml
        target dir lands under the source folder copy (target/release);
        CARGO_TARGET_DIR may also redirect it into the build folder.  Try
        the known candidates first, then fall back to a recursive walk
        across both folders so a different target-dir layout can never
        silently produce a missing-binary package failure.
        """
        target_dirs = [
            os.environ.get("CARGO_TARGET_DIR"),
            os.path.join(self.build_folder, "target"),
            os.path.join(self.source_folder, "target"),
        ]
        for base in target_dirs:
            if not base:
                continue
            for name in ("libbankstown.so", "libbankstown.dylib"):
                cand = os.path.join(base, "release", name)
                if os.path.isfile(cand):
                    return cand
        # Recursive fallback across build/source trees.
        for root in (self.build_folder, self.source_folder):
            if not root or not os.path.isdir(root):
                continue
            for current, _dirs, files in os.walk(root):
                if os.path.basename(current) != "release":
                    continue
                for name in ("libbankstown.so", "libbankstown.dylib"):
                    cand = os.path.join(current, name)
                    if os.path.isfile(cand):
                        return cand
        return None