#!/usr/bin/env python3
"""Conan recipe for bottom 0.12.3.

Rust/Cargo are build tools rather than Conan requirements.  OHOS workers that
do not provision them use the checksum-pinned Harmonybrew fallback in
``conandata.yml``; the download stays inside the isolated Conan build folder.
"""

import hashlib
import os
import shlex
import shutil
import ssl
import tarfile
import urllib.error
import urllib.request

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class BottomConan(ConanFile):
    name = "bottom"
    version = "0.12.3"
    description = "A customizable cross-platform graphical process/system monitor for the terminal"
    license = "MIT"
    homepage = "https://github.com/ClementTsang/bottom"
    url = ""
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"bottom is only supported on Linux/OHOS, got {self.settings.os}"
            )

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _rust_target(self):
        override = os.environ.get("RUST_TARGET")
        if override:
            return override
        if str(self.settings.os) != "OHOS":
            return None
        targets = {
            "armv8": "aarch64-unknown-linux-ohos",
            "armv8.3": "aarch64-unknown-linux-ohos",
            "x86_64": "x86_64-unknown-linux-ohos",
        }
        try:
            return targets[str(self.settings.arch)]
        except KeyError:
            raise ConanInvalidConfiguration(
                f"No Rust target mapping for OHOS architecture {self.settings.arch}"
            )

    @staticmethod
    def _find_tool(name):
        candidates = [
            shutil.which(name), os.environ.get(name.upper()),
            os.environ.get(f"HNP_{name.upper()}"),
            f"/data/service/hnp/bin/{name}",
            f"/storage/Users/currentUser/usr/local/bin/{name}",
            os.path.expanduser(f"~/.harmonybrew/bin/{name}"),
            os.path.expanduser(f"~/.cargo/bin/{name}"),
        ]
        for candidate in candidates:
            if not candidate:
                continue
            real = candidate + ".real"
            if not candidate.endswith(".real") and os.path.isfile(real):
                candidate = real
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        return None

    @staticmethod
    def _set_ca_bundle(*roots):
        candidates = [
            os.environ.get("SSL_CERT_FILE"),
            "/storage/Users/currentUser/usr/local/ssl/cert.pem",
            "/etc/ssl/certs/cacert.pem", "/etc/ssl/cert.pem",
            os.path.expanduser("~/.harmonybrew/etc/ca-certificates/cert.pem"),
        ]
        for root in roots:
            if not root or not os.path.isdir(root):
                continue
            for directory, _dirs, files in os.walk(root):
                for name in ("cert.pem", "cacert.pem"):
                    if name in files:
                        candidates.append(os.path.join(directory, name))
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                os.environ["SSL_CERT_FILE"] = candidate
                os.environ["CURL_CA_BUNDLE"] = candidate
                return candidate
        return None

    @staticmethod
    def _sha256(path):
        digest = hashlib.sha256()
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _download_bottle(self, url, destination, expected_sha256):
        self._set_ca_bundle()
        try:
            urllib.request.urlretrieve(url, destination)
        except (urllib.error.URLError, ssl.SSLError) as exc:
            if "CERTIFICATE_VERIFY_FAILED" not in str(exc):
                raise
            self.output.warning("no usable CA bundle; retrying fixed Harmonybrew mirror without TLS verification")
            context = ssl._create_unverified_context()
            with urllib.request.urlopen(url, context=context) as response:
                with open(destination, "wb") as handle:
                    shutil.copyfileobj(response, handle)
        actual = self._sha256(destination)
        if actual != expected_sha256:
            raise ConanInvalidConfiguration(
                f"Rust toolchain bottle checksum mismatch for {url}: expected {expected_sha256}, got {actual}"
            )

    @staticmethod
    def _extract_tarball(archive, destination):
        root = os.path.realpath(destination)
        with tarfile.open(archive, "r:gz") as handle:
            for member in handle.getmembers():
                target = os.path.realpath(os.path.join(destination, member.name))
                if target != root and not target.startswith(root + os.sep):
                    raise ConanInvalidConfiguration(f"unsafe path in Rust toolchain bottle: {member.name}")
            handle.extractall(destination)

    def _ensure_ca_bundle(self):
        ca_bundle = self._set_ca_bundle()
        if ca_bundle or str(self.settings.os) != "OHOS":
            return ca_bundle
        ca_bottle = next(
            (item for item in self.conan_data.get("rust_toolchain", [])
             if item["name"] == "ca-certificates"),
            None,
        )
        if ca_bottle is None:
            raise ConanInvalidConfiguration("OHOS Cargo requires a CA certificate bundle")
        base = os.path.join(self.build_folder, "ca-certificates")
        os.makedirs(base, exist_ok=True)
        archive = os.path.join(base, "ca-certificates.tar.gz")
        if not os.path.isfile(archive) or self._sha256(archive) != ca_bottle["sha256"]:
            self._download_bottle(ca_bottle["url"], archive, ca_bottle["sha256"])
        self._extract_tarball(archive, base)
        ca_bundle = self._set_ca_bundle(base)
        if not ca_bundle:
            raise ConanInvalidConfiguration(
                "Harmonybrew CA certificate bottle did not contain cert.pem or cacert.pem"
            )
        return ca_bundle

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

    def _bootstrap_rust_toolchain(self):
        if str(self.settings.os) != "OHOS":
            return None, None
        base = os.path.join(self.build_folder, "rust-toolchain")
        os.makedirs(base, exist_ok=True)
        for bottle in self.conan_data.get("rust_toolchain", []):
            archive = os.path.join(base, bottle["name"] + ".tar.gz")
            if not os.path.isfile(archive) or self._sha256(archive) != bottle["sha256"]:
                self._download_bottle(bottle["url"], archive, bottle["sha256"])
            self._extract_tarball(archive, base)

        cargo = rustc = None
        for root, _dirs, files in os.walk(base):
            if cargo is None and "cargo.real" in files:
                cargo = os.path.join(root, "cargo.real")
            if rustc is None:
                if "rustc.real" in files:
                    rustc = os.path.join(root, "rustc.real")
                elif "rustc" in files:
                    rustc = os.path.join(root, "rustc")
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
        self._set_ca_bundle(base)
        return cargo, rustc

    def _toolchain(self):
        cargo = self._find_tool("cargo")
        rustc = self._find_tool("rustc")
        if (not cargo or not rustc) and str(self.settings.os) == "OHOS":
            cargo, rustc = self._bootstrap_rust_toolchain()
        if not cargo or not rustc:
            raise ConanInvalidConfiguration("Rust/Cargo toolchain is required; provision cargo/rustc or use the OHOS Harmonybrew fallback")
        return cargo, rustc

    def _build_env(self, cargo, rustc):
        ca_bundle = self._ensure_ca_bundle()
        compiler_executables = self.conf.get("tools.build:compiler_executables", default={}) or {}
        cc = compiler_executables.get("c") or shutil.which("clang") or "/data/service/hnp/bin/clang"
        cxx = compiler_executables.get("cpp") or shutil.which("clang++") or "/data/service/hnp/bin/clang++"
        tmpdir = os.environ.get("HMBS_TMPDIR") or os.environ.get("TMPDIR") or os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        cargo_dir = os.path.join(self.source_folder, ".cargo")
        os.makedirs(cargo_dir, exist_ok=True)
        target = self._rust_target()
        config = ('[source.crates-io]\nreplace-with = "rsproxy-sparse"\n'
                  '[source.rsproxy-sparse]\nregistry = "sparse+https://rsproxy.cn/index/"\n'
                  '[net]\nretry = 10\n[http]\ntimeout = 600\nlow-speed-limit = 1\n')
        if ca_bundle:
            config += f'cainfo = "{ca_bundle}"\n'
        if target and str(self.settings.os) == "OHOS":
            config += f"\n[target.{target}]\nlinker = \"{cc}\"\n"
        with open(os.path.join(cargo_dir, "config.toml"), "w", encoding="utf-8") as handle:
            handle.write(config)
        env = dict(os.environ)
        env.update({"CARGO": cargo, "RUSTC": rustc, "CC": cc, "CXX": cxx,
                    "RUSTFLAGS": f"-C linker={cc}", "CARGO_NET_RETRY": "10",
                    "CARGO_HTTP_TIMEOUT": "600", "CARGO_BUILD_JOBS": "1",
                    "TMPDIR": tmpdir, "TMP": tmpdir, "TEMP": tmpdir})
        if ca_bundle:
            env.update({"CARGO_HTTP_CAINFO": ca_bundle,
                        "SSL_CERT_FILE": ca_bundle, "CURL_CA_BUNDLE": ca_bundle})
        env["PATH"] = os.pathsep.join([os.path.dirname(cargo), os.path.dirname(rustc), env.get("PATH", "")])
        return env

    def build(self):
        cargo, rustc = self._toolchain()
        env = self._build_env(cargo, rustc)
        command = [cargo, "build", "--release", "--locked"]
        target = self._rust_target()
        if target:
            command.extend(["--target", target])
        saved = dict(os.environ)
        os.environ.clear()
        os.environ.update(env)
        try:
            self.run(" ".join(shlex.quote(part) for part in command), cwd=self.source_folder)
        finally:
            os.environ.clear()
            os.environ.update(saved)

    def _binary_path(self):
        target = self._rust_target()
        if target:
            return os.path.join(self.source_folder, "target", target, "release", "btm")
        return os.path.join(self.source_folder, "target", "release", "btm")

    def package(self):
        binary = self._binary_path()
        if not os.path.isfile(binary):
            raise ConanException(f"bottom build output not found: {binary}")
        copy(self, "btm", src=os.path.dirname(binary), dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
