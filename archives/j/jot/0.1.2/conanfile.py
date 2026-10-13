#!/usr/bin/env python3
"""Conan recipe — jot 0.1.2 (shashwatah/jot, terminal note-management CLI)

jot 是 shashwatah/jot 项目（Homebrew 稳定版 0.1.2）——一个用 Rust 编写的终端
快速笔记管理工具，构建产物为 ``jt`` 二进制。

本项目为 Rust/cargo 项目，需 cargo/rustc（aarch64-unknown-linux-ohos）。真机
预检日志先后显示：1) ``cargo: inaccessible or not found``（默认 PATH 无 cargo）；
2) 前轮 Harmonybrew rust bottle 引导方案因 ``rust-1.97.1.arm64_ohos.bottle.tar.gz``
在镜像返回 HTTP 404 而失败。据此改用仓库内已合入的 below/0.11.0、libetebase/0.5.8
方案：以 ``tool_requires("rust-toolchain/1.97.1")`` 引入基础设施包（官方 rust-lang
dist tarball，经 rsproxy.cn/USTC 镜像下载，含 aarch64-unknown-linux-ohos 宿主与
目标标准库）；该包二进制未签码，OHOS loader 拒执（EACCES errno 13），故将
cargo/rustc 及 rustc dlopen 的 librustc_driver dylib 复制到 build 目录并用
binary-sign-tool -selfSign 1 自签，其余只读负载（rustlib，~500MB）软链；
cargo 运行期动态链接 libssl/libcrypto/libz，Harmonybrew openssl/zlib bottles
（存在）解包后放入 LD_LIBRARY_PATH（OHOS loader 忽略 DT_RUNPATH）。

编译期依赖 libc 被 jot 的 Cargo.lock 锁在 0.2.132，该版本未定义
target_env="ohos"（aarch64-unknown-linux-ohos）的 ctype，而其
unix/linux_like/linux 模块又把 OHOS 当 linux-like 编译，遂报
`E0425 cannot find type c_char/c_long/time_t/__u64/__SIZEOF_PTHREAD_*`。
已按 weggli/0.2.4 先例用 conandata patches（Cargo.lock 补丁）把 libc
提升到 0.2.155（首个含 OHOS 定义、同一 rust-toolchain/1.97.1 下真机
已验证的版本），构建保持 `--locked` 可复现。

上游测试：按 HMBS 守则审计上游 0.1.2 源码（见 test_package/MANIFEST.yml 的
upstream_test_audit）确认 jot 没有任何测试（无 tests/ 目录、src/ 全部 11 个文件均无
#[test]/#[cfg(test)] 模块、Cargo.toml 无 [dev-dependencies]、仓库无 .github CI）。
因此按守则输出 status:"no_tests"、discovered:0、executed:0 及具体 reason。
"""
import json
import os
import shlex
import shutil
import subprocess
import tarfile
import urllib.error
import urllib.request

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout

OHOS_RUST_TARGET = "aarch64-unknown-linux-ohos"

# cargo 运行期动态链接 libssl/libcrypto/libz（DT_NEEDED）；OHOS loader 忽略
# DT_RUNPATH，须显式放进 LD_LIBRARY_PATH。下方 URL/sha256 取自 harmonybrew
# 官方公式清单（https://harmonybrew.atomgit.com/api/formula.jws.json）中
# openssl@3 与 zlib-ng-compat 的 arm64_ohos 当前 bottle，且 sha256 已对实际
# 归档逐位校验一致。
#
# 注意：bottle 版本/命名会随 harmonybrew 更新而变。真机曾遇到旧版本归档
# openssl@3-3.6.4 / zlib-ng-compat-2.3.3_1 在 /bottles/ 下 HTTP 404（该仓库
# 不保留历史归档，直接替换为新版本号）。若再遇 404，请到上述 JWS 清单读取
# 当前 stable 版本的 arm64_ohos url+sha256 并更新此处，勿沿用旧号。
RUST_RUNTIME_BOTTLES = (
    ("openssl3",
     "https://harmonybrew.atomgit.com/bottles/"
     "openssl%403-3.6.5_1.arm64_ohos.bottle.1.tar.gz",
     "ae1d5bf9252d65d86053e68d7c91fc9d0066016bce50662ce4a32a0b0e954ef2"),
    ("zlib",
     "https://harmonybrew.atomgit.com/bottles/"
     "zlib-ng-compat-2.3.3_2.arm64_ohos.bottle.1.tar.gz",
     "7092bfe7af8908f4a7c72493881291fe2416f27fc6502c34e22346a4dbfc4c51"),
)


