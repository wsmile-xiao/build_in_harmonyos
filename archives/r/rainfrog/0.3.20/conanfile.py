#!/usr/bin/env python3
"""Conan recipe — rainfrog 0.3.20 (cargo / Rust, OHOS).

rainfrog 是终端数据库管理 TUI：ratatui + crossterm 做界面，sqlx 做后端
（postgres / mysql / sqlite），单二进制 `rainfrog`。

OHOS 适配要点（本配方实际采用）：
- **Rust 工具链取自仓库内 conan 包 `rust-toolchain/1.97.1`**（`tool_requires`）：
  它是 rust-lang 官方 dist（宿主与目标均 aarch64-unknown-linux-ohos），已发布 ohpcd。
  为何不用 harmorybrew 的 rust bottle（alass 先例的做法）：CI 实测 `rust-1.97.1`
  bottle 已被轮换为 404（同 URL 本机命中旧缓存边缘仍 200），而当前可取的
  `rust-1.98.1_2` 其 cargo 额外动态依赖 libgit2/libssh2/libcurl/libsqlite3/libzstd
  五个库（实测 NEEDED），补它们的 bottle 链更脆弱。rust-toolchain 则随制品仓固定、
  cargo 只需 libssl/libcrypto/libz（闭包小）。
  代价：该包二进制**未带 OHOS 签名**，直接 exec 报 Permission denied（errno 13），
  故须在构建期内自签名（见 `_provision_toolchain`）。
- **默认特性 `["duckdb", "arboard"]` 必须关闭**：duckdb 是 bundled C++ 全量构建、
  arboard 走 Wayland/X11 剪贴板，均与"数据库 TUI 可运行"无关 → `--no-default-features`。
- **TLS 用 `tls-rustls`**（纯 Rust）→ 不为 TLS 链接 OpenSSL 动态库。
- ⚠️ `oracle = 0.6.3` 为非可选依赖，本环境实测 `--no-default-features` 下可正常编过。

测试：`build()` 内真实执行 `cargo test`，并以 `HMBS_UPSTREAM_TEST_RESULT`
marker 输出客观计数（上游测试是 `src/**/*.rs` 内联 `#[test]`，无顶层 tests/）。
"""
import glob
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.layout import basic_layout


CARGO_BUILD_ARGS = ("build", "--release", "--locked", "--no-default-features")
CARGO_TEST_ARGS = (
    "test", "--release", "--locked", "--no-default-features", "--tests",
)
UPSTREAM_TEST_COMMAND = "cargo " + " ".join(CARGO_TEST_ARGS)

SIGNER_CANDIDATES = (
    "/data/service/hnp/bin/binary-sign-tool",
    "binary-sign-tool",
)


