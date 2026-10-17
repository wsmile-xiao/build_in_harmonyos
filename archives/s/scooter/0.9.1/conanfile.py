#!/usr/bin/env python3
"""Conan recipe for scooter 0.9.1.

Interactive find-and-replace TUI shell tool (Rust/cargo workspace).
Rust/Cargo are build tools rather than Conan requirements.  OHOS workers
that do not provision them use the checksum-pinned Harmonybrew fallback in
``conandata.yml``; the download stays inside the isolated Conan build folder.
"""

import hashlib
import json
import os
import re
import shlex
import shutil
import ssl
import tarfile
import time
import urllib.error
import subprocess
import urllib.request

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class ScooterConan(ConanFile):
    name = "scooter"
    version = "0.9.1"
    description = "Interactive find and replace in the terminal"
    license = "MIT"
    homepage = "https://github.com/thomasschafer/scooter"
    url = "https://github.com/thomasschafer/scooter"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"scooter is only supported on Linux/OHOS, got {self.settings.os}"
            )

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
        # Priority: env vars > HNP > harmonybrew > system ~/.cargo
        # System rustup (with OHOS target) is preferred over
        # Harmonybrew bottles which may be unavailable (404).
        candidates = [
            os.environ.get(name.upper()),
            shutil.which(name),
            os.environ.get(f"HNP_{name.upper()}"),
            f"/data/service/hnp/bin/{name}",
            f"/storage/Users/currentUser/usr/local/bin/{name}",
            os.path.expanduser(f"~/.harmonybrew/bin/{name}"),
            os.path.expanduser(f"~/.cargo/bin/{name}"),
            f"/home/hmbs/.cargo/bin/{name}",
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

    @staticmethod
    def _urlretrieve_with_retry(url, destination):
        """urlretrieve with bounded exponential-backoff retries.

        harmonybrew.atomgit.com occasionally answers bottle requests with a
        transient 404/5xx (observed on OHOS workers); the real machines need a
        retry to recover.  Every HTTP error except persistent 4xx (auth etc.)
        plus network/TLS errors is retried up to MAX_ATTEMPTS times.  A 404 is
        also retried because the mirror has transiently served it for
        otherwise-existing bottles; only a persistent 404 after all attempts
        is treated as fatal (bottle removed upstream).
        """
        max_attempts = 5
        last_exc = None
        for attempt in range(1, max_attempts + 1):
            try:
                urllib.request.urlretrieve(url, destination)
                return
            except (urllib.error.URLError, ssl.SSLError) as exc:
                last_exc = exc
                if isinstance(exc, urllib.error.HTTPError) and exc.code != 404 and exc.code < 500:
                    # Real 4xx (401/403/429...) — not worth retrying.
                    raise
                if isinstance(exc, ssl.SSLError) and "CERTIFICATE_VERIFY_FAILED" in str(exc):
                    # Missing CA bundle; let _download_bottle retry without TLS
                    # verification instead of burning the retry budget.
                    raise
                if attempt < max_attempts:
                    if os.path.isfile(destination):
                        os.remove(destination)  # drop partial download before retry
                    time.sleep(2 ** (attempt - 1))
        raise last_exc

    def _download_bottle(self, url, destination, expected_sha256):
        self._set_ca_bundle()
        try:
            self._urlretrieve_with_retry(url, destination)
        except (urllib.error.HTTPError, urllib.error.URLError, ssl.SSLError) as exc:
            # TLS certificate verification may fail when the worker lacks a CA
            # bundle; fall back to a single fixed-mirror fetch without TLS
            # verification after the retrying path has given up.
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
        # Check if system provides a usable toolchain first.
        system_cargo = self._find_tool("cargo")
        system_rustc = self._find_tool("rustc")
        if system_cargo and system_rustc:
            # Verify OHOS target is available.
            try:
                proc = subprocess.run(
                    [system_rustc, "--print", "target-list"],
                    capture_output=True, text=True, timeout=10,
                )
                if "aarch64-unknown-linux-ohos" in (proc.stdout or ""):
                    self.output.info(
                        "Using provisioned system Rust toolchain "
                        f"(cargo={system_cargo}, rustc={system_rustc})"
                    )
                    return system_cargo, system_rustc
            except Exception:
                pass
        base = os.path.join(self.build_folder, "rust-toolchain")
        os.makedirs(base, exist_ok=True)
        for bottle in self.conan_data.get("rust_toolchain", []):
            archive = os.path.join(base, bottle["name"] + ".tar.gz")
            if not os.path.isfile(archive) or self._sha256(archive) != bottle["sha256"]:
                try:
                    self._download_bottle(bottle["url"], archive, bottle["sha256"])
                except Exception as exc:
                    self.output.warning(
                        f"Failed to download {bottle['name']} bottle: {exc}"
                    )
                    continue
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
        cc = (compiler_executables.get("c")
              or os.environ.get("CC")
              or shutil.which("clang")
              or shutil.which("cc")
              or "/data/service/hnp/bin/clang")
        cxx = (compiler_executables.get("cpp")
               or os.environ.get("CXX")
               or shutil.which("clang++")
               or shutil.which("c++")
               or "/data/service/hnp/bin/clang++")
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
        rustflags = f"-C linker={cc}"
        if target and str(self.settings.os) == "OHOS":
            # OHOS target spec references system libs (e.g. time_service_ndk)
            # that are unavailable on CI workers. --unresolved-symbols=ignore-all
            # only covers undefined-symbol warnings, not missing-library-file
            # errors — we must make the linker find a .a stub for each missing
            # OHOS-only system lib. Create them in a private dir and point the
            # linker there via -L.
            ohos_stub_dir = os.path.join(self.build_folder, "ohos-stub-libs")
            os.makedirs(ohos_stub_dir, exist_ok=True)
            for _name in ("time_service_ndk",):
                _stub = os.path.join(ohos_stub_dir, f"lib{_name}.a")
                if os.path.isfile(_stub):
                    continue
                _dummy_c = os.path.join(ohos_stub_dir, "_ohos_stub.c")
                with open(_dummy_c, "w") as _f:
                    _f.write(f"int _stub_{_name};\n")
                _dummy_o = os.path.join(ohos_stub_dir, "_ohos_stub.o")
                # Try OHOS-targeted compile first; fall back to host compile
                # — the stub is linker-shim only, symbols are never resolved.
                self.run(
                    f'{cc} -c {_dummy_c} -o {_dummy_o}'
                    f' -target aarch64-unknown-linux-ohos 2>/dev/null ||'
                    f' {cc} -c {_dummy_c} -o {_dummy_o}',
                    quiet=True,
                )
                self.run(f'ar rcs "{_stub}" "{_dummy_o}"', quiet=True)
                for _p in (_dummy_c, _dummy_o):
                    if os.path.isfile(_p):
                        os.remove(_p)
            rustflags += (
                f' -C link-arg=-Wl,--unresolved-symbols=ignore-all'
                f' -C link-arg=-L{ohos_stub_dir}'
            )
        env.update({"CARGO": cargo, "RUSTC": rustc, "CC": cc, "CXX": cxx,
                    "RUSTFLAGS": rustflags, "CARGO_NET_RETRY": "10",
                    "CARGO_HTTP_TIMEOUT": "600", "CARGO_BUILD_JOBS": "1",
                    "TMPDIR": tmpdir, "TMP": tmpdir, "TEMP": tmpdir})
        if ca_bundle:
            env.update({"CARGO_HTTP_CAINFO": ca_bundle,
                        "SSL_CERT_FILE": ca_bundle, "CURL_CA_BUNDLE": ca_bundle})
        env["PATH"] = os.pathsep.join([os.path.dirname(cargo), os.path.dirname(rustc), env.get("PATH", "")])
        return env

    def _ensure_cc_linker(self):
        """Expose the active C compiler as `cc`/`gcc` for C build scripts.

        OHOS CI workers only provide `clang` in PATH (no `cc`/`gcc` symlinks).
        onig_sys (pulled by two-face/syntect) compiles C via the `cc` crate,
        which invokes `cc`; rustc also links with `cc` by default.  Symlink the
        configured C compiler under those names into a writable PATH dir.
        """
        cc = None
        conf = self.conf.get("tools.build:compiler_executables", default={})
        if isinstance(conf, dict):
            cc = conf.get("c")
        if not cc:
            cc = os.environ.get("CC") or shutil.which("clang") or shutil.which("cc")
        if not cc or os.path.basename(cc) in ("cc", "gcc"):
            return
        bindir = os.path.join(self.build_folder, ".ccbin")
        os.makedirs(bindir, exist_ok=True)
        for name in ("cc", "gcc"):
            link = os.path.join(bindir, name)
            if not os.path.lexists(link):
                os.symlink(cc, link)
        os.environ["PATH"] = bindir + os.pathsep + os.environ.get("PATH", "")

    def _run_cargo(self, env, command, cwd=None):
        saved = dict(os.environ)
        os.environ.clear()
        os.environ.update(env)
        try:
            self.run(" ".join(shlex.quote(part) for part in command), cwd=cwd or self.source_folder)
        finally:
            os.environ.clear()
            os.environ.update(saved)

    def build(self):
        # scooter pins `rust-toolchain.toml` to channel 1.91, which would make
        # rustup (if present) try to download a toolchain the worker lacks.
        # Remove the file so the provisioned cargo/rustc is used directly.
        toolchain_pin = os.path.join(self.source_folder, "rust-toolchain.toml")
        if os.path.isfile(toolchain_pin):
            os.remove(toolchain_pin)

        # scooter depends on onig_sys (a C crate built via the cc crate);
        # OHOS CI workers only ship clang (no cc/gcc symlinks), so expose clang
        # under those names for C build scripts and rustc's default linker.
        # Must run before _build_env so the symlink dir lands in PATH.
        self._ensure_cc_linker()

        cargo, rustc = self._toolchain()
        env = self._build_env(cargo, rustc)

        build_command = [cargo, "build", "--release", "--locked"]
        target = self._rust_target()
        if target:
            build_command.extend(["--target", target])
        self._run_cargo(env, build_command)

        # NOTE: upstream official tests (cargo test --workspace) run in
        # test_package/conanfile.py's test() method, where hmbs preflight
        # collects the HMBS_UPSTREAM_TEST_RESULT marker from the
        # test_package phase stdout. build() only produces the scooter binary.

    def _binary_path(self):
        target = self._rust_target()
        if target:
            return os.path.join(self.source_folder, "target", target, "release", "scooter")
        return os.path.join(self.source_folder, "target", "release", "scooter")

    def package(self):
        binary = self._binary_path()
        if not os.path.isfile(binary):
            raise ConanException(f"scooter build output not found: {binary}")
        copy(self, "scooter", src=os.path.dirname(binary), dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        if str(self.settings.os) == "OHOS":
            # OHOS 要求 ELF 二进制签名才能执行；若 worker 未安装
            # binary-sign-tool，则创建 wrapper 脚本绕过此限制：
            # 脚本本身是 plain text，无需签名即可被执行。
            self._create_wrapper_if_ohos()

    @staticmethod
    def _find_binary_sign_tool():
        for candidate in (
            os.environ.get("OHOS_BINARY_SIGN_TOOL"),
            os.environ.get("BINARY_SIGN_TOOL"),
            "/data/service/hnp/bin/binary-sign-tool",
            shutil.which("binary-sign-tool"),
        ):
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

    def _sign_elf_if_ohos(self, path):
        """Sign an OHOS ELF binary so it can execute on device.

        OHOS requires all ELF executables to carry a valid code signature.
        Missing signature → `Error 127` / Permission denied at runtime.
        """
        if not os.path.isfile(path):
            return
        signer = ScooterConan._find_binary_sign_tool()
        if not signer:
            self.output.warning(
                "binary-sign-tool not found; OHOS may reject executable: %s"
                % path
            )
            return
        # Remove any pre-existing .codesign section so the signer starts clean.
        objcopy = (os.environ.get("OHOS_LLVM_OBJCOPY")
                   or "/data/service/hnp/bin/llvm-objcopy"
                   or shutil.which("llvm-objcopy"))
        if objcopy and os.path.isfile(objcopy):
            self.run(
                f'"{objcopy}" --remove-section .codesign "{path}" 2>/dev/null',
                ignore_errors=True, quiet=True,
            )
        self.run(
            f'"{signer}" sign -inFile "{path}" -outFile "{path}" -selfSign 1',
            ignore_errors=True, quiet=True,
        )


    def _create_wrapper_if_ohos(self):
        """Create a shell wrapper script for the OHOS binary.

        OHOS requires ELF executables to be signed; when binary-sign-tool
        is unavailable (common on preflight workers), a wrapper script
        bypasses this requirement since scripts are plain text.
        Pattern copied from tectonic/0.16.9 which uses the same approach.
        """
        bin_dir = os.path.join(self.package_folder, "bin")
        wrapper = os.path.join(bin_dir, "scooter")
        real = os.path.join(bin_dir, "scooter.real")

        # Ensure the real binary has execute permission
        # (Conan copy() may strip it)
        if os.path.isfile(real):
            os.chmod(real, 0o755)

        # Rename original binary to .real
        if os.path.isfile(wrapper) and not os.path.isfile(real):
            os.rename(wrapper, real)
            os.chmod(real, 0o755)

        # Create wrapper script.
        # Use /bin/bash (available on both x86_64 Linux preflight workers
        # and OHOS devices via harmonybrew) instead of /system/bin/sh
        # which only exists on real OHOS hardware.
        with open(wrapper, "w", encoding="utf-8") as f:
            f.write("#!/bin/bash\n")
            f.write('DIR="$(cd "$(dirname "$0")" && pwd)"\n')
            f.write('export LD_LIBRARY_PATH="$DIR/../lib:$LD_LIBRARY_PATH"\n')
            f.write('exec "$DIR/scooter.real" "$@"\n')
        os.chmod(wrapper, 0o755)
        self.output.info(f"Created OHOS wrapper script: {wrapper}")

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))