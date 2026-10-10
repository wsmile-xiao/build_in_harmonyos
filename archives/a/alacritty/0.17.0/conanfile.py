#!/usr/bin/env python3
"""Conan recipe — alacritty 0.17.0 (cargo)

alacritty is a fast, cross-platform, OpenGL terminal emulator written in
Rust (alacritty/alacritty, Apache-2.0). Upstream is a 4-crate workspace
(alacritty / alacritty_terminal / alacritty_config /
alacritty_config_derive); the ``alacritty`` bin is built with
``cargo build --release --manifest-path alacritty/Cargo.toml``.

OHOS 适配要点（0 源码补丁，纯 feature 开关）：
- 以 ``--no-default-features --features wayland`` 构建。根因：glutin
  0.32.3 的 build.rs cfg_aliases 把 ``target_env = "ohos"`` 排除出
  ``free_unix``（x11_platform/wayland_platform 均为 false，其平台模块
  在 OHOS 上被编出），而 winit 0.30.13 的 ``free_unix`` 不排除 ohos——
  开默认 x11 feature 时 alacritty 只用 ``not(macos/windows)`` 门控的
  x11 代码会引用不存在的 ``glutin::platform::x11`` / ``x11_visual`` /
  ``DisplayApiPreference::EglThenGlx``（E0432/E0599）。关闭 x11 feature
  后相关代码全部编出；winit 的 wayland 后端（free_unix 含 ohos）+
  glutin 的 egl_backend（不排除 ohos）提供窗口/GL 路径（鸿蒙 PC 即
  Wayland 合成器体系）。OHOS 上 x11 后端无意义，无功能损失。
- 工具链处理沿用 archives/a/argc/1.24.0（已合入）：先探测已知 cargo
  位置；无则用 Python urllib 从 Harmonybrew bottles 自举 OHOS Rust
  工具链（rust-1.98.1_1 r1 版：cargo.real 仅链 libc/libssl/libcrypto/
  libz，openssl3 + zlib 3 瓶集闭包；r2 版 cargo 动态链 libgit2/
  libssh2/libcurl/libsqlite3 需 12+ 瓶，libsignal-core 0.103.1 同款
  取舍），并修复 bottle 内硬编码 Cellar 路径的 wrapper 脚本。
- fontconfig（crossfont → yeslogic-fontconfig-sys 经 pkg-config 链接）：
  不做运行时动态链接（实测 conan 缓存构建的 libfontconfig.so.1 在
  hmdfs 上被 musl loader 以 EACCES 拒绝加载，改权限位/换目录均无效；
  Harmonybrew 构建的同名 .so 可正常加载），改为从 Harmonybrew bottles
  自举**静态 fontconfig 闭包**（libfontconfig.a + libexpat.a + libintl.a
  + libfreetype.a + libz.a + libbz2.a + libpng16.a），合成自包含
  fontconfig.pc（无 Requires）挂到 PKG_CONFIG_PATH，并用 RUSTFLAGS
  ``-L <闭包目录>`` 前置（链接顺序先到先得，闭包 .a 优先）。freetype
  本体由 freetype-sys 对 ohos target 自动 vendored 编译。结果：
  bin/alacritty NEEDED 仅 libc++_shared.so + libc.so（/system/lib64
  系统自带），消费者无需任何 LD_LIBRARY_PATH。
- 上游测试在 test_package 阶段执行（hmbs 预检只从 test_package 阶段
  stdout 采集 HMBS_UPSTREAM_TEST_RESULT 标记，tlsx/1.2.2 先例）。
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class AlacrittyConan(ConanFile):
    name = "alacritty"
    version = "0.17.0"
    description = "A fast, cross-platform, OpenGL terminal emulator"
    license = "Apache-2.0"
    homepage = "https://alacritty.org"
    url = "https://github.com/alacritty/alacritty"
    topics = ("terminal", "emulator", "rust", "opengl", "wayland")

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self, src_folder="src")

    def validate(self):
        # R32: settings.os check must use in (Linux, OHOS)
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"alacritty supports Linux and OHOS only, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------
    # .cargo/config.toml: clang 链接器 + rsproxy.cn sparse 镜像 + 网络容错
    # ------------------------------------------------------------------
    def _cargo_config_content(self):
        # 与 argc/1.24.0、libsignal-core 家族一致；两处设备实测增补：
        # (1) multiplexing=false——设备 cargo 链接的 libcurl 可能未编译
        #     HTTP/2，sparse 索引默认多路复用直接报
        #     "failed to enable HTTP/2, is curl not built right?"，
        #     强制 HTTP/1.1 后 rsproxy.cn sparse 正常；
        # (2) cainfo 指向存在的系统 CA 存储（设备无默认 CA bundle）。
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
            "multiplexing = false\n"
        )
        for ca in self._ca_candidates():
            if os.path.isfile(ca):
                content += 'cainfo = "%s"\n' % ca
                break
        return content

    @staticmethod
    def _ca_candidates():
        return [
            "/storage/Users/currentUser/usr/local/ssl/cert.pem",
            "/etc/ssl/certs/cacert.pem",
            "/etc/ssl/cert.pem",
            os.path.expanduser("~/.harmonybrew/etc/ca-certificates/cert.pem"),
        ]

    def _write_cargo_configs(self):
        """Write .cargo/config.toml into both the source and build folders.

        cargo discovers config.toml from the cwd and its ancestors; build()
        runs with cwd = source folder (where Cargo.toml lives), so the
        config MUST exist there — writing only the build folder is never
        discovered (libsignal-core 0.103.1 CI #63478 precedent). The build
        folder copy is kept for conan-layout compatibility.
        """
        content = self._cargo_config_content()
        for base in (self.source_folder, self.build_folder):
            cargo_dir = os.path.join(base, ".cargo")
            os.makedirs(cargo_dir, exist_ok=True)
            with open(os.path.join(cargo_dir, "config.toml"), "w") as f:
                f.write(content)

    # ------------------------------------------------------------------
    # Rust 工具链 + fontconfig 静态闭包自举（照搬 argc 1.24.0 范式）
    # ------------------------------------------------------------------
    # Rust 工具链瓶（仅当设备无 cargo 时才下载解包）
    _RUST_BOTTLES = {
        # r1 版：cargo.real 仅链 libc/libssl/libcrypto/libz（NEEDED 实测），
        # openssl3 + zlib 3 瓶集即全覆盖；r2 版（rust-1.98.1_2）的 cargo
        # 动态链 libgit2/libssh2/libcurl/libsqlite3，需 12+ 瓶传递闭包
        "rust": "https://harmonybrew.atomgit.com/bottles/rust-1.98.1_1.arm64_ohos.bottle.tar.gz",
        "openssl3": "https://harmonybrew.atomgit.com/bottles/openssl%403-3.6.4_1.arm64_ohos.bottle.tar.gz",
        "zlib": "https://harmonybrew.atomgit.com/bottles/zlib-ng-compat-2.3.3_2.arm64_ohos.bottle.tar.gz",
    }

    # fontconfig 静态闭包瓶（链接期使用，始终需要）：libfontconfig.a 引用
    # XML_* (expat)、libintl_dgettext (gettext)、FT_* (freetype 兜底归档)；
    # freetype.a 引用 png_/BZ2_/zlib 符号
    _FC_BOTTLES = {
        "fontconfig": "https://harmonybrew.atomgit.com/bottles/fontconfig-2.17.1_1.arm64_ohos.bottle.tar.gz",
        "freetype": "https://harmonybrew.atomgit.com/bottles/freetype-2.14.3_1.arm64_ohos.bottle.tar.gz",
        "expat": "https://harmonybrew.atomgit.com/bottles/expat-2.8.4_1.arm64_ohos.bottle.tar.gz",
        "gettext": "https://harmonybrew.atomgit.com/bottles/gettext-1.0_1.arm64_ohos.bottle.tar.gz",
        "libpng": "https://harmonybrew.atomgit.com/bottles/libpng-1.6.58_1.arm64_ohos.bottle.1.tar.gz",
        "bzip2": "https://harmonybrew.atomgit.com/bottles/bzip2-1.0.8_2.arm64_ohos.bottle.tar.gz",
        "zlib": "https://harmonybrew.atomgit.com/bottles/zlib-ng-compat-2.3.3_2.arm64_ohos.bottle.tar.gz",
    }

    _CLOSURE_LIBS = (
        "libfontconfig.a",
        "libexpat.a",
        "libintl.a",
        "libfreetype.a",
        "libz.a",
        "libbz2.a",
        "libpng16.a",
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
        available system CA store so the download stays TLS-verified. Only
        when no CA store exists at all, fall back to an unverified context
        for the fixed internal Harmonybrew mirror (E185 / kosli-cli
        precedent); the package cannot build without the toolchain.
        """
        import ssl
        import urllib.error
        import urllib.request

        if not os.environ.get("SSL_CERT_FILE"):
            for ca in self._ca_candidates():
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

    def _unpack_bottles(self, bottles):
        """Download and unpack the given Harmonybrew bottles into the
        build folder; return the unpack base directory. Idempotent: the
        rust bottle is ~190MB, re-extraction wastes minutes."""
        import tarfile

        base = os.path.join(self.build_folder, "rust-toolchain")
        os.makedirs(base, exist_ok=True)
        for name, url in bottles.items():
            tgz = os.path.join(base, name + ".tar.gz")
            if not os.path.isfile(tgz):
                self._download_bottle(url, tgz)
            if not os.path.isfile(tgz + ".extracted"):
                with tarfile.open(tgz, "r:gz") as tf:
                    tf.extractall(base)
                open(tgz + ".extracted", "w").write("ok")
        return base

    @staticmethod
    def _locate_cargo_in(base):
        """Find cargo under the unpacked bottle base. Old bottles
        (<= rust-1.98.1_1) ship ``bin/cargo`` as a wrapper script execing
        ``cargo.real``; newer ones may ship a plain ELF. Prefer the
        ``.real`` binary, then any non-``#!`` cargo file."""
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
                        continue  # wrapper script (old layout, .real missing)
                cargo_real = cand
                break
        return cargo_real

    @staticmethod
    def _repair_wrappers(bin_dir):
        """Rewrite bottle wrapper scripts that hardcode Cellar absolute
        paths (/storage/Users/currentUser/.harmonybrew/Cellar/...) which do
        not exist once unpacked into the build folder (rc=127). Bottle
        wrappers may be mode 0555 — OHOS denies owner writes strictly, so
        add the write bit first (libsignal-core 0.103.1 precedent)."""
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
                continue  # real ELF, not a wrapper
            try:
                os.chmod(wrapper, os.stat(wrapper).st_mode | 0o200)
            except OSError:
                pass
            with open(wrapper, "w") as f:
                f.write("#!/bin/sh\n")
                f.write("# repaired by alacritty recipe: exec local .real binary\n")
                f.write('exec "%s" "$@"\n' % real)

    @staticmethod
    def _toolchain_lib_dirs(base):
        """Lib dirs providing libssl/libcrypto/libz for the unpacked
        cargo.real (OHOS loader ignores DT_RUNPATH)."""
        lib_dirs = []
        for root, _dirs, files in os.walk(base):
            if os.path.basename(root) == "lib":
                libs = set(files)
                if libs & {"libssl.so", "libcrypto.so", "libz.so"}:
                    lib_dirs.append(root)
        return lib_dirs

    def _ensure_fontconfig_closure(self, base):
        """Collect the static fontconfig closure archives from the unpacked
        bottles into <build>/fontconfig-closure and synthesize a
        self-contained fontconfig.pc there.

        The pc deliberately declares NO Requires (self-contained Libs
        only) so pkg-config resolution never needs an external freetype2.pc,
        and the Libs list covers the whole static closure in dependency
        order (fontconfig → expat/intl → freetype → z/bz2/png).
        """
        closure = os.path.join(self.build_folder, "fontconfig-closure")
        os.makedirs(closure, exist_ok=True)
        found = {}
        for root, _dirs, files in os.walk(base):
            for lib in self._CLOSURE_LIBS:
                if lib in files and lib not in found:
                    found[lib] = os.path.join(root, lib)
        missing = [l for l in self._CLOSURE_LIBS if l not in found]
        if missing:
            raise ConanInvalidConfiguration(
                "fontconfig static closure incomplete, missing: %s" % missing
            )
        for lib, src in found.items():
            dst = os.path.join(closure, lib)
            if not os.path.isfile(dst):
                shutil.copy2(src, dst)
        pc_dir = os.path.join(closure, "pkgconfig")
        os.makedirs(pc_dir, exist_ok=True)
        with open(os.path.join(pc_dir, "fontconfig.pc"), "w") as f:
            f.write("prefix=%s\n" % closure)
            f.write("Name: fontconfig\n")
            f.write(
                "Description: fontconfig static closure "
                "(Harmonybrew arm64_ohos bottles) for OHOS Rust GUI consumers\n"
            )
            f.write("Version: 2.17.1\n")
            f.write(
                "Libs: -L${prefix} -lfontconfig -lexpat -lintl "
                "-lfreetype -lz -lbz2 -lpng16\n"
            )
        self.output.info(
            "fontconfig static closure at %s (%d archives)"
            % (closure, len(found))
        )
        return closure

    def _ensure_toolchain(self):
        """Return (cargo_path, closure_dir).

        Always unpacks the fontconfig closure bottles; only unpacks the
        Rust toolchain bottles when no cargo is found on the system (CI
        workers / clean devices), keeping the fast path fast (~35MB vs
        +190MB)."""
        cargo = self._find_cargo()
        if cargo:
            base = self._unpack_bottles(self._FC_BOTTLES)
        else:
            bottles = dict(self._RUST_BOTTLES)
            bottles.update(self._FC_BOTTLES)
            base = self._unpack_bottles(bottles)
            cargo = self._locate_cargo_in(base)
            if not cargo:
                raise ConanInvalidConfiguration(
                    "failed to bootstrap Rust toolchain from Harmonybrew bottles"
                )
            self._repair_wrappers(os.path.dirname(cargo))
            lib_dirs = self._toolchain_lib_dirs(base)
            if lib_dirs:
                prev = os.environ.get("LD_LIBRARY_PATH", "")
                os.environ["LD_LIBRARY_PATH"] = ":".join(
                    lib_dirs + ([prev] if prev else [])
                )
            os.environ["PATH"] = (
                os.path.dirname(cargo) + os.pathsep + os.environ.get("PATH", "")
            )
        closure = self._ensure_fontconfig_closure(base)
        return cargo, closure

    def _build_env(self, closure_dir):
        """Build env: clang as the C linker for cargo build scripts, the
        static fontconfig closure on PKG_CONFIG_PATH + RUSTFLAGS -L (link
        order: closure .a wins over any system .so), a writable TMPDIR
        (OHOS /tmp is read-only), and a CA bundle for cargo's TLS."""
        env = dict(os.environ)
        clang = shutil.which("clang") or "/data/service/hnp/bin/clang"
        clangxx = shutil.which("clang++") or "/data/service/hnp/bin/clang++"
        env["CC"] = clang
        env["CXX"] = clangxx
        env.setdefault("CFLAGS", "-fPIC -O2")
        env.setdefault("CXXFLAGS", "-fPIC -O2")
        env["RUSTFLAGS"] = f"-C linker={clang} -L {closure_dir}"
        env["PKG_CONFIG_PATH"] = os.path.join(closure_dir, "pkgconfig")
        tmpdir = os.environ.get("HMBS_TMPDIR") or os.environ.get("TMPDIR")
        if not tmpdir:
            tmpdir = os.path.join(os.path.expanduser("~"), "tmp", "alacritty")
            os.makedirs(tmpdir, exist_ok=True)
        for var in ("TMPDIR", "TMP", "TEMP"):
            env[var] = tmpdir
        hnp_bin = "/data/service/hnp/bin"
        if os.path.isdir(hnp_bin):
            env["PATH"] = hnp_bin + os.pathsep + env.get("PATH", "")
        if not env.get("SSL_CERT_FILE"):
            for ca in self._ca_candidates():
                if os.path.isfile(ca):
                    env["SSL_CERT_FILE"] = ca
                    env["CURL_CA_BUNDLE"] = ca
                    break
        return env

    def build(self):
        self._write_cargo_configs()
        cargo, closure = self._ensure_toolchain()
        env = self._build_env(closure)
        self.output.info("building alacritty with cargo: %s" % cargo)
        # 上游 Cargo.lock 与 manifest 完全匹配（sha256 与 tag 归档一致），
        # --locked 保证零重解析、版本零漂移。-j 2：HMFS 上并发链接偶发
        # "Text file busy (os error 26)"（设备实测一次），限并发规避。
        subprocess.check_call(
            [
                cargo, "build", "--release", "--locked", "-j", "2",
                "--no-default-features", "--features", "wayland",
                "--manifest-path", "alacritty/Cargo.toml",
            ],
            cwd=self.source_folder,
            env=env,
        )
        # NOTE: upstream official tests run in test_package/conanfile.py's
        # test() method — hmbs preflight collects the
        # HMBS_UPSTREAM_TEST_RESULT marker from the test_package phase
        # stdout only (tlsx/1.2.2 precedent); build() just produces the
        # alacritty binary.

    def package(self):
        # target-dir resolves relative to the cargo invocation cwd
        # (source folder); probe the build-folder variant as well
        # (libsignal-core 0.103.1 layout precedent).
        target_dir = os.path.join(self.source_folder, "target", "release")
        if not os.path.isfile(os.path.join(target_dir, "alacritty")):
            target_dir = os.path.join(self.build_folder, "target", "release")
        if not os.path.isfile(os.path.join(target_dir, "alacritty")):
            raise ConanInvalidConfiguration(
                "cargo build produced no alacritty binary under %s" % target_dir
            )
        copy(self, "alacritty", src=target_dir,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE-APACHE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "LICENSE-MIT", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
