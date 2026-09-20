#!/usr/bin/env python3
"""Conan recipe — libdovi 3.4.0 (Dolby Vision metadata, Rust + cargo-c).

Upstream: https://github.com/quietvoid/dovi_tool/tree/main/dolby_vision
Crate dolby_vision 3.4.0, C-API built via cargo-c (cbuild/cinstall).

Layout in source archive (dovi_tool-libdovi-3.4.0):
  dolby_vision/   # crate + Cargo.lock + cbindgen.toml
  assets/         # test fixtures referenced by cargo tests / C examples

Build: cargo cbuild --release --locked --all-features in dolby_vision/,
install via cargo cinstall --prefix=/ --destdir=<package_folder>.
Upstream tests: cargo test --release --locked --all-features in dolby_vision/.
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
from conan.tools.env import Environment
from conan.tools.files import copy, get, export_conandata_patches


class LibdoviConan(ConanFile):
    name = "libdovi"
    version = "3.4.0"
    description = "Library to read and write Dolby Vision metadata (C-API)"
    license = "MIT"
    homepage = "https://github.com/quietvoid/dovi_tool/tree/main/dolby_vision"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("dolby-vision", "dovi", "hdr", "metadata")

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libdovi is only supported on Linux/OHOS, got {self.settings.os}"
            )

    def layout(self):
        self.folders.source = "src"
        self.folders.build = "build"

    def _pick_writable_tmpdir(self, fallback_sub=".hmbs-tmp"):
        """Probe a writable tmpdir (HMBS readonly_tmp guard).

        Prefer HMBS-injected TMPDIR/TMP/TEMP only after a real write
        probe; fall back to a build-folder private dir (conan guarantees
        it writable). makedirs success alone does not prove writability.
        """
        cands = []
        for key in ("HMBS_TMPDIR", "TMPDIR", "TMP", "TEMP"):
            try:
                val = os.environ.get(key)
            except Exception:
                val = None
            if val and val not in cands:
                cands.append(val)
        try:
            cands.append(os.path.join(self.build_folder, fallback_sub))
        except Exception:
            pass
        for cand in cands:
            if not cand:
                continue
            try:
                os.makedirs(cand, exist_ok=True)
                probe = os.path.join(cand, ".tmp-write-probe")
                with open(probe, "w", encoding="utf-8") as handle:
                    handle.write("ok")
                try:
                    os.unlink(probe)
                except OSError:
                    pass
                return cand
            except OSError:
                continue
        return cands[0] if cands else None

    def generate(self):
        _tmp = self._pick_writable_tmpdir()
        shell_env = Environment()
        shell_env.define("SHELL", "/bin/sh")
        if _tmp:
            shell_env.define("TMPDIR", _tmp)
            shell_env.define("TMP", _tmp)
            shell_env.define("TEMP", _tmp)
        shell_env.vars(self).save_script("hmbs_shell")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ---- Rust toolchain helpers (proven pattern from bulletty/0.2.2) ----
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
            shutil.which(name),
            os.environ.get(name.upper()),
            os.environ.get(f"HNP_{name.upper()}"),
            f"/data/service/hnp/bin/{name}",
            os.path.expanduser(f"~/.harmonybrew/bin/{name}"),
            os.path.expanduser(f"~/.cargo/bin/{name}"),
            f"/usr/bin/{name}",
            f"/usr/local/bin/{name}",
            os.path.expanduser(f"~/.local/bin/{name}"),
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
            "/etc/ssl/certs/cacert.pem",
            "/etc/ssl/cert.pem",
        ]
        for root in roots:
            if not root or not os.path.isdir(root):
                continue
            for directory, _dirs, files in os.walk(root):
                for fname in ("cert.pem", "cacert.pem"):
                    if fname in files:
                        candidates.append(os.path.join(directory, fname))
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
        last_exc = None
        for attempt in range(3):
            try:
                req = urllib.request.Request(url, headers={
                    "User-Agent": "curl/8.5.0",
                    "Accept": "*/*",
                })
                ca_file = os.environ.get("SSL_CERT_FILE")
                if ca_file and os.path.isfile(ca_file):
                    try:
                        ctx = ssl.create_default_context(cafile=ca_file)
                    except Exception:
                        ctx = ssl.create_default_context()
                else:
                    ctx = ssl._create_unverified_context()
                try:
                    with urllib.request.urlopen(req, context=ctx, timeout=600) as response:
                        with open(destination, "wb") as handle:
                            shutil.copyfileobj(response, handle)
                except (urllib.error.URLError, ssl.SSLError) as exc:
                    if "CERTIFICATE_VERIFY_FAILED" in str(exc):
                        ctx2 = ssl._create_unverified_context()
                        with urllib.request.urlopen(req, context=ctx2, timeout=600) as response:
                            with open(destination, "wb") as handle:
                                shutil.copyfileobj(response, handle)
                    else:
                        raise
                actual = self._sha256(destination)
                if actual != expected_sha256:
                    try:
                        os.remove(destination)
                    except OSError:
                        pass
                    raise ConanInvalidConfiguration(
                        f"Rust toolchain bottle checksum mismatch for {url}: "
                        f"expected {expected_sha256}, got {actual}"
                    )
                return
            except Exception as exc:
                last_exc = exc
                self.output.warning(f"download failed for {url} attempt {attempt + 1}/3: {exc}")
                if attempt < 2:
                    import time
                    time.sleep(1 + attempt)
        if last_exc is not None:
            raise last_exc
        raise ConanInvalidConfiguration(f"failed to download {url}")

    @staticmethod
    def _extract_tarball(archive, destination):
        root = os.path.realpath(destination)
        with tarfile.open(archive, "r:gz") as handle:
            for member in handle.getmembers():
                target = os.path.realpath(os.path.join(destination, member.name))
                if target != root and not target.startswith(root + os.sep):
                    raise ConanInvalidConfiguration(
                        f"unsafe path in Rust toolchain bottle: {member.name}"
                    )
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
            try:
                self._download_bottle(ca_bottle["url"], archive, ca_bottle["sha256"])
            except Exception as exc:
                if ca_bottle.get("optional") and self._is_not_found(exc):
                    self.output.warning(
                        "optional ca-certificates bottle unavailable (404), "
                        "continuing without bottled CA: %s" % exc
                    )
                    return self._set_ca_bundle()
                raise
        self._extract_tarball(archive, base)
        ca_bundle = self._set_ca_bundle(base)
        if not ca_bundle:
            raise ConanInvalidConfiguration(
                "Harmonybrew CA certificate bottle did not contain cert.pem or cacert.pem"
            )
        return ca_bundle

    @staticmethod
    def _repair_wrappers(bin_dir):
        for fname in sorted(os.listdir(bin_dir)):
            if fname.endswith(".real"):
                continue
            wrapper = os.path.join(bin_dir, fname)
            real = os.path.join(bin_dir, fname + ".real")
            if os.path.islink(wrapper) or not os.path.isfile(wrapper) or not os.path.isfile(real):
                continue
            with open(wrapper, "rb") as handle:
                if not handle.read(512).startswith(b"#!"):
                    continue
            with open(wrapper, "w", encoding="utf-8") as handle:
                handle.write('#!/bin/sh\nexec %s "$@"\n' % shlex.quote(real))

    @staticmethod
    def _collect_pkg_config_dirs(base):
        pkg_dirs = []
        for root, _dirs, files in os.walk(base):
            if any(name.endswith(".pc") for name in files):
                pkg_dirs.append(root)
        seen = set()
        uniq = []
        for d in pkg_dirs:
            if d not in seen:
                seen.add(d)
                uniq.append(d)
        return uniq

    @staticmethod
    def _find_openssl_prefix(base):
        for root, _dirs, files in os.walk(base):
            if "openssl.pc" in files:
                lib_dir = os.path.dirname(root)
                prefix = os.path.dirname(lib_dir)
                if os.path.isdir(os.path.join(prefix, "include", "openssl")):
                    return prefix
                if os.path.isdir(os.path.join(prefix, "include")):
                    return prefix
                return prefix
        for root, _dirs, files in os.walk(base):
            if "opensslv.h" in files and "openssl" in root:
                maybe_prefix = os.path.dirname(os.path.dirname(root))
                if os.path.isdir(maybe_prefix):
                    return maybe_prefix
        return None

    @staticmethod
    def _find_pkg_config_bin():
        for cand in (
            shutil.which("pkg-config"),
            os.environ.get("PKG_CONFIG"),
            os.environ.get("HMBS_PKG_CONFIG"),
            "/storage/Users/currentUser/usr/local/bin/pkg-config",
            os.path.expanduser("~/.harmonybrew/bin/pkg-config"),
            "/usr/bin/pkg-config",
            "/usr/local/bin/pkg-config",
        ):
            if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
                return cand
        return None

    @staticmethod
    def _is_not_found(exc):
        # Harmonybrew prunes old bottles; a 404 for an *optional* bottle
        # must degrade to a warning, not a build failure (CI #50534 hit
        # zlib-ng-compat-2.3.3_1 404 after rust-1.98.1 itself downloaded fine).
        if getattr(exc, "code", None) == 404:
            return True
        text = str(exc)
        return "404" in text and ("Not Found" in text or "HTTP Error" in text)

    def _bootstrap_rust_toolchain(self):
        if str(self.settings.os) != "OHOS":
            return None, None
        base = os.path.join(self.build_folder, "rust-toolchain")
        os.makedirs(base, exist_ok=True)
        for bottle in self.conan_data.get("rust_toolchain", []):
            if bottle["name"] == "ca-certificates":
                continue
            archive = os.path.join(base, bottle["name"] + ".tar.gz")
            if os.path.isfile(archive) and self._sha256(archive) == bottle["sha256"]:
                self._extract_tarball(archive, base)
                continue
            try:
                self._download_bottle(bottle["url"], archive, bottle["sha256"])
            except Exception as exc:
                if bottle.get("optional") and self._is_not_found(exc):
                    self.output.warning(
                        "optional bottle %s unavailable (404), continuing without it: %s"
                        % (bottle["name"], exc)
                    )
                    try:
                        if os.path.isfile(archive):
                            os.remove(archive)
                    except OSError:
                        pass
                    continue
                raise
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
        if str(self.settings.os) == "OHOS":
            for system_lib in ("/system/lib64", "/data/storage/el1/bundle/libs/arm64"):
                if os.path.isdir(system_lib) and system_lib not in lib_dirs:
                    lib_dirs.append(system_lib)
        if lib_dirs:
            previous = os.environ.get("LD_LIBRARY_PATH")
            os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
                lib_dirs + ([previous] if previous else [])
            )
        # Smoke-test the bootstrapped cargo while an optional bottle is
        # missing: a loader failure (e.g. libz.so gone with the skipped
        # bottle) must surface here with a clear message, not later as a
        # cryptic cargo-install error.
        try:
            probe = subprocess.run(
                [cargo, "--version"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                timeout=120,
            )
            if probe.returncode != 0:
                raise ConanInvalidConfiguration(
                    "bootstrapped cargo cannot run (missing optional bottle "
                    "runtime library?): %s" % ((probe.stdout or "").strip()[-500:])
                )
            self.output.info("bootstrapped %s" % (probe.stdout or "").strip())
        except ConanInvalidConfiguration:
            raise
        except Exception as exc:
            raise ConanInvalidConfiguration(
                "bootstrapped cargo cannot run: %s" % exc
            )
        # Provide pkg-config + OpenSSL location for openssl-sys (cargo-c build).
        # Without these `cargo install cargo-c` fails with
        # "Could not find directory of OpenSSL installation" + pkg-config error.
        pkg_dirs = self._collect_pkg_config_dirs(base)
        if pkg_dirs:
            previous = os.environ.get("PKG_CONFIG_PATH")
            os.environ["PKG_CONFIG_PATH"] = os.pathsep.join(
                pkg_dirs + ([previous] if previous else [])
            )
            self.output.info("using bottled PKG_CONFIG_PATH=%s" % os.environ["PKG_CONFIG_PATH"])
        openssl_prefix = self._find_openssl_prefix(base)
        if openssl_prefix:
            os.environ["OPENSSL_DIR"] = openssl_prefix
            os.environ.setdefault("OPENSSL_STATIC", "0")
            self.output.info("using bottled OpenSSL prefix %s" % openssl_prefix)
        pkg_bin = self._find_pkg_config_bin()
        if pkg_bin:
            os.environ["PKG_CONFIG"] = pkg_bin
            self.output.info("using pkg-config %s" % pkg_bin)
        else:
            # No pkg-config binary on the runner: let openssl-sys use
            # OPENSSL_DIR directly instead of failing on missing pkg-config.
            os.environ["OPENSSL_NO_PKG_CONFIG"] = "1"
            self.output.info("pkg-config not found; set OPENSSL_NO_PKG_CONFIG=1")
        self._set_ca_bundle(base)
        return cargo, rustc

    def _toolchain(self):
        cargo = self._find_tool("cargo")
        rustc = self._find_tool("rustc")
        if (not cargo or not rustc) and str(self.settings.os) == "OHOS":
            cargo, rustc = self._bootstrap_rust_toolchain()
        if not cargo or not rustc:
            raise ConanInvalidConfiguration(
                "Rust/Cargo toolchain is required; provision cargo/rustc "
                "or use the OHOS Harmonybrew fallback"
            )
        return cargo, rustc

    def _select_clang(self):
        import glob as _glob
        compilers = self.conf.get("tools.build:compiler_executables", default={}) or {}
        for key in ("c", "cc"):
            cand = compilers.get(key)
            if cand and os.path.basename(cand).startswith("clang") and os.path.isfile(cand):
                self.output.info("OHOS clang from profile conf [%s]: %s" % (key, cand))
                return cand
        for envkey in ("CC", "HMBS_CC", "OHOS_SDK_ROOT", "OHOS_NDK_HOME"):
            base = os.environ.get(envkey, "")
            if not base:
                continue
            # Only accept files whose name is a clang driver, never a
            # generic shim (HMBS_INSTALL points at an `install` shim).
            if os.path.isfile(base):
                if os.path.basename(base).startswith("clang") and os.access(base, os.X_OK):
                    self.output.info("OHOS clang via $%s: %s" % (envkey, base))
                    return base
                continue
            if not os.path.isdir(base):
                continue
            for rel in ("bin/clang", "ohos/native/llvm/bin/clang",
                        "native/llvm/bin/clang"):
                cand = os.path.join(base, rel)
                if os.path.isfile(cand):
                    self.output.info("OHOS clang via $%s: %s" % (envkey, cand))
                    return cand
        for tool in ("clang", "aarch64-unknown-linux-ohos-clang"):
            found = shutil.which(tool)
            if found and os.path.isfile(found):
                self.output.info("OHOS clang via PATH [%s]: %s" % (tool, found))
                return found
        # SDK version may differ from the pinned 26.0.0.18; glob it.
        for pattern in (
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/bin/clang",
            "/data/service/hnp/ohos-sdk*/ohos/native/llvm/bin/clang",
            "/data/service/hnp/*/ohos/native/llvm/bin/clang",
            "/data/service/hnp/native/llvm/bin/clang",
            "/opt/ohos-sdk*/ohos/native/llvm/bin/clang",
        ):
            for cand in sorted(_glob.glob(pattern)):
                if os.path.isfile(cand):
                    self.output.info("OHOS clang via SDK glob [%s]: %s" % (pattern, cand))
                    return cand
        for cand in (
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/clang",
            "/data/service/hnp/bin/clang",
            "/storage/Users/currentUser/usr/local/bin/clang",
            os.path.expanduser("~/.harmonybrew/bin/clang"),
            "/usr/bin/clang",
            "/usr/local/bin/clang",
        ):
            if cand and os.path.basename(cand).startswith("clang") and os.path.isfile(cand):
                self.output.info("OHOS clang via well-known path: %s" % cand)
                return cand
        raise ConanInvalidConfiguration(
            "OHOS clang not found; checked profile conf tools.build:compiler_executables, "
            "$CC, PATH clang, and SDK well-known paths"
        )

    def _select_clangxx(self, cc):
        compilers = self.conf.get("tools.build:compiler_executables", default={}) or {}
        for key in ("cpp", "cxx"):
            cand = compilers.get(key)
            if cand and os.path.isfile(cand):
                return cand
        for envkey in ("CXX", "HMBS_CXX"):
            cand = os.environ.get(envkey, "")
            if cand and os.path.isfile(cand):
                return cand
        bindir = os.path.dirname(cc) if cc else ""
        if bindir:
            cand = os.path.join(bindir, "clang++")
            if os.path.isfile(cand):
                return cand
        found = shutil.which("clang++")
        if found and os.path.isfile(found):
            return found
        if cc and cc.endswith("clang") and os.path.isfile(cc + "++"):
            return cc + "++"
        return cc

    def _cargo_env(self, cargo, rustc):
        ca_bundle = self._ensure_ca_bundle()
        cc = self._select_clang()
        cxx = self._select_clangxx(cc)
        # readonly_tmp guard: HMBS runners mount /tmp read-only; probe
        # writability instead of trusting env blindly, fall back to a
        # build-folder private dir (conan guarantees it writable).
        tmpdir = self._pick_writable_tmpdir(fallback_sub="tmp")
        if not tmpdir:
            tmpdir = os.path.join(self.build_folder, "tmp")
            os.makedirs(tmpdir, exist_ok=True)
        # Keep all cargo traffic (registry, target, temp) inside the
        # writable build folder so nothing touches the read-only /tmp.
        cargo_home = os.path.join(self.build_folder, "cargo-home")
        cargo_target = os.path.join(self.build_folder, "cargo-target")
        for _d in (cargo_home, os.path.join(cargo_home, "bin"), cargo_target):
            try:
                os.makedirs(_d, exist_ok=True)
            except OSError:
                pass
        crate_dir = os.path.join(self.source_folder, "dolby_vision")
        cargo_dir = os.path.join(crate_dir, ".cargo")
        os.makedirs(cargo_dir, exist_ok=True)
        target = self._rust_target()
        config = (
            '[source.crates-io]\nreplace-with = "rsproxy-sparse"\n'
            '[source.rsproxy-sparse]\nregistry = "sparse+https://rsproxy.cn/index/"\n'
            '[net]\nretry = 10\n[http]\ntimeout = 600\nlow-speed-limit = 1\n'
        )
        if ca_bundle:
            config += f'cainfo = "{ca_bundle}"\n'
        if target and str(self.settings.os) == "OHOS":
            config += f'\n[target.{target}]\nlinker = "{cc}"\n'
        with open(os.path.join(cargo_dir, "config.toml"), "w", encoding="utf-8") as handle:
            handle.write(config)
        env = dict(os.environ)
        env.update({
            "CARGO": cargo,
            "RUSTC": rustc,
            "CC": cc,
            "CXX": cxx,
            "RUSTFLAGS": f"-C linker={cc}",
            "CARGO_NET_RETRY": "10",
            "CARGO_HTTP_TIMEOUT": "600",
            "CARGO_BUILD_JOBS": "1",
            "CARGO_HOME": cargo_home,
            "CARGO_TARGET_DIR": cargo_target,
            "TMPDIR": tmpdir,
            "TMP": tmpdir,
            "TEMP": tmpdir,
        })
        if ca_bundle:
            env.update({
                "CARGO_HTTP_CAINFO": ca_bundle,
                "SSL_CERT_FILE": ca_bundle,
                "CURL_CA_BUNDLE": ca_bundle,
            })
        env["PATH"] = os.pathsep.join(
            [os.path.dirname(cargo), os.path.dirname(rustc), env.get("PATH", "")]
        )
        # Re-derive bottled OpenSSL/pkg-config locations so the cargo-c
        # build (cargo install cargo-c -> openssl-sys) inherits them even
        # when cargo/rustc came from PATH instead of the bottle fallback.
        try:
            _bt_base = os.path.join(self.build_folder, "rust-toolchain")
            if os.path.isdir(_bt_base):
                _pkg_dirs = self._collect_pkg_config_dirs(_bt_base)
                if _pkg_dirs:
                    _prev = env.get("PKG_CONFIG_PATH", "")
                    env["PKG_CONFIG_PATH"] = os.pathsep.join(
                        _pkg_dirs + ([_prev] if _prev else [])
                    )
                _ossl = self._find_openssl_prefix(_bt_base)
                if _ossl and not env.get("OPENSSL_DIR"):
                    env["OPENSSL_DIR"] = _ossl
                    env.setdefault("OPENSSL_STATIC", "0")
                if not env.get("PKG_CONFIG"):
                    _pkg_bin = self._find_pkg_config_bin()
                    if _pkg_bin:
                        env["PKG_CONFIG"] = _pkg_bin
                if not env.get("PKG_CONFIG") and env.get("OPENSSL_DIR"):
                    env["OPENSSL_NO_PKG_CONFIG"] = "1"
                if env.get("LD_LIBRARY_PATH") and "LD_LIBRARY_PATH" not in env:
                    pass
            # Propagate os.environ values set by _bootstrap_rust_toolchain.
            for _k in ("OPENSSL_DIR", "OPENSSL_STATIC", "OPENSSL_NO_PKG_CONFIG",
                       "PKG_CONFIG", "PKG_CONFIG_PATH", "LD_LIBRARY_PATH"):
                _v = os.environ.get(_k)
                if _v and not env.get(_k):
                    env[_k] = _v
        except Exception:
            pass
        env.setdefault("PKG_CONFIG_ALLOW_SYSTEM_LIBS", "1")
        env.setdefault("PKG_CONFIG_ALLOW_SYSTEM_CFLAGS", "1")
        return env, crate_dir, target, cc

    def _cargo_c_bottle_entry(self):
        # Prebuilt cargo-c (musl static) avoids `cargo install cargo-c`
        # from source, which compiles ~200 crates (gix/...) and is killed
        # on the true machine (SSH drop during "Compiling gix-filter").
        data = self.conan_data.get("cargo_c", {}) or {}
        arch = str(self.settings.arch)
        if arch in ("armv8", "armv8.3", "arm64", "aarch64"):
            key = "aarch64"
        elif arch in ("x86_64",):
            key = "x86_64"
        else:
            return None
        entry = data.get(key)
        if not isinstance(entry, dict):
            return None
        if not entry.get("url") or not entry.get("sha256"):
            return None
        return entry

    def _install_cargo_c_prebuilt(self, cargo, env, crate_dir):
        entry = self._cargo_c_bottle_entry()
        if entry is None:
            return False
        url = entry["url"]
        sha = entry["sha256"]
        dest_dir = os.path.join(self.build_folder, "cargo-c")
        try:
            os.makedirs(dest_dir, exist_ok=True)
        except OSError:
            pass
        archive = os.path.join(dest_dir, "cargo-c.tar.gz")
        try:
            if not (os.path.isfile(archive) and self._sha256(archive) == sha):
                self.output.info("downloading prebuilt cargo-c %s" % url)
                self._download_bottle(url, archive, sha)
            self._extract_tarball(archive, dest_dir)
        except Exception as exc:
            self.output.warning(
                "prebuilt cargo-c download/extract failed, "
                "falling back to source install: %s" % exc
            )
            return False
        for _name in ("cargo-cbuild", "cargo-cinstall", "cargo-capi", "cargo-ctest"):
            _p = os.path.join(dest_dir, _name)
            try:
                if os.path.isfile(_p) and not os.access(_p, os.X_OK):
                    os.chmod(_p, 0o755)
            except OSError as exc:
                self.output.warning("chmod %s failed: %s" % (_p, exc))
        env["PATH"] = os.pathsep.join([dest_dir, env.get("PATH", "")])
        # Verify the prebuilt payload before accepting it.
        try:
            probe = subprocess.run(
                [os.path.join(dest_dir, "cargo-cbuild"), "--version"],
                cwd=crate_dir, env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, timeout=120,
            )
            out = (probe.stdout or "").strip()
            self.output.info(
                "prebuilt cargo-c direct verify exit=%s: %s"
                % (probe.returncode, out[-1000:] or "<empty>")
            )
            if probe.returncode != 0:
                return False
            probe2 = subprocess.run(
                [cargo, "cbuild", "--version"],
                cwd=crate_dir, env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, timeout=120,
            )
            out2 = (probe2.stdout or "").strip()
            self.output.info(
                "prebuilt cargo-c cargo-subcommand verify exit=%s: %s"
                % (probe2.returncode, out2[-1000:] or "<empty>")
            )
            if probe2.returncode == 0:
                self.output.info("cargo-c available (prebuilt): %s" % out2)
                return True
            return False
        except Exception as exc:
            self.output.warning("prebuilt cargo-c verify raised: %s" % exc)
            return False

    def _ensure_cbindgen(self, cargo, env, crate_dir):
        # cbindgen (~20 crates) builds in ~1 min vs cargo-c (~200 crates,
        # 15+ min then SSH drop). Used only for the manual C-API fallback.
        cargo_home = env.get("CARGO_HOME") or os.path.join(self.build_folder, "cargo-home")
        bin_dir = os.path.join(cargo_home, "bin")
        cbindgen_bin = os.path.join(bin_dir, "cbindgen")
        try:
            probe = subprocess.run(
                [cbindgen_bin, "--version"],
                cwd=crate_dir, env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, timeout=120,
            )
            if probe.returncode == 0:
                self.output.info("cbindgen available: %s" % (probe.stdout or "").strip())
                return cbindgen_bin
        except Exception:
            pass
        try:
            os.makedirs(bin_dir, exist_ok=True)
        except OSError:
            pass
        target_dir = os.path.join(self.build_folder, "cbindgen-target")
        try:
            os.makedirs(target_dir, exist_ok=True)
        except OSError:
            pass
        install_env = dict(env)
        install_env["CARGO_HOME"] = cargo_home
        install_env["CARGO_TARGET_DIR"] = target_dir
        _writable = self._pick_writable_tmpdir(fallback_sub="tmp")
        if _writable:
            install_env["TMPDIR"] = _writable
            install_env["TMP"] = _writable
            install_env["TEMP"] = _writable
        install_env["PATH"] = os.pathsep.join(
            [bin_dir, os.path.dirname(cargo), env.get("PATH", "")]
        )
        cmd = [cargo, "install", "cbindgen", "--locked",
               "--root", cargo_home, "--target-dir", target_dir]
        self.output.info("RUN: " + " ".join(shlex.quote(p) for p in cmd))
        proc = subprocess.run(cmd, cwd=crate_dir, env=install_env, text=True)
        if proc.returncode != 0:
            self.output.warning("cargo install cbindgen failed (exit=%s)" % proc.returncode)
            return None
        try:
            if os.path.isfile(cbindgen_bin) and not os.access(cbindgen_bin, os.X_OK):
                os.chmod(cbindgen_bin, 0o755)
        except OSError:
            pass
        try:
            probe = subprocess.run(
                [cbindgen_bin, "--version"],
                cwd=crate_dir, env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, timeout=120,
            )
            if probe.returncode == 0:
                self.output.info("cbindgen available: %s" % (probe.stdout or "").strip())
                return cbindgen_bin
        except Exception as exc:
            self.output.warning("cbindgen verify raised: %s" % exc)
        return None

    def _build_manual_capi(self, env, crate_dir, target):
        # cargo-c-free C-API build. Upstream gates the C API behind
        # `#[cfg(any(cargo_c, feature = "capi"))]` (src/lib.rs) and the
        # recipe always passes --all-features, so plain `cargo rustc`
        # includes every C symbol the consumer test uses; `--cfg cargo_c`
        # is passed as well for exact parity with the cargo-c build.
        # Mirrors cargo-c metadata: lib name "dovi", header
        # "include/libdovi/rpu_parser.h", pkg-config file "dovi.pc".
        libtype = "cdylib" if self.options.shared else "staticlib"
        build_env = dict(env)
        build_env["RUSTFLAGS"] = (env.get("RUSTFLAGS", "") + " -Cpanic=abort").strip()
        rustc_cmd = [
            env.get("CARGO") or "cargo", "rustc",
            "--release", "--locked", "--all-features",
            "--crate-type=%s" % libtype,
        ]
        if target:
            rustc_cmd.extend(["--target", target])
        rustc_cmd.extend(["--", "--cfg", "cargo_c"])
        self.output.info("RUN: " + " ".join(shlex.quote(p) for p in rustc_cmd))
        proc = subprocess.run(rustc_cmd, cwd=crate_dir, env=build_env, text=True)
        if proc.returncode != 0:
            raise ConanException("manual cargo rustc C-API build failed (exit=%s)" % proc.returncode)
        target_base = env.get("CARGO_TARGET_DIR") or os.path.join(self.build_folder, "cargo-target")
        release_dir = os.path.join(target_base, target, "release") if target else os.path.join(target_base, "release")
        src_lib = os.path.join(release_dir, "libdolby_vision.a" if libtype == "staticlib" else "libdolby_vision.so")
        if not os.path.isfile(src_lib):
            raise ConanException("manual build artifact missing: %s" % src_lib)
        lib_dir = os.path.join(self.package_folder, "lib")
        inc_dir = os.path.join(self.package_folder, "include", "libdovi")
        pc_dir = os.path.join(lib_dir, "pkgconfig")
        for _d in (lib_dir, inc_dir, pc_dir):
            os.makedirs(_d, exist_ok=True)
        dst_lib = os.path.join(lib_dir, "libdovi.a" if libtype == "staticlib" else "libdovi.so")
        shutil.copyfile(src_lib, dst_lib)
        self.output.info("installed %s" % dst_lib)
        cbindgen_bin = getattr(self, "_cbindgen_bin", None) or os.path.join(
            env.get("CARGO_HOME") or os.path.join(self.build_folder, "cargo-home"), "bin", "cbindgen")
        header_out = os.path.join(self.build_folder, "rpu_parser.h")
        cb_cmd = [cbindgen_bin, "--config", "cbindgen.toml",
                  "--crate", "dolby_vision", "--output", header_out]
        self.output.info("RUN: " + " ".join(shlex.quote(p) for p in cb_cmd))
        proc_cb = subprocess.run(cb_cmd, cwd=crate_dir, env=env, text=True)
        if proc_cb.returncode != 0 or not os.path.isfile(header_out):
            raise ConanException("cbindgen header generation failed (exit=%s)" % proc_cb.returncode)
        shutil.copyfile(header_out, os.path.join(inc_dir, "rpu_parser.h"))
        self.output.info("installed include/libdovi/rpu_parser.h")
        pc_content = (
            "prefix=/\n"
            "exec_prefix=${prefix}\n"
            "libdir=${exec_prefix}/lib\n"
            "includedir=${prefix}/include\n"
            "\n"
            "Name: dovi\n"
            "Description: Dolby Vision metadata parsing and writing\n"
            "Version: 3.4.0\n"
            "Libs: -L${libdir} -ldovi\n"
            "Cflags: -I${includedir}\n"
        )
        with open(os.path.join(pc_dir, "dovi.pc"), "w", encoding="utf-8") as handle:
            handle.write(pc_content)
        self.output.info("installed lib/pkgconfig/dovi.pc")

    def _ensure_cargo_c(self, cargo, env, crate_dir):
        # cargo-c provides `cargo cbuild` / `cargo cinstall`.
        # Returns "cargo-c" or "manual". Never runs `cargo install cargo-c`
        # from source (round-2: it killed the true-machine SSH session).
        probe = subprocess.run(
            [cargo, "cbuild", "--version"],
            cwd=crate_dir, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )
        if probe.returncode == 0:
            self.output.info(f"cargo-c available: {(probe.stdout or '').strip()}")
            return "cargo-c"
        self.output.info(
            "cargo-c probe failed (exit=%s): %s"
            % (probe.returncode, ((probe.stdout or '').strip()[-1000:] or "<empty>"))
        )
        # Fast path first: prebuilt musl binary (no compilation, no /tmp
        # pressure). Fallback is a cargo-c-free manual build.
        if self._install_cargo_c_prebuilt(cargo, env, crate_dir):
            return "cargo-c"
        self.output.info(
            "prebuilt cargo-c unavailable, falling back to manual "
            "cargo-c-free C-API build (no cargo install)"
        )
        cbindgen = self._ensure_cbindgen(cargo, env, crate_dir)
        if cbindgen:
            self._cbindgen_bin = cbindgen
            return "manual"
        raise ConanException(
            "neither prebuilt cargo-c nor cbindgen is available; "
            "refusing to run `cargo install cargo-c` from source "
            "(killed the true-machine SSH session)"
        )

    @staticmethod
    def _parse_cargo_test_output(output):
        # cargo/libtest prints lines like:
        #   test result: ok. 42 passed; 0 failed; 0 ignored; ...
        passed = failed = ignored = 0
        suites = 0
        for line in output.splitlines():
            m = re.search(
                r"test result:\s+ok\.\s+(\d+)\s+passed;\s+(\d+)\s+failed;\s+(\d+)\s+ignored",
                line,
            )
            if m:
                suites += 1
                passed += int(m.group(1))
                failed += int(m.group(2))
                ignored += int(m.group(3))
                continue
            m2 = re.search(
                r"test result:\s+FAILED\.\s+(\d+)\s+passed;\s+(\d+)\s+failed",
                line,
            )
            if m2:
                suites += 1
                passed += int(m2.group(1))
                failed += int(m2.group(2))
        return suites, passed, failed, ignored

    def build(self):
        os.environ["SHELL"] = "/bin/sh"
        _tmp = self._pick_writable_tmpdir()
        if _tmp:
            os.environ["TMPDIR"] = _tmp
            os.environ["TMP"] = _tmp
            os.environ["TEMP"] = _tmp
            try:
                tempfile.tempdir = _tmp
            except Exception:
                pass
        cargo, rustc = self._toolchain()
        env, crate_dir, target, cc = self._cargo_env(cargo, rustc)
        if not os.path.isfile(os.path.join(crate_dir, "Cargo.toml")):
            raise ConanException(f"dolby_vision crate not found in {crate_dir}")
        capi_mode = self._ensure_cargo_c(cargo, env, crate_dir)
        self.output.info("C-API build mode: %s" % capi_mode)

        # ---- upstream test suite (must run before packaging) ----
        test_cmd = [cargo, "test", "--release", "--locked", "--all-features"]
        if target:
            test_cmd.extend(["--target", target])
        self.output.info("RUN upstream: " + " ".join(shlex.quote(p) for p in test_cmd))
        proc = subprocess.run(
            test_cmd, cwd=crate_dir, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )
        combined = proc.stdout or ""
        # Always echo the full suite log so CI/preflight keeps raw evidence.
        self.output.info("---- cargo test output begin ----")
        for line in combined.splitlines()[-200:]:
            self.output.info(line)
        self.output.info("---- cargo test output end ----")
        suites, passed, failed, ignored = self._parse_cargo_test_output(combined)
        discovered = passed + failed + ignored
        executed = passed + failed
        status = "passed" if proc.returncode == 0 and failed == 0 and executed > 0 else "failed"
        upstream = {
            "status": status,
            "framework": "cargo-test",
            "command": " ".join(shlex.quote(p) for p in test_cmd),
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": ignored,
        }
        if suites == 0:
            upstream["reason"] = (
                "No 'test result:' lines parsed from cargo test output; "
                f"exit={proc.returncode}. See full log above."
            )
            status = "failed"
            upstream["status"] = status
        msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False)
        print(msg, flush=True)
        self.output.info(msg)
        # Persist for test_package re-emit on Conan cache hit (build()
        # is skipped when the binary is cached, so the marker would
        # otherwise disappear and the evidence gate stays incomplete).
        try:
            with open(os.path.join(self.build_folder, "hmbs_upstream.json"),
                      "w", encoding="utf-8") as _fh:
                json.dump(upstream, _fh)
        except Exception:
            pass
        if proc.returncode != 0 or failed != 0 or executed == 0:
            raise ConanException(
                f"upstream cargo test failed (exit={proc.returncode}, "
                f"passed={passed}, failed={failed}, ignored={ignored})"
            )

        # ---- build + install the C library ----
        if capi_mode == "manual":
            self._build_manual_capi(env, crate_dir, target)
            return
        # cargo-c path (prebuilt or system-provided)
        libtype = "cdylib" if self.options.shared else "staticlib"
        build_cmd = [
            cargo, "cbuild", "--release", "--locked", "--all-features",
            f"--library-type={libtype}",
        ]
        if target:
            build_cmd.extend(["--target", target])
        build_cmd.extend(["--prefix", "/"])
        self.output.info("RUN: " + " ".join(shlex.quote(p) for p in build_cmd))
        proc_build = subprocess.run(build_cmd, cwd=crate_dir, env=env, text=True)
        if proc_build.returncode != 0:
            raise ConanException(f"cargo cbuild failed (exit={proc_build.returncode})")

        install_cmd = [
            cargo, "cinstall", "--release", "--locked", "--all-features",
            f"--library-type={libtype}",
        ]
        if target:
            install_cmd.extend(["--target", target])
        install_cmd.extend(["--prefix", "/", "--destdir", self.package_folder])
        self.output.info("RUN: " + " ".join(shlex.quote(p) for p in install_cmd))
        proc_install = subprocess.run(install_cmd, cwd=crate_dir, env=env, text=True)
        if proc_install.returncode != 0:
            raise ConanException(f"cargo cinstall failed (exit={proc_install.returncode})")

    def package(self):
        # Files are already staged into package_folder by `cargo cinstall`
        # (--prefix=/ --destdir=<package_folder>). Keep the license file
        # in the canonical location as well.
        crate_dir = os.path.join(self.source_folder, "dolby_vision")
        for lic in ("LICENSE", "LICENSE-MIT", "LICENSE-APACHE"):
            src = os.path.join(crate_dir, lic)
            if os.path.isfile(src):
                copy(self, lic, src=os.path.dirname(src),
                     dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
                break
        # Fallback: if cinstall staged under usr/ (some cargo-c versions
        # honor --prefix=/ by writing <destdir>/usr/...), relocate up.
        usr_dir = os.path.join(self.package_folder, "usr")
        if os.path.isdir(usr_dir) and not os.path.isdir(os.path.join(self.package_folder, "lib")):
            for entry in os.listdir(usr_dir):
                src = os.path.join(usr_dir, entry)
                dst = os.path.join(self.package_folder, entry)
                if os.path.exists(dst):
                    continue
                shutil.move(src, dst)
        # Carry the real in-build cargo-test result into the package so
        # test_package can re-emit HMBS_UPSTREAM_TEST_RESULT on cache hit.
        try:
            _src = os.path.join(self.build_folder, "hmbs_upstream.json")
            if os.path.isfile(_src):
                _dst_dir = os.path.join(self.package_folder, "res")
                os.makedirs(_dst_dir, exist_ok=True)
                shutil.copyfile(_src, os.path.join(_dst_dir, "hmbs_upstream.json"))
        except Exception:
            pass

    def package_info(self):
        self.cpp_info.libs = ["dovi"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("pkg_config_name", "dovi")
