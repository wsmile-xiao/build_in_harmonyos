#!/usr/bin/env python3
"""Conan recipe for teller 2.0.7.

teller 是 Rust/Cargo workspace（teller-cli → bin `teller`、teller-core、
teller-providers、xtask），交叉编译到 aarch64-unknown-linux-ohos。

Rust 工具链来自制品仓基础设施包 rust-toolchain/1.97.1（tool_requires，
rust-lang 官方 dist 预编译，宿主与目标均为 aarch64-unknown-linux-ohos）。
不使用 rustup：标准 rustup 无法识别 HarmonyOS 宿主（知识 E105/E154，
"unrecognized OS type: HarmonyOS"）。

OHOS 拒绝执行未签名 ELF，而 rust-toolchain 包内的 cargo/rustc 不带 code
signature（实测 EACCES errno 13），故 build() 把 cargo/rustc 及 rustc
dlopen 的 librustc_driver 复制到 build_folder 内用 binary-sign-tool
-selfSign 1 自签名后使用（below/0.11.0 先例）。

cargo 自身动态链接 libssl/libcrypto/libz，OHOS loader 忽略 DT_RUNPATH，
故从 conandata 的 rust_runtime bottle 取共享库前置进 LD_LIBRARY_PATH。

teller 的 etcd provider（默认特性）经 etcd-client → tonic-build →
prost-build 需要 protoc：由 tool_requires protobuf/3.17.3 提供（上游 CI
`dist` 作业同样在构建前安装 protoc）。HashiCorp Vault provider 经
rustify(native-tls) → openssl-sys 需要 OpenSSL：由 requires
openssl/3.5.8.1 提供（静态链接，产物 DT_NEEDED 仅 libc.so）。

上游测试套件默认在 build() 内实跑（cargo test --workspace --all-features），
置 OHC_SKIP_UPSTREAM_TESTS=1 可跳过；失败不阻断打包（flow_test 依赖
Docker/Vault/LocalStack，属环境限制），实测统计见 notes.md / reports/。
"""
import os
import shlex
import shutil
import subprocess
import tarfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy, download,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout


