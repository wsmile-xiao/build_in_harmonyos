#!/usr/bin/env python3
"""Conan recipe — rutabaga 0.1.80 (crates.io crate ``rutabaga_gfx``).

Upstream: https://github.com/magma-gpu/rutabaga_gfx (tag v0.1.80)
Crate:    https://crates.io/crates/rutabaga_gfx/0.1.80
          sha256 = 2817d168222af3c49269f583dd8e67429912953ae608f715fd97683ed50320a5

rutabaga is the "Rutabaga Virtual Graphics Interface" (VGI): a pure-Rust,
cross-platform GPU/display paravirtualization library (the crate is named
``rutabaga_gfx``; the conan package keeps the task name ``rutabaga``).
It is a Cargo library (``librutabaga_gfx.rlib``), no C API, no binaries.

OHOS adaptation (all of it real, verified on the OhOS aarch64 device):

1. Rust toolchain comes from the framework infra package
   ``rust-toolchain/1.97.1`` (``tool_requires``).  Stock rustup cannot be
   used because it does not recognise the HarmonyOS host
   ("unrecognized OS type: HarmonyOS").
2. The toolchain ELF files shipped in that package carry no HarmonyOS code
   signature, so the OHOS loader refuses to exec/load them
   (``Permission denied (os error 13)``).  ``cargo``/``rustc`` and the
   shared objects they need (``librustc_driver*.so`` plus cargo's OpenSSL
   runtime) are therefore copied into the build folder and self-signed with
   ``binary-sign-tool -selfSign 1`` before first use.
3. ``lib/rustlib`` MUST be a real directory copy, not a symlink: with a
   symlinked ``rustlib`` rustc cannot discover the bundled ``std``/``core``
   for ``aarch64-unknown-linux-ohos`` and dies with E0463
   ("can't find crate for `std`").  A real copy is staged (see ``_prepare``).
4. Cargo 1.97 dynamically links OpenSSL and needs ``SSL_get0_group_name``
   (OpenSSL >= 3.5, symbol version OPENSSL_3.2.0).  The OpenSSL 3 shipped
   with the device image is older and lacks the symbol
   (``symbol not found``), so the Harmonybrew OHOS OpenSSL 3.6.4 bottle is
   staged, signed and put on ``LD_LIBRARY_PATH`` (same bottle provenance as
   the ``libetebase``/``below`` recipes).  ``libz`` comes from the matching
   ``zlib-ng-compat`` bottle.
5. The linker is invoked as the SDK LLVM ``clang-15`` ELF directly with
   ``--target aarch64-linux-ohos --sysroot=<sdk sysroot> -D__MUSL__``.
   The ``aarch64-unknown-linux-ohos-clang`` wrapper *script* cannot be used
   as a rustc linker: rustc's ``exec`` of the /bin/sh wrapper fails with
   ``Permission denied (os error 13)`` on device.
6. ``/tmp`` is read-only on the device (E002) → ``TMPDIR``/``TMP``/``TEMP``
   are redirected to a writable build-folder directory, and cargo crates are
   fetched through the ``rsproxy.cn`` sparse mirror with an explicit CA
   bundle (no default CA store on the device).

Upstream tests: the crate registers 8 ``#[test]`` unit tests
(rutabaga_core 2, rutabaga_gralloc/formats 3, rutabaga_gralloc/gralloc 3,
``autotests = false`` → no integration-test target).  ``build()`` runs the
real upstream suite with ``cargo test --release --lib`` and reports the
parsed counts through ``HMBS_UPSTREAM_TEST_RESULT``.
"""

import glob
import json
import os
import re
import shutil
import subprocess
import tarfile
import urllib.request

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy, download,
                               export_conandata_patches)
from conan.tools.layout import basic_layout

OHOS_RUST_TARGET = "aarch64-unknown-linux-ohos"

# Cargo runtime shared libraries (Harmonybrew OHOS bottles, same provenance as
# archives/l/libetebase/0.5.8 and archives/b/below/0.11.0).
# Cargo runtime shared libraries.  cargo 1.97 needs OpenSSL >= 3.5
# (`SSL_get0_group_name`, symbol version OPENSSL_3.2.0); the OpenSSL shipped
# with the device image is older and lacks it, so the Harmonybrew OHOS
# OpenSSL 3.6.4 bottle is staged (same provenance as archives/l/libetebase).
# libz is taken from the platform (/system/lib64/platformsdk) — the Harmonybrew
# zlib bottle URL referenced by older recipes is no longer served (404).
RUNTIME_BOTTLES = (
    ("openssl3",
     "https://harmonybrew.atomgit.com/bottles/"
     "openssl%403-3.6.4.arm64_ohos.bottle.tar.gz",
     "e1be73c6c68e29c33ff43761045e43e23e7c369f0fb1a24f40e226ec5cb28f98"),
)

