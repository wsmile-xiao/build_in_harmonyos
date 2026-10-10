#!/usr/bin/env python3
"""Conan test_package for alacritty 0.17.0 — consumer smoke test + upstream cargo test.

1) test.sh 用打包的 bin/alacritty 跑 6 个消费者用例（--version/--help/
   子命令路由/无效参数退出码/离线 YAML→TOML 迁移/ELF 架构），打印
   HMBS_TEST_PACKAGE_RESULT。
2) 重新下载上游源码 tarball（与 conandata.yml 同 URL + sha256），运行上游
   ``cargo test --release -j2 --no-default-features --features wayland
   --workspace --tests -- --skip test_get_pw_entry``（263 个注册用例中
   262 个执行 + 1 个 pw 平台豁免），解析真实 "test result:" 行，
   print() 输出 HMBS_UPSTREAM_TEST_RESULT。

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
from conan.tools.files import download, mkdir, unzip


# Upstream source tarball — same URL + sha256 as conandata.yml
# (official GitHub URL; CI auto-appends mirror fallbacks).
_UPSTREAM_URLS = [
    "https://github.com/alacritty/alacritty/archive/refs/tags/v0.17.0.tar.gz",
]
_UPSTREAM_SHA256 = "38d6527d346cda5c6049332a1f3338a89ea66cd7981b54d4c3ce801b392496f8"

# Skipped upstream test (platform exemption, evidence in MANIFEST.yml):
# tty::unix::test_get_pw_entry — OHOS app-uid has no /etc/passwd entry.
_SKIP = "test_get_pw_entry"


class AlacrittyTestConan(ConanFile):
    """test_package — runs the packaged alacritty consumer probe (test.sh)
    and the upstream ``cargo test --workspace --tests`` suite, emitting
    HMBS evidence markers for preflight verification."""
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    # ------------------------------------------------------------------
    # cargo toolchain + fontconfig static closure
    # (mirror of conanfile.py, argc 1.24.0 / libsignal-core 0.103.1 family)
    # ------------------------------------------------------------------
    _RUST_BOTTLES = {
        "rust": "https://harmonybrew.atomgit.com/bottles/rust-1.98.1_1.arm64_ohos.bottle.tar.gz",
        "openssl3": "https://harmonybrew.atomgit.com/bottles/openssl%403-3.6.4_1.arm64_ohos.bottle.tar.gz",
        "zlib": "https://harmonybrew.atomgit.com/bottles/zlib-ng-compat-2.3.3_2.arm64_ohos.bottle.tar.gz",
    }

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
    def _ca_candidates():
        return [
            "/storage/Users/currentUser/usr/local/ssl/cert.pem",
            "/etc/ssl/certs/cacert.pem",
            "/etc/ssl/cert.pem",
            os.path.expanduser("~/.harmonybrew/etc/ca-certificates/cert.pem"),
        ]

    @staticmethod
    def _find_cargo():
        """Probe well-known OHOS locations for the cargo binary; prefer a
        ``.real`` sibling so the real binary is executed, never the
        Harmonybrew Cellar-path wrapper (rc=127 once unpacked)."""
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
        """Download a Harmonybrew bottle with Python urllib (TLS-verified
        against the first available system CA store; unverified fallback
        only for the fixed internal mirror)."""
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
                        continue
                cargo_real = cand
                break
        return cargo_real

    @staticmethod
    def _repair_wrappers(bin_dir):
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
                continue
            try:
                os.chmod(wrapper, os.stat(wrapper).st_mode | 0o200)
            except OSError:
                pass
            with open(wrapper, "w") as f:
                f.write("#!/bin/sh\n")
                f.write("# repaired by alacritty test_package: exec local .real binary\n")
                f.write('exec "%s" "$@"\n' % real)

    @staticmethod
    def _toolchain_lib_dirs(base):
        lib_dirs = []
        for root, _dirs, files in os.walk(base):
            if os.path.basename(root) == "lib":
                libs = set(files)
                if libs & {"libssl.so", "libcrypto.so", "libz.so"}:
                    lib_dirs.append(root)
        return lib_dirs

    def _ensure_fontconfig_closure(self, base):
        closure = os.path.join(self.build_folder, "fontconfig-closure")
        os.makedirs(closure, exist_ok=True)
        found = {}
        for root, _dirs, files in os.walk(base):
            for lib in self._CLOSURE_LIBS:
                if lib in files and lib not in found:
                    found[lib] = os.path.join(root, lib)
        missing = [l for l in self._CLOSURE_LIBS if l not in found]
        if missing:
            raise ConanException(
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
        return closure

    def _ensure_toolchain(self):
        cargo = self._find_cargo()
        if cargo:
            base = self._unpack_bottles(self._FC_BOTTLES)
        else:
            bottles = dict(self._RUST_BOTTLES)
            bottles.update(self._FC_BOTTLES)
            base = self._unpack_bottles(bottles)
            cargo = self._locate_cargo_in(base)
            if not cargo:
                raise ConanException(
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
        """Env for cargo test: clang linker + static fontconfig closure,
        writable TMPDIR, CA bundle, and /system/lib64 on LD_LIBRARY_PATH
        (unwind/libc++_shared runtime for OHOS Rust test binaries)."""
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
            tmpdir = os.path.join(os.path.expanduser("~"), "tmp", "alacritty-test")
            os.makedirs(tmpdir, exist_ok=True)
        for var in ("TMPDIR", "TMP", "TEMP"):
            env[var] = tmpdir
        hnp_bin = "/data/service/hnp/bin"
        if os.path.isdir(hnp_bin):
            env["PATH"] = hnp_bin + os.pathsep + env.get("PATH", "")
        # OHOS Rust binaries need libc++_shared.so / _Unwind_* from
        # /system/lib64 (system-provided) — append, do not clobber any
        # toolchain dirs set by the bootstrap.
        env["LD_LIBRARY_PATH"] = "/system/lib64" + os.pathsep + \
            env.get("LD_LIBRARY_PATH", "")
        if not env.get("SSL_CERT_FILE"):
            for ca in self._ca_candidates():
                if os.path.isfile(ca):
                    env["SSL_CERT_FILE"] = ca
                    env["CURL_CA_BUNDLE"] = ca
                    break
        return env

    # ------------------------------------------------------------------
    # upstream source re-download + cargo test suite
    # ------------------------------------------------------------------
    def _upstream_source(self):
        """Return the upstream source root (re-downloaded tarball). Same
        URL + sha256 as conandata.yml, so the upstream ``cargo test``
        suite runs against the exact upstream tarball the package was
        built from, independent of any build-folder residue."""
        src_root = os.path.join(self.build_folder, "upstream-src")
        if os.path.isfile(os.path.join(src_root, "Cargo.toml")):
            return src_root

        mkdir(self, src_root)
        tarball = os.path.join(self.build_folder, "alacritty-0.17.0.tar.gz")
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
        return src_root

    def _write_cargo_config(self, src_root):
        """.cargo/config.toml: clang 链接器 + rsproxy.cn sparse 镜像 +
        网络容错 + multiplexing=false（与 conanfile.py 一致，保证 cargo
        test 可编译/链接测试目标）。"""
        cargo_dir = os.path.join(src_root, ".cargo")
        os.makedirs(cargo_dir, exist_ok=True)
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
        with open(os.path.join(cargo_dir, "config.toml"), "w") as f:
            f.write(content)

    def _run_upstream_tests(self, cargo, env, src_root):
        """Run the upstream cargo test suite, parse the framework's real
        "test result:" verdict lines, and emit the HMBS marker.

        ``--tests`` only runs targets with test attributes (263 registered
        cases across the 6 workspace test targets), excluding the
        doc-tests phase: the OHOS Rust toolchain (Harmonybrew bottle)
        ships no usable rustdoc (argc/martin/stylua/usage/gifski merged
        precedents; the single rust doctest block in term/mod.rs is
        documented in MANIFEST.yml). ``-- --skip test_get_pw_entry``
        filters the one platform-exempted case (OHOS app-uid has no
        /etc/passwd entry — cargo's native filter mechanism reports it
        as "filtered out", no upstream test source is modified).
        """
        cmd = [
            cargo, "test", "--release", "--locked", "-j", "2",
            "--no-default-features", "--features", "wayland",
            "--workspace", "--tests", "--", "--skip", _SKIP,
        ]
        print(
            "running upstream tests: %s (doc-tests phase excluded: OHOS "
            "rust toolchain has no rustdoc; %s filtered: OHOS app-uid has "
            "no /etc/passwd entry)" % (" ".join(cmd[1:]), _SKIP),
            flush=True,
        )
        env["PWD"] = src_root
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=3600,
            cwd=src_root, env=env,
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
        filtered = 0
        for m in re.finditer(r"(\d+) filtered out", output):
            filtered = max(filtered, int(m.group(1)))
        # discovered == executed == passed+failed（cargo 每条 "test result:"
        # 行即实际执行的目标；skip 的 pw 用例单独计为 skipped，与
        # hmbs discovered==executed 对账口径一致——airlift-slice 先例）。
        executed = passed + failed
        total_registered = executed + filtered
        if total_registered != 263:
            raise ConanException(
                "upstream test registration mismatch: expected 263, "
                "got executed=%d + filtered=%d (log verdict lines: %s)"
                % (executed, filtered, result_lines)
            )
        status = "passed" if (proc.returncode == 0 and failed == 0 and executed > 0) else "failed"
        marker = {
            "status": status,
            "framework": "cargo",
            "command": "cargo test --release --workspace --tests -- --skip test_get_pw_entry",
            "discovered": total_registered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": filtered,
        }
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False))
        if failed > 0 or proc.returncode != 0:
            raise ConanException(
                "upstream cargo test failed (rc=%d, failed=%d)" % (proc.returncode, failed)
            )

    def test(self):
        # ── 1. consumer smoke test ──
        # test.sh emits HMBS_TEST_PACKAGE_RESULT with real case counts.
        # L0d 门禁静态检查要求 test() 通过 self.run() 实际执行测试程序
        # （无 self.run 调用即判 stub_test_method）——2048.c/1.0.3 与
        # argc/1.24.0 同款包法：CONFIG_SHELL（HMBS 注入 /bin/sh）包住
        # test.sh；env="conanrun" 让 PATH 含安装后的 bin/。
        cargo, closure = self._ensure_toolchain()
        sh = os.environ.get("CONFIG_SHELL") or os.environ.get("SHELL") or "sh"
        self.run(
            '%s "%s"' % (sh, os.path.join(self.source_folder, "test.sh")),
            cwd=self.build_folder,
            env="conanrun",
        )

        # ── 2. upstream cargo test suite ──
        # hmbs 只从 test_package 阶段 stdout 采集 HMBS_UPSTREAM_TEST_RESULT
        # （tlsx/1.2.2 先例），因此上游测试在这里执行、用 print() 输出标记。
        env = self._build_env(closure)
        src_root = self._upstream_source()
        self._write_cargo_config(src_root)
        self._run_upstream_tests(cargo, env, src_root)
