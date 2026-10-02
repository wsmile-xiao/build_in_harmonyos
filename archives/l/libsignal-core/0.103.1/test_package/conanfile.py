#!/usr/bin/env python3
"""Conan test_package for libsignal-core 0.103.1 — consumer rlib probe + upstream cargo test.

1) test.sh 用 rustc 直接 --extern 链打包的 liblibsignal_core.rlib（+ rand
   依赖 rlib）编译 probe.rs，验证 rlib 交付闭包可用；打印
   HMBS_TEST_PACKAGE_RESULT。
2) 重新下载上游源码 tarball（与 conandata.yml 同 URL 列表 + sha256），
   应用同一个 manifest 补丁（workspace 缩容到 rust/core）+ 用打包产物
   中的重生成 Cargo.lock（package_folder/Cargo.lock，与主配方同一份
   锁，真机零 git 解析）覆盖上游锁，运行上游 cargo test --locked
   -p libsignal-core --lib --release（25 个 src 单测），打印
   HMBS_UPSTREAM_TEST_RESULT。

hmbs preflight 只从 test_package 阶段 stdout 采集标记（tlsx/1.2.2 先例；
build() 阶段输出与包缓存命中时的输出均不被采纳）。
"""
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import download, mkdir, patch, unzip


# Upstream source tarball — same ordered URL list + sha256 as conandata.yml
# (gh-proxy.com mirror first, official GitHub fallback).
_UPSTREAM_URLS = [
    "https://gh-proxy.com/https://github.com/signalapp/libsignal/archive/refs/tags/v0.103.1.tar.gz",
    "https://github.com/signalapp/libsignal/archive/refs/tags/v0.103.1.tar.gz",
]
_UPSTREAM_SHA256 = "1a85145629a2a5ba085c9dbc346d990e7ee5e9a9e5320b88889a0feaa0278c0e"
_PATCH = "0001-minimal-workspace-rust-core.patch"


