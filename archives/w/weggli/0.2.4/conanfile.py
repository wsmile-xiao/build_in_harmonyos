#!/usr/bin/env python3
"""Conan recipe — weggli 0.2.4 (Cargo / Rust).

weggli is a semantic search tool for C and C++ codebases (originally Google
Project Zero, now maintained at weggli-rs/weggli). It is a pure Cargo project:
the tree-sitter C runtime comes from the `tree-sitter` crate and weggli's own
vendored C/C++ grammars (third_party/grammars/**) are compiled by build.rs
through the `cc` crate, so the OHOS clang/clang++ toolchain is the only
external compiler dependency.

OHOS adaptation
---------------
1. Toolchain (R36): `rust-toolchain/1.97.1` from the ohpcd repository
   (tool_requires) provides cargo/rustc plus the aarch64-unknown-linux-ohos
   standard library. Conan unpacks that payload with mode 0660, so cargo and
   rustc are copied into the private build folder, made executable, and — only
   if the OHOS loader still refuses them — self-signed with the OHOS
   binary-sign-tool (below/0.11.0 precedent). The remaining payload is
   symlinked, never duplicated.
2. Cargo runtime: cargo 1.97 dynamic-links libssl.so/libcrypto.so/libz.so and
   uses symbols (SSL_get0_group_name) the system OpenSSL 3.0 does not export;
   the sha256-pinned Harmonybrew OHOS bottles are unpacked into the build
   folder and put on LD_LIBRARY_PATH (below/argc/alass precedent). No shared
   system prefix is written (R49).
3. CXXSTDLIB=c++: build.rs compiles one C++ grammar file, and the `cc` crate
   emits `-lstdc++` by default while the OHOS SDK ships libc++ only.
4. patches/000{1,2}: deterministic lock-graph migration for target_env=ohos
   (knowledge E358) — nix 0.17.0 -> 0.28.0 (nix 0.28 being the first release
   with OHOS support, `signal` feature enabled) and libc 0.2.112 -> 0.2.155
   (first libc with target_env="ohos" definitions), regenerated with
   `cargo update -p … --precise` so the build stays `--locked`. No weggli
   source line is changed.

Upstream tests (R51): the complete Rust suite is executed in build() against
the patched source — 2 lib unit tests, 9 tests/cli.rs and 45 tests/query.rs
cases — with the real `test result:` lines parsed into
res/upstream_test_result.json. test_package re-emits HMBS_UPSTREAM_TEST_RESULT
from that record (ali/0.8.0 precedent: a cached binary skips build(), so the
evidence has to be re-published from the package). The optional Python binding
suite (tests/__init__.py, 4 unittest cases, Cargo feature `python` + pyo3
0.13.2) was executed during adaptation on the OHOS device (4 passed; the OHOS
loader needs LD_PRELOAD=libpython3.12.so.1.0 for pyo3 extension modules) and is
documented in notes.md / reports/upstream-tests.md; it is not part of this
package's gate because the package ships the CLI binary only.
"""
import json
import os
import re
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout

OHOS_TARGET = "aarch64-unknown-linux-ohos"
_OHOS_TARGET_ENV = OHOS_TARGET.upper().replace("-", "_")
UPSTREAM_TEST_COMMAND = (
    "cargo test --release --locked --target aarch64-unknown-linux-ohos "
    "--lib --bins --tests -- --test-threads=1"
)
# 2 (src/result.rs, src/util.rs) + 9 (tests/cli.rs) + 45 (tests/query.rs)
UPSTREAM_TEST_DISCOVERED = 56

# OHOS 拒绝执行无执行位（Conan 包内文件为 0660）的 ELF。
_SIGN_TOOL_CANDIDATES = (
    "/data/service/hnp/bin/binary-sign-tool",
    "binary-sign-tool",
)


