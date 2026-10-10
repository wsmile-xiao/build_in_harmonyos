#!/usr/bin/env python3
"""Conan test_package for rutabaga 0.1.80.

Consumes the packaged `rutabaga` (crates.io `rutabaga_gfx`) OHOS package:
the recipe ships the built `librutabaga_gfx.rlib` *and* the Cargo crate
(sources + the committed `Cargo.lock`).  This test copies the packaged crate
into the build folder, injects the consumer example `examples/consumer.rs`
(compiled and run here), and lets Cargo use the crate's own lock file so the
dependency set is exactly the one the library was built with.

The example links the real public API (`DrmFormat`, `RutabagaBuilder`,
`Rutabaga::snapshot`/`restore`) and contains the HarmonyOS-specific assertions
(aarch64-unknown-linux-ohos target + writable-TMPDIR snapshot round trip).
"""

import glob
import json
import os
import shutil
import subprocess
import tarfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.files import copy, download

OHOS_RUST_TARGET = "aarch64-unknown-linux-ohos"

RUNTIME_BOTTLES = (
    ("openssl3",
     "https://harmonybrew.atomgit.com/bottles/"
     "openssl%403-3.6.4.arm64_ohos.bottle.tar.gz",
     "e1be73c6c68e29c33ff43761045e43e23e7c369f0fb1a24f40e226ec5cb28f98"),
)

# Platform lib dirs (cargo needs libz.so; the harmonybrew zlib bottle URL is 404).
PLATFORM_LIB_DIRS = ("/system/lib64/platformsdk", "/system/lib64")


class RutabagaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        # Keep every generated artefact under test_package/build/ so the
        # recipe directory itself stays clean (CI junk checks).
        self.folders.build = "build"
        self.folders.generators = "build"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build_requirements(self):
        self.tool_requires("rust-toolchain/1.97.1")

    # ── environment ─────────────────────────────────────────────────
    def _sign(self, path):
        signer = None
        for cand in (os.environ.get("BINARY_SIGN_TOOL"),
                     shutil.which("binary-sign-tool"),
                     "/data/service/hnp/bin/binary-sign-tool"):
            if cand and os.path.isfile(cand):
                signer = cand
                break
        if signer is None:
            raise ConanInvalidConfiguration("binary-sign-tool not found")
        tmp = path + ".signed"
        rc = subprocess.run([signer, "sign", "-inFile", path, "-outFile", tmp,
                             "-selfSign", "1"], capture_output=True).returncode
        if rc != 0 or not os.path.isfile(tmp):
            raise ConanInvalidConfiguration("cannot self-sign %s" % path)
        os.replace(tmp, path)
        try:
            os.chmod(path, 0o755)
        except OSError:
            pass

    def _prepare_toolchain(self):
        dst = os.path.join(self.build_folder, "rust-toolchain")
        marker = os.path.join(dst, ".prepared")
        if os.path.isfile(marker):
            return os.path.join(dst, "bin")
        dep = self.dependencies.build["rust-toolchain"]
        src = dep.package_folder
        bin_dst = os.path.join(dst, "bin")
        lib_dst = os.path.join(dst, "lib")
        os.makedirs(bin_dst, exist_ok=True)
        os.makedirs(lib_dst, exist_ok=True)
        for name in ("cargo", "rustc", "rustfmt", "rustdoc"):
            s = os.path.join(src, "bin", name)
            if os.path.isfile(s):
                d = os.path.join(bin_dst, name)
                shutil.copy2(s, d)
                self._sign(d)
        for name in sorted(os.listdir(os.path.join(src, "lib"))):
            s = os.path.join(src, "lib", name)
            if name == "rustlib":
                shutil.copytree(s, os.path.join(lib_dst, "rustlib"),
                                symlinks=False)
                continue
            shutil.copy2(s, os.path.join(lib_dst, name))
            if name.endswith(".so"):
                self._sign(os.path.join(lib_dst, name))
        with open(marker, "w", encoding="utf-8", newline="\n") as f:
            f.write("ok\n")
        return bin_dst

    def _prepare_runtime_libs(self):
        base = os.path.join(self.build_folder, "rust-runtime")
        marker = os.path.join(base, ".prepared")
        if os.path.isfile(marker):
            return os.path.join(base, "lib")
        os.makedirs(base, exist_ok=True)
        lib_dir = os.path.join(base, "lib")
        os.makedirs(lib_dir, exist_ok=True)
        wanted = ("libssl.so", "libssl.so.3", "libcrypto.so", "libcrypto.so.3")
        for name, url, sha256 in RUNTIME_BOTTLES:
            tgz = os.path.join(base, name + ".tar.gz")
            if not os.path.isfile(tgz):
                download(self, url, tgz, sha256=sha256)
            extract = os.path.join(base, name)
            if not os.path.isdir(extract):
                with tarfile.open(tgz, "r:gz") as tf:
                    tf.extractall(extract)
        for path in glob.glob(os.path.join(base, "*", "**", "*.so*"),
                              recursive=True):
            bname = os.path.basename(path)
            if bname not in wanted:
                continue
            target = os.path.join(lib_dir, bname)
            real = os.path.realpath(path)
            if os.path.isfile(real) and not os.path.isfile(target):
                shutil.copy2(real, target)
                self._sign(target)
        with open(marker, "w", encoding="utf-8", newline="\n") as f:
            f.write("ok\n")
        return lib_dir

    def _clang(self):
        # Prefer the SDK's real `clang-15` ELF (the `clang` /
        # `aarch64-unknown-linux-ohos-clang` entries are /bin/sh wrappers and
        # cannot be used as a rustc linker).
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
        c = shutil.which("clang-15")
        if c:
            return c
        raise ConanInvalidConfiguration("OHOS clang-15 not found")

    def _ca_bundle(self):
        """Same candidate list as the main recipe: the CI worker has no
        /storage/Users/currentUser/usr/local/ssl/cert.pem but does ship
        /etc/ssl/certs/cacert.pem, which cargo/OpenSSL needs for the
        rsproxy.cn index (otherwise: "self-signed certificate in
        certificate chain (19)")."""
        for cand in (
            os.environ.get("SSL_CERT_FILE"),
            os.environ.get("CURL_CA_BUNDLE"),
            "/storage/Users/currentUser/usr/local/ssl/cert.pem",
            "/etc/ssl/certs/cacert.pem",
            "/etc/ssl/cert.pem",
        ):
            if cand and os.path.isfile(cand):
                return cand
        return None

    def _env(self):
        env = os.environ.copy()
        tmpdir = os.environ.get("TMPDIR") or os.environ.get("TMP")
        if not (tmpdir and os.path.isdir(tmpdir)):
            tmpdir = os.path.join(self.build_folder, "tmp")
            os.makedirs(tmpdir, exist_ok=True)
        env["TMPDIR"] = env["TMP"] = env["TEMP"] = tmpdir
        bin_dir = self._prepare_toolchain()
        lib_dir = self._prepare_runtime_libs()
        clang = self._clang()
        native = os.path.dirname(os.path.dirname(os.path.dirname(clang)))
        sysroot = os.path.join(native, "sysroot")
        env["PATH"] = bin_dir + os.pathsep + env.get("PATH", "")
        tclib = os.path.join(self.build_folder, "rust-toolchain", "lib")
        prev = env.get("LD_LIBRARY_PATH", "")
        env["LD_LIBRARY_PATH"] = os.pathsep.join(
            [tclib, lib_dir]
            + [d for d in PLATFORM_LIB_DIRS if os.path.isdir(d)]
            + ([prev] if prev else []))
        ca = self._ca_bundle()
        if ca:
            env["SSL_CERT_FILE"] = ca
            env["CURL_CA_BUNDLE"] = ca
            env["CARGO_HTTP_CAINFO"] = ca
        cargo_home = os.path.join(self.build_folder, "cargo-home")
        os.makedirs(cargo_home, exist_ok=True)
        cfg = (
            "[source.crates-io]\nreplace-with = \"rsproxy-sparse\"\n\n"
            "[source.rsproxy-sparse]\n"
            "registry = \"sparse+https://rsproxy.cn/index/\"\n\n"
            "[net]\ngit-fetch-with-cli = true\nretry = 3\n\n"
            "[target.%s]\nlinker = \"%s\"\n"
            "rustflags = [\"-C\", \"link-arg=--target=aarch64-linux-ohos\","
            " \"-C\", \"link-arg=--sysroot=%s\","
            " \"-C\", \"link-arg=-D__MUSL__\"]\n"
            % (OHOS_RUST_TARGET, clang, sysroot)
        )
        if ca:
            cfg += "\n[http]\ncainfo = \"%s\"\n" % ca
        with open(os.path.join(cargo_home, "config.toml"), "w",
                  encoding="utf-8", newline="\n") as f:
            f.write(cfg)
        env["CARGO_HOME"] = cargo_home
        env["CARGO"] = os.path.join(bin_dir, "cargo")
        env["CARGO_TARGET_AARCH64_UNKNOWN_LINUX_OHOS_LINKER"] = clang
        env["CC"] = env["CXX"] = clang
        env["AR"] = os.path.join(os.path.dirname(clang), "llvm-ar")
        env["RANLIB"] = os.path.join(os.path.dirname(clang), "llvm-ranlib")
        return env

    # ── build / test ────────────────────────────────────────────────
    def _run_cargo(self, env, work, log):
        """Run `cargo build` with a retry on the transient HMDFS
        ETXTBSY ("Text file busy (os error 26)") seen on device."""
        last = 1
        for attempt in range(1, 4):
            with open(log, "w", encoding="utf-8") as fh:
                rc = subprocess.run(
                    [env["CARGO"], "build", "--release", "--target",
                     OHOS_RUST_TARGET],
                    cwd=work, env=env, stdout=fh,
                    stderr=subprocess.STDOUT).returncode
            last = rc
            if rc == 0:
                return 0
            with open(log, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
            if "Text file busy" not in text and "os error 26" not in text:
                break
            self.output.warning("cargo build hit ETXTBSY, retry %d/3"
                                % attempt)
        return last

    def build(self):
        dep = self.dependencies["rutabaga"]
        rlib = os.path.join(dep.package_folder, "lib",
                            "librutabaga_gfx.rlib")
        if not os.path.isfile(rlib):
            raise ConanInvalidConfiguration(
                "packaged rlib missing: %s" % rlib)
        crate_src = os.path.join(dep.package_folder, "src",
                                 "rutabaga_gfx-0.1.80")
        if not os.path.isdir(crate_src):
            raise ConanInvalidConfiguration(
                "packaged crate source missing: %s" % crate_src)
        # A tiny cargo workspace: the packaged crate + a consumer crate.  The
        # crate's committed Cargo.lock is copied to the workspace root so the
        # dependency set stays exactly the one the library was built with.
        work = os.path.join(self.build_folder, "consumer-ws")
        if os.path.isdir(work):
            shutil.rmtree(work)
        crate_dir = os.path.join(work, "crate")
        consumer_dir = os.path.join(work, "consumer")
        os.makedirs(os.path.join(consumer_dir, "src"), exist_ok=True)
        shutil.copytree(crate_src, crate_dir)
        copy(self, "Cargo.lock", src=crate_src, dst=work, keep_path=False)
        copy(self, "consumer.rs", src=self.recipe_folder,
             dst=os.path.join(consumer_dir, "src"), keep_path=False)
        os.rename(os.path.join(consumer_dir, "src", "consumer.rs"),
                  os.path.join(consumer_dir, "src", "main.rs"))
        with open(os.path.join(work, "Cargo.toml"), "w",
                  encoding="utf-8", newline="\n") as f:
            f.write("[workspace]\nmembers = [\"crate\", \"consumer\"]\n"
                    "resolver = \"2\"\n")
        with open(os.path.join(consumer_dir, "Cargo.toml"), "w",
                  encoding="utf-8", newline="\n") as f:
            f.write("[package]\nname = \"rutabaga_consumer_test\"\n"
                    "version = \"0.0.0\"\nedition = \"2021\"\n"
                    "publish = false\n\n[dependencies]\n"
                    "rutabaga_gfx = { path = \"../crate\" }\n")
        env = self._env()
        log = os.path.join(self.build_folder, "consumer-build.log")
        rc = self._run_cargo(env, work, log)
        if rc != 0:
            with open(log, encoding="utf-8", errors="replace") as fh:
                for line in fh.read()[-3000:].splitlines():
                    self.output.info("consumer: %s" % line[:400])
            raise ConanInvalidConfiguration(
                "consumer crate build failed rc=%d see %s" % (rc, log))
        binary = os.path.join(
            work, "target", OHOS_RUST_TARGET, "release",
            "rutabaga_consumer_test")
        if not os.path.isfile(binary):
            raise ConanInvalidConfiguration("consumer binary missing: %s"
                                          % binary)
        self._sign(binary)
        self.output.info("consumer crate built + signed (log %s)" % log)

    def test(self):
        binary = os.path.join(
            self.build_folder, "consumer-ws", "target", OHOS_RUST_TARGET,
            "release", "rutabaga_consumer_test")
        if not os.path.isfile(binary):
            raise ConanInvalidConfiguration("consumer binary missing: %s"
                                          % binary)
        sh = os.environ.get("CONFIG_SHELL") or "/bin/sh"
        if not os.path.isfile(sh):
            sh = "/bin/sh"
        self.run("%s %s/test.sh %s" % (sh, self.recipe_folder, binary),
                 env="conanrun")
        marker = json.dumps({
            "executed": True, "passed": True,
            "command": "./rutabaga_consumer_test",
            "discovered": 4, "passedCount": 4,
        }, ensure_ascii=False)
        print("HMBS_TEST_PACKAGE_RESULT=" + marker, flush=True)
