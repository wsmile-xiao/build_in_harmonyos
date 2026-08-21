#!/usr/bin/env python3
"""Consumer test for cargo-bloat, including a dependency-free Cargo fixture."""

import hashlib
import os
import shlex
import shutil
import ssl
import tarfile
import urllib.error
import urllib.request

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run


RUST_TOOLCHAIN_BOTTLES = (
    ("rust", "https://harmonybrew.atomgit.com/bottles/rust-1.97.1.arm64_ohos.bottle.tar.gz", "21b135fd7f403d08752a0fcc2bac70ee9a79909ad0e05e7c3ebbdd9afa66525e"),
    ("openssl3", "https://harmonybrew.atomgit.com/bottles/openssl%403-3.6.3.arm64_ohos.bottle.tar.gz", "f773ba9053a6ac7ecf6b5d56e78d24d8386d60327f1f184d11132e965254d285"),
    ("zlib", "https://harmonybrew.atomgit.com/bottles/zlib-ng-compat-2.3.3_1.arm64_ohos.bottle.tar.gz", "1c17a31f8104701bce6b471af8dbbd14bb67d16a504eec087018feb05493a430"),
    ("ca-certificates", "https://harmonybrew.atomgit.com/bottles/ca-certificates-2026-08-13.arm64_ohos.bottle.tar.gz", "2916654bf828a59e1fd9862299300b48c1e5e7cb09fef279d4f78aaf066cd006"),
)


class CargoBloatTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    @staticmethod
    def _sha256(path):
        digest = hashlib.sha256()
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _set_ca_bundle():
        if os.environ.get("SSL_CERT_FILE"):
            return
        for candidate in ("/storage/Users/currentUser/usr/local/ssl/cert.pem", "/etc/ssl/certs/cacert.pem", "/etc/ssl/cert.pem", os.path.expanduser("~/.harmonybrew/etc/ca-certificates/cert.pem")):
            if os.path.isfile(candidate):
                os.environ["SSL_CERT_FILE"] = candidate
                os.environ["CURL_CA_BUNDLE"] = candidate
                return

    def _download(self, url, destination, expected):
        self._set_ca_bundle()
        try:
            urllib.request.urlretrieve(url, destination)
        except (urllib.error.URLError, ssl.SSLError) as exc:
            if "CERTIFICATE_VERIFY_FAILED" not in str(exc):
                raise
            with urllib.request.urlopen(url, context=ssl._create_unverified_context()) as response:
                with open(destination, "wb") as handle:
                    shutil.copyfileobj(response, handle)
        actual = self._sha256(destination)
        if actual != expected:
            raise ConanInvalidConfiguration(f"Rust toolchain bottle checksum mismatch: expected {expected}, got {actual}")

    @staticmethod
    def _extract(archive, destination):
        root = os.path.realpath(destination)
        with tarfile.open(archive, "r:gz") as handle:
            for member in handle.getmembers():
                target = os.path.realpath(os.path.join(destination, member.name))
                if target != root and not target.startswith(root + os.sep):
                    raise ConanInvalidConfiguration(f"unsafe path in Rust toolchain bottle: {member.name}")
            handle.extractall(destination)

    @staticmethod
    def _repair_wrappers(bin_dir):
        for name in sorted(os.listdir(bin_dir)):
            if name.endswith(".real"):
                continue
            wrapper = os.path.join(bin_dir, name)
            real = os.path.join(bin_dir, name + ".real")
            if os.path.islink(wrapper) or not os.path.isfile(wrapper) or not os.path.isfile(real):
                continue
            with open(wrapper, "rb") as handle:
                if not handle.read(512).startswith(b"#!"):
                    continue
            with open(wrapper, "w", encoding="utf-8") as handle:
                handle.write("#!/bin/sh\nexec %s \"$@\"\n" % shlex.quote(real))

    def _locate(self, base):
        cargo = rustc = None
        for root, _dirs, files in os.walk(base):
            if cargo is None and "cargo.real" in files:
                cargo = os.path.join(root, "cargo.real")
            if rustc is None:
                if "rustc.real" in files:
                    rustc = os.path.join(root, "rustc.real")
                elif "rustc" in files:
                    rustc = os.path.join(root, "rustc")
        return cargo, rustc

    def _bootstrap_rust(self):
        if str(self.settings.os) != "OHOS":
            return None, None
        base = os.path.join(self.build_folder, "rust-toolchain")
        os.makedirs(base, exist_ok=True)
        cargo, rustc = self._locate(base)
        if not cargo or not rustc:
            for name, url, sha256 in RUST_TOOLCHAIN_BOTTLES:
                archive = os.path.join(base, name + ".tar.gz")
                if not os.path.isfile(archive) or self._sha256(archive) != sha256:
                    self._download(url, archive, sha256)
                self._extract(archive, base)
            cargo, rustc = self._locate(base)
        if not cargo or not rustc:
            raise ConanInvalidConfiguration("Harmonybrew Rust bottle did not contain cargo/rustc")
        self._repair_wrappers(os.path.dirname(cargo))
        lib_dirs = []
        for root, _dirs, files in os.walk(base):
            if os.path.basename(root) == "lib" and {"libssl.so", "libcrypto.so", "libz.so"} & set(files):
                lib_dirs.append(root)
        if lib_dirs:
            previous = os.environ.get("LD_LIBRARY_PATH")
            os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(lib_dirs + ([previous] if previous else []))
        self._set_ca_bundle()
        return cargo, rustc

    def _toolchain(self):
        cargo = shutil.which("cargo")
        rustc = shutil.which("rustc")
        if (not cargo or not rustc) and str(self.settings.os) == "OHOS":
            cargo, rustc = self._bootstrap_rust()
        if not cargo or not rustc:
            raise ConanInvalidConfiguration("cargo/rustc are required for the fixture test")
        return cargo, rustc

    def _rust_target(self):
        override = os.environ.get("RUST_TARGET")
        if override:
            return override
        if str(self.settings.os) != "OHOS":
            return None
        return {"armv8": "aarch64-unknown-linux-ohos", "armv8.3": "aarch64-unknown-linux-ohos", "x86_64": "x86_64-unknown-linux-ohos"}.get(str(self.settings.arch))

    def test(self):
        if not can_run(self):
            self.output.info("cross-build: runtime test deferred to OHOS/shadow CI")
            return
        dependency = self.dependencies[self.tested_reference_str]
        binary = os.path.join(dependency.package_folder, "bin", "cargo-bloat")
        manifest = os.path.join(self.source_folder, "sample", "Cargo.toml")
        script = os.path.join(self.source_folder, "test_cargo_bloat.py")
        cargo, rustc = self._toolchain()
        target = self._rust_target()
        clang = shutil.which("clang") or "/data/service/hnp/bin/clang"
        env = dict(os.environ)
        env.update({"CARGO": cargo, "RUSTC": rustc, "CARGO_BUILD_JOBS": "1", "CARGO_NET_RETRY": "10", "CARGO_HTTP_TIMEOUT": "600", "RUSTFLAGS": f"-C linker={clang}"})
        if target:
            env["CARGO_BUILD_TARGET"] = target
        tmpdir = env.get("HMBS_TMPDIR") or env.get("TMPDIR") or os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env.update({"TMPDIR": tmpdir, "TMP": tmpdir, "TEMP": tmpdir})
        env["PATH"] = os.pathsep.join([os.path.dirname(binary), os.path.dirname(cargo), os.path.dirname(rustc), env.get("PATH", "")])
        saved = dict(os.environ)
        os.environ.clear()
        os.environ.update(env)
        try:
            # Do not pass env="conanrun": it would replace the fallback Cargo PATH.
            self.run(f'python3 "{script}" "{binary}" "{manifest}"', cwd=self.source_folder)
        finally:
            os.environ.clear()
            os.environ.update(saved)
