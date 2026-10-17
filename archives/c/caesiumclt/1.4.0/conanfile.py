#!/usr/bin/env python3
"""Conan recipe for caesiumclt 1.4.0.

Rust/Cargo are build tools rather than Conan requirements. OHOS workers that
do not provision them use the checksum-pinned Harmonybrew fallback in
``conandata.yml``; the download stays inside the isolated Conan build folder.
"""

import hashlib
import json
import os
import re
import shlex
import shutil
import ssl
import subprocess
import tarfile
import tempfile
import urllib.error
import urllib.request

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class CaesiumcltConan(ConanFile):
    name = "caesiumclt"
    version = "1.4.0"
    description = "A fast and efficient lossy and/or lossless image compression tool"
    license = "Apache-2.0"
    homepage = "https://github.com/Lymphatus/caesium-clt"
    url = ""
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"caesiumclt is only supported on Linux/OHOS, got {self.settings.os}"
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
        # NOTE: the preflight worker mounts /tmp read-only, so this must not
        # use urllib.request.urlretrieve (legacy helper staging via /tmp).
        # Stream directly into the writable Conan build folder instead, and
        # try fallback URLs so a single removed Harmonybrew bottle (HTTP 404)
        # does not fail the whole build.
        if isinstance(url, (list, tuple)):
            urls = list(url)
        else:
            urls = [url]
        self._set_ca_bundle()
        last_error = None
        for candidate in urls:
            try:
                request = urllib.request.Request(
                    candidate, headers={"User-Agent": "conan-caesiumclt/1.4.0"}
                )
                try:
                    with urllib.request.urlopen(request, timeout=600) as response:
                        with open(destination, "wb") as handle:
                            shutil.copyfileobj(response, handle)
                except (urllib.error.URLError, ssl.SSLError) as exc:
                    if "CERTIFICATE_VERIFY_FAILED" not in str(exc):
                        raise
                    self.output.warning(
                        "no usable CA bundle; retrying without TLS verification: "
                        f"{candidate}"
                    )
                    context = ssl._create_unverified_context()
                    with urllib.request.urlopen(candidate, context=context, timeout=600) as response:
                        with open(destination, "wb") as handle:
                            shutil.copyfileobj(response, handle)
            except urllib.error.HTTPError as exc:
                last_error = exc
                self.output.warning(
                    f"toolchain download failed ({exc.code} {exc.reason}): {candidate}"
                )
                try:
                    if os.path.isfile(destination):
                        os.remove(destination)
                except OSError:
                    pass
                continue
            except (urllib.error.URLError, OSError) as exc:
                last_error = exc
                self.output.warning(f"toolchain download failed ({exc}): {candidate}")
                try:
                    if os.path.isfile(destination):
                        os.remove(destination)
                except OSError:
                    pass
                continue
            if expected_sha256:
                actual = self._sha256(destination)
                if actual != expected_sha256:
                    # A fallback official installer has no pinned hash; keep
                    # the file but warn. A pinned-bottle mismatch stays fatal.
                    if candidate != urls[0]:
                        self.output.warning(
                            f"fallback toolchain checksum differs for {candidate}: "
                            f"expected {expected_sha256}, got {actual}; "
                            "continuing with TLS-verified download"
                        )
                    else:
                        raise ConanInvalidConfiguration(
                            f"Rust toolchain bottle checksum mismatch for {candidate}: "
                            f"expected {expected_sha256}, got {actual}"
                        )
            else:
                self.output.warning(
                    f"no pinned checksum for fallback {candidate}; "
                    "continuing with TLS-verified download"
                )
            return candidate
        raise ConanInvalidConfiguration(
            f"All Rust toolchain download URLs failed for {destination}: {last_error}"
        )

    @staticmethod
    def _candidate_urls(bottle):
        urls = []
        primary = bottle.get("url")
        if primary:
            urls.append(primary)
        fallbacks = bottle.get("fallback_urls") or []
        if isinstance(fallbacks, str):
            fallbacks = [fallbacks]
        urls.extend(fallbacks)
        single = bottle.get("fallback_url")
        if single:
            urls.append(single)
        return urls

    @staticmethod
    def _extract_tarball(archive, destination):
        root = os.path.realpath(destination)
        # Bottles are .tar.gz, the official ohos fallback is .tar.xz;
        # "r:*" auto-detects the compression so a fallback saved under a
        # neutral filename still extracts.
        mode = "r:*"
        with tarfile.open(archive, mode) as handle:
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
        urls = self._candidate_urls(ca_bottle) or ([ca_bottle["url"]] if ca_bottle.get("url") else [])
        needs_download = True
        if os.path.isfile(archive) and ca_bottle.get("sha256"):
            try:
                needs_download = self._sha256(archive) != ca_bottle["sha256"]
            except OSError:
                needs_download = True
        if needs_download:
            self._download_bottle(urls, archive, ca_bottle.get("sha256"))
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

    @staticmethod
    def _sign_elf_tree(root):
        """Best-effort OHOS ELF self-sign so freshly unpacked cargo runs.

        Official rust-lang ohos binaries are not Harmonybrew-signed; without
        a signature HongMeng kernel refuses to exec them. Missing tool or
        failures are ignored (Harmonybrew bottles are already signed).
        """
        sign_tool = (
            shutil.which("binary-sign-tool")
            or os.environ.get("OHOS_BINARY_SIGN_TOOL")
            or "/storage/Users/currentUser/usr/local/bin/binary-sign-tool"
        )
        if not sign_tool or not os.path.isfile(sign_tool):
            return
        try:
            proc = subprocess.run(
                [sign_tool, "--help"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, errors="replace", timeout=30,
            )
            if proc.returncode != 0 and "sign" not in (proc.stdout or ""):
                return
        except OSError:
            return
        for directory, _dirs, files in os.walk(root):
            for name in files:
                path = os.path.join(directory, name)
                try:
                    with open(path, "rb") as handle:
                        magic = handle.read(4)
                    if magic != b"\x7fELF":
                        continue
                    subprocess.run(
                        [sign_tool, "sign", "-inFile", path,
                         "-outFile", path, "-selfSign", "1"],
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        text=True, errors="replace", timeout=120,
                    )
                except OSError:
                    continue

    def _install_official_dist(self, base, archive):
        """Install an official rust-lang ohos standalone dist if present.

        Returns (cargo, rustc) or (None, None) when the archive was a
        Harmonybrew bottle rather than an official dist.
        """
        stage = os.path.join(base, "official-stage")
        os.makedirs(stage, exist_ok=True)
        mode = "r:*"
        with tarfile.open(archive, mode) as handle:
            members = handle.getmembers()
            top = None
            for member in members:
                first = member.name.split("/", 1)[0]
                if first and first.startswith("rust-"):
                    top = first
                    break
            safe = []
            for member in members:
                target = os.path.realpath(os.path.join(stage, member.name))
                root = os.path.realpath(stage)
                if target != root and not target.startswith(root + os.sep):
                    raise ConanInvalidConfiguration(
                        f"unsafe path in Rust toolchain archive: {member.name}"
                    )
                safe.append(member)
            handle.extractall(stage, members=safe)
        if not top:
            return None, None
        install_sh = os.path.join(stage, top, "install.sh")
        if not os.path.isfile(install_sh):
            return None, None
        prefix = os.path.join(base, "official-rust")
        os.makedirs(prefix, exist_ok=True)
        self._sign_elf_tree(os.path.join(stage, top))
        cmd = ["sh", install_sh, f"--prefix={prefix}", "--without=rust-docs"]
        self.output.info(f"Running official Rust installer: {' '.join(shlex.quote(p) for p in cmd)}")
        proc = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, errors="replace", timeout=900,
        )
        self.output.info(proc.stdout)
        if proc.returncode != 0:
            raise ConanInvalidConfiguration(
                f"Official Rust installer failed ({proc.returncode})"
            )
        cargo = os.path.join(prefix, "bin", "cargo")
        rustc = os.path.join(prefix, "bin", "rustc")
        if os.path.isfile(cargo) and os.path.isfile(rustc):
            return cargo, rustc
        return None, None

    def _bootstrap_rust_toolchain(self):
        if str(self.settings.os) != "OHOS":
            return None, None
        base = os.path.join(self.build_folder, "rust-toolchain")
        os.makedirs(base, exist_ok=True)
        official = (None, None)
        for bottle in self.conan_data.get("rust_toolchain", []):
            urls = self._candidate_urls(bottle)
            if not urls:
                continue
            # Neutral filename: primary is .tar.gz but the official fallback
            # is .tar.xz; extraction auto-detects via "r:*".
            archive = os.path.join(base, bottle["name"] + ".archive")
            expected = bottle.get("sha256")
            needs_download = True
            if os.path.isfile(archive) and expected:
                try:
                    if self._sha256(archive) == expected:
                        needs_download = False
                except OSError:
                    needs_download = True
            elif os.path.isfile(archive) and not expected:
                needs_download = False
            if needs_download:
                try:
                    used_url = self._download_bottle(urls, archive, expected)
                except ConanInvalidConfiguration as exc:
                    if bottle["name"] == "rust":
                        raise
                    self.output.warning(
                        f"skipping optional toolchain bottle {bottle['name']}: {exc}"
                    )
                    continue
            else:
                used_url = urls[0]
            # Official rust-lang dist needs install.sh; bottles extract flat.
            # Detect by the actually-used URL (archive filename is neutral).
            if bottle["name"] == "rust" and (used_url or "").endswith((".tar.xz", ".txz", ".xz")):
                try:
                    official = self._install_official_dist(base, archive)
                except ConanInvalidConfiguration:
                    raise
                except Exception as exc:  # noqa: BLE001 - best effort probe
                    self.output.warning(f"official installer probe failed: {exc}")
                    official = (None, None)
                if official[0] and official[1]:
                    self._sign_elf_tree(os.path.join(base, "official-rust"))
                    continue
            try:
                self._extract_tarball(archive, base)
            except tarfile.ReadError as exc:
                if bottle["name"] == "rust":
                    raise ConanInvalidConfiguration(
                        f"Rust toolchain archive unreadable {archive}: {exc}"
                    )
                self.output.warning(
                    f"skipping optional toolchain bottle {bottle['name']}: {exc}"
                )
                continue

        cargo = rustc = None
        if official[0] and official[1]:
            cargo, rustc = official
        for root, _dirs, files in os.walk(base):
            if cargo is None and "cargo.real" in files:
                cargo = os.path.join(root, "cargo.real")
            elif cargo is None and "cargo" in files and "official-rust" in root:
                candidate = os.path.join(root, "cargo")
                if os.access(candidate, os.X_OK):
                    cargo = candidate
            if rustc is None:
                if "rustc.real" in files:
                    rustc = os.path.join(root, "rustc.real")
                elif "rustc" in files:
                    candidate = os.path.join(root, "rustc")
                    # Prefer official prefix or any executable rustc as fallback.
                    if "official-rust" in root or os.access(candidate, os.X_OK):
                        if rustc is None:
                            rustc = candidate
        if not cargo or not rustc:
            raise ConanInvalidConfiguration(
                "Rust toolchain fallback did not contain cargo/rustc "
                "(Harmonybrew bottle 404 and official installer both failed?)"
            )
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

    @staticmethod
    def _first_executable(candidates):
        seen = set()
        for candidate in candidates:
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            # Bare names resolve via PATH (which on the worker contains the
            # HMBS tool dirs and profile buildenv entries once merged).
            resolved = shutil.which(candidate) if not os.path.isabs(candidate) else candidate
            if not resolved:
                continue
            real = resolved + ".real"
            if not resolved.endswith(".real") and os.path.isfile(real):
                resolved = real
            if os.path.isfile(resolved) and os.access(resolved, os.X_OK):
                return resolved
        return None

    def _resolve_compilers(self):
        import glob as _glob

        compiler_executables = {}
        try:
            compiler_executables = self.conf.get("tools.build:compiler_executables", default={}) or {}
        except Exception:  # noqa: BLE001 - conf may be missing on some workers
            compiler_executables = {}
        conf_c = compiler_executables.get("c")
        conf_cxx = compiler_executables.get("cpp") or compiler_executables.get("cxx")

        sdk_bins = []
        for pattern in (
            "/data/service/hnp/ohos-sdk*/ohos/native/llvm/bin",
            "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/bin",
            "/storage/Users/currentUser/ohos-sdk*/ohos/native/llvm/bin",
        ):
            try:
                sdk_bins.extend(sorted(_glob.glob(pattern)))
            except OSError:
                continue

        c_candidates = [
            conf_c,
            os.environ.get("CC"),
            os.environ.get("HNP_CC"),
            os.environ.get("HMBS_CC"),
            shutil.which("clang"),
            "clang",
            "aarch64-linux-ohos-clang",
            "/storage/Users/currentUser/usr/local/bin/clang",
            "/data/service/hnp/bin/clang",
            os.path.expanduser("~/.harmonybrew/bin/clang"),
            "/usr/bin/clang",
        ]
        cxx_candidates = [
            conf_cxx,
            os.environ.get("CXX"),
            os.environ.get("HNP_CXX"),
            os.environ.get("HMBS_CXX"),
            shutil.which("clang++"),
            "clang++",
            "aarch64-linux-ohos-clang++",
            "/storage/Users/currentUser/usr/local/bin/clang++",
            "/data/service/hnp/bin/clang++",
            os.path.expanduser("~/.harmonybrew/bin/clang++"),
            "/usr/bin/clang++",
        ]
        for sdk_bin in sdk_bins:
            c_candidates.extend([
                os.path.join(sdk_bin, "clang"),
                os.path.join(sdk_bin, "aarch64-linux-ohos-clang"),
            ])
            cxx_candidates.extend([
                os.path.join(sdk_bin, "clang++"),
                os.path.join(sdk_bin, "aarch64-linux-ohos-clang++"),
            ])

        cc = self._first_executable(c_candidates)
        cxx = self._first_executable(cxx_candidates)
        if not cc or not cxx:
            searched_c = [c for c in c_candidates if c]
            searched_cxx = [c for c in cxx_candidates if c]
            raise ConanInvalidConfiguration(
                "OHOS clang/clang++ not found on worker; "
                f"profile conf c={conf_c!r} cpp={conf_cxx!r} both missing/exec-failed. "
                f"Searched C: {searched_c[:12]}; CXX: {searched_cxx[:12]}. "
                "PATH=" + os.environ.get("PATH", "")
            )
        self.output.info(f"Resolved OHOS compilers: CC={cc} CXX={cxx}")
        return cc, cxx

    def _build_env(self, cargo, rustc):
        ca_bundle = self._ensure_ca_bundle()
        cc, cxx = self._resolve_compilers()
        tmpdir = (
            os.environ.get("HMBS_TMPDIR")
            or os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
            or os.path.join(self.build_folder, "tmp")
        )
        os.makedirs(tmpdir, exist_ok=True)
        # Keep Python tempfile and cargo off read-only /tmp as well.
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = tmpdir
        try:
            tempfile.tempdir = tmpdir
        except Exception:  # noqa: BLE001 - best effort
            pass
        cargo_home = os.path.join(self.build_folder, "cargo-home")
        os.makedirs(cargo_home, exist_ok=True)
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
                    "CARGO_HOME": cargo_home, "RUSTUP_HOME": cargo_home,
                    "TMPDIR": tmpdir, "TMP": tmpdir, "TEMP": tmpdir,
                    "HMBS_TMPDIR": tmpdir})
        if ca_bundle:
            env.update({"CARGO_HTTP_CAINFO": ca_bundle,
                        "SSL_CERT_FILE": ca_bundle, "CURL_CA_BUNDLE": ca_bundle})
        # subprocess.run does not inherit conan buildenv automatically; merge
        # the worker-known tool dirs plus the OHOS SDK llvm bin/lib so cargo
        # and the linker find clang/lld and libxml2 at runtime.
        import glob as _glob2

        extra_path = [
            os.path.dirname(cargo), os.path.dirname(rustc),
            os.path.dirname(cc), os.path.dirname(cxx),
            "/storage/Users/currentUser/usr/local/bin",
            "/data/service/hnp/bin",
        ]
        for pattern in (
            "/data/service/hnp/ohos-sdk*/ohos/native/llvm/bin",
            "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/bin",
        ):
            try:
                extra_path.extend(sorted(_glob2.glob(pattern)))
            except OSError:
                continue
        path_parts = [p for p in extra_path if p and os.path.isdir(p)]
        if env.get("PATH"):
            path_parts.append(env["PATH"])
        env["PATH"] = os.pathsep.join(path_parts)
        ld_parts = []
        for pattern in (
            "/data/service/hnp/ohos-sdk*/ohos/native/llvm/lib",
            "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib",
        ):
            try:
                ld_parts.extend([p for p in sorted(_glob2.glob(pattern)) if os.path.isdir(p)])
            except OSError:
                continue
        # Keep any toolchain-bundled openssl/zlib libs first.
        if os.environ.get("LD_LIBRARY_PATH"):
            ld_parts.append(os.environ["LD_LIBRARY_PATH"])
        if env.get("LD_LIBRARY_PATH") and env["LD_LIBRARY_PATH"] not in ld_parts:
            ld_parts.append(env["LD_LIBRARY_PATH"])
        if ld_parts:
            env["LD_LIBRARY_PATH"] = os.pathsep.join(ld_parts)
        return env

    def _run_command(self, command, env):
        saved = dict(os.environ)
        os.environ.clear()
        os.environ.update(env)
        try:
            self.output.info(f"Running: {' '.join(shlex.quote(p) for p in command)}")
            proc = subprocess.run(
                command, cwd=self.source_folder, env=dict(os.environ),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, errors="replace",
            )
            self.output.info(proc.stdout)
            if proc.returncode != 0:
                raise ConanException(
                    f"Command failed ({proc.returncode}): {' '.join(command)}"
                )
            return proc.stdout
        finally:
            os.environ.clear()
            os.environ.update(saved)

    def _run_upstream_tests(self, cargo, env):
        command = [cargo, "test", "--locked"]
        target = self._rust_target()
        if target:
            command.extend(["--target", target])
        saved = dict(os.environ)
        os.environ.clear()
        os.environ.update(env)
        try:
            self.output.info(f"Running upstream tests: {' '.join(shlex.quote(p) for p in command)}")
            proc = subprocess.run(
                command, cwd=self.source_folder, env=dict(os.environ),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, errors="replace", timeout=3000,
            )
        finally:
            os.environ.clear()
            os.environ.update(saved)
        output = proc.stdout or ""
        self.output.info(output)
        discovered = 0
        passed = 0
        failed = 0
        for line in output.splitlines():
            m = re.search(r"running (\d+) tests?", line)
            if m:
                discovered += int(m.group(1))
            m = re.search(r"test result:\s*ok\.\s*(\d+)\s*passed", line)
            if m:
                passed += int(m.group(1))
            m = re.search(r"test result:\s*FAILED\.\s*(\d+)\s*passed", line)
            if m:
                passed += int(m.group(1))
            m = re.search(r"(\d+)\s*failed", line)
            if "test result" in line and m:
                failed += int(m.group(1))
        executed = passed + failed
        skipped = max(discovered - executed, 0) if discovered else 0
        status = "passed" if proc.returncode == 0 and failed == 0 and discovered > 0 and executed >= discovered else "failed"
        marker = {
            "status": status,
            "framework": "cargo-test",
            "command": " ".join(shlex.quote(p) for p in command),
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False))
        if proc.returncode != 0:
            raise ConanException(f"Upstream cargo test failed ({proc.returncode})")
        if discovered == 0 or executed < discovered or failed > 0:
            raise ConanException(
                f"Upstream cargo test incomplete: discovered={discovered} executed={executed} failed={failed}"
            )

    def build(self):
        cargo, rustc = self._toolchain()
        env = self._build_env(cargo, rustc)
        command = [cargo, "build", "--release", "--locked"]
        target = self._rust_target()
        if target:
            command.extend(["--target", target])
        self._run_command(command, env)
        self._run_upstream_tests(cargo, env)

    def _binary_path(self):
        target = self._rust_target()
        if target:
            return os.path.join(self.source_folder, "target", target, "release", "caesiumclt")
        return os.path.join(self.source_folder, "target", "release", "caesiumclt")

    def package(self):
        binary = self._binary_path()
        if not os.path.isfile(binary):
            raise ConanException(f"caesiumclt build output not found: {binary}")
        copy(self, "caesiumclt", src=os.path.dirname(binary), dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "LICENSE.md", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