class JotConan(ConanFile):
    name = "jot"
    version = "0.1.2"
    description = "jot - rapid note management for the terminal (jt binary)"
    license = "MIT"
    homepage = "https://github.com/shashwatah/jot"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"jot is only supported on Linux/OHOS, got {self.settings.os}"
            )

    def build_requirements(self):
        # 基础设施包：官方 rust-lang dist tarball（rsproxy/USTC 镜像），
        # 含 OHOS aarch64 宿主与目标标准库（below/0.11.0、libetebase/0.5.8 先例）。
        if str(self.settings.os) == "OHOS":
            self.tool_requires("rust-toolchain/1.97.1")

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        # patches/ 随配方导出（conandata.yml 的 patches 声明），
        # 由 build() 的 apply_conandata_patches 应用到源码树。
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _rust_target(self):
        """OHOS Rust target triple（与 below/libetebase 一致）。"""
        if str(self.settings.os) != "OHOS":
            return None
        targets = {
            "armv8": OHOS_RUST_TARGET,
            "armv8.3": OHOS_RUST_TARGET,
            "x86_64": "x86_64-unknown-linux-ohos",
        }
        try:
            return targets[str(self.settings.arch)]
        except KeyError:
            raise ConanInvalidConfiguration(
                f"No Rust target mapping for OHOS architecture {self.settings.arch}"
            )

    # ── toolchain discovery / signing ────────────────────────────────

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
        bin_dir = self._prepare_signed_toolchain()
        candidate = os.path.join(bin_dir, "cargo")
        if os.path.isfile(candidate):
            return candidate
        raise ConanInvalidConfiguration(
            "Rust/Cargo toolchain not found: no system cargo and no "
            "rust-toolchain/1.97.1 tool_requires package available"
        )

    def _rust_toolchain_dep(self):
        try:
            return self.dependencies.build.get("rust-toolchain")
        except (KeyError, ConanException):
            return None

    def _toolchain_dir(self):
        return os.path.join(self.build_folder, "rust-toolchain")

    def _prepare_signed_toolchain(self):
        """在 build 目录stage一个可执行的 Rust 工具链（纯 copy+sign 形态）。

        rust-toolchain/1.97.1 二进制未签码，OHOS loader 拒执（EACCES）。把
        cargo/rustc 及 rustc dlopen 的 librustc_driver dylib 复制到 build
        目录并 `binary-sign-tool -selfSign 1` 自签；其余只读负载（rustlib，
        ~500MB）软链。幂等（marker）。

        **纯 copy+sign，无任何附加改造**：不加 LD_PRELOAD、不加 patchelf RPATH、
        不做 `_strip_codesign` 剥离。这与已合入真机全绿的同源食谱
        below/0.11.0、libetebase/0.5.8 完全一致——它们在同一个
        rust-toolchain/1.97.1 包 + 同一 OHOS loader 下，纯 copy+sign 即让
        cargo/rustc 及上游测试全部运行（notes.md R51/R10）。此前 jot 独有叠加
        strip-codesign → LD_PRELOAD → patchelf RPATH 的组合（R5–R9）一直复现
        `rustc -vV` exit 127 `Error relocating ... symbol not found`；经仓库内
        全局检索，全部已合入 Rust 食谱（below/libetebase 等）均不含这些加固，
        故删除 `_strip_codesign`（它是对签好 driver 的二次 ELF 重写，不是
        binary-sign-tool 必需的前置，反而是加载期符号错的最佳嫌疑）。driver
        由 rustc 在 exec 时经自身相对路径（<bin>/../lib，rainfrog DRAFT-13336）
        dlopen，放到 rust-toolchain/lib/ 即可被加载。
        """
        dst = self._toolchain_dir()
        bin_dst = os.path.join(dst, "bin")
        lib_dst = os.path.join(dst, "lib")
        marker = os.path.join(dst, ".prepared")
        if os.path.isfile(marker):
            return bin_dst
        tool = self._rust_toolchain_dep()
        if tool is None:
            raise ConanInvalidConfiguration(
                "rust-toolchain/1.97.1 tool_requires package not available"
            )
        src = tool.package_folder
        os.makedirs(bin_dst, exist_ok=True)
        os.makedirs(lib_dst, exist_ok=True)
        # Must-exec 二进制 + rustc dlopen 的 dylib：复制并自签。
        # 注意：已存在的副本也应加入 to_sign，否则 marker 背后残留未签副本
        # 会持续 execve EACCES（PermissionError 13）。
        to_sign = []
        for name in ("cargo", "rustc"):
            s = os.path.join(src, "bin", name)
            if os.path.isfile(s):
                d = os.path.join(bin_dst, name)
                if not os.path.isfile(d):
                    shutil.copy2(s, d)
                    try:
                        os.chmod(d, 0o755)
                    except OSError:
                        pass
                to_sign.append(d)
        src_lib = os.path.join(src, "lib")
        if os.path.isdir(src_lib):
            for name in sorted(os.listdir(src_lib)):
                if name.startswith("librustc_driver") and name.endswith(".so"):
                    d = os.path.join(lib_dst, name)
                    if not os.path.isfile(d):
                        shutil.copy2(os.path.join(src_lib, name), d)
                        try:
                            os.chmod(d, 0o755)
                        except OSError:
                            pass
                    to_sign.append(d)
        signer = self._find_binary_sign_tool()
        if signer is None:
            self.output.warning(
                "binary-sign-tool not found; toolchain binaries stay "
                "unsigned and may be rejected by the OHOS loader (EACCES)"
            )
        else:
            # 纯 copy+sign（与 below/libetebase 完全一致）：不剥离 .codesign、
            # 不写 patchelf RPATH、不设 LD_PRELOAD，直接对复刻的 cargo/rustc/
            # librustc_driver 逐个 -selfSign 1。此形态已在同一 infra 包 + 同一
            # OHOS loader 下由已合入食谱实测通过。
            for path in to_sign:
                tmp = path + ".signed"
                proc = subprocess.run(
                    [signer, "sign", "-inFile", path, "-outFile", tmp,
                     "-selfSign", "1"],
                    capture_output=True, text=True)
                if proc.returncode != 0 or not os.path.isfile(tmp):
                    raise ConanInvalidConfiguration(
                        "binary-sign-tool failed for %s (rc=%d): %s"
                        % (path, proc.returncode, proc.stderr[:200])
                    )
                os.replace(tmp, path)
                try:
                    os.chmod(path, 0o755)
                except OSError:
                    pass
                self.output.info(
                    "signed toolchain binary: %s" % os.path.basename(path)
                )
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
        with open(marker, "w", encoding="utf-8", newline="\n") as f:
            f.write("signed toolchain prepared\n")
        return bin_dst

    def _find_binary_sign_tool(self):
        candidates = [
            os.environ.get("BINARY_SIGN_TOOL"),
            shutil.which("binary-sign-tool"),
            shutil.which("hapsign"),
            "/data/service/hnp/bin/binary-sign-tool",
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

    def _prepare_runtime_libs(self):
        """stage cargo 运行期共享库（libssl/libcrypto/libz）到 LD_LIBRARY_PATH。

        用 Python urllib 下载（device curl 无 CA bundle；本机已证 urllib 可网络，
        前轮仅因不存在的 rust bottle 404）。幂等：已存在且校验通过则跳过。
        """
        base = os.path.join(self.build_folder, "rust-runtime")
        os.makedirs(base, exist_ok=True)
        lib_dirs = []
        for name, url, sha256 in RUST_RUNTIME_BOTTLES:
            tgz = os.path.join(base, name + ".tar.gz")
            if not os.path.isfile(tgz) or self._sha256(tgz) != sha256:
                self._download_bottle(url, tgz, sha256)
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
        os.makedirs(cargo_home, exist_ok=True)
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
        with open(os.path.join(cargo_home, "config.toml"),
                  "w", encoding="utf-8", newline="\n") as f:
            f.write(content)

    def _rust_environment(self, cargo):
        env = os.environ.copy()
        # HMBS readonly_tmp hardening：cargo fallback /tmp 只读，重定向到可写 TMPDIR。
        tmpdir = (env.get("TMPDIR") or env.get("TMP") or env.get("TEMP") or "")
        if not tmpdir or not os.path.isdir(tmpdir):
            tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env["TMPDIR"] = tmpdir
        env["TMP"] = tmpdir
        env["TEMP"] = tmpdir

        env["CARGO"] = cargo
        extra_paths = [os.path.dirname(cargo)]
        extra_paths += [d for d in ("/system/bin", "/system/sbin",
                                    "/vendor/bin") if os.path.isdir(d)]
        env["PATH"] = os.pathsep.join(
            extra_paths) + os.pathsep + env.get("PATH", "")

        lib_dirs = [os.path.join(self._toolchain_dir(), "lib")]
        lib_dirs += self._prepare_runtime_libs()
        if lib_dirs:
            prev = env.get("LD_LIBRARY_PATH", "")
            env["LD_LIBRARY_PATH"] = os.pathsep.join(
                lib_dirs + ([prev] if prev else []))

        # 不设 LD_PRELOAD：E502 / paperjam 真机证据表明 OHOS(CI worker) 对
        # 用户目录共享库的 dlopen / LD_PRELOAD 一律拒绝（无论是否有签名），
        # 失败表象正是本错误的 `Error loading shared library librustc_driver-*.so:
        # (needed by rustc)`。R8（strip-codesign + LD_PRELOAD）的残留错误即由此
        # LD_PRELOAD 触发。rustc 通过自身可执行文件相对路径（<bin>/../lib，
        # rainfrog DRAFT-13336）dlopen 其 librustc_driver，编译期签名工具链时
        # 已把自签 driver 放到 rust-toolchain/lib/，无需 LD_PRELOAD 也无需
        # patchelf RPATH——与已合入的 below/0.11.0（纯 copy+sign+LD_LIBRARY_PATH）
        # 完全一致。driver 由 rustc 在 exec 时经路径 dlopen 加载即可。

        ca = self._ca_bundle()
        if ca:
            env["SSL_CERT_FILE"] = ca
            env["CURL_CA_BUNDLE"] = ca

        cargo_home = os.path.join(self.build_folder, "cargo-home")
        os.makedirs(cargo_home, exist_ok=True)
        self._configure_rsproxy(cargo_home, ca)
        env["CARGO_HOME"] = cargo_home

        # 目标链接器/工具链：clang（conf 优先，回退真机常见路径）
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}
        ) or {}
        cc = compiler_executables.get("c") or shutil.which("clang") \
            or "/data/service/hnp/bin/clang"
        cxx = compiler_executables.get("cpp") or shutil.which("clang++") \
            or "/data/service/hnp/bin/clang++"
        llvm_bin = os.path.dirname(cc)
        ar = os.path.join(llvm_bin, "llvm-ar")
        ranlib = os.path.join(llvm_bin, "llvm-ranlib")
        env.update({
            "CC": cc,
            "CXX": cxx,
            "CARGO_TARGET_AARCH64_UNKNOWN_LINUX_OHOS_LINKER": cc,
            "CC_aarch64_unknown_linux_ohos": cc,
            "CXX_aarch64_unknown_linux_ohos": cxx,
            "AR_aarch64_unknown_linux_ohos": ar,
            "RANLIB_aarch64_unknown_linux_ohos": ranlib,
            "CARGO_NET_RETRY": "10",
            "CARGO_HTTP_TIMEOUT": "600",
            "CARGO_BUILD_JOBS": "1",
        })
        if ca:
            env["CARGO_HTTP_CAINFO"] = ca
        return env

    def build(self):
        # 先应用 conandata.yml 声明的源码补丁（libc 0.2.132 → 0.2.155，
        # 首个支持 OHOS target_env 的版本，保持 --locked 可复现）。
        apply_conandata_patches(self)
        cargo = self._find_cargo(os.environ.copy())
        if not os.path.basename(cargo) == "cargo" or not os.path.isfile(cargo):
            raise ConanInvalidConfiguration(f"invalid cargo path: {cargo}")
        env = self._rust_environment(cargo)
        target = self._rust_target()
        command = [cargo, "build", "--release", "--locked"]
        if target:
            command.extend(["--target", target])
        # 与已合入真机全绿的 below/0.11.0（同 rust-toolchain/1.97.1 infa 包 +
        # 同一 OHOS loader）逐字一致地直接 subprocess.run(env=env) 投递构建环境，
        # 而不是 Conan 的 self.run()。self.run 会走 Conan buildenv/runenv 包装，
        # 按配方声明的 runenv 重写 LD_LIBRARY_PATH，把手动放进
        # rust-toolchain/lib/ 的自签 librustc_driver 路径丢掉，令 cargo 派生的
        # `rustc -vV` 从系统默认路径载到旧 driver → `Error loading shared
        # library librustc_driver-*.so (needed by rustc)` + 连锁 `Error
        # relocating ... symbol not found`（stale_runtime_library 门禁）。
        # subprocess.run 原样透传 env，保证 rustc 能由 DT_NEEDED/相对路径
        # dlopen 到本次自签的 driver。不设 LD_PRELOAD（OHOS worker 拒绝
        # 用户目录共享库 LD_PRELOAD，E502/paperjam 证据）。
        proc = subprocess.run(command, cwd=self.source_folder, env=env)
        if proc.returncode != 0:
            raise ConanException(
                "cargo build failed (rc=%d): %s"
                % (proc.returncode,
                   " ".join(shlex.quote(part) for part in command))
            )

        # HMBS machine evidence：jot 0.1.2 经源码审计确认无任何上游测试
        # （test_package/MANIFEST.yml 的 upstream_test_audit）。输出 no_tests
        # 标记；缓存命中导致 build() 被跳过时，由 test_package 每轮重发。
        upstream = {
            "status": "no_tests",
            "framework": "cargo-test",
            "command": "",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": "Audited shashwatah/jot v0.1.2 source tarball "
                      "(sha256 d7da3220c29102ee7c51e2a5656ceb6672ae3b85be22c5ddcd176b330c6029c9): "
                      "no tests/ directory; all 11 source files in src/ show no "
                      "#[test] or #[cfg(test)] modules; Cargo.toml has no "
                      "[dev-dependencies]; repo has no .github CI workflow. "
                      "Cargo.lock present for reproducible --locked build. "
                      "Therefore status no_tests."
        }
        msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False)
        print(msg, flush=True)
        self.output.info(msg)

    def _binary_path(self):
        target = self._rust_target()
        if target:
            return os.path.join(self.source_folder, "target", target,
                                "release", "jt")
        return os.path.join(self.source_folder, "target", "release", "jt")

    def package(self):
        binary = self._binary_path()
        if not os.path.isfile(binary):
            raise ConanException(f"jot build output not found: {binary}")
        copy(self, "jt", src=os.path.dirname(binary),
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))

    # ── bottle download helpers (Python urllib) ──────────────────────

    @staticmethod
    def _sha256(path):
        import hashlib
        digest = hashlib.sha256()
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _download_bottle(self, url, destination, expected_sha256):
        import ssl as _ssl
        urls_to_try = []
        seen = set()

        def _add(u):
            if u not in seen:
                seen.add(u)
                urls_to_try.append(u)

        _add(url)
        if "harmonybrew.atomgit.com" in url:
            _add("https://gh-proxy.com/" + url)
            if "%40" in url:
                decoded = url.replace("%40", "@")
                _add(decoded)
                _add("https://gh-proxy.com/" + decoded)
        last_exc = None
        for attempt_url in urls_to_try:
            try:
                req = urllib.request.Request(attempt_url, headers={
                    "User-Agent": "curl/8.5.0",
                    "Accept": "*/*",
                })
                ca_file = self._ca_bundle()
                if ca_file and os.path.isfile(ca_file):
                    try:
                        ctx = _ssl.create_default_context(cafile=ca_file)
                    except Exception:
                        ctx = _ssl.create_default_context()
                else:
                    ctx = _ssl._create_unverified_context()
                try:
                    with urllib.request.urlopen(req, context=ctx,
                                                timeout=600) as response:
                        with open(destination, "wb") as handle:
                            shutil.copyfileobj(response, handle)
                except (urllib.error.URLError, _ssl.SSLError) as exc:
                    if "CERTIFICATE_VERIFY_FAILED" in str(exc):
                        self.output.warning(
                            "no usable CA bundle; retrying %s without TLS "
                            "verification" % attempt_url
                        )
                        ctx2 = _ssl._create_unverified_context()
                        with urllib.request.urlopen(req, context=ctx2,
                                                    timeout=600) as response:
                            with open(destination, "wb") as handle:
                                shutil.copyfileobj(response, handle)
                    else:
                        raise
                actual = self._sha256(destination)
                if actual != expected_sha256:
                    try:
                        os.remove(destination)
                    except OSError:
                        pass
                    raise ConanInvalidConfiguration(
                        "bottle checksum mismatch for %s: expected %s, got %s"
                        % (attempt_url, expected_sha256, actual))
                if attempt_url != url:
                    self.output.info(
                        "downloaded %s (fallback for %s)" % (attempt_url, url))
                return
            except urllib.error.HTTPError as exc:
                last_exc = exc
                if exc.code in (403, 404, 410):
                    self.output.warning(
                        "HTTP %s for %s, trying next mirror"
                        % (exc.code, attempt_url))
                else:
                    raise
            except (urllib.error.URLError, _ssl.SSLError, OSError) as exc:
                last_exc = exc
                self.output.warning(
                    "download failed for %s: %s" % (attempt_url, exc))
        if last_exc is not None:
            raise last_exc
        raise ConanInvalidConfiguration(
            "failed to download %s: no mirrors succeeded" % url)
