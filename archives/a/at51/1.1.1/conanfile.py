#!/usr/bin/env python3

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class At51Conan(ConanFile):
    name = "at51"
    version = "1.1.1"
    description = "Some applications for reverse engineering 8051 firmware"
    license = "MIT"
    homepage = "https://github.com/8051Enthusiast/at51"
    url = "https://github.com/8051Enthusiast/at51"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("OHOS", "Linux", "Windows"):
            raise ConanInvalidConfiguration(
                "at51 is supported on OHOS, Linux, and Windows"
            )

    def source(self):
        get(
            self,
            **self.conan_data["sources"],
            strip_root=True,
        )

    def build(self):
        apply_conandata_patches(self)

        cargo = self._ensure_rust()
        self._configure_rust()

        self.run(
            f'"{cargo}" build --release --locked',
            cwd=self.source_folder,
            env="conanbuild",
        )

        self.run(
            f'"{cargo}" test --release --locked --no-fail-fast --bins --tests',
            cwd=self.source_folder,
            env="conanbuild",
        )

    def package(self):
        binary = self._binary_name()
        for target_dir in self._candidate_release_dirs():
            if os.path.isfile(os.path.join(target_dir, binary)):
                copy(
                    self,
                    binary,
                    src=target_dir,
                    dst=os.path.join(self.package_folder, "bin"),
                    keep_path=False,
                )
                break
        else:
            raise ConanInvalidConfiguration(
                f"at51 binary not found in Cargo release target directories"
            )

        copy(
            self,
            "LICENSE*",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        copy(
            self,
            "README.md",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "res"),
            keep_path=False,
        )
        copy(
            self,
            "CHANGELOG.md",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "res"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []

    def _ensure_rust(self):
        cargo = self._find_rust_tool("cargo")
        rustc = self._find_rust_tool("rustc")
        if cargo and rustc:
            self.output.info(f"Using cargo: {cargo}")
            self.output.info(f"Using rustc: {rustc}")
            self._activate_rust_toolchain(cargo, rustc)
            return cargo

        if str(self.settings.os) == "Windows":
            raise ConanInvalidConfiguration("Rust/Cargo toolchain is unavailable")

        self.output.info("Bootstrapping Rust from Harmonybrew bottles...")
        cargo = self._bootstrap_rust_toolchain()
        bin_dir = os.path.dirname(cargo)
        rustc = os.path.join(bin_dir, "rustc.real")
        if not os.path.isfile(rustc):
            rustc = os.path.join(bin_dir, "rustc")
        if not os.path.isfile(rustc):
            rustc = self._find_rust_tool("rustc")

        if not cargo or not rustc:
            raise ConanInvalidConfiguration("Rust/Cargo toolchain is unavailable")

        self.output.info(f"Using bootstrapped cargo: {cargo}")
        self.output.info(f"Using bootstrapped rustc: {rustc}")
        self._activate_rust_toolchain(cargo, rustc)
        return cargo

    def _find_rust_tool(self, name):
        candidates = [
            shutil.which(name),
            os.path.expanduser(f"~/.harmonybrew/bin/{name}"),
            os.path.expanduser(f"~/.cargo/bin/{name}"),
            f"/data/service/hnp/bin/{name}",
            f"/storage/Users/currentUser/usr/local/bin/{name}",
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

    def _activate_rust_toolchain(self, cargo, rustc):
        bin_dir = os.path.dirname(cargo)
        os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
        os.environ["CARGO"] = cargo
        os.environ["RUSTC"] = rustc
        self._configure_rust_runtime_libs()
        self._configure_ca_bundle()

    def _download_bottle(self, url, destination):
        import socket
        import ssl
        import urllib.error
        import urllib.request

        self._configure_ca_bundle()
        tmp_destination = destination + ".tmp"
        if os.path.exists(tmp_destination):
            os.remove(tmp_destination)

        def download(context=None):
            request = urllib.request.Request(
                url,
                headers={"User-Agent": "Conan at51 recipe"},
            )
            total = 0
            expected = None
            with urllib.request.urlopen(
                request,
                context=context,
                timeout=120,
            ) as response, open(tmp_destination, "wb") as output:
                length = response.headers.get("Content-Length")
                if length:
                    expected = int(length)
                while True:
                    if expected is not None and total >= expected:
                        break
                    read_size = 1024 * 1024
                    if expected is not None:
                        read_size = min(read_size, expected - total)
                    chunk = response.read(read_size)
                    if not chunk:
                        break
                    output.write(chunk)
                    total += len(chunk)

            if expected is not None and total != expected:
                raise ConanInvalidConfiguration(
                    f"incomplete download for {url}: got {total}, expected {expected}"
                )
            os.replace(tmp_destination, destination)

        try:
            download()
        except (urllib.error.URLError, ssl.SSLError, socket.timeout, TimeoutError) as exc:
            if "CERTIFICATE_VERIFY_FAILED" not in str(exc):
                if os.path.exists(tmp_destination):
                    os.remove(tmp_destination)
                raise
            os.environ.pop("SSL_CERT_FILE", None)
            os.environ.pop("CURL_CA_BUNDLE", None)
            self.output.warning(
                "no CA bundle on device, downloading %s with an unverified TLS context"
                % url
            )
            context = ssl._create_unverified_context()
            download(context)

    def _bootstrap_rust_toolchain(self):
        base = os.path.join(self.build_folder, "rust-toolchain")
        os.makedirs(base, exist_ok=True)
        bottles = {
            "rust": "https://harmonybrew.atomgit.com/bottles/rust-1.97.1.arm64_ohos.bottle.tar.gz",
            "openssl3": "https://harmonybrew.atomgit.com/bottles/openssl%403-3.6.3.arm64_ohos.bottle.tar.gz",
            "zlib": "https://harmonybrew.atomgit.com/bottles/zlib-ng-compat-2.3.3_1.arm64_ohos.bottle.tar.gz",
        }
        for name, url in bottles.items():
            archive = os.path.join(base, name + ".tar.gz")
            if not os.path.isfile(archive):
                self.output.info(f"Downloading {name} bottle from {url}")
                self._download_bottle(url, archive)
            try:
                self._extract_bottle(archive, base)
            except Exception:
                if os.path.exists(archive):
                    os.remove(archive)
                self.output.warning(f"Discarding corrupt {name} bottle and retrying")
                self._download_bottle(url, archive)
                self._extract_bottle(archive, base)

        cargo = None
        for root, _dirs, files in os.walk(base):
            if "cargo.real" in files:
                cargo = os.path.join(root, "cargo.real")
                break
        if not cargo:
            raise ConanInvalidConfiguration(
                "failed to bootstrap Rust toolchain from Harmonybrew bottles"
            )

        bin_dir = os.path.dirname(cargo)
        for name in sorted(os.listdir(bin_dir)):
            if name.endswith(".real"):
                continue
            wrapper = os.path.join(bin_dir, name)
            real = os.path.join(bin_dir, name + ".real")
            if os.path.islink(wrapper) or not os.path.isfile(wrapper) or not os.path.isfile(real):
                continue
            try:
                with open(wrapper, "rb") as f:
                    head = f.read(512)
            except OSError:
                continue
            if not head.startswith(b"#!"):
                continue
            with open(wrapper, "w", encoding="utf-8") as f:
                f.write("#!/bin/sh\n")
                f.write("# repaired by at51 recipe: exec local .real binary\n")
                f.write(f'exec "{real}" "$@"\n')

        self._configure_rust_runtime_libs(base)
        return cargo

    def _extract_bottle(self, archive, destination):
        tar = shutil.which("tar")
        if tar and os.path.basename(archive).startswith("rust"):
            self.run(
                f'"{tar}" --exclude "*/share/man/*" --exclude "share/man/*" '
                f'-xzf "{archive}" -C "{destination}"'
            )
            return

        import tarfile

        with tarfile.open(archive, "r:gz") as archive_file:
            archive_file.extractall(
                destination,
                members=(
                    member
                    for member in archive_file
                    if "/share/man/" not in member.name
                    and not member.name.endswith("/share/man")
                ),
            )

    def _configure_rust_runtime_libs(self, root=None):
        roots = [root] if root else [os.path.expanduser("~/.harmonybrew")]
        lib_dirs = []
        for base in roots:
            if not base or not os.path.isdir(base):
                continue
            for current, _dirs, files in os.walk(base):
                if os.path.basename(current) != "lib":
                    continue
                libs = set(files)
                if libs & {"libssl.so", "libcrypto.so", "libz.so"}:
                    lib_dirs.append(current)
        if lib_dirs:
            previous = os.environ.get("LD_LIBRARY_PATH", "")
            os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
                lib_dirs + ([previous] if previous else [])
            )

    def _configure_ca_bundle(self):
        if os.environ.get("SSL_CERT_FILE"):
            return
        for ca in (
            "/storage/Users/currentUser/usr/local/ssl/cert.pem",
            "/etc/ssl/certs/cacert.pem",
            "/etc/ssl/cert.pem",
            os.path.expanduser("~/.harmonybrew/etc/ca-certificates/cert.pem"),
        ):
            if os.path.isfile(ca):
                os.environ["SSL_CERT_FILE"] = ca
                os.environ["CURL_CA_BUNDLE"] = ca
                break

    def _configure_rust(self):
        self._configure_temp_dir()
        self._configure_cargo_home()

        target_dir = os.environ.get("CARGO_TARGET_DIR")
        if not target_dir:
            target_dir = os.path.join(self.build_folder, "cargo-target")
            os.environ["CARGO_TARGET_DIR"] = target_dir
        os.makedirs(target_dir, exist_ok=True)

        if str(self.settings.os) in ("OHOS", "Linux"):
            clang = self._select_clang()
            compile_flags, link_flags = self._clang_flags(clang)

            os.environ["CC"] = clang
            os.environ["CXX"] = clang
            os.environ["CFLAGS"] = " ".join(["-fPIC", "-O2"] + compile_flags)
            os.environ["CXXFLAGS"] = " ".join(
                ["-fPIC", "-O2", "--driver-mode=g++"] + compile_flags
            )
            os.environ["CARGO_TARGET_AARCH64_UNKNOWN_LINUX_OHOS_LINKER"] = clang
            rustflags = [f"-C linker={clang}"]
            rustflags.extend(f"-C link-arg={flag}" for flag in link_flags)
            os.environ["RUSTFLAGS"] = " ".join(rustflags)

    def _select_clang(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        candidates = [
            compilers.get("c"),
            shutil.which("clang"),
            "/storage/Users/currentUser/usr/local/bin/clang",
            "/storage/Users/currentUser/usr/local/bin/clang-15",
            "/data/service/hnp/bin/clang",
        ]
        for candidate in candidates:
            resolved = self._resolve_clang_binary(candidate)
            if resolved and os.path.isfile(resolved) and os.access(resolved, os.X_OK):
                return resolved
        raise ConanInvalidConfiguration("usable OHOS clang toolchain not found")

    def _resolve_clang_binary(self, candidate):
        if not candidate:
            return None
        if os.path.basename(candidate) == "clang":
            real = os.path.join(os.path.dirname(candidate), "clang-15")
            if os.path.isfile(real) and os.access(real, os.X_OK):
                return real
        return candidate

    def _clang_flags(self, clang):
        bin_dir = os.path.dirname(clang)
        sysroot = os.path.abspath(os.path.join(bin_dir, "..", "sysroot"))
        if not os.path.isdir(sysroot):
            return [], []

        lib_dir = os.path.join(sysroot, "usr", "lib", "aarch64-linux-ohos")
        common = [
            f"--sysroot={sysroot}",
            "-fuse-ld=lld",
            "-Wl,--code-sign",
            f"-L{lib_dir}",
        ]
        return common + ["-D__MUSL__"], common

    def _configure_temp_dir(self):
        tmpdir = (
            os.environ.get("HMBS_TMPDIR")
            or os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
        )
        if not tmpdir or not self._is_writable_dir(tmpdir):
            tmpdir = os.path.join(self.build_folder, "tmp")

        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir

    def _configure_cargo_home(self):
        cargo_home = os.environ.get("CARGO_HOME")
        if not cargo_home:
            cargo_home = os.path.join(self.build_folder, "cargo-home")
            os.environ["CARGO_HOME"] = cargo_home

        os.makedirs(cargo_home, exist_ok=True)

        vendor_dir = os.environ.get("AT51_CARGO_VENDOR_DIR")
        config_path = os.path.join(cargo_home, "config.toml")
        with open(config_path, "w", encoding="utf-8") as f:
            if vendor_dir:
                vendor_dir = os.path.abspath(vendor_dir).replace("\\", "/")
                f.write(
                    '[source.crates-io]\n'
                    'replace-with = "vendored-sources"\n\n'
                    '[source.vendored-sources]\n'
                    f'directory = "{vendor_dir}"\n\n'
                    '[net]\n'
                    'offline = true\n'
                )
            else:
                f.write(
                    '[source.crates-io]\n'
                    'replace-with = "rsproxy-sparse"\n\n'
                    '[source.rsproxy-sparse]\n'
                    'registry = "sparse+https://rsproxy.cn/index/"\n\n'
                    '[net]\n'
                    'retry = 10\n\n'
                    '[http]\n'
                    'timeout = 600\n'
                    'low-speed-limit = 1\n'
                )

    @staticmethod
    def _is_writable_dir(path):
        try:
            os.makedirs(path, exist_ok=True)
            probe = os.path.join(path, ".conan-at51-write-test")
            with open(probe, "w", encoding="utf-8") as f:
                f.write("ok")
            os.remove(probe)
            return True
        except OSError:
            return False

    def _candidate_release_dirs(self):
        seen = set()
        for base in (
            os.environ.get("CARGO_TARGET_DIR"),
            os.path.join(self.build_folder, "cargo-target"),
            os.path.join(self.source_folder, "target"),
        ):
            if not base:
                continue
            release_dir = os.path.join(base, "release")
            if release_dir not in seen:
                seen.add(release_dir)
                yield release_dir

    def _binary_name(self):
        return "at51.exe" if str(self.settings.os) == "Windows" else "at51"