class RainfrogConan(ConanFile):
    name = "rainfrog"
    version = "0.3.20"
    description = (
        "rainfrog — a database management TUI for the terminal "
        "(ratatui + crossterm + sqlx: postgres/mysql/sqlite)"
    )
    license = "MIT"
    homepage = "https://github.com/achristmascarl/rainfrog"
    url = "https://github.com/achristmascarl/rainfrog"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "rainfrog is supported on Linux and OHOS"
            )

    def build_requirements(self):
        # 仓库内工具链包（rust-lang 官方 dist + OHOS aarch64 宿主/目标标准库）。
        # 见模块 docstring：相对 harmonybrew rust bottle，它随制品仓固定、
        # 不依赖外部 CDN，且 cargo 的运行库闭包小。
        self.tool_requires("rust-toolchain/1.97.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ── 工具可用性探测 ────────────────────────────────────────────────
    @staticmethod
    def _runnable(path, expected_name):
        """用**实际执行**判定工具是否可用，绝不用 os.access。

        OHOS 上权限位与"能否 exec"不等价：本机
        /storage/Users/currentUser/usr/local/bin/cargo 是 0o750、组
        file_manager，os.access(X_OK) 返回 True，但 exec 实际报
        Permission denied —— 照抄 os.access 的写法会让构建当场崩在
        PermissionError，而不会退到工具链供给路径。
        """
        if not path or not os.path.isfile(path):
            return False
        try:
            proc = subprocess.run(
                [path, "--version"], capture_output=True, text=True, timeout=60
            )
        except (OSError, subprocess.SubprocessError):
            return False
        return proc.returncode == 0 and expected_name in (
            (proc.stdout or "") + (proc.stderr or "")
        )

    @staticmethod
    def _find_tool(name):
        """在系统/常见位置找"真能跑"的 cargo/rustc（可选路径，找不到就供给）。"""
        patterns = [
            "/storage/Users/currentUser/usr/"
            f"rust-*-aarch64-unknown-linux-ohos/bin/{name}",
            os.path.expanduser(f"~/usr/rust-*-aarch64-unknown-linux-ohos/bin/{name}"),
        ]
        candidates = []
        for pattern in patterns:
            candidates.extend(glob.glob(pattern))

        def rust_version(path):
            m = re.search(r"/rust-([0-9]+(?:\.[0-9]+)*)-", path)
            return tuple(int(p) for p in m.group(1).split(".")) if m else ()

        candidates.sort(key=rust_version, reverse=True)
        candidates += [
            shutil.which(name),
            os.environ.get(name.upper()),
            os.environ.get(f"HNP_{name.upper()}"),
            f"/data/service/hnp/bin/{name}",
            os.path.expanduser(f"~/.harmonybrew/bin/{name}"),
        ]
        for c in candidates:
            if RainfrogConan._runnable(c, name):
                return c
        return None

    # ── 从 conan 工具包取工具链并自签名 ────────────────────────────────
    @staticmethod
    def _find_signer():
        for cand in SIGNER_CANDIDATES:
            if os.path.isabs(cand):
                if os.path.isfile(cand) and os.access(cand, os.X_OK):
                    return cand
            else:
                found = shutil.which(cand)
                if found:
                    return found
        return None

    def _sign(self, path, signer):
        """就地自签名：先写 .signed 再 os.replace，避免签名过程把原文件截断。"""
        tmp = path + ".signed"
        proc = subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", tmp, "-selfSign", "1"],
            capture_output=True, text=True, timeout=600,
        )
        if proc.returncode != 0 or not os.path.isfile(tmp):
            raise ConanException(
                f"failed to sign {path}: {(proc.stdout or '') + (proc.stderr or '')}"
            )
        os.replace(tmp, path)
        os.chmod(path, 0o755)

    def _provision_toolchain(self):
        """从 tool_requires 的 `rust-toolchain` 包取出可执行的 cargo/rustc。

        rust-lang 官方 dist 的二进制**不带 OHOS code signature**，在本设备/CI 上
        直接 exec 报 `Permission denied`（errno 13，与 mode 位和路径无关）；
        故复制到构建目录后逐个自签名。`rustc` 还会 dlopen
        `librustc_driver-*.so`，该库也须一并签名。
        实测：签名后 cargo/rustc 均可执行（cargo 1.97.1 / rustc 1.97.1）。
        """
        pkg = self.dependencies.build["rust-toolchain"].package_folder
        # rustc 靠自身路径推导 sysroot，二进制一旦搬离包目录就找不到 target 标准库
        # （实测 E0463 can't find crate for `std`）。故记下包目录作为显式 sysroot，
        # 由 _build_env 以 --sysroot 传给 rustc；这样只复制+签名需要 exec 的少数
        # 文件，~890MB 的只读负载（std rlib 等）留在包内不动。
        self._rust_sysroot = pkg
        src_bin = os.path.join(pkg, "bin")
        src_lib = os.path.join(pkg, "lib")
        dest = os.path.join(self.build_folder, "rust-toolchain")
        os.makedirs(os.path.join(dest, "bin"), exist_ok=True)
        os.makedirs(os.path.join(dest, "lib"), exist_ok=True)

        signer = self._find_signer()
        if not signer:
            raise ConanInvalidConfiguration(
                "binary-sign-tool not found; it is required to sign the "
                "unsigned rust-toolchain binaries on OHOS "
                f"(looked for: {', '.join(SIGNER_CANDIDATES)})"
            )

        targets = []
        for name in ("cargo", "rustc"):
            s = os.path.join(src_bin, name)
            if os.path.isfile(s):
                d = os.path.join(dest, "bin", name)
                shutil.copy2(s, d)
                targets.append(d)
        for drv in glob.glob(os.path.join(src_lib, "librustc_driver-*.so")):
            d = os.path.join(dest, "lib", os.path.basename(drv))
            shutil.copy2(drv, d)
            targets.append(d)
        if not targets:
            raise ConanInvalidConfiguration(
                f"rust-toolchain package has no cargo/rustc under {src_bin}"
            )
        for t in targets:
            self._sign(t, signer)
            self.output.info(f"signed {os.path.relpath(t, dest)}")

        cargo = os.path.join(dest, "bin", "cargo")
        rustc = os.path.join(dest, "bin", "rustc")
        if not (RainfrogConan._runnable(cargo, "cargo")
                and RainfrogConan._runnable(rustc, "rustc")):
            raise ConanInvalidConfiguration(
                "signed rust-toolchain binaries are still not runnable"
            )
        return cargo, rustc

    # ── 运行期库（cargo 动态链接 libssl/libcrypto/libz）────────────────
    def _fetch_runtime_libs(self):
        """下载 OpenSSL / zlib / 根证书、备好 LD_LIBRARY_PATH 与 SSL_CERT_FILE。

        为何仍需外部 bottle：`rust-toolchain` 的 cargo 动态链接
        libssl.so / libcrypto.so / libz.so（实测 NEEDED），而这三者不在该工具包内。
        这些 bottle 在 CI 上实测可正常下载（与 rust bottle 不同，后者已 404）。
        按候选集依次尝试，任一成功即返回（单一 URL 不可达不再一击致命）。
        """
        base = os.path.join(self.build_folder, "rust-libs")
        os.makedirs(base, exist_ok=True)
        last_error = None
        for label, bottles in (
            ("pinned", self.conan_data.get("runtime_libs", [])),
            ("fallback-current", self.conan_data.get("runtime_libs_fallback", [])),
        ):
            if not bottles:
                continue
            try:
                self.output.info(f"provisioning rust runtime libs (candidate: {label})")
                for bottle in bottles:
                    get(
                        self,
                        url=bottle["url"],
                        sha256=bottle["sha256"],
                        destination=base,
                        keep_permissions=True,
                        strip_root=False,
                    )
                break
            except ConanException as exc:
                last_error = exc
                self.output.warning(
                    f"runtime-libs candidate '{label}' failed ({exc}); trying next"
                )
                continue
        else:
            if last_error is not None:
                raise ConanInvalidConfiguration(
                    "no rust runtime-libs candidate could be provisioned; "
                    f"last error: {last_error}"
                )

        lib_dirs = []
        for root, _dirs, files in os.walk(base):
            if os.path.basename(root) != "lib":
                continue
            if {"libssl.so", "libcrypto.so", "libz.so"} & set(files):
                lib_dirs.append(root)
        for d in lib_dirs:
            for f in os.listdir(d):
                p = os.path.join(d, f)
                if os.path.isfile(p) and not os.path.islink(p):
                    try:
                        os.chmod(p, 0o755)
                    except OSError:
                        pass
        if lib_dirs:
            existing = os.environ.get("LD_LIBRARY_PATH", "")
            os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
                lib_dirs + ([existing] if existing else [])
            )
        else:
            self.output.warning(
                "no libssl/libcrypto/libz directory found in runtime bottles"
            )

        if not os.environ.get("SSL_CERT_FILE"):
            for root, _dirs, files in os.walk(base):
                for cert_name in ("cert.pem", "cacert.pem"):
                    cert = os.path.join(root, cert_name)
                    if os.path.isfile(cert):
                        os.environ["SSL_CERT_FILE"] = cert
                        os.environ["CURL_CA_BUNDLE"] = cert
                        break
                if os.environ.get("SSL_CERT_FILE"):
                    break

    # ── 构建环境 ─────────────────────────────────────────────────────
    def _build_env(self):
        # 先备运行期库：cargo 需要 libssl/libcrypto/libz，库没就位它起不来，
        # 而"起不起得来"是下面判定工具可用的方式。
        self._fetch_runtime_libs()

        self._rust_sysroot = None
        cargo = self._find_tool("cargo")
        rustc = self._find_tool("rustc")
        if not (cargo and rustc) and str(self.settings.os) == "OHOS":
            self.output.info(
                "no runnable cargo/rustc on this host — provisioning from the "
                "rust-toolchain conan package (signing as needed)"
            )
            cargo, rustc = self._provision_toolchain()
        if not cargo or not rustc:
            raise ConanInvalidConfiguration(
                "Rust/Cargo toolchain is required to build rainfrog; "
                "provision the OHOS Rust toolchain before conan create"
            )

        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}
        )
        cc = compiler_executables.get("c") or (
            shutil.which("clang") or "/data/service/hnp/bin/clang"
        )
        cxx = compiler_executables.get("cpp") or (
            shutil.which("clang++") or "/data/service/hnp/bin/clang++"
        )
        tmpdir = (
            os.environ.get("HMBS_TMPDIR")
            or os.environ.get("TMPDIR")
            or os.path.join(self.build_folder, "tmp")
        )
        os.makedirs(tmpdir, exist_ok=True)

        cargo_config_dir = os.path.join(self.source_folder, ".cargo")
        os.makedirs(cargo_config_dir, exist_ok=True)
        with open(
            os.path.join(cargo_config_dir, "config.toml"), "w", encoding="utf-8"
        ) as handle:
            handle.write(
                '[source.crates-io]\nreplace-with = "rsproxy-sparse"\n'
                '[source.rsproxy-sparse]\n'
                'registry = "sparse+https://rsproxy.cn/index/"\n'
                "[net]\nretry = 10\n"
                "[http]\ntimeout = 600\nlow-speed-limit = 1\n"
            )

        env = dict(os.environ)
        env.update(
            {
                "CARGO": cargo,
                "RUSTC": rustc,
                "CC": cc,
                "CXX": cxx,
                "RUSTFLAGS": (
                    (f"--sysroot={self._rust_sysroot} " if self._rust_sysroot else "")
                    + f"-C linker={cc}"
                ),
                "CARGO_TARGET_DIR": os.path.join(self.build_folder, "target"),
                "CARGO_NET_RETRY": "10",
                "CARGO_HTTP_TIMEOUT": "600",
                "CARGO_BUILD_JOBS": "1",
                "TMPDIR": tmpdir,
                "TMP": tmpdir,
                "TEMP": tmpdir,
            }
        )
        if not env.get("SSL_CERT_FILE"):
            for ca in (
                "/storage/Users/currentUser/usr/local/ssl/cert.pem",
                "/etc/ssl/certs/cacert.pem",
                "/etc/ssl/cert.pem",
                os.path.expanduser("~/.harmonybrew/etc/ca-certificates/cert.pem"),
            ):
                if os.path.isfile(ca):
                    env["SSL_CERT_FILE"] = ca
                    env["CURL_CA_BUNDLE"] = ca
                    break
        tool_dirs = list(dict.fromkeys(
            [os.path.dirname(cargo), os.path.dirname(rustc)]
        ))
        env["PATH"] = os.pathsep.join(tool_dirs + [env.get("PATH", "")])
        return cargo, env

    @staticmethod
    def _parse_test_counts(output):
        passed = failed = ignored = 0
        pattern = re.compile(
            r"test result:\s+\w+\.\s+(\d+) passed;\s+"
            r"(\d+) failed;\s+(\d+) ignored;"
        )
        for m in pattern.finditer(output):
            passed += int(m.group(1))
            failed += int(m.group(2))
            ignored += int(m.group(3))
        return passed, failed, ignored

    def _run_upstream_tests(self, cargo, env):
        proc = subprocess.run(
            [cargo, *CARGO_TEST_ARGS],
            cwd=self.source_folder,
            env=env,
            capture_output=True,
            text=True,
            timeout=3600,
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        print(output, flush=True)
        passed, failed, ignored = self._parse_test_counts(output)
        executed = passed + failed
        marker = {
            "status": "passed" if proc.returncode == 0 and failed == 0 else "failed",
            "framework": "cargo-test",
            "command": UPSTREAM_TEST_COMMAND,
            "discovered": executed + ignored,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": ignored,
        }
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker), flush=True)
        if proc.returncode != 0 or failed != 0 or executed == 0:
            raise ConanException(
                "rainfrog upstream cargo tests failed or produced no results: "
                + json.dumps(marker)
            )

    def build(self):
        apply_conandata_patches(self)
        cargo, env = self._build_env()
        proc = subprocess.run(
            [cargo, *CARGO_BUILD_ARGS],
            cwd=self.source_folder,
            env=env,
            capture_output=True,
            text=True,
            timeout=7200,
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        print(output, flush=True)
        if proc.returncode != 0:
            raise ConanException(
                f"cargo build failed with exit code {proc.returncode}"
            )
        self._run_upstream_tests(cargo, env)

    def package(self):
        target_dir = os.path.join(self.build_folder, "target", "release")
        binary = os.path.join(target_dir, self.name)
        if not os.path.isfile(binary):
            raise ConanException(
                f"rainfrog binary not found after cargo build: {binary}"
            )
        copy(
            self,
            self.name,
            src=target_dir,
            dst=os.path.join(self.package_folder, "bin"),
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
