#!/usr/bin/env python3
"""Conan recipe for herdr 0.8.2 — Rust/Cargo CLI tool with vendored libghostty-vt (Zig build).

Rust/Cargo are build tools rather than Conan requirements.  OHOS workers that
do not provision them use the checksum-pinned Harmonybrew fallback in
conandata.yml; the download stays inside the isolated Conan build folder.

The vendored libghostty-vt requires Zig 0.15.2 to build.  On OHOS the Zig
build runner and generated intermediate tools cannot execute without ELF
signing, so a pre‑build step signs every generated ELF before retrying.
"""

import hashlib
import os
import platform
import shlex
import shutil
import ssl
import subprocess
import tarfile
import urllib.error
import urllib.request

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class HerdrConan(ConanFile):
    name = "herdr"
    version = "0.8.2"
    description = "Terminal workspace manager for AI coding agents"
    license = "Apache-2.0"
    homepage = "https://herdr.dev"
    url = "https://github.com/herdrdev/herdr"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"herdr is only supported on Linux/OHOS, got {self.settings.os}"
            )

    def requirements(self):
        pass

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        """Download the source tarball with urllib (conan get() is unstable for
        large downloads on OHOS) and verify the sha256 before extracting."""
        import requests
        entry = self.conan_data["sources"]
        url = entry["url"]
        if isinstance(url, list):
            url = url[0]
        expected = entry["sha256"]
        dest = os.path.join(self.source_folder, ".source-download.tar.gz")
        os.makedirs(self.source_folder, exist_ok=True)
        # Prefer a pre-cached source tarball (conan in-process HTTP downloads are
        # unstable on some OHOS workers; the cache is populated out-of-process).
        cached = None
        cache_dir = os.environ.get("OHC_SOURCE_CACHE") or os.path.join(
            os.path.expanduser("~"), ".cache", "ohc-sources"
        )
        for name in (f"{self.name}-{self.version}.tar.gz", "source.tar.gz"):
            candidate = os.path.join(cache_dir, name)
            if os.path.isfile(candidate) and self._sha256(candidate) == expected:
                cached = candidate
                break
        if cached:
            shutil.copy2(cached, dest)
            self.output.info(f"using cached source tarball: {cached}")
        else:
            self._set_ca_bundle()
            last_error = None
            mirrors = [url] + (entry["url"][1:] if isinstance(entry["url"], list) else [])
            for mirror in mirrors:
                if mirror.startswith("file://"):
                    # CI pre-download rewrites conandata.yml URLs to file:// paths
                    shutil.copy2(mirror[len("file://"):], dest)
                    break
                try:
                    with requests.get(mirror, timeout=600, stream=True) as response:
                        response.raise_for_status()
                        with open(dest, "wb") as handle:
                            for chunk in response.iter_content(1 << 16):
                                handle.write(chunk)
                    break
                except (requests.RequestException, OSError) as exc:
                    last_error = exc
                    self.output.warning(f"download failed for {mirror}: {exc}; trying next mirror")
            else:
                raise ConanException(f"failed to download source: {last_error}")
        actual = self._sha256(dest)
        if actual != expected:
            raise ConanException(f"source sha256 mismatch: expected {expected}, got {actual}")
        tmp = os.path.join(self.source_folder, ".source-extract-tmp")
        if os.path.isdir(tmp):
            shutil.rmtree(tmp)
        os.makedirs(tmp, exist_ok=True)
        self._extract_tarball(dest, tmp)
        # Strip the single top-level directory (e.g. herdr-0.8.2/)
        items = os.listdir(tmp)
        if len(items) == 1 and os.path.isdir(os.path.join(tmp, items[0])):
            src_dir = os.path.join(tmp, items[0])
            for item in os.listdir(src_dir):
                shutil.move(os.path.join(src_dir, item), os.path.join(self.source_folder, item))
            shutil.rmtree(tmp)
        else:
            for item in items:
                shutil.move(os.path.join(tmp, item), os.path.join(self.source_folder, item))
            os.rmdir(tmp)
        os.unlink(dest)

    # ── Rust toolchain helpers ──

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
            self.output.warning("retrying without TLS verification")
            context = ssl._create_unverified_context()
            with urllib.request.urlopen(url, context=context) as response:
                with open(destination, "wb") as handle:
                    shutil.copyfileobj(response, handle)
        actual = self._sha256(destination)
        if actual != expected_sha256:
            raise ConanInvalidConfiguration(
                f"checksum mismatch for {url}: expected {expected_sha256}, got {actual}"
            )

    @staticmethod
    def _extract_tarball(archive, destination):
        root = os.path.realpath(destination)
        with tarfile.open(archive, "r:gz") as handle:
            for member in handle.getmembers():
                target = os.path.realpath(os.path.join(destination, member.name))
                if target != root and not target.startswith(root + os.sep):
                    raise ConanInvalidConfiguration(
                        f"unsafe path in toolchain archive: {member.name}"
                    )
            handle.extractall(destination, filter="data")

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
            raise ConanInvalidConfiguration("CA certificate bottle contained no cert.pem")
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
            raise ConanInvalidConfiguration(
                "Harmonybrew Rust bottle did not contain cargo/rustc"
            )
        self._repair_wrappers(os.path.dirname(cargo))
        lib_dirs = []
        for root, _dirs, files in os.walk(base):
            if os.path.basename(root) == "lib" and {"libssl.so", "libcrypto.so", "libz.so"} & set(files):
                lib_dirs.append(root)
        if lib_dirs:
            previous = os.environ.get("LD_LIBRARY_PATH")
            os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
                lib_dirs + ([previous] if previous else [])
            )
        self._set_ca_bundle(base)
        return cargo, rustc

    def _toolchain(self):
        cargo = self._find_tool("cargo")
        rustc = self._find_tool("rustc")
        if (not cargo or not rustc) and str(self.settings.os) == "OHOS":
            cargo, rustc = self._bootstrap_rust_toolchain()
        if not cargo or not rustc:
            raise ConanInvalidConfiguration(
                "Rust/Cargo toolchain is required; provision cargo/rustc or use the OHOS Harmonybrew fallback"
            )
        return cargo, rustc

    # ── Zig toolchain helpers (vendored libghostty-vt) ──

    def _download_zig(self):
        """Download and unpack the pinned Zig 0.15.2 for the host arch.

        Prefers the OHC_SOURCE_CACHE directory (populated out-of-process on
        OHOS workers where in-process HTTP downloads are unstable).
        """
        base = os.path.join(self.build_folder, "zig")
        os.makedirs(base, exist_ok=True)
        host_arch = platform.machine().lower()
        if host_arch in ("aarch64", "arm64"):
            entry = self.conan_data["zig"]["aarch64-linux"]
            cache_name = "zig-0.15.2-aarch64.tar.xz"
        elif host_arch in ("x86_64", "amd64"):
            entry = self.conan_data["zig"]["x86_64-linux"]
            cache_name = "zig-0.15.2-x86_64.tar.xz"
        else:
            raise ConanInvalidConfiguration(f"no Zig binary for host arch {host_arch}")

        # Check OHC_SOURCE_CACHE first
        cache_dir = os.environ.get("OHC_SOURCE_CACHE") or os.path.join(
            os.path.expanduser("~"), ".cache", "ohc-sources"
        )
        cached = os.path.join(cache_dir, cache_name)
        if os.path.isfile(cached) and self._sha256(cached) == entry["sha256"]:
            archive = cached
            self.output.info(f"using cached zig: {cached}")
        else:
            archive = os.path.join(base, "zig.tar.xz")
            if not os.path.isfile(archive) or self._sha256(archive) != entry["sha256"]:
                self._download_bottle(entry["url"], archive, entry["sha256"])
        zig_dir = os.path.join(base, "zig-bin")
        if not os.path.isfile(os.path.join(zig_dir, "zig")):
            if os.path.isdir(zig_dir):
                shutil.rmtree(zig_dir)
            os.makedirs(zig_dir)
            with tarfile.open(archive, "r:xz") as handle:
                handle.extractall(zig_dir)
            subdir = os.listdir(zig_dir)[0]
            shutil.move(os.path.join(zig_dir, subdir), os.path.join(zig_dir, "content"))
            for item in os.listdir(os.path.join(zig_dir, "content")):
                shutil.move(
                    os.path.join(zig_dir, "content", item),
                    os.path.join(zig_dir, item),
                )
            shutil.rmtree(os.path.join(zig_dir, "content"))
        zig = os.path.join(zig_dir, "zig")
        if str(self.settings.os) == "OHOS":
            self._sign_elf(zig)
        return zig

    @staticmethod
    def _sign_elf(path):
        """Sign a single ELF so the OHOS SELinux policy allows execution."""
        sign_tool = shutil.which("binary-sign-tool")
        if not sign_tool:
            sign_tool = "/storage/Users/currentUser/.harmonybrew/bin/binary-sign-tool"
        if not os.path.isfile(sign_tool):
            return
        tmp = path + ".signed"
        for _ in range(3):
            result = subprocess.run(
                [sign_tool, "sign", "-inFile", path, "-outFile", tmp, "-selfSign", "1"],
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode == 0 and os.path.isfile(tmp):
                shutil.move(tmp, path)
                os.chmod(path, 0o755)
                return
        raise ConanException(f"failed to sign ELF: {path}")

    def _build_libghostty_vt(self, zig, env):
        """Build vendored libghostty-vt.a via zig build.

        On OHOS the zig build runner and generated tools are unsigned ELFs
        that the kernel refuses to exec; sign every generated ELF and retry
        until the build completes.  On Linux/CI the build.rs runs zig build
        itself with the correct zig target for the host architecture.
        """
        if str(self.settings.os) != "OHOS":
            self.output.info("skipping prebuild on non-OHOS; build.rs invokes zig build")
            return
        zig_targets = {
            "armv8": "aarch64-linux-musl",
            "armv8.3": "aarch64-linux-musl",
            "x86_64": "x86_64-linux-musl",
        }
        try:
            zig_target = zig_targets[str(self.settings.arch)]
        except KeyError:
            raise ConanInvalidConfiguration(
                f"No zig target for OHOS arch {self.settings.arch}"
            )
        vendored = os.path.join(self.source_folder, "vendor", "libghostty-vt")
        lib_out = os.path.join(vendored, "zig-out", "lib", "libghostty-vt.a")
        if os.path.isfile(lib_out):
            self.output.info("libghostty-vt.a already present, skipping zig build")
            return
        version_string = "1.3.2-HEAD"
        version_file = os.path.join(vendored, "VERSION")
        if os.path.isfile(version_file):
            version_string = open(version_file, encoding="utf-8").read().strip()
        args = [
            "build", "-Demit-lib-vt", "-Doptimize=ReleaseFast",
            "-Dsimd=true", f"-Dtarget={zig_target}",
            f"-Dversion-string={version_string}",
            "-Demit-xcframework=false",
        ]
        for attempt in range(20):
            result = subprocess.run(
                [zig] + args, cwd=vendored, env=env,
                capture_output=True, text=True, timeout=600,
            )
            if result.returncode == 0:
                return
            signed = 0
            if str(self.settings.os) == "OHOS":
                readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
                for root, _dirs, files in os.walk(os.path.join(vendored, ".zig-cache", "o")):
                    for name in files:
                        path = os.path.join(root, name)
                        try:
                            with open(path, "rb") as handle:
                                if handle.read(4) != b"\x7fELF":
                                    continue
                        except OSError:
                            continue
                        if readelf:
                            sections = subprocess.run(
                                [readelf, "-S", path], capture_output=True,
                                text=True, timeout=30,
                            )
                            if ".codesign" in sections.stdout:
                                continue
                        self._sign_elf(path)
                        signed += 1
            self.output.warning(
                f"zig build attempt {attempt + 1} failed; signed {signed} ELF(s), retrying"
            )
        raise ConanException("zig build for libghostty-vt failed after repeated signing retries")

    # ── Build ──

    def build(self):
        apply_conandata_patches(self)
        cargo, rustc = self._toolchain()
        env = dict(os.environ)
        cc = shutil.which("clang") or "/storage/Users/currentUser/.harmonybrew/bin/clang"
        tmpdir = os.environ.get("HMBS_TMPDIR") or os.environ.get("TMPDIR") or \
            os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        ca_bundle = self._ensure_ca_bundle()
        target = self._rust_target()

        cargo_dir = os.path.join(self.source_folder, ".cargo")
        os.makedirs(cargo_dir, exist_ok=True)
        config = (
            '[source.crates-io]\nreplace-with = "rsproxy-sparse"\n'
            '[source.rsproxy-sparse]\nregistry = "sparse+https://rsproxy.cn/index/"\n'
            '[net]\nretry = 10\n[http]\ntimeout = 600\nlow-speed-limit = 1\n'
        )
        if ca_bundle:
            config += f'cainfo = "{ca_bundle}"\n'
        if target:
            config += f"\n[target.{target}]\nlinker = \"{cc}\"\n"
        with open(os.path.join(cargo_dir, "config.toml"), "w", encoding="utf-8") as handle:
            handle.write(config)

        env.update({
            "CARGO": cargo, "RUSTC": rustc, "CC": cc, "CXX": cc,
            "RUSTFLAGS": f"-C linker={cc}", "CARGO_NET_RETRY": "10",
            "CARGO_HTTP_TIMEOUT": "600", "CARGO_BUILD_JOBS": "1",
            "TMPDIR": tmpdir, "TMP": tmpdir, "TEMP": tmpdir,
            "PATH": os.pathsep.join([
                os.path.dirname(cargo), os.path.dirname(rustc), env.get("PATH", ""),
            ]),
        })
        if ca_bundle:
            env.update({
                "CARGO_HTTP_CAINFO": ca_bundle,
                "SSL_CERT_FILE": ca_bundle, "CURL_CA_BUNDLE": ca_bundle,
            })

        zig = self._download_zig()
        env["ZIG"] = zig
        self._build_libghostty_vt(zig, env)

        command = [cargo, "build", "--release", "--locked"]
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
            return os.path.join(
                self.source_folder, "target", target, "release", "herdr"
            )
        return os.path.join(self.source_folder, "target", "release", "herdr")

    def package(self):
        binary = self._binary_path()
        if not os.path.isfile(binary):
            raise ConanException(f"herdr build output not found: {binary}")
        copy(self, "herdr", src=os.path.dirname(binary),
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