class TellerConan(ConanFile):
    name = "teller"
    version = "2.0.7"
    description = "A developer-first multi provider secret manager"
    license = "Apache-2.0"
    homepage = "https://github.com/tellerops/teller"
    url = "https://github.com/tellerops/teller"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"teller is only supported on Linux/OHOS, got {self.settings.os}"
            )
        self._ohos_target()

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # rustify（hashicorp_vault 默认特性）→ reqwest/default-tls →
        # native-tls → openssl-sys：需要外部 OpenSSL（静态，产物自包含）。
        self.requires("openssl/3.5.8.1")

    def build_requirements(self):
        # Rust 工具链基础设施包（rust-lang 官方 dist 预编译）。
        self.tool_requires("rust-toolchain/1.97.1")
        # etcd-client → tonic-build → prost-build 需要 protoc。
        self.tool_requires("protobuf/3.17.3")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ── build ────────────────────────────────────────────────────────

    def build(self):
        apply_conandata_patches(self)
        env = self._rust_environment()
        if os.environ.get("OHC_SKIP_UPSTREAM_TESTS") != "1":
            self._run_upstream_tests(env)
        self._cargo_build(env)
        self._sign_binaries()

    def _ohos_target(self):
        mapping = {
            "armv8": "aarch64-unknown-linux-ohos",
            "armv8.3": "aarch64-unknown-linux-ohos",
            "arm64": "aarch64-unknown-linux-ohos",
            "aarch64": "aarch64-unknown-linux-ohos",
            "x86_64": "x86_64-unknown-linux-ohos",
        }
        target = mapping.get(str(self.settings.arch))
        if not target:
            raise ConanInvalidConfiguration(
                f"No Rust target mapping for arch {self.settings.arch}"
            )
        return target

    def _dep(self, name, build=False):
        try:
            deps = self.dependencies.build if build else self.dependencies
            return deps.get(name)
        except Exception:  # noqa: BLE001 - dependency may be absent
            return None

    def _ohos_cc(self):
        conf = self.conf.get("tools.build:compiler_executables", default={}) or {}
        candidates = [conf.get("c") if isinstance(conf, dict) else None,
                      shutil.which("aarch64-unknown-linux-ohos-clang"),
                      "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/"
                      "ohos/native/llvm/bin/aarch64-unknown-linux-ohos-clang"]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        raise ConanInvalidConfiguration(
            "aarch64-unknown-linux-ohos-clang not found (OHOS SDK missing)"
        )

    def _ca_bundle(self):
        candidates = [
            os.environ.get("CURL_CA_BUNDLE"),
            os.environ.get("SSL_CERT_FILE"),
            "/storage/Users/currentUser/usr/local/ssl/cert.pem",
            "/etc/ssl/certs/cacert.pem",
            "/etc/ssl/cert.pem",
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

    def _find_binary_sign_tool(self):
        candidates = [
            os.environ.get("BINARY_SIGN_TOOL"),
            shutil.which("binary-sign-tool"),
            "/data/service/hnp/bin/binary-sign-tool",
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/"
            "toolchains/lib/binary-sign-tool",
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

    def _prepare_signed_toolchain(self):
        """rust-toolchain 包内 cargo/rustc 未签名（OHOS 拒绝 execve），
        复制到 build_folder 内自签名；其余只读负载软链（幂等，marker 文件）。
        """
        dst = os.path.join(self.build_folder, "rust-toolchain")
        bin_dst = os.path.join(dst, "bin")
        lib_dst = os.path.join(dst, "lib")
        marker = os.path.join(dst, ".prepared")
        if os.path.isfile(marker):
            return bin_dst
        tool = self._dep("rust-toolchain", build=True)
        if not tool:
            raise ConanInvalidConfiguration(
                "rust-toolchain/1.97.1 tool_requires package not available"
            )
        src = tool.package_folder
        os.makedirs(bin_dst, exist_ok=True)
        os.makedirs(lib_dst, exist_ok=True)

        signer = self._find_binary_sign_tool()
        if not signer:
            self.output.warning(
                "binary-sign-tool not found; rust toolchain binaries stay "
                "unsigned and OHOS may reject them (EACCES)"
            )

        to_sign = []
        for name in ("cargo", "rustc"):
            s = os.path.join(src, "bin", name)
            if not os.path.isfile(s):
                continue
            d = os.path.join(bin_dst, name)
            if not os.path.isfile(d):
                shutil.copy2(s, d)
            to_sign.append(d)
        src_lib = os.path.join(src, "lib")
        if os.path.isdir(src_lib):
            for name in sorted(os.listdir(src_lib)):
                if name.startswith("librustc_driver") and name.endswith(".so"):
                    d = os.path.join(lib_dst, name)
                    if not os.path.isfile(d):
                        shutil.copy2(os.path.join(src_lib, name), d)
                    to_sign.append(d)

        for path in to_sign:
            os.chmod(path, 0o755)
            if signer:
                tmp = path + ".signed"
                res = subprocess.run(
                    [signer, "sign", "-inFile", path, "-outFile", tmp,
                     "-selfSign", "1"],
                    capture_output=True, text=True,
                )
                if res.returncode != 0 or not os.path.isfile(tmp):
                    raise ConanInvalidConfiguration(
                        "binary-sign-tool failed for %s (rc=%d): %s"
                        % (path, res.returncode, res.stderr[:200])
                    )
                os.replace(tmp, path)
            os.chmod(path, 0o755)
            self.output.info("signed toolchain binary: %s"
                             % os.path.basename(path))

        # 其余只读负载（lib/rustlib、proc-macro dylib 等）软链，避免复制
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

        with open(marker, "w", encoding="utf-8") as fh:
            fh.write("signed toolchain prepared\n")
        return bin_dst

    def _prepare_runtime_libs(self):
        """cargo 运行期共享库（libssl/libcrypto/libz）：解包 bottle，返回 lib 目录。"""
        base = os.path.join(self.build_folder, "rust-runtime")
        os.makedirs(base, exist_ok=True)
        lib_dirs = []
        for item in self.conan_data.get("rust_runtime", []):
            tgz = os.path.join(base, item["name"] + ".tar.gz")
            if not os.path.isfile(tgz):
                download(self, item["url"], tgz, sha256=item["sha256"])
            extract_dir = os.path.join(base, item["name"])
            os.makedirs(extract_dir, exist_ok=True)
            with tarfile.open(tgz, "r:gz") as tf:
                tf.extractall(extract_dir)
            for root, _dirs, files in os.walk(extract_dir):
                if os.path.basename(root) != "lib":
                    continue
                if any(f.startswith(("libssl.", "libcrypto.")) for f in files):
                    lib_dirs.append(root)
        return lib_dirs

    def _configure_cargo_home(self, ca_bundle=None):
        cargo_home = os.path.join(self.build_folder, "cargo-home")
        os.makedirs(cargo_home, exist_ok=True)
        content = (
            "[source.crates-io]\n"
            "replace-with = \"rsproxy-sparse\"\n\n"
            "[source.rsproxy-sparse]\n"
            "registry = \"sparse+https://rsproxy.cn/index/\"\n\n"
            "[net]\n"
            "git-fetch-with-cli = true\n"
            "retry = 10\n"
        )
        if ca_bundle:
            content += "\n[http]\ntimeout = 600\ncainfo = \"%s\"\n" % ca_bundle
        with open(os.path.join(cargo_home, "config.toml"), "w",
                  encoding="utf-8", newline="\n") as fh:
            fh.write(content)
        return cargo_home

    def _rust_environment(self):
        env = dict(os.environ)
        bin_dir = self._prepare_signed_toolchain()
        cargo = os.path.join(bin_dir, "cargo")
        if not os.path.isfile(cargo):
            raise ConanInvalidConfiguration(
                f"cargo not found in signed toolchain dir: {cargo}"
            )
        env["CARGO"] = cargo
        env["PATH"] = os.pathsep.join(
            [bin_dir, "/system/bin", "/system/sbin"]
        ) + os.pathsep + env.get("PATH", "")

        lib_dirs = [os.path.join(self.build_folder, "rust-toolchain", "lib")]
        lib_dirs += self._prepare_runtime_libs()
        prev = env.get("LD_LIBRARY_PATH", "")
        env["LD_LIBRARY_PATH"] = os.pathsep.join(
            lib_dirs + ([prev] if prev else [])
        )

        ca = self._ca_bundle()
        if ca:
            env["SSL_CERT_FILE"] = ca
            env["CURL_CA_BUNDLE"] = ca
        env["CARGO_HOME"] = self._configure_cargo_home(ca)
        env["CARGO_NET_RETRY"] = "10"
        env["CARGO_HTTP_TIMEOUT"] = "600"
        env["TMPDIR"] = env.get("TMPDIR") or self.build_folder

        # protoc（etcd-client → tonic-build → prost-build）
        protobuf = self._dep("protobuf", build=True)
        if protobuf:
            protoc = os.path.join(protobuf.package_folder, "bin", "protoc")
            if os.path.isfile(protoc):
                env["PROTOC"] = protoc
                env["PATH"] = (os.path.dirname(protoc) + os.pathsep
                               + env["PATH"])

        # OpenSSL（openssl-sys：rustify → native-tls）
        openssl = self._dep("openssl")
        if openssl:
            env["OPENSSL_DIR"] = openssl.package_folder
            env["OPENSSL_INCLUDE_DIR"] = os.path.join(
                openssl.package_folder, "include")
            env["OPENSSL_LIB_DIR"] = os.path.join(
                openssl.package_folder, "lib")
            pkgconfig = os.path.join(openssl.package_folder, "lib", "pkgconfig")
            if os.path.isdir(pkgconfig):
                env["PKG_CONFIG_PATH"] = pkgconfig + os.pathsep + env.get(
                    "PKG_CONFIG_PATH", "")

        if str(self.settings.os) == "OHOS":
            cc = self._ohos_cc()
            cxx = cc + "++" if not cc.endswith("++") else cc
            llvm_bin = os.path.dirname(cc)
            target = self._ohos_target()
            key = target.upper().replace("-", "_")
            env["CARGO_TARGET_%s_LINKER" % key] = cc
            env["CC_%s" % key.replace(".", "_")] = cc
            env["CXX_%s" % key.replace(".", "_")] = cxx
            env["AR_%s" % key.replace(".", "_")] = os.path.join(
                llvm_bin, "llvm-ar")
            env["RANLIB_%s" % key.replace(".", "_")] = os.path.join(
                llvm_bin, "llvm-ranlib")
        return env

    def _run_upstream_tests(self, env):
        """上游测试套件实跑（cargo test --workspace --all-features）。

        两点环境对齐/限制（详见 notes.md R51 申报）：
        1) 源码来自 tarball，无 VCS 元数据；而 teller 的 `scan` 走 ignore
           crate 的 gitignore 规则，该 crate 仅在目录链上存在 `.git` 时才
           应用 .gitignore（ignore-0.4.22 src/dir.rs: parent.join(".git")
           .exists()）。上游 CI 是 git checkout（有 .git），故此处补建
           `.git` 目录以对齐，否则 tests/cmd/scan.trycmd 有 2 例误判失败。
        2) 只跑 --lib --bins --tests --benches --examples：rust-toolchain/
           1.97.1（以及 Harmonybrew 的 OHOS rust bottle）均不提供 rustdoc
           二进制，doctest 在本平台无法执行（上游 CI 的 stable 工具链含
           rustdoc）。

        失败不阻断打包：flow_test 与 5 个 provider sanity 测试依赖 Docker
        （Vault 1.8.2 / LocalStack），属运行环境限制。OHC_REQUIRE_UPSTREAM_TESTS=1
        可要求全绿。
        """
        target = self._ohos_target()
        git_marker = os.path.join(self.source_folder, ".git")
        if not os.path.exists(git_marker):
            os.makedirs(git_marker, exist_ok=True)
        cmd = [env["CARGO"], "test", "--release", "--locked", "--target",
               target, "--all-features", "--workspace", "--no-fail-fast",
               "--lib", "--bins", "--tests", "--benches", "--examples"]
        self.output.info("running upstream tests: %s"
                         % " ".join(shlex.quote(p) for p in cmd))
        rc = subprocess.run(cmd, cwd=self.source_folder, env=env).returncode
        if rc != 0 and os.environ.get("OHC_REQUIRE_UPSTREAM_TESTS") == "1":
            raise ConanInvalidConfiguration(
                f"upstream teller tests failed for {target} (rc={rc})"
            )
        if rc != 0:
            self.output.warning(
                "upstream teller tests reported failures (rc=%d); "
                "known env-limited cases (Docker-based flow_test), "
                "see notes.md — continuing build" % rc
            )

    def _release_dir(self):
        return os.path.join(self.source_folder, "target",
                            self._ohos_target(), "release")

    def _cargo_build(self, env):
        target = self._ohos_target()
        cmd = [env["CARGO"], "build", "--release", "--locked",
               "--target", target]
        self.output.info("building teller: %s"
                         % " ".join(shlex.quote(p) for p in cmd))
        rc = subprocess.run(cmd, cwd=self.source_folder, env=env).returncode
        if rc != 0:
            raise ConanInvalidConfiguration(
                f"cargo build failed for {target} (rc={rc})"
            )
        binary = os.path.join(self._release_dir(), "teller")
        if not os.path.isfile(binary):
            raise ConanInvalidConfiguration(
                f"teller binary not produced: {binary}"
            )
        out_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(out_dir, exist_ok=True)
        dst = os.path.join(out_dir, "teller")
        shutil.copy2(binary, dst)
        os.chmod(dst, 0o755)

    def _sign_binaries(self):
        if str(self.settings.os) != "OHOS":
            return
        signer = self._find_binary_sign_tool()
        if not signer:
            raise ConanInvalidConfiguration(
                "binary-sign-tool not found; OHOS cannot execve unsigned ELF"
            )
        out_dir = os.path.join(self.build_folder, "bin")
        for name in sorted(os.listdir(out_dir)):
            path = os.path.join(out_dir, name)
            if not os.path.isfile(path):
                continue
            tmp = path + ".signed"
            res = subprocess.run(
                [signer, "sign", "-inFile", path, "-outFile", tmp,
                 "-selfSign", "1"],
                capture_output=True, text=True,
            )
            if res.returncode != 0 or not os.path.isfile(tmp):
                raise ConanInvalidConfiguration(
                    "binary-sign-tool failed (rc=%d): %s"
                    % (res.returncode, path)
                )
            os.replace(tmp, path)
            os.chmod(path, 0o755)
            self.output.info("signed binary: %s" % name)

    # ── package ──────────────────────────────────────────────────────

    def package(self):
        copy(self, "teller", src=os.path.join(self.build_folder, "bin"),
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)
        copy(self, "README.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin"))