class WeggliConan(ConanFile):
    name = "weggli"
    version = "0.2.4"
    description = ("weggli: a fast and robust semantic search tool for C and "
                   "C++ codebases")
    license = "Apache-2.0"
    homepage = "https://github.com/weggli-rs/weggli"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self, src_folder="src")

    def export_sources(self):
        # 两个补丁随配方导出（conandata.yml 的 patches 声明）
        export_conandata_patches(self)

    def build_requirements(self):
        # R36：Rust 工具链来自制品仓已发布的基础设施包
        # （rust-toolchain/1.97.1，OHOS armv8 二进制）。
        self.tool_requires("rust-toolchain/1.97.1")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"Unsupported OS: {self.settings.os}")
        if str(self.settings.arch) not in ("armv8", "aarch64"):
            raise ConanInvalidConfiguration(
                f"Unsupported arch: {self.settings.arch}")
        if str(self.settings.build_type) != "Release":
            raise ConanInvalidConfiguration("Release build_type is required")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ── toolchain ──────────────────────────────────────────────────────

    def _toolchain_root(self):
        return os.path.join(self.build_folder, "rust-toolchain")

    def _prepare_toolchain(self, runtime_dirs):
        """Copy cargo/rustc into a private, executable toolchain root.

        rustc resolves its sysroot from its own path, so lib/ is mirrored with
        symlinks and only the binaries that must be exec'ed are copied
        (below/0.11.0 precedent).

        HMDFS rejects chmod (E046) and refuses to exec the unsigned Conan
        payload even when the mode reads 0770 (EACCES), so cargo/rustc (and the
        librustc_driver that rustc dlopens) are self-signed with the OHOS
        binary-sign-tool whenever the probe cannot start them.
        """
        dep = self.dependencies.build.get("rust-toolchain")
        if not dep:
            raise ConanInvalidConfiguration(
                "rust-toolchain/1.97.1 tool_requires is required")
        src = dep.package_folder
        root = self._toolchain_root()
        bin_dst = os.path.join(root, "bin")
        lib_dst = os.path.join(root, "lib")
        os.makedirs(bin_dst, exist_ok=True)
        os.makedirs(lib_dst, exist_ok=True)

        executables = []
        for name in ("cargo", "rustc"):
            source = os.path.join(src, "bin", name)
            if not os.path.isfile(source):
                raise ConanInvalidConfiguration(
                    f"rust-toolchain payload is missing bin/{name}")
            target = os.path.join(bin_dst, name)
            shutil.copy2(source, target)
            os.chmod(target, 0o755)
            executables.append(target)

        src_lib = os.path.join(src, "lib")
        symlink_later = []
        if os.path.isdir(src_lib):
            for name in sorted(os.listdir(src_lib)):
                source = os.path.join(src_lib, name)
                if name.startswith("librustc_driver") and name.endswith(".so"):
                    target = os.path.join(lib_dst, name)
                    shutil.copy2(source, target)
                    os.chmod(target, 0o755)
                    executables.append(target)
                    continue
                symlink_later.append(name)
        for name in symlink_later:
            self._link(os.path.join(src_lib, name),
                       os.path.join(lib_dst, name))
        for name in ("etc", "libexec", "share"):
            source = os.path.join(src, name)
            if os.path.isdir(source):
                self._link(source, os.path.join(root, name))

        if not self._toolchain_runs(bin_dst, lib_dst, runtime_dirs):
            self._sign(executables)
            if not self._toolchain_runs(bin_dst, lib_dst, runtime_dirs):
                raise ConanInvalidConfiguration(
                    "rust-toolchain cargo/rustc cannot be executed on OHOS")
        return bin_dst, lib_dst

    @staticmethod
    def _link(source, target):
        if not os.path.exists(target) and not os.path.islink(target):
            os.symlink(source, target)

    def _toolchain_runs(self, bin_dst, lib_dst, runtime_dirs):
        env = dict(os.environ)
        env["LD_LIBRARY_PATH"] = os.pathsep.join(
            [lib_dst, *runtime_dirs, env.get("LD_LIBRARY_PATH", "")])
        try:
            proc = subprocess.run([os.path.join(bin_dst, "cargo"), "--version"],
                                  capture_output=True, text=True,
                                  env=env, timeout=120)
        except (OSError, subprocess.SubprocessError) as exc:
            self.output.warning(f"cargo probe failed: {exc}")
            return False
        if proc.returncode == 0:
            self.output.info(f"toolchain: {proc.stdout.strip()}")
        else:
            self.output.warning(
                f"cargo probe rc={proc.returncode}: {proc.stderr.strip()[:200]}")
        return proc.returncode == 0

    def _sign(self, paths):
        signer = next((c for c in _SIGN_TOOL_CANDIDATES if os.path.isfile(c)),
                      None)
        if not signer:
            self.output.warning(
                "binary-sign-tool not found; the OHOS loader may reject the "
                "toolchain binaries")
            return
        for path in paths:
            signed = path + ".signed"
            proc = subprocess.run(
                [signer, "sign", "-inFile", path, "-outFile", signed,
                 "-selfSign", "1"], capture_output=True, text=True)
            if proc.returncode != 0 or not os.path.isfile(signed):
                self.output.warning(f"binary-sign-tool failed for {path}")
                continue
            os.replace(signed, path)
            os.chmod(path, 0o755)

    # ── cargo runtime (OpenSSL/zlib shared libraries) ──────────────────

    def _runtime_lib_dirs(self):
        base = os.path.join(self.build_folder, "cargo-runtime")
        dirs = []
        for root, _dirs, files in os.walk(base):
            if os.path.basename(root) != "lib":
                continue
            if {"libssl.so", "libcrypto.so", "libz.so"} & set(files):
                dirs.append(root)
        return dirs

    def _prepare_cargo_runtime(self):
        base = os.path.join(self.build_folder, "cargo-runtime")
        os.makedirs(base, exist_ok=True)
        for bottle in self.conan_data["cargo_runtime"]:
            get(self, url=bottle["url"], sha256=bottle["sha256"],
                destination=os.path.join(base, "dl"),
                strip_root=False, keep_permissions=True)
        dirs = self._runtime_lib_dirs()
        if not dirs:
            raise ConanInvalidConfiguration(
                "cargo runtime libraries (libssl/libcrypto/libz) were not "
                "unpacked from the pinned Harmonybrew bottles")
        return dirs

    # ── build environment (R33: every variable defined here, no shell env) ─

    def _compilers(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={})
        cc = compilers.get("c") or shutil.which("clang") \
            or "/data/service/hnp/bin/clang"
        cxx = compilers.get("cpp") or shutil.which("clang++") \
            or "/data/service/hnp/bin/clang++"
        return cc, cxx

    def _sdk_lib_dir(self, cc):
        """OHOS SDK llvm/lib: the bundled lld needs its libxml2.so.16."""
        binary_dir = os.path.dirname(os.path.realpath(cc))
        candidate = os.path.join(os.path.dirname(binary_dir), "lib")
        return candidate if os.path.isdir(candidate) else ""

    def _ca_bundle(self):
        for candidate in (
            os.environ.get("SSL_CERT_FILE"),
            "/storage/Users/currentUser/usr/local/ssl/cert.pem",
            "/etc/ssl/certs/cacert.pem",
            "/etc/ssl/cert.pem",
            os.path.expanduser("~/.harmonybrew/etc/ca-certificates/cert.pem"),
        ):
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

    def _build_env(self, bin_dst, lib_dst, runtime_dirs):
        cc, cxx = self._compilers()
        cargo_home = os.path.join(self.build_folder, "cargo-home")
        target_dir = os.path.join(self.build_folder, "target")
        tmpdir = os.environ.get("HMBS_TMPDIR") \
            or os.path.join(self.build_folder, "tmp")
        for directory in (cargo_home, target_dir, tmpdir):
            os.makedirs(directory, exist_ok=True)

        ca_bundle = self._ca_bundle()
        # crates.io 走 rsproxy.cn 稀疏镜像（设备无 crates.io CA 链），
        # 并把系统 CA 显式交给 cargo，否则拉索引报 CERTIFICATE_VERIFY_FAILED。
        with open(os.path.join(cargo_home, "config.toml"), "w",
                  encoding="utf-8", newline="\n") as handle:
            handle.write(
                '[source.crates-io]\nreplace-with = "rsproxy-sparse"\n'
                '[source.rsproxy-sparse]\n'
                'registry = "sparse+https://rsproxy.cn/index/"\n'
                "[net]\nretry = 10\ngit-fetch-with-cli = true\n"
                "[http]\ntimeout = 600\nlow-speed-limit = 1\n"
            )
            if ca_bundle:
                handle.write(f'cainfo = "{ca_bundle}"\n')

        env = dict(os.environ)
        for name in ("RUSTFLAGS", "RUSTC", "CARGO", "CARGO_BUILD_TARGET"):
            env.pop(name, None)
        path_parts = [bin_dst]
        hnp_bin = "/data/service/hnp/bin"
        if os.path.isdir(hnp_bin):
            path_parts.append(hnp_bin)
        lib_parts = [lib_dst, *runtime_dirs]
        sdk_lib = self._sdk_lib_dir(cc)
        if sdk_lib:
            lib_parts.append(sdk_lib)
        env.update({
            "PATH": os.pathsep.join(path_parts + [env.get("PATH", "")]),
            "LD_LIBRARY_PATH": os.pathsep.join(
                lib_parts + [env.get("LD_LIBRARY_PATH", "")]),
            "CARGO_HOME": cargo_home,
            "CARGO_TARGET_DIR": target_dir,
            "CARGO_BUILD_JOBS": "2",
            "CARGO_NET_RETRY": "10",
            "CARGO_HTTP_TIMEOUT": "600",
            "TMPDIR": tmpdir,
            "TMP": tmpdir,
            "TEMP": tmpdir,
            "CC": cc,
            "CXX": cxx,
            # build.rs 经 cc 编译 tree-sitter-cpp 的 scanner.cc；cc 默认发
            # `-lstdc++`，OHOS SDK 只提供 libc++。
            "CXXSTDLIB": "c++",
            f"CARGO_TARGET_{_OHOS_TARGET_ENV}_LINKER": cc,
        })
        if ca_bundle:
            env["SSL_CERT_FILE"] = ca_bundle
            env["CURL_CA_BUNDLE"] = ca_bundle
            env["CARGO_HTTP_CAINFO"] = ca_bundle
        return env

    def _run(self, command, env, timeout, check=True):
        self.output.info(f"$ {shlex.join(command)}")
        proc = subprocess.run(command, cwd=self.source_folder, env=env,
                              capture_output=True, text=True, timeout=timeout)
        output = (proc.stdout or "") + (proc.stderr or "")
        print(output, flush=True)
        if check and proc.returncode != 0:
            raise ConanException(
                f"{shlex.join(command)} failed (rc={proc.returncode})")
        return proc.returncode, output

    # ── build + upstream tests ────────────────────────────────────────

    def build(self):
        apply_conandata_patches(self)
        # cargo 运行期共享库先就位：工具链可执行性探测（cargo --version）本身
        # 就需要 libssl.so/libcrypto.so。
        runtime_dirs = self._prepare_cargo_runtime()
        bin_dst, lib_dst = self._prepare_toolchain(runtime_dirs)
        env = self._build_env(bin_dst, lib_dst, runtime_dirs)
        cargo = os.path.join(bin_dst, "cargo")

        # ① 真实构建；--locked 保证锁图就是 patches/0001 迁移后的确定性锁图
        self._run([cargo, "build", "--release", "--locked",
                   "--target", OHOS_TARGET], env, timeout=3600)

        # ② 上游测试（R51）：真实执行完整 Rust 套件，计数取自框架输出
        rc, output = self._run(
            [cargo, "test", "--release", "--locked", "--target", OHOS_TARGET,
             "--lib", "--bins", "--tests", "--", "--test-threads=1"],
            env, timeout=3600, check=False)
        passed, failed, ignored = self._parse_test_counts(output)
        executed = passed + failed
        status = "passed" if rc == 0 and failed == 0 and executed > 0 else "failed"
        record = {
            "status": status,
            "framework": "cargo",
            "command": UPSTREAM_TEST_COMMAND,
            "discovered": executed,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": ignored,
            "expected_discovered": UPSTREAM_TEST_DISCOVERED,
        }
        self._persist_upstream_result(record)
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(record), flush=True)
        if status != "passed" or executed != UPSTREAM_TEST_DISCOVERED:
            raise ConanException(
                "upstream cargo test failed or produced unexpected counts: "
                f"{record}")

    @staticmethod
    def _parse_test_counts(output):
        passed = failed = ignored = 0
        for match in re.finditer(
                r"test result:\s+\w+\.\s+(\d+) passed;\s+(\d+) failed;\s+"
                r"(\d+) ignored", output):
            passed += int(match.group(1))
            failed += int(match.group(2))
            ignored += int(match.group(3))
        return passed, failed, ignored

    def _persist_upstream_result(self, record):
        directory = os.path.join(self.source_folder, "res")
        os.makedirs(directory, exist_ok=True)
        with open(os.path.join(directory, "upstream_test_result.json"), "w",
                  encoding="utf-8") as handle:
            json.dump(record, handle, ensure_ascii=False, indent=2)
            handle.write("\n")

    # ── package ───────────────────────────────────────────────────────

    def package(self):
        target_dir = os.path.join(self.build_folder, "target", OHOS_TARGET,
                                  "release")
        binary = os.path.join(target_dir, "weggli")
        if not os.path.isfile(binary):
            raise ConanInvalidConfiguration(
                f"cargo did not produce the expected executable: {binary}")
        copy(self, "weggli", src=target_dir,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)
        copy(self, "README.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "weggli"),
             keep_path=False)
        copy(self, "upstream_test_result.json",
             src=os.path.join(self.source_folder, "res"),
             dst=os.path.join(self.package_folder, "res"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libs = []