class LibsignalCoreTestConan(ConanFile):
    """test_package — runs the packaged rlib consumer probe (test.sh) and
    the upstream ``cargo test -p libsignal-core --lib --release`` suite,
    emitting HMBS evidence markers for preflight verification."""
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    # ------------------------------------------------------------------
    # cargo toolchain resolution (mirror of conanfile.py, argc 1.24.0)
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
        available system CA store before connecting; only when no CA
        store exists at all, fall back to an unverified context for the
        fixed internal Harmonybrew mirror (mirror of conanfile.py).
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
        """Download and unpack the Harmonybrew OHOS Rust toolchain bottles
        (mirror of conanfile.py)."""
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
            raise ConanException(
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
        raise ConanException("cargo toolchain is required to run upstream tests")

    def _build_env(self):
        """Env for cargo test: clang as the C linker, a writable TMPDIR
        (OHOS /tmp is read-only), and a CA bundle for cargo's TLS when
        the system provides one (mirror of conanfile.py)."""
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
            tmpdir = os.path.join(os.path.expanduser("~"), "tmp", "libsignal-core-test")
            os.makedirs(tmpdir, exist_ok=True)
        for var in ("TMPDIR", "TMP", "TEMP"):
            env[var] = tmpdir
        hnp_bin = "/data/service/hnp/bin"
        if os.path.isdir(hnp_bin):
            env["PATH"] = hnp_bin + os.pathsep + env.get("PATH", "")
        if not env.get("SSL_CERT_FILE"):
            for ca in ("/storage/Users/currentUser/usr/local/ssl/cert.pem",
                       "/etc/ssl/certs/cacert.pem",
                       os.path.expanduser("~/.harmonybrew/etc/ca-certificates/cert.pem")):
                if os.path.isfile(ca):
                    env["SSL_CERT_FILE"] = ca
                    env["CURL_CA_BUNDLE"] = ca
                    break
        return env

    # ------------------------------------------------------------------
    # upstream source re-download + patch + cargo test suite
    # ------------------------------------------------------------------
    def _upstream_source(self, pkg_folder):
        """Return the upstream source root (re-downloaded tarball + the same
        patch and lock as the main recipe).

        Same URL list + sha256 as conandata.yml, so the upstream
        ``cargo test`` suite runs against the exact upstream tarball the
        package was built from, independent of any build-folder residue.
        The regenerated lock is taken from the packaged artifact itself
        (pkg_folder/Cargo.lock), so the lock exists in exactly one place
        in this MR — the main recipe's exported source — and the two
        build paths provably share the same file.
        """
        src_root = os.path.join(self.build_folder, "upstream-src")
        if os.path.isfile(os.path.join(src_root, "Cargo.toml")):
            return src_root

        mkdir(self, src_root)
        tarball = os.path.join(self.build_folder, "libsignal-0.103.1.tar.gz")
        if not os.path.isfile(tarball):
            download(self, url=_UPSTREAM_URLS, filename=tarball,
                     sha256=_UPSTREAM_SHA256, verify=True)
        unzip(self, tarball, destination=src_root, strip_root=True)
        try:
            os.remove(tarball)
        except OSError:
            pass
        if not os.path.isfile(os.path.join(src_root, "Cargo.toml")):
            raise ConanException(
                "Upstream tarball extracted but Cargo.toml missing under %s"
                % src_root)

        # 上游 tarball 的 Cargo.toml 为 CRLF；补丁 0001（纯 manifest
        # hunk）用 LF 编写，先把 2 个待补丁文件统一成 LF 再打（LF↔LF 在
        # git apply/GNU patch/patch-ng 下均实证通过；CRLF/LF 混写曾导致
        # "patch does not apply" 谜案）。Cargo.lock 不打补丁——打完后用
        # 打包产物里的重生成锁整体覆盖（见下）。
        for rel in ("Cargo.toml", "rust/core/Cargo.toml"):
            path = os.path.join(src_root, rel)
            if not os.path.isfile(path):
                continue
            with open(path, "rb") as f:
                data = f.read()
            normalized = data.replace(b"\r\n", b"\n")
            if normalized != data:
                with open(path, "wb") as f:
                    f.write(normalized)

        # 应用与主配方相同的补丁（workspace 缩容到 rust/core，纯 manifest
        # hunk）——与主配方 patches/0001 逐字节相同的 84 行文件（第三轮
        # 缩容：test_package 原自带 7140 行全量补丁副本已同步替换；老补丁
        # 的锁 hunk 效果本就被随后的锁覆盖抵消，替换为 manifest-only 版
        # 不改变任何构建语义）。用 conan.tools.files.patch（patch-ng，纯
        # Python，无外部二进制）：CI #63565 实证 CI worker 的
        # /data/service/hnp/bin/git 缺 libz.so 加载失败（rc=127），而主配方
        # source() 的同款 apply_conandata_patches（同一补丁 0001）在 CI
        # build 阶段已通过。
        # 与 apply_conandata_patches 保持完全一致：不传 strip → conan
        # 2.29 patch() 默认 strip=0（设备侧读 conan 源码实证）。patch-ng
        # 1.19.x 对 --- a/X +++ b/X 纯 unified 格式在 strip=0 下正确
        # 应用（CI #63565 build 阶段 + 真机第 6-15 轮同款调用全绿）。
        # 注意：strip=1 会二次剥离 a/ 前缀导致失败（见 notes.md）。
        patch_file = os.path.join(self.source_folder, "patches", _PATCH)
        patch(self, base_path=src_root, patch_file=patch_file)
        # Cargo.lock 直接取自打包产物（package_folder/Cargo.lock，主配方
        # package() 从随附锁拷贝）：补丁只改 manifest，上游 6577 行锁对
        # 缩容后 workspace 无效，必须整体覆盖，否则 cargo test --locked
        # 一失配就重解析整个 workspace 去克隆 github。锁在 MR 里只存在
        # 主配方一份（exports_sources），两条构建路径用同一份文件。
        lock_file = os.path.join(pkg_folder, "Cargo.lock")
        if not os.path.isfile(lock_file):
            raise ConanException(
                "packaged Cargo.lock missing from %s" % pkg_folder
            )
        shutil.copy(lock_file, os.path.join(src_root, "Cargo.lock"))
        with open(os.path.join(src_root, "Cargo.lock"), encoding="utf-8") as f:
            lock_text = f.read()
        if lock_text.count("[[package]]") != 80:
            raise ConanException(
                "shipped Cargo.lock has %d packages, expected 80"
                % lock_text.count("[[package]]")
            )
        core_toml = os.path.join(src_root, "rust", "core", "Cargo.toml")
        if os.path.isfile(core_toml) \
                and "boring = { workspace = true }" in open(core_toml).read():
            raise ConanException("dev-dep patch did not take effect on rust/core/Cargo.toml")
        root_toml = os.path.join(src_root, "Cargo.toml")
        root_toml_text = open(root_toml).read()
        if "[patch.crates-io]" in root_toml_text:
            raise ConanException("patch did not remove [patch.crates-io] from root Cargo.toml")
        m = re.search(r"members = \[(.*?)\]", root_toml_text, re.S)
        if not m or "rust/bridge" in m.group(1):
            raise ConanException("patch did not shrink the workspace to rust/core")
        return src_root

    def _write_cargo_config(self, src_root):
        """.cargo/config.toml: clang 链接器 + rsproxy.cn sparse 镜像 + 网络
        容错（与 conanfile.py generate() 一致，保证 cargo test 可拉取
        dev-dependencies 并链接）。"""
        cargo_dir = os.path.join(src_root, ".cargo")
        os.makedirs(cargo_dir, exist_ok=True)
        config_path = os.path.join(cargo_dir, "config.toml")
        with open(config_path, "w") as f:
            f.write('[build]\ntarget-dir = "target"\n')
            if str(self.settings.os) == "OHOS":
                f.write(
                    "\n[target.aarch64-unknown-linux-ohos]\n"
                    'linker = "/data/service/hnp/bin/clang"\n'
                )
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

    def _run_upstream_tests(self, cargo, env, src_root):
        """Run upstream ``cargo test --locked -p libsignal-core --lib
        --release``, parse the framework's real "test result:" verdict
        lines, and emit the HMBS marker.

        ``--lib`` runs only the src/ unit tests (core has no tests/ dir)
        and excludes the doc-tests phase: the OHOS Rust toolchain
        (Harmonybrew bottle) ships no usable rustdoc, so cargo cannot even
        spawn it (ENOENT at ``Doc-tests``; same-repo merged precedent
        martin/1.13.0 hit the identical "No such file or directory" and
        judged it a platform limitation, as did stylua/usage/gifski).
        libsignal-core's source has zero doctests, so excluding the empty
        phase drops no test cases: all 25 real cases still run.
        ``--locked`` 与随补丁交付的 Cargo.lock 配套：锁即当前，一旦失配
        立即报错，而不是重解析整个 workspace 去克隆 github 卡死。
        """
        env["PWD"] = src_root
        print("running upstream tests: cargo test --locked -p "
              "libsignal-core --lib --release (doc-tests phase excluded: "
              "OHOS rust toolchain has no rustdoc, core has 0 doctests)",
              flush=True)
        proc = subprocess.run(
            [cargo, "test", "--locked", "-p", "libsignal-core", "--lib", "--release"],
            capture_output=True,
            text=True,
            timeout=3600,
            cwd=src_root,
            env=env,
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        print(output, flush=True)

        result_lines = re.findall(
            r"test result: (\w+)\. (\d+) passed; (\d+) failed; (\d+) ignored",
            output,
        )
        passed = sum(int(n) for _, n, _, _ in result_lines)
        failed = sum(int(n) for _, _, n, _ in result_lines)
        ignored = sum(int(n) for _, _, _, n in result_lines)
        # discovered == executed == passed+failed：cargo 报告的每个
        # "test result:" 行即实际执行的测试（ignored 用例不执行、单独
        # 计为 skipped）。与 hmbs 门禁 discovered==executed 对账一致
        # （airlift-slice 先例）。
        executed = passed + failed
        status = "passed" if (proc.returncode == 0 and failed == 0 and executed > 0) else "failed"
        marker = {
            "status": status,
            "framework": "cargo",
            "command": "cargo test --locked -p libsignal-core --lib --release",
            "discovered": executed,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": ignored,
        }
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False))
        if failed > 0 or proc.returncode != 0:
            raise ConanException(
                "upstream cargo test failed (rc=%d, failed=%d)" % (proc.returncode, failed)
            )

    def test(self):
        # ── 1. consumer rlib probe ──
        # test.sh 用 rustc 直链打包的 rlib 闭包编译 probe.rs，打印
        # HMBS_TEST_PACKAGE_RESULT（真实断言计数取自 probe 输出）。
        # L0d 门禁静态检查要求 test() 通过 self.run() 实际执行测试程序
        # （无 self.run 调用即判 stub_test_method）——这里与已合入先例
        # 2048.c/1.0.3 同款包法：CONFIG_SHELL（HMBS 注入 /bin/sh）包住
        # test.sh；self.run 经 shell=True 走 /bin/sh -c，设备实测同源。
        # 上游 cargo test（步骤 2）保留 subprocess.run：self.run 的输出
        # 只进 conan 输出流、无法交回 Python 解析 "test result:" 行。
        # conan 2.29 的 run() 参数语义（真机第 10 轮实证）：env 只接受
        # env-file 名列表（"conanrun" 等），传 dict 直接 AssertionError；
        # 且默认 ignore_errors=False——非零退出码 run() 自己 raise，无需
        # 手工查 rc。环境注入改走 os.environ.update + env=None（不触发
        # conan env-file 机制，PATH/CC/TMPDIR 全部原样生效）。
        cargo = self._ensure_cargo()
        env = self._build_env()
        os.environ.update(env)
        libdir = os.path.join(
            self.dependencies["libsignal-core"].package_folder, "lib")
        sh = os.environ.get("CONFIG_SHELL") or os.environ.get("SHELL") or "sh"
        self.run(
            '%s "%s" "%s"' % (sh, os.path.join(self.source_folder, "test.sh"), libdir),
            cwd=self.build_folder,
            env=None,
        )

        # ── 2. upstream cargo test suite ──
        # hmbs 只从 test_package 阶段 stdout 采集 HMBS_UPSTREAM_TEST_RESULT
        # （tlsx/1.2.2 先例），因此上游测试在这里执行、用 print() 输出标记。
        pkg_folder = self.dependencies["libsignal-core"].package_folder
        src_root = self._upstream_source(pkg_folder)
        self._write_cargo_config(src_root)
        self._run_upstream_tests(cargo, env, src_root)