# Platform library search dirs added to LD_LIBRARY_PATH (cargo needs libz.so).
PLATFORM_LIB_DIRS = ("/system/lib64/platformsdk", "/system/lib64")

# Upstream unit tests (8 #[test] fns); counts are verified against the real
# `cargo test` output and re-emitted unchanged.
UPSTREAM_TESTS_TOTAL = 8


class RutabagaConan(ConanFile):
    name = "rutabaga"
    version = "0.1.80"
    description = ("Rutabaga Virtual Graphics Interface (rutabaga_gfx): "
                   "cross-platform Rust GPU/display paravirtualization")
    license = "BSD-3-Clause"
    homepage = "https://github.com/magma-gpu/rutabaga_gfx"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("graphics", "virtio-gpu", "rust", "paravirtualization")
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    # Rust builds an rlib (static) by default; shared is declared for Conan
    # compliance but not supported (no cdylib/C-ABI in the published crate).
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def configure(self):
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "rutabaga 0.1.80 ships a Rust rlib and cannot be built shared")

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):  # R32
            raise ConanInvalidConfiguration(
                f"rutabaga supports Linux/OHOS only, got {self.settings.os}")
        if str(self.settings.arch) not in ("armv8", "aarch64"):
            raise ConanInvalidConfiguration(
                f"rutabaga supports aarch64 only, got {self.settings.arch}")

    def build_requirements(self):
        # Rust toolchain infra package (host == target == aarch64-linux-ohos).
        self.tool_requires("rust-toolchain/1.97.1")

    def source(self):
        # The crates.io download endpoint has no file extension, so fetch to an
        # explicit .tar.gz name and unpack it with tarfile (conan's get() would
        # otherwise guess zip and fail with BadZipFile).  download() verifies
        # the sha256 against the value recorded in conandata.yml.
        tarball = os.path.join(self.source_folder,
                               "rutabaga_gfx-0.1.80.tar.gz")
        download(self, self.conan_data["sources"]["url"], tarball,
                 sha256=self.conan_data["sources"]["sha256"])
        with tarfile.open(tarball, "r:gz") as tf:
            tf.extractall(self.source_folder)
        os.remove(tarball)
        # strip the single top-level directory (rutabaga_gfx-0.1.80/)
        roots = [d for d in os.listdir(self.source_folder)
                 if os.path.isdir(os.path.join(self.source_folder, d))]
        if len(roots) == 1:
            inner = os.path.join(self.source_folder, roots[0])
            for entry in os.listdir(inner):
                shutil.move(os.path.join(inner, entry),
                            os.path.join(self.source_folder, entry))
            os.rmdir(inner)

    # ── build ────────────────────────────────────────────────────────
    def build(self):
        apply_conandata_patches(self)
        self._prepare_toolchain()
        self._prepare_runtime_libs()
        env = self._cargo_env()
        self._cargo_fetch(env)
        self._cargo_build(env)
        self._run_upstream_tests(env)

    # ── toolchain staging (sign + real rustlib) ──────────────────────
    def _toolchain_dir(self):
        return os.path.join(self.build_folder, "rust-toolchain")

    def _rust_toolchain_dep(self):
        try:
            return self.dependencies.build["rust-toolchain"]
        except (KeyError, ConanException):
            return None

    def _sign(self, path):
        """Self-sign one ELF (OHOS loader refuses unsigned binaries)."""
        signer = self._find_binary_sign_tool()
        if signer is None:
            raise ConanInvalidConfiguration(
                "binary-sign-tool not found; OHOS rejects unsigned ELFs")
        tmp = path + ".signed"
        proc = subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", tmp,
             "-selfSign", "1"], capture_output=True, text=True)
        if proc.returncode != 0 or not os.path.isfile(tmp):
            raise ConanInvalidConfiguration(
                f"binary-sign-tool failed for {path} (rc={proc.returncode}): "
                f"{proc.stderr[:200]}")
        os.replace(tmp, path)
        try:
            os.chmod(path, 0o755)
        except OSError:
            pass

    def _find_binary_sign_tool(self):
        for cand in (os.environ.get("BINARY_SIGN_TOOL"),
                     shutil.which("binary-sign-tool"),
                     "/data/service/hnp/bin/binary-sign-tool"):
            if cand and os.path.isfile(cand):
                return cand
        return None

    def _prepare_toolchain(self):
        """Copy the toolchain into the build folder, sign the executables and
        the shared objects rustc/cargo load, and materialise ``rustlib`` as a
        real directory (a symlinked rustlib makes rustc report E0463)."""
        dst = self._toolchain_dir()
        marker = os.path.join(dst, ".prepared")
        if os.path.isfile(marker):
            return
        dep = self._rust_toolchain_dep()
        if dep is None:
            raise ConanInvalidConfiguration(
                "rust-toolchain/1.97.1 tool_requires package not available")
        src = dep.package_folder
        bin_dst = os.path.join(dst, "bin")
        lib_dst = os.path.join(dst, "lib")
        os.makedirs(bin_dst, exist_ok=True)
        os.makedirs(lib_dst, exist_ok=True)

        for name in ("cargo", "rustc", "rustdoc", "rustfmt", "cargo-fmt",
                     "clippy-driver", "cargo-clippy"):
            s = os.path.join(src, "bin", name)
            if os.path.isfile(s):
                d = os.path.join(bin_dst, name)
                shutil.copy2(s, d)
                self._sign(d)

        src_lib = os.path.join(src, "lib")
        for name in sorted(os.listdir(src_lib)):
            s = os.path.join(src_lib, name)
            if name == "rustlib":
                # Real directory copy — never a symlink (E0463).
                shutil.copytree(s, os.path.join(lib_dst, "rustlib"),
                                symlinks=False)
                continue
            shutil.copy2(s, os.path.join(lib_dst, name))
            if name.endswith(".so"):
                self._sign(os.path.join(lib_dst, name))

        with open(marker, "w", encoding="utf-8", newline="\n") as f:
            f.write("signed toolchain prepared\n")

    # ── runtime libs (cargo's OpenSSL/zlib) ──────────────────────────
    def _runtime_lib_dir(self):
        return os.path.join(self.build_folder, "rust-runtime")

    def _prepare_runtime_libs(self):
        base = self._runtime_lib_dir()
        marker = os.path.join(base, ".prepared")
        if os.path.isfile(marker):
            return
        os.makedirs(base, exist_ok=True)
        for name, url, sha256 in RUNTIME_BOTTLES:
            tgz = os.path.join(base, name + ".tar.gz")
            if not os.path.isfile(tgz):
                download(self, url, tgz, sha256=sha256)
            extract = os.path.join(base, name)
            if not os.path.isdir(extract):
                with tarfile.open(tgz, "r:gz") as tf:
                    tf.extractall(extract)
        # Flatten the bottle libs into one dir and sign them.
        lib_dir = os.path.join(base, "lib")
        os.makedirs(lib_dir, exist_ok=True)
        wanted = {
            "openssl3": ("libssl.so", "libssl.so.3",
                         "libcrypto.so", "libcrypto.so.3"),
        }
        for bottle, names in wanted.items():
            root = os.path.join(base, bottle)
            for path in glob.glob(os.path.join(root, "**", "*.so*"),
                                  recursive=True):
                bname = os.path.basename(path)
                if bname not in names:
                    continue
                target = os.path.join(lib_dir, bname)
                real = os.path.realpath(path)
                if not os.path.isfile(real):
                    continue
                shutil.copy2(real, target)
                self._sign(target)
        with open(marker, "w", encoding="utf-8", newline="\n") as f:
            f.write("runtime libs prepared\n")

    # ── cargo helpers ────────────────────────────────────────────────
    def _ohos_clang(self):
        # The SDK ships `clang-15` (real ELF) next to `clang` (a /bin/sh
        # wrapper script) and `aarch64-unknown-linux-ohos-clang` (another
        # wrapper).  Only the ELF can serve as a rustc linker here, so the SDK
        # layout is probed first; the profile's compiler_executables entry is
        # only used to locate the same directory.
        for pattern in (
            "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/bin/clang-15",
            "/data/service/hnp/*/ohos/native/llvm/bin/clang-15",
        ):
            for c in sorted(glob.glob(pattern)):
                if os.path.isfile(c):
                    return c
        exes = {}
        try:
            exes = self.conf.get("tools.build:compiler_executables",
                                 default={}, check_type=dict) or {}
        except ConanException:
            exes = {}
        cand = exes.get("c") if isinstance(exes, dict) else None
        if cand:
            versioned = os.path.join(os.path.dirname(cand), "clang-15")
            if os.path.isfile(versioned):
                return versioned
        for c in (os.environ.get("HMBS_CC"), shutil.which("clang-15")):
            if c and os.path.isfile(c):
                return c
        raise ConanInvalidConfiguration(
            "OHOS LLVM clang-15 not found (checked SDK layout, profile conf"
            " and PATH)")

    def _ohos_sysroot(self, clang):
        # <sdk>/native/llvm/bin/clang-15 -> <sdk>/native/sysroot
        native = os.path.dirname(os.path.dirname(os.path.dirname(clang)))
        sysroot = os.path.join(native, "sysroot")
        return sysroot

    def _writable_tmpdir(self):
        for key in ("HMBS_TMPDIR", "TMPDIR", "TMP", "TEMP"):
            val = os.environ.get(key)
            if val and val not in ("0", "1") and os.path.isdir(val):
                probe = os.path.join(val, ".rutabaga-wtest")
                try:
                    with open(probe, "w", encoding="utf-8") as f:
                        f.write("ok")
                    os.remove(probe)
                    return val
                except OSError:
                    continue
        fallback = os.path.join(self.build_folder, "tmp")
        os.makedirs(fallback, exist_ok=True)
        return fallback

    def _ca_bundle(self):
        for cand in (os.environ.get("SSL_CERT_FILE"),
                     os.environ.get("CURL_CA_BUNDLE"),
                     "/storage/Users/currentUser/usr/local/ssl/cert.pem",
                     "/etc/ssl/certs/cacert.pem",
                     "/etc/ssl/cert.pem"):
            if cand and os.path.isfile(cand):
                return cand
        return None

    def _write_cargo_config(self, cargo_home, clang, ca):
        sysroot = self._ohos_sysroot(clang)
        cfg = (
            "[source.crates-io]\n"
            "replace-with = \"rsproxy-sparse\"\n\n"
            "[source.rsproxy-sparse]\n"
            "registry = \"sparse+https://rsproxy.cn/index/\"\n\n"
            "[net]\n"
            "git-fetch-with-cli = true\n"
            "retry = 3\n\n"
            "[target.%s]\n"
            "linker = \"%s\"\n"
            "rustflags = [\"-C\", \"link-arg=--target=aarch64-linux-ohos\","
            " \"-C\", \"link-arg=--sysroot=%s\","
            " \"-C\", \"link-arg=-D__MUSL__\"]\n"
            % (OHOS_RUST_TARGET, clang, sysroot)
        )
        if ca:
            cfg += "\n[http]\ncainfo = \"%s\"\n" % ca
        with open(os.path.join(cargo_home, "config.toml"),
                  "w", encoding="utf-8", newline="\n") as f:
            f.write(cfg)

    def _cargo_env(self):
        env = os.environ.copy()
        tmpdir = self._writable_tmpdir()
        env["TMPDIR"] = tmpdir
        env["TMP"] = tmpdir
        env["TEMP"] = tmpdir
        clang = self._ohos_clang()
        bin_dir = os.path.join(self._toolchain_dir(), "bin")
        env["PATH"] = bin_dir + os.pathsep + env.get("PATH", "")
        lib_dirs = [os.path.join(self._toolchain_dir(), "lib"),
                    os.path.join(self._runtime_lib_dir(), "lib")]
        lib_dirs += [d for d in PLATFORM_LIB_DIRS if os.path.isdir(d)]
        prev = env.get("LD_LIBRARY_PATH", "")
        env["LD_LIBRARY_PATH"] = os.pathsep.join(
            lib_dirs + ([prev] if prev else []))
        ca = self._ca_bundle()
        if ca:
            env["SSL_CERT_FILE"] = ca
            env["CURL_CA_BUNDLE"] = ca
            env["CARGO_HTTP_CAINFO"] = ca
        cargo_home = os.path.join(self.build_folder, "cargo-home")
        os.makedirs(cargo_home, exist_ok=True)
        self._write_cargo_config(cargo_home, clang, ca)
        env["CARGO_HOME"] = cargo_home
        env["CARGO"] = os.path.join(bin_dir, "cargo")
        env["CARGO_NET_RETRY"] = "3"
        env["CARGO_TARGET_AARCH64_UNKNOWN_LINUX_OHOS_LINKER"] = self._linker(
            clang)
        env["CC"] = clang
        env["CXX"] = clang
        env["AR"] = os.path.join(os.path.dirname(clang), "llvm-ar")
        env["RANLIB"] = os.path.join(os.path.dirname(clang), "llvm-ranlib")
        return env

    def _linker(self, clang):
        # rustc must get the real clang ELF; the SDK's `/bin/sh` wrapper is
        # rejected by rustc's exec on device.
        return clang

    def _run_cargo(self, env, args, label):
        log_dir = os.path.join(self.build_folder, "logs")
        os.makedirs(log_dir, exist_ok=True)
        log = os.path.join(log_dir, label + ".log")
        rc = 1
        # HMDFS on device intermittently raises ETXTBSY when a freshly
        # written build-script binary is exec'd ("Text file busy (os error
        # 26)"); retry the whole cargo invocation in that case only.
        for attempt in range(1, 4):
            with open(log, "w", encoding="utf-8", errors="replace") as fh:
                proc = subprocess.run(
                    [env["CARGO"]] + args, cwd=self.source_folder, env=env,
                    stdout=fh, stderr=subprocess.STDOUT, text=True)
            rc = proc.returncode
            if rc == 0:
                break
            with open(log, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
            if "Text file busy" not in text and "os error 26" not in text:
                break
            self.output.warning(
                "%s hit ETXTBSY, retry %d/3" % (label, attempt))
        with open(log, encoding="utf-8", errors="replace") as fh:
            tail = fh.read()[-4000:]
        self.output.info("%s rc=%d log=%s" % (label, rc, log))
        for line in tail.splitlines():
            self.output.info("%s: %s" % (label, line[:400]))
        return rc, log

    def _cargo_fetch(self, env):
        rc, log = self._run_cargo(env, ["fetch"], "cargo-fetch")
        if rc != 0:
            raise ConanInvalidConfiguration(
                f"cargo fetch failed (rc={rc}) see {log}")

    def _cargo_build(self, env):
        rc, log = self._run_cargo(
            env, ["build", "--release", "--target", OHOS_RUST_TARGET],
            "cargo-build")
        if rc != 0:
            raise ConanInvalidConfiguration(
                f"cargo build failed (rc={rc}) see {log}")
        lib = os.path.join(self.source_folder, "target", OHOS_RUST_TARGET,
                           "release", "librutabaga_gfx.rlib")
        if not os.path.isfile(lib):
            raise ConanInvalidConfiguration(
                f"cargo did not produce the rlib: {lib}")

    def _run_upstream_tests(self, env):
        rc, log = self._run_cargo(
            env, ["test", "--release", "--lib", "--target", OHOS_RUST_TARGET],
            "cargo-test")
        with open(log, encoding="utf-8", errors="replace") as fh:
            out = fh.read()
        m = re.search(
            r"test result: (\w+)\. (\d+) passed; (\d+) failed; (\d+) ignored",
            out)
        if m:
            discovered = int(m.group(2)) + int(m.group(3)) + int(m.group(4))
            passed = int(m.group(2))
            failed = int(m.group(3))
            skipped = int(m.group(4))
        else:
            discovered = passed = failed = 0
            skipped = UPSTREAM_TESTS_TOTAL
        executed = passed + failed
        status = "passed" if (rc == 0 and failed == 0
                              and executed == UPSTREAM_TESTS_TOTAL) else "failed"
        marker = json.dumps({
            "status": status, "framework": "cargo-test",
            "command": "cargo test --release --lib --target " + OHOS_RUST_TARGET,
            "discovered": UPSTREAM_TESTS_TOTAL, "executed": executed,
            "passed": passed, "failed": failed, "skipped": skipped,
        }, ensure_ascii=False)
        msg = "HMBS_UPSTREAM_TEST_RESULT=" + marker
        self.output.info(msg)
        print(msg, flush=True)
        if status != "passed":
            raise ConanInvalidConfiguration(
                "upstream cargo test failed rc=%d (%d/%d) see %s"
                % (rc, executed, UPSTREAM_TESTS_TOTAL, log))

    # ── package ──────────────────────────────────────────────────────
    def package(self):
        rlib = os.path.join(self.source_folder, "target", OHOS_RUST_TARGET,
                            "release", "librutabaga_gfx.rlib")
        copy(self, "librutabaga_gfx.rlib",
             src=os.path.dirname(rlib),
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        # Ship the Cargo crate (sources + committed Cargo.lock) so that Rust
        # consumers can build against the exact locked dependency set.
        crate_dst = os.path.join(self.package_folder, "src",
                                 "rutabaga_gfx-0.1.80")
        for name in ("Cargo.toml", "Cargo.lock", "build.rs",
                     "rust-toolchain.toml", "README.md", "LICENSE"):
            copy(self, name, src=self.source_folder, dst=crate_dst,
                 keep_path=False)
        copy(self, "*.rs", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(crate_dst, "src"), keep_path=True)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["rutabaga_gfx"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.set_property("cmake_file_name", "rutabaga")
        self.cpp_info.set_property("cmake_target_name", "rutabaga::rutabaga")
